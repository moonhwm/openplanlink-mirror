#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""a2a_node.py —— 最小 A2A JSON-RPC 节点（127.0.0.1:4173），HMAC-SHA3-512 认证 + 席位信箱。

线格式：POST /  body = {"envelope": {…}, "body_b64": "<JSON-RPC 请求的 base64>"}
  · 若 recipient == 节点自身 → 处理并返回 HMAC 包络响应（回显）
  · 若 recipient == 其它席位 → 验证后存入该席位信箱，返回 queued
GET /               → 节点状态
GET /mailbox/<seat> → 取该席位待收消息（含 envelope + body_b64）
"""
import base64
import json
import os
import secrets
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import a2a_hmac as M
import totp as TOTP

# MFA 第二因子（TOTP）共享密钥：RFC 6238 演示向量 base32（"12345678901234567890"）。
# 生产环境应替换为随机 20 字节并妥善保管。
TOTP_SECRET = base64.b32decode("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ")

HOST = "127.0.0.1"
PORT = 4173
KEY_FILE = r"C:\Users\欧阳宏俊\.a2a-hmac-key.bin"
KEY = open(KEY_FILE, "rb").read()
if len(KEY) != 64:
    raise SystemExit("密钥文件须为 64 字节")
KEY_ID = "opl-a2a-2026q4"
SEAT = "a2a-node-local"
NONCE_FILE = r"C:\Users\欧阳宏俊\.a2a-node-nonces.json"
MAILBOX_FILE = r"C:\Users\欧阳宏俊\.a2a-node-mailbox.json"
DLQ_FILE = r"C:\Users\欧阳宏俊\.a2a-node-dlq.json"
AUDIT_FILE = r"C:\Users\欧阳宏俊\.a2a-node-audit.jsonl"
seen = set()
mailbox = {}
dlq = []  # 死信队列：投递失败的消息（未知席位等），可重试，不丢失
# 席位注册表：中转前校验目标合法；未知席位拒绝
SEATS = {"cairn-dsh", "workbuddy-hy4", "a2a-node-local", "shoucang-seat", "zcode-moon", "kimi-seat"}

AGENT_CARD = {
    "protocolVersion": "0.3.0",
    "name": "A2A 本地节点 · cairn-dsh（石敢当）",
    "description": "最小 A2A JSON-RPC 节点：HMAC-SHA3-512 认证、席位信箱路由、nonce/信箱持久化、MFA(TOTP) 双因子。127.0.0.1:4173",
    "url": "http://127.0.0.1:4173",
    "preferredTransport": "JSONRPC",
    "version": "0.2.0",
    "license": "AGPL-3.0",
    "x-licenses": {
        "code": "AGPL-3.0-only",
        "documentation": "CC-BY-SA-4.0"
    },
    "x-agpl-source-offer": {
        "correspondingSourceUrl": "https://github.com/moonhwm/openplanlink-mirror",
        "offer": "Corresponding source of the network-interacting version is offered at the above repository under AGPL-3.0-only; see LICENSE and NOTICE there.",
        "section": "AGPL-3.0 section 13"
    },
    "provider": {"organization": "cairn-dsh / 石敢当", "url": "http://127.0.0.1:4173"},
    "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": False},
    "securitySchemes": {
        "hmac-sha3-512": {"type": "hmac", "in": "envelope", "description": "A2A 消息包络认证（第一因子，a2a-hmac-sha3-512/v1）"},
        "totp": {"type": "totp", "in": "query", "description": "信箱读取 TOTP（第二因子，RFC 6238，?totp=<6位>）"},
    },
    "defaultInputModes": ["application/json"],
    "defaultOutputModes": ["application/json"],
    "skills": [
        {"id": "a2a-hmac-echo", "name": "HMAC Echo + Mailbox",
         "description": "HMAC-SHA3-512 认证的消息回显与席位信箱路由（信箱读取需 TOTP 第二因子）",
         "tags": ["a2a", "hmac", "mailbox", "mfa"], "inputModes": ["application/json"], "outputModes": ["application/json"]}
    ],
}


def _load_state():
    global seen, mailbox, dlq
    if os.path.exists(NONCE_FILE):
        try:
            seen = set(json.load(open(NONCE_FILE, encoding="utf-8")))
        except Exception:
            seen = set()
    if os.path.exists(MAILBOX_FILE):
        try:
            mailbox = json.load(open(MAILBOX_FILE, encoding="utf-8"))
        except Exception:
            mailbox = {}
    if os.path.exists(DLQ_FILE):
        try:
            dlq = json.load(open(DLQ_FILE, encoding="utf-8"))
        except Exception:
            dlq = []


def _atomic_json(path, obj):
    """transactional outbox 原子性：先写临时文件再 os.replace，避免半写/崩溃残留。"""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def _save_state():
    _atomic_json(NONCE_FILE, list(seen))
    _atomic_json(MAILBOX_FILE, mailbox)
    _atomic_json(DLQ_FILE, dlq)


def _audit(event, detail):
    """事件驱动审计：异常事件追加审计日志（告警留痕，补偿=不改变状态仅记痕）。"""
    import datetime
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "event": event}
    rec.update(detail)
    try:
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 审计失败不阻断主流程（与"不影响核心业务流连续性"一致）


def _rpc_result(rpc):
    return {"jsonrpc": "2.0", "id": rpc.get("id"),
            "result": {"echo_method": rpc.get("method"), "echo_params": rpc.get("params"), "node": SEAT}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        out = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_GET(self):
        if self.path == "/.well-known/agent-card.json":
            self._send(200, AGENT_CARD)
        elif self.path.startswith("/dlq"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            code = (q.get("totp") or [""])[0]
            if not TOTP.verify(TOTP_SECRET, code):
                _audit("MFA_FAIL", {"path": self.path, "ip": self.client_address[0]})
                self._send(401, {"error": "TOTP 失败（第二因子缺失/错误）"})
                return
            self._send(200, {"dlq": dlq, "count": len(dlq)})
        elif self.path.startswith("/mailbox/"):
            # MFA：取信箱需 TOTP 第二因子（?totp=<6位口令>）
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            code = (q.get("totp") or [""])[0]
            if not TOTP.verify(TOTP_SECRET, code):
                _audit("MFA_FAIL", {"path": self.path, "ip": self.client_address[0]})
                self._send(401, {"error": "TOTP 失败（第二因子缺失/错误）"})
                return
            seat = self.path.split("/")[-1].split("?")[0]
            self._send(200, {"messages": mailbox.get(seat, [])})
        else:
            self._send(200, {"status": "up", "seat": SEAT, "protocol": "a2a-hmac-sha3-512/v1"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n).decode("utf-8"))
            envelope = req["envelope"]
            body = base64.b64decode(req["body_b64"])

            ok, reason = M.verify_envelope(envelope, KEY, KEY_ID, envelope.get("recipient_id"), body=body, seen_nonces=seen)
            # 注意：节点只验证"发给自己或经自己中转"的消息；中转消息按 recipient 存箱
            if not ok:
                _audit("HMAC_FAIL", {"reason": reason, "ip": self.client_address[0],
                                     "sender": envelope.get("sender_id"), "recipient": envelope.get("recipient_id")})
                self._send(401, {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": reason}})
                return

            if envelope["recipient_id"] == SEAT:
                rpc = json.loads(body.decode("utf-8"))
                result = _rpc_result(rpc)
                resp_bytes = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                resp_env = M.build_envelope(SEAT, envelope["sender_id"], resp_bytes, KEY, KEY_ID)
                self._send(200, {"envelope": resp_env, "body_b64": base64.b64encode(resp_bytes).decode("ascii")})
            else:
                if envelope["recipient_id"] not in SEATS:
                    _audit("UNKNOWN_SEAT", {"recipient": envelope["recipient_id"], "sender": envelope.get("sender_id")})
                    # 死信队列：未知席位消息入 DLQ（不丢失，可重试），而非仅 404 丢弃
                    dlq.append({"envelope": envelope, "body_b64": base64.b64encode(body).decode("ascii"),
                                "reason": "未知席位", "ts": envelope.get("timestamp")})
                    _save_state()
                    self._send(404, {"jsonrpc": "2.0", "id": None,
                                     "error": {"code": -32602, "message": "未知席位: %s" % envelope["recipient_id"]}})
                    return
                mailbox.setdefault(envelope["recipient_id"], []).append(
                    {"envelope": envelope, "body_b64": base64.b64encode(body).decode("ascii")})
                self._send(200, {"queued": True, "recipient": envelope["recipient_id"]})
            _save_state()  # nonce 与信箱一并落盘
        except Exception as e:
            self._send(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error: %s" % e}})


if __name__ == "__main__":
    _load_state()
    srv = HTTPServer((HOST, PORT), Handler)
    print("A2A node on http://%s:%d  (seat=%s, nonce=%d, mailbox=%d)" %
          (HOST, PORT, SEAT, len(seen), len(mailbox)), flush=True)
    srv.serve_forever()
