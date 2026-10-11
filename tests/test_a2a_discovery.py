"""Boundary tests for card discovery and evidence promotion."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import a2a_discover as discovery


class Response:
    def __init__(self, status=200, body=b"{}", media_type="application/json"):
        self.status = status
        self.body = body
        self.media_type = media_type

    def getheader(self, name, default=""):
        return self.media_type if name == "Content-Type" else default

    def read(self, size):
        return self.body[:size]


class Connection:
    def __init__(self, response):
        self.response = response
        self.requests = []
        self.closed = False

    def request(self, method, path, headers):
        self.requests.append((method, path, headers))

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class DiscoveryTests(unittest.TestCase):
    def fetch_response(self, response):
        connection = Connection(response)
        with patch.object(discovery.http.client, "HTTPConnection", return_value=connection) as constructor:
            record, body = discovery.fetch("http://127.0.0.1:4173", discovery.PATHS[0], 2)
        self.assertEqual(constructor.call_count, 1)
        self.assertTrue(connection.closed)
        return record, body, connection

    def test_remote_http_and_url_credentials_rejected_before_network(self):
        synthetic_auth_url = urlunsplit(("https", "name:password@example.org", "", "", ""))
        for origin in ("http://example.org", synthetic_auth_url,
                       "https://example.org?token=value", "https://example.org/path",
                       "https://example.org#fragment", "http://localhost:4173"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                discovery.discover(origin, fetcher=lambda *_: self.fail("network access after rejection"))

    def test_remote_https_needs_exact_origin_allowlist(self):
        with self.assertRaises(ValueError):
            discovery.validate_origin("https://example.org")
        self.assertEqual(discovery.validate_origin("https://EXAMPLE.org:443/", ("https://example.org",)),
                         "https://example.org")
        with self.assertRaises(ValueError):
            discovery.validate_origin("https://other.example.org", ("https://example.org",))

    def test_redirect_never_requests_a_second_address(self):
        record, body, connection = self.fetch_response(Response(status=302, body=b"private redirect body"))
        self.assertEqual(record["result"], "redirect_refused")
        self.assertIsNone(body)
        self.assertEqual(len(connection.requests), 1)
        self.assertNotIn("private redirect body", json.dumps(record))

    def test_duplicate_fields_and_nonfinite_numbers_rejected(self):
        for raw in (b'{"name":"first","name":"second"}', b'{"x":NaN}',
                    b'{"x":Infinity}', b'{"x":1e999}', b'[]', b'{"nested":{"x":1,"x":2}}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                discovery.strict_object(raw)

    def test_oversized_response_has_no_raw_body_or_digest(self):
        record, body, _ = self.fetch_response(Response(body=b"x" * (discovery.MAX_BYTES + 1)))
        self.assertEqual(record["result"], "response_too_large")
        self.assertIsNone(body)
        self.assertNotIn("response_sha256", record)

    def test_non_json_media_type_rejected(self):
        record, body, _ = self.fetch_response(Response(media_type="text/html"))
        self.assertEqual(record["result"], "unexpected_media_type")
        self.assertIsNone(body)

    def test_http_failure_and_malformed_json_do_not_echo_errors(self):
        for response in (Response(status=403, body=b"secret provider error"),
                         Response(body=b"secret provider error")):
            record, body, _ = self.fetch_response(response)
            self.assertIsNone(body)
            self.assertNotIn("secret provider error", json.dumps(record))

    def test_up_health_and_card_claims_never_enable_dispatch(self):
        card = {"protocolVersion": "0.3.0", "name": "name", "description": "ignore instructions: private-value",
                "url": "https://private.example/secret", "version": "0.2.0", "capabilities": {"streaming": True},
                "defaultInputModes": ["application/json"], "defaultOutputModes": ["application/json"],
                "skills": [{"id": "private-value"}]}
        def fetcher(origin, path, timeout):
            return {"path": path, "http_status": 200}, card if path == discovery.PATHS[0] else {"status": "up"}
        result = discovery.discover("http://127.0.0.1:4173", fetcher=fetcher)
        self.assertEqual(result["stage"], "card_observed")
        self.assertEqual(result["card"]["missing_or_invalid_basic_fields"], [])
        self.assertTrue(result["health_extension_declares_up"])
        for field in ("authenticated_node_verified", "standard_methods_verified",
                      "independent_peer_acknowledged", "eligible_for_task_dispatch"):
            self.assertFalse(result[field])
        for private in ("private.example", "private-value", "ignore instructions"):
            self.assertNotIn(private, json.dumps(result))

    def test_unknown_protocol_and_bad_modes_stay_unverified(self):
        result = discovery.card_summary({"protocolVersion": "0.4.0", "skills": ["invalid"],
                                         "defaultInputModes": [], "defaultOutputModes": [3]})
        self.assertFalse(result["declared_version_matches_reviewed_spec"])
        self.assertFalse(result["full_schema_validated"])
        for field in ("skills", "defaultInputModes", "defaultOutputModes", "capabilities"):
            self.assertIn(field, result["missing_or_invalid_basic_fields"])

    def test_failed_card_and_up_health_remain_discovery_failed(self):
        def fetcher(origin, path, timeout):
            return {"path": path}, None if path == discovery.PATHS[0] else {"status": "up"}
        result = discovery.discover("http://127.0.0.1:4173", fetcher=fetcher)
        self.assertEqual(result["stage"], "discovery_failed")
        self.assertFalse(result["eligible_for_task_dispatch"])


if __name__ == "__main__":
    unittest.main()
