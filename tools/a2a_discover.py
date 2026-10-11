"""Observe explicitly configured A2A cards without promoting unverified claims."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import json
import math
from pathlib import Path
import re
import ssl
from urllib.parse import urlsplit, urlunsplit

MAX_BYTES = 65_536
PATHS = ("/.well-known/agent-card.json", "/health")
VERSION = re.compile(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\Z")
TEXT_FIELDS = ("protocolVersion", "name", "description", "url", "version")
LIST_FIELDS = ("defaultInputModes", "defaultOutputModes", "skills")


def canonical_origin(value: str) -> str:
    """Accept an origin only; no authentication or other request data in a URL."""
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise ValueError("invalid_origin") from None
    if (parts.scheme not in ("http", "https") or not parts.hostname or
            parts.username is not None or parts.password is not None or
            parts.path not in ("", "/") or parts.query or parts.fragment or
            (port is not None and not 1 <= port <= 65535) or
            any(ord(char) <= 32 or ord(char) == 127 for char in value)):
        raise ValueError("invalid_origin")
    host = parts.hostname.lower()
    # Only literal loopback HTTP is accepted, so DNS cannot widen this exception.
    if parts.scheme == "http" and host not in ("127.0.0.1", "::1"):
        raise ValueError("remote_http_refused")
    host = f"[{host}]" if ":" in host else host
    default_port = 443 if parts.scheme == "https" else 80
    authority = host if port is None or port == default_port else f"{host}:{port}"
    return urlunsplit((parts.scheme, authority, "", "", ""))


def validate_origin(value: str, allowed_origins: tuple[str, ...] = ()) -> str:
    origin = canonical_origin(value)
    parts = urlsplit(origin)
    if parts.hostname not in ("127.0.0.1", "::1"):
        allowed = {canonical_origin(item) for item in allowed_origins}
        if origin not in allowed:
            raise ValueError("origin_not_allowlisted")
    return origin


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite_json_number")


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite_json_number")
    return number


def strict_object(raw: bytes) -> dict:
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                       parse_constant=reject_constant, parse_float=finite_float)
    if not isinstance(value, dict):
        raise ValueError("json_object_required")
    return value


def fetch(origin: str, path: str, timeout: float) -> tuple[dict, dict | None]:
    parts = urlsplit(origin)
    connection = (http.client.HTTPSConnection(parts.hostname, parts.port, timeout=timeout,
                  context=ssl.create_default_context()) if parts.scheme == "https"
                  else http.client.HTTPConnection(parts.hostname, parts.port, timeout=timeout))
    record = {"path": path, "http_status": None, "json_object_verified": False}
    try:
        connection.request("GET", path, headers={"Accept": "application/json"})
        response = connection.getresponse()
        record["http_status"] = response.status
        if response.status != 200:
            record["result"] = "redirect_refused" if 300 <= response.status < 400 else "http_failure"
            return record, None
        if response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            record["result"] = "unexpected_media_type"
            return record, None
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            record["result"] = "response_too_large"
            return record, None
        body = strict_object(raw)
        record.update(result="json_object_observed", response_bytes=len(raw),
                      response_sha256=hashlib.sha256(raw).hexdigest(), json_object_verified=True)
        return record, body
    except (OSError, ValueError, RecursionError, http.client.HTTPException) as error:
        record.update(result="request_or_parse_failure", error_type=type(error).__name__)
        return record, None
    finally:
        connection.close()


def card_summary(card: dict) -> dict:
    """Return finite facts only; descriptive fields and service URLs stay private."""
    invalid = [field for field in TEXT_FIELDS
               if not isinstance(card.get(field), str) or not card[field].strip()]
    invalid += [field for field in LIST_FIELDS if not isinstance(card.get(field), list)]
    if not isinstance(card.get("capabilities"), dict):
        invalid.append("capabilities")
    for field in ("defaultInputModes", "defaultOutputModes"):
        if isinstance(card.get(field), list) and (
                not card[field] or any(not isinstance(item, str) or not item.strip() for item in card[field])):
            invalid.append(field)
    if isinstance(card.get("skills"), list) and any(not isinstance(item, dict) for item in card["skills"]):
        invalid.append("skills")
    version = card.get("protocolVersion")
    version = version if isinstance(version, str) and VERSION.fullmatch(version) else None
    capabilities = card.get("capabilities")
    return {
        "declared_protocol_version": version,
        "declared_version_matches_reviewed_spec": version == "0.3.0",
        "missing_or_invalid_basic_fields": sorted(set(invalid)),
        "basic_fields_checked": True,
        "full_schema_validated": False,
        "skill_count_declared": len(card["skills"]) if isinstance(card.get("skills"), list) else None,
        "streaming_declared": capabilities.get("streaming") is True if isinstance(capabilities, dict) else False,
        "security_schemes_declared_count": len(card["securitySchemes"])
            if isinstance(card.get("securitySchemes"), dict) else None,
        "card_signature_verified": False,
        "descriptive_text_or_advertised_urls_returned": False,
    }


def discover(origin: str, allowed_origins: tuple[str, ...] = (), timeout: float = 5,
             ttl_seconds: int = 90, fetcher=fetch) -> dict:
    origin = validate_origin(origin, allowed_origins)
    if not 0 < timeout <= 10 or not 1 <= ttl_seconds <= 300:
        raise ValueError("invalid_probe_bounds")
    observed = datetime.now(timezone.utc)
    probes = []
    card = None
    health = None
    for path in PATHS:
        probe, body = fetcher(origin, path, timeout)
        probes.append(probe)
        if path == PATHS[0]:
            card = body
        else:
            health = body
    result = {
        "schema": "openplanlink.a2a-discovery/1", "spec_id": "012-a2a-discovery",
        "origin": origin, "observed_at_utc": observed.isoformat(),
        "observation_expires_at_utc": (observed + timedelta(seconds=ttl_seconds)).isoformat(),
        "stage": "card_observed" if card is not None else "discovery_failed",
        "probes": probes,
        "health_extension_declares_up": isinstance(health, dict) and health.get("status") in ("up", "alive"),
        "health_path_is_project_extension": True,
        "authenticated_node_verified": False, "standard_methods_verified": False,
        "independent_peer_acknowledged": False, "eligible_for_task_dispatch": False,
        "process_started_or_modified": False, "routes_modified": False,
        "credentials_read_or_sent": False,
    }
    if card is not None:
        result["card"] = card_summary(card)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="http://127.0.0.1:4173")
    parser.add_argument("--allow-origin", action="append", default=[])
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--ttl-seconds", type=int, default=90)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = discover(args.origin, tuple(args.allow_origin), args.timeout, args.ttl_seconds)
        data = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        with args.output.open("xb") as output:
            output.write(data)
        if args.output.read_bytes() != data:
            raise OSError("output_readback_differs")
        print(json.dumps({"stage": result["stage"], "card_observed": "card" in result,
                          "authenticated_node_verified": False, "eligible_for_task_dispatch": False}))
        return 0 if result["stage"] == "card_observed" else 1
    except (OSError, ValueError) as error:
        print(json.dumps({"result": "failed", "error_type": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
