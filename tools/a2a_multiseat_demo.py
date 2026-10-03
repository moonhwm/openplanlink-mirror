#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Exchange authenticated messages between two seats through the local node."""

import base64
import http.client
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import a2a_hmac as M

KEY_FILE = Path(os.environ.get("OPL_A2A_HMAC_KEY_FILE", Path.home() / ".a2a-hmac-key.bin"))
KEY_ID = os.environ.get("OPL_A2A_HMAC_KEY_ID", "opl-a2a-2026q4")
NODE_HOST = os.environ.get("OPL_A2A_NODE_HOST", "127.0.0.1")
NODE_PORT = int(os.environ.get("OPL_A2A_NODE_PORT", "4173"))
NODE_SEAT = "a2a-node-local"
MAX_RESPONSE_BYTES = 1_048_576
A, B = "cairn-dsh", "workbuddy-hy4"


def request_body(method, params):
    request = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}
    return request, json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def post(key, sender, recipient, method, params, response_cache):
    request, body = request_body(method, params)
    envelope = M.build_envelope(sender, recipient, body, key, KEY_ID)
    payload = {"envelope": envelope, "body_b64": base64.b64encode(body).decode("ascii")}
    connection = http.client.HTTPConnection(NODE_HOST, NODE_PORT, timeout=10)
    try:
        connection.request("POST", "/", body=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        status = response.status
        if response.length is not None and response.length > MAX_RESPONSE_BYTES:
            return status, False, {"error": "响应超过上限"}
        response_data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(response_data) > MAX_RESPONSE_BYTES:
            return status, False, {"error": "响应超过上限"}
    except (OSError, http.client.HTTPException):
        return 0, False, {"error": "节点连接失败"}
    finally:
        connection.close()
    try:
        data = json.loads(response_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, False, {"error": "响应格式非法"}
    if status != 200 or not isinstance(data, dict) or "envelope" not in data:
        return status, False, data
    response_body = base64.b64decode(data["body_b64"], validate=True)
    ok, _ = M.verify_envelope(
        data["envelope"], key, KEY_ID, NODE_SEAT, sender, response_body, response_cache
    )
    rpc = json.loads(response_body.decode("utf-8"))
    ok = (
        ok
        and rpc.get("jsonrpc") == "2.0"
        and rpc.get("id") == request["id"]
        and "error" not in rpc
        and isinstance(rpc.get("result"), dict)
    )
    return status, ok, rpc


def consume_message(key, recipient, sender, message_id, messages, inbound_cache, response_cache, method, params):
    message = next(
        (item for item in messages if item.get("envelope", {}).get("nonce") == message_id),
        None,
    )
    if message is None:
        return False, False
    try:
        body = base64.b64decode(message["body_b64"], validate=True)
        delivered_ok, _ = M.verify_envelope(
            message["envelope"], key, KEY_ID, sender, recipient, body, inbound_cache
        )
        rpc = json.loads(body.decode("utf-8"))
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return False, False
    delivered_ok = (
        delivered_ok
        and rpc.get("jsonrpc") == "2.0"
        and rpc.get("method") == method
        and rpc.get("params") == params
    )
    if not delivered_ok:
        return False, False
    _, ack_ok, ack = post(
        key,
        recipient,
        NODE_SEAT,
        "mailbox/ack",
        {"message_ids": [message_id]},
        response_cache,
    )
    return True, ack_ok and ack.get("result", {}).get("acknowledged") == 1


def main():
    key = KEY_FILE.read_bytes()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        response_a = M.ReplayCache(root / "response-a.sqlite3")
        response_b = M.ReplayCache(root / "response-b.sqlite3")
        inbound_a = M.ReplayCache(root / "inbound-a.sqlite3")
        inbound_b = M.ReplayCache(root / "inbound-b.sqlite3")

        forward_params = {"msg": "A 向 B 问好"}
        code, ack_ok, ack = post(key, A, B, "seat/hello", forward_params, response_a)
        queued = ack.get("result", {}).get("queued") is True
        message_id = ack.get("result", {}).get("message_id")
        print("A→B 投递 code=%s 回执验签=%s queued=%s" % (code, ack_ok, queued))

        code, mailbox_ok, mailbox_rpc = post(key, B, NODE_SEAT, "mailbox/get", {}, response_b)
        messages = mailbox_rpc.get("result", {}).get("messages", []) if mailbox_ok else []
        delivered_ok, mailbox_ack_ok = consume_message(
            key, B, A, message_id, messages, inbound_b, response_b, "seat/hello", forward_params
        )
        print("B 认证取信 code=%s 回执验签=%s 消息验签=%s 确认=%s" % (
            code, mailbox_ok, delivered_ok, mailbox_ack_ok
        ))

        reverse_params = {"ok": True}
        code, reverse_ack_ok, reverse_ack = post(key, B, A, "seat/ack", reverse_params, response_b)
        reverse_queued = reverse_ack.get("result", {}).get("queued") is True
        reverse_message_id = reverse_ack.get("result", {}).get("message_id")
        print("B→A 投递 code=%s 回执验签=%s queued=%s" % (code, reverse_ack_ok, reverse_queued))

        code, reverse_mailbox_ok, reverse_mailbox_rpc = post(key, A, NODE_SEAT, "mailbox/get", {}, response_a)
        reverse_messages = reverse_mailbox_rpc.get("result", {}).get("messages", []) if reverse_mailbox_ok else []
        reverse_delivered_ok, reverse_mailbox_ack_ok = consume_message(
            key,
            A,
            B,
            reverse_message_id,
            reverse_messages,
            inbound_a,
            response_a,
            "seat/ack",
            reverse_params,
        )
        print("A 认证取信 code=%s 回执验签=%s 消息验签=%s 确认=%s" % (
            code, reverse_mailbox_ok, reverse_delivered_ok, reverse_mailbox_ack_ok
        ))

    passed = all((ack_ok, queued, mailbox_ok, delivered_ok, mailbox_ack_ok,
                  reverse_ack_ok, reverse_queued, reverse_mailbox_ok,
                  reverse_delivered_ok, reverse_mailbox_ack_ok))
    print("★ VERDICT=" + ("PASS" if passed else "BAD"))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
