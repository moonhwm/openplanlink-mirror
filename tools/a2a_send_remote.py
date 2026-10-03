#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Send one authenticated message/send request to a remote A2A node."""

import base64
import http.client
import json
import os
import sqlite3
import sys
import uuid
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import a2a_hmac as M

sys.stdout.reconfigure(encoding="utf-8")

REMOTE_HOST = os.environ.get("OPL_A2A_REMOTE_HOST", "120.46.86.165")
REMOTE_PORT = os.environ.get("OPL_A2A_REMOTE_PORT", "80")
REMOTE_PATH = os.environ.get("OPL_A2A_REMOTE_PATH", "/functions/v1/app")
REMOTE_SEAT = os.environ.get("OPL_A2A_REMOTE_SEAT_ID")
KEY_FILE = os.environ.get("OPL_A2A_REMOTE_HMAC_KEY_FILE")
KEY_ID = os.environ.get("OPL_A2A_REMOTE_KEY_ID")
SENDER = os.environ.get("OPL_A2A_SENDER_ID", "cairn-dsh")
REPLAY_DB = Path(os.environ.get(
    "OPL_A2A_REMOTE_REPLAY_DB",
    Path.home() / f".a2a-remote-{SENDER}-replay.sqlite3",
))
MAX_RESPONSE_BYTES = 1_048_576


def _reject_json_constant(value):
    raise ValueError(f"非法 JSON 常量: {value}")


def _unique_json_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("JSON 对象包含重复键")
        value[key] = item
    return value


def _strict_json_loads(value):
    return json.loads(
        value,
        parse_constant=_reject_json_constant,
        object_pairs_hook=_unique_json_object,
    )


def main():
    if not REMOTE_SEAT or not KEY_FILE or not KEY_ID:
        print("缺少远端席位或双边认证配置")
        return 1
    try:
        remote_port = int(REMOTE_PORT)
        if not 1 <= remote_port <= 65535:
            raise ValueError("远端端口超出范围")
        key = Path(KEY_FILE).read_bytes()
        replay_cache = M.ReplayCache(REPLAY_DB)
        request_id = str(uuid.uuid4())
        rpc = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"kind": "text", "text": "来自 cairn-dsh（石敢当）的认证握手"}],
                }
            },
        }
        body = json.dumps(
            rpc, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        envelope = M.build_envelope(SENDER, REMOTE_SEAT, body, key, KEY_ID)
        payload = json.dumps({
            "envelope": envelope,
            "body_b64": base64.b64encode(body).decode("ascii"),
        }, separators=(",", ":")).encode("utf-8")
    except (OSError, ValueError, TypeError, sqlite3.Error):
        print("认证材料或配置不可用")
        return 1

    connection = http.client.HTTPConnection(REMOTE_HOST, remote_port, timeout=20)
    try:
        connection.request(
            "POST",
            REMOTE_PATH,
            body=payload,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        status = response.status
        if response.length is not None and response.length > MAX_RESPONSE_BYTES:
            print("远端响应超过上限")
            return 1
        response_data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(response_data) > MAX_RESPONSE_BYTES:
            print("远端响应超过上限")
            return 1
    except (OSError, http.client.HTTPException):
        print("远端连接失败")
        return 1
    finally:
        connection.close()

    if status != 200:
        print("远端 HTTP 状态异常")
        return 1
    try:
        data = _strict_json_loads(response_data.decode("utf-8"))
        if not isinstance(data, dict) or set(data) != {"envelope", "body_b64"}:
            raise ValueError("响应字段集合不匹配")
        response_body = base64.b64decode(data["body_b64"], validate=True)
        ok, reason = M.verify_envelope(
            data["envelope"], key, KEY_ID, REMOTE_SEAT, SENDER, response_body, replay_cache
        )
        rpc_response = _strict_json_loads(response_body.decode("utf-8"))
    except (
        UnicodeDecodeError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        json.JSONDecodeError,
    ):
        print("远端响应格式非法")
        return 1

    ok = (
        ok
        and isinstance(rpc_response, dict)
        and rpc_response.get("jsonrpc") == "2.0"
        and rpc_response.get("id") == request_id
        and "error" not in rpc_response
        and isinstance(rpc_response.get("result"), dict)
    )
    print("远端响应验证 = %s（%s）" % (ok, reason))
    print("★ VERDICT=" + ("PASS" if ok else "BAD"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
