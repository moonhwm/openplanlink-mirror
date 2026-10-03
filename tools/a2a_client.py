#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Send one authenticated JSON-RPC request to the local A2A node."""

import base64
import http.client
import json
import os
import sys
import uuid
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import a2a_hmac as M

NODE_HOST = os.environ.get("OPL_A2A_NODE_HOST", "127.0.0.1")
NODE_PORT = int(os.environ.get("OPL_A2A_NODE_PORT", "4173"))
KEY_FILE = Path(os.environ.get("OPL_A2A_HMAC_KEY_FILE", Path.home() / ".a2a-hmac-key.bin"))
KEY_ID = os.environ.get("OPL_A2A_HMAC_KEY_ID", "opl-a2a-2026q4")
SENDER = os.environ.get("OPL_A2A_SENDER_ID", "cairn-dsh")
NODE_SEAT = "a2a-node-local"
MAX_RESPONSE_BYTES = 1_048_576
REPLAY_DB = Path(os.environ.get("OPL_A2A_CLIENT_REPLAY_DB", Path.home() / f".a2a-client-{SENDER}-replay.sqlite3"))


def main():
    key = KEY_FILE.read_bytes()
    replay_cache = M.ReplayCache(REPLAY_DB)
    request_id = str(uuid.uuid4())
    rpc = {"jsonrpc": "2.0", "id": request_id, "method": "seat/hello", "params": {"msg": "强制 A2A 使用"}}
    body = json.dumps(rpc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    envelope = M.build_envelope(SENDER, NODE_SEAT, body, key, KEY_ID)
    payload = {"envelope": envelope, "body_b64": base64.b64encode(body).decode("ascii")}

    connection = http.client.HTTPConnection(NODE_HOST, NODE_PORT, timeout=10)
    try:
        connection.request("POST", "/", body=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        status = response.status
        if response.length is not None and response.length > MAX_RESPONSE_BYTES:
            print("节点响应超过上限")
            return 1
        response_data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(response_data) > MAX_RESPONSE_BYTES:
            print("节点响应超过上限")
            return 1
    except (OSError, http.client.HTTPException):
        print("节点连接失败")
        return 1
    finally:
        connection.close()
    try:
        data = json.loads(response_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        print("节点响应格式非法")
        return 1
    if status != 200 or not isinstance(data, dict) or "envelope" not in data:
        print("节点返回错误")
        return 1

    response_body = base64.b64decode(data["body_b64"], validate=True)
    ok, reason = M.verify_envelope(
        data["envelope"], key, KEY_ID, NODE_SEAT, SENDER, response_body, replay_cache
    )
    rpc_response = json.loads(response_body.decode("utf-8"))
    ok = (
        ok
        and rpc_response.get("jsonrpc") == "2.0"
        and rpc_response.get("id") == request_id
        and "error" not in rpc_response
        and isinstance(rpc_response.get("result"), dict)
        and rpc_response["result"].get("echo_method") == "seat/hello"
    )
    print("节点响应验证 = %s（%s）" % (ok, reason))
    print("★ VERDICT=" + ("PASS" if ok else "BAD"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
