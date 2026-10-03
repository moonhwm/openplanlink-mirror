#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Integration tests for the repository A2A node on an isolated local port."""

import base64
import http.client
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import a2a_hmac as M

KEY_ID = "opl-a2a-2026q4"
NODE_SEAT = "a2a-node-local"
A = "cairn-dsh"
B = "workbuddy-hy4"


class A2ANodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.key = os.urandom(M.KEY_BYTES)
        cls.key_file = cls.root / "key.bin"
        cls.key_file.write_bytes(cls.key)
        cls.state_db = cls.root / "node-state.sqlite3"
        connection = sqlite3.connect(cls.state_db)
        try:
            connection.execute(
                "CREATE TABLE mailbox_messages ("
                "message_id TEXT PRIMARY KEY, recipient TEXT NOT NULL, "
                "sender TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL, "
                "expires_at REAL)"
            )
            connection.execute(
                "INSERT INTO mailbox_messages "
                "(message_id, recipient, sender, payload, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, NULL)",
                ("0" * 32, B, A, "{}", 0),
            )
            connection.commit()
        finally:
            connection.close()
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            cls.port = probe.getsockname()[1]
        try:
            cls._start_server()
            connection = sqlite3.connect(cls.state_db)
            try:
                cls.migrated_expiry = connection.execute(
                    "SELECT expires_at FROM mailbox_messages WHERE message_id = ?",
                    ("0" * 32,),
                ).fetchone()[0]
            finally:
                connection.close()
        except Exception:
            cls._stop_server()
            cls.temporary.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls._stop_server()
        cls.temporary.cleanup()

    @classmethod
    def _start_server(cls):
        environment = os.environ.copy()
        environment.update({
            "OPL_A2A_NODE_HOST": "127.0.0.1",
            "OPL_A2A_NODE_PORT": str(cls.port),
            "OPL_A2A_HMAC_KEY_FILE": str(cls.key_file),
            "OPL_A2A_HMAC_KEY_ID": KEY_ID,
            "OPL_A2A_STATE_DB": str(cls.state_db),
        })
        cls.process = subprocess.Popen(
            [sys.executable, "-B", str(TOOLS_DIR / "a2a_node.py")],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if cls.process.poll() is not None:
                raise RuntimeError(cls._stop_server())
            try:
                connection = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=0.2)
                connection.request("GET", "/")
                response = connection.getresponse()
                response.read()
                connection.close()
                if response.status == 200:
                    return
            except OSError:
                time.sleep(0.05)
        error = cls._stop_server()
        raise RuntimeError(error or "A2A test node did not start")

    @classmethod
    def _stop_server(cls):
        process = getattr(cls, "process", None)
        if process is None:
            return ""
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        error = ""
        if process.stderr is not None and not process.stderr.closed:
            error = process.stderr.read()
            process.stderr.close()
        cls.process = None
        return error

    def _body(self, method, params=None):
        request = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params or {}}
        return request, json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _post(self, envelope, body):
        payload = {"envelope": envelope, "body_b64": base64.b64encode(body).decode("ascii")}
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.request("POST", "/", body=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        status = response.status
        connection.close()
        return status, data

    def _call(self, sender, recipient, method, params=None):
        request, body = self._body(method, params)
        envelope = M.build_envelope(sender, recipient, body, self.key, KEY_ID)
        status, data = self._post(envelope, body)
        return request, envelope, body, status, data

    def _verify_response(self, data, recipient, request_id, cache_name):
        body = base64.b64decode(data["body_b64"], validate=True)
        cache = M.ReplayCache(self.root / cache_name)
        ok, reason = M.verify_envelope(
            data["envelope"], self.key, KEY_ID, NODE_SEAT, recipient, body, cache
        )
        self.assertTrue(ok, reason)
        response = json.loads(body.decode("utf-8"))
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], request_id)
        self.assertNotIn("error", response)
        return response

    def test_migration_backfills_null_expiry(self):
        self.assertEqual(self.migrated_expiry, M.DEFAULT_WINDOW)

    def test_cli_programs(self):
        environment = os.environ.copy()
        environment.update({
            "OPL_A2A_NODE_HOST": "127.0.0.1",
            "OPL_A2A_NODE_PORT": str(self.port),
            "OPL_A2A_HMAC_KEY_FILE": str(self.key_file),
            "OPL_A2A_HMAC_KEY_ID": KEY_ID,
            "OPL_A2A_CLIENT_REPLAY_DB": str(self.root / "client-response.sqlite3"),
        })
        for script in ("a2a_client.py", "a2a_multiseat_demo.py"):
            completed = subprocess.run(
                [sys.executable, "-B", str(TOOLS_DIR / script)],
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode(errors="replace"))
            self.assertIn(b"VERDICT=PASS", completed.stdout)

    def test_echo_response_is_authenticated(self):
        request, _, _, status, data = self._call(A, NODE_SEAT, "seat/hello", {"msg": "hi"})
        self.assertEqual(status, 200)
        response = self._verify_response(data, A, request["id"], "echo-response.sqlite3")
        self.assertEqual(response["result"]["echo_method"], "seat/hello")

    def test_expired_mailbox_message_is_removed(self):
        _, envelope, _, status, _ = self._call(A, B, "seat/hello", {"msg": "expires"})
        self.assertEqual(status, 200)
        connection = sqlite3.connect(self.state_db)
        try:
            connection.execute(
                "UPDATE mailbox_messages SET expires_at = 0 WHERE message_id = ?",
                (envelope["nonce"],),
            )
            connection.commit()
        finally:
            connection.close()
        request, _, _, status, data = self._call(B, NODE_SEAT, "mailbox/get")
        self.assertEqual(status, 200)
        response = self._verify_response(data, B, request["id"], "expired-response.sqlite3")
        self.assertEqual(response["result"]["messages"], [])

    def test_invalid_input_does_not_leave_transaction_open(self):
        status, data = self._post("not-an-envelope", b"x")
        self.assertEqual(status, 400)
        self.assertEqual(data["error"]["message"], "解析错误")

        invalid_body = b"not-json"
        envelope = M.build_envelope(A, NODE_SEAT, invalid_body, self.key, KEY_ID)
        status, data = self._post(envelope, invalid_body)
        self.assertEqual(status, 400)
        self.assertEqual(data["error"]["message"], "解析错误")

        nonfinite_body = b'{"jsonrpc":"2.0","id":"x","method":"seat/hello","params":{"x":NaN}}'
        envelope = M.build_envelope(A, NODE_SEAT, nonfinite_body, self.key, KEY_ID)
        status, data = self._post(envelope, nonfinite_body)
        self.assertEqual(status, 400)
        self.assertEqual(data["error"]["message"], "解析错误")

        duplicate_body = b'{"jsonrpc":"2.0","id":"x","method":"seat/hello","method":"seat/ack","params":{}}'
        envelope = M.build_envelope(A, NODE_SEAT, duplicate_body, self.key, KEY_ID)
        status, data = self._post(envelope, duplicate_body)
        self.assertEqual(status, 400)
        self.assertEqual(data["error"]["message"], "解析错误")

        _, _, _, status, _ = self._call(A, NODE_SEAT, "seat/hello")
        self.assertEqual(status, 200)

    def test_replay_is_rejected(self):
        _, envelope, body, status, _ = self._call(A, NODE_SEAT, "seat/hello")
        self.assertEqual(status, 200)
        status, data = self._post(envelope, body)
        self.assertEqual(status, 401)
        self.assertEqual(data["error"]["message"], "重复 nonce")

    def test_tampered_body_is_rejected(self):
        _, body = self._body("seat/hello")
        envelope = M.build_envelope(A, NODE_SEAT, body, self.key, KEY_ID)
        status, data = self._post(envelope, b"tampered")
        self.assertEqual(status, 401)
        self.assertEqual(data["error"]["message"], "正文摘要不匹配")

    def test_unknown_seats_are_rejected(self):
        _, body = self._body("seat/hello")
        unknown_sender = M.build_envelope("unknown-seat", NODE_SEAT, body, self.key, KEY_ID)
        self.assertEqual(self._post(unknown_sender, body)[0], 401)
        unknown_recipient = M.build_envelope(A, "unknown-seat", body, self.key, KEY_ID)
        self.assertEqual(self._post(unknown_recipient, body)[0], 404)

    def test_mailbox_persists_and_requires_ack(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.request("GET", f"/mailbox/{B}")
        response = connection.getresponse()
        response.read()
        connection.close()
        self.assertEqual(response.status, 404)

        queue_request, queue_envelope, queue_body, status, queue_data = self._call(
            A, B, "seat/hello", {"msg": "queued"}
        )
        self.assertEqual(status, 200)
        queue_response = self._verify_response(queue_data, A, queue_request["id"], "response-a.sqlite3")
        self.assertTrue(queue_response["result"]["queued"])
        message_id = queue_response["result"]["message_id"]
        self.assertEqual(message_id, queue_envelope["nonce"])

        self._stop_server()
        self._start_server()

        mailbox_request, _, _, status, mailbox_data = self._call(B, NODE_SEAT, "mailbox/get")
        self.assertEqual(status, 200)
        mailbox_response = self._verify_response(mailbox_data, B, mailbox_request["id"], "response-b.sqlite3")
        message = next(
            item for item in mailbox_response["result"]["messages"]
            if item["envelope"]["nonce"] == message_id
        )
        delivered_body = base64.b64decode(message["body_b64"], validate=True)
        inbound_cache = M.ReplayCache(self.root / "mailbox-inbound.sqlite3")
        ok, reason = M.verify_envelope(
            message["envelope"], self.key, KEY_ID, A, B, delivered_body, inbound_cache
        )
        self.assertTrue(ok, reason)
        self.assertEqual(delivered_body, queue_body)

        second_request, _, _, status, second_data = self._call(B, NODE_SEAT, "mailbox/get")
        self.assertEqual(status, 200)
        second_response = self._verify_response(second_data, B, second_request["id"], "response-b.sqlite3")
        second_ids = {
            item["envelope"]["nonce"] for item in second_response["result"]["messages"]
        }
        self.assertIn(message_id, second_ids)

        ack_request, _, _, status, ack_data = self._call(
            B, NODE_SEAT, "mailbox/ack", {"message_ids": [message_id]}
        )
        self.assertEqual(status, 200)
        ack_response = self._verify_response(ack_data, B, ack_request["id"], "response-b.sqlite3")
        self.assertEqual(ack_response["result"]["acknowledged"], 1)

        self._stop_server()
        self._start_server()
        empty_request, _, _, status, empty_data = self._call(B, NODE_SEAT, "mailbox/get")
        self.assertEqual(status, 200)
        empty_response = self._verify_response(empty_data, B, empty_request["id"], "response-b.sqlite3")
        self.assertEqual(empty_response["result"]["messages"], [])

    def test_replay_persists_across_restart(self):
        _, envelope, body, status, _ = self._call(A, NODE_SEAT, "seat/hello")
        self.assertEqual(status, 200)
        self._stop_server()
        self._start_server()
        status, data = self._post(envelope, body)
        self.assertEqual(status, 401)
        self.assertEqual(data["error"]["message"], "重复 nonce")


if __name__ == "__main__":
    unittest.main(verbosity=2)
