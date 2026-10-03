#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Authenticated A2A JSON-RPC message exchange primitives."""

import json
import sys
import tempfile
import uuid
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import a2a_hmac as M


def rpc_body(method, params):
    request = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}
    return json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class Seat:
    def __init__(self, seat_id, key_id, key, replay_database):
        self.seat_id = seat_id
        self.key_id = key_id
        self.key = key
        self.replay_cache = M.ReplayCache(replay_database)

    def send(self, recipient, method, params):
        body = rpc_body(method, params)
        envelope = M.build_envelope(self.seat_id, recipient, body, self.key, self.key_id)
        return envelope, body

    def receive(self, sender, envelope, body):
        ok, reason = M.verify_envelope(
            envelope,
            self.key,
            self.key_id,
            sender,
            self.seat_id,
            body,
            self.replay_cache,
        )
        if not ok:
            return ok, reason, None
        return ok, reason, json.loads(body.decode("utf-8"))


def demo():
    key = __import__("secrets").token_bytes(M.KEY_BYTES)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        a = Seat("cairn-dsh", "opl-a2a-2026q4", key, root / "a.sqlite3")
        b = Seat("workbuddy-hy4", "opl-a2a-2026q4", key, root / "b.sqlite3")

        envelope, body = a.send(b.seat_id, "seat/hello", {"msg": "强制 A2A 使用"})
        ok, reason, rpc = b.receive(a.seat_id, envelope, body)
        print("A→B 验证 = %s（%s）method=%s" % (ok, reason, rpc.get("method") if rpc else None))

        replay_ok, replay_reason, _ = b.receive(a.seat_id, envelope, body)
        print("重放拒绝 = %s（%s）" % (replay_ok, replay_reason))

        tampered_envelope, _ = a.send(b.seat_id, "seat/hello", {"msg": "x"})
        tampered_ok, tampered_reason, _ = b.receive(a.seat_id, tampered_envelope, b"tampered-body")
        print("篡改拒绝 = %s（%s）" % (tampered_ok, tampered_reason))

        response_envelope, response_body = b.send(a.seat_id, "seat/ack", {"ok": True})
        response_ok, response_reason, response_rpc = a.receive(b.seat_id, response_envelope, response_body)
        print("B→A 应答 = %s（%s）method=%s" % (
            response_ok,
            response_reason,
            response_rpc.get("method") if response_rpc else None,
        ))

    passed = (
        ok
        and rpc.get("method") == "seat/hello"
        and not replay_ok
        and replay_reason == "重复 nonce"
        and not tampered_ok
        and tampered_reason == "正文摘要不匹配"
        and response_ok
        and response_rpc.get("method") == "seat/ack"
    )
    print("★ VERDICT=" + ("PASS" if passed else "BAD"))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(demo())
