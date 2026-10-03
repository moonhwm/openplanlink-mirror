#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Minimal loopback A2A JSON-RPC node with HMAC-SHA3-512 authentication."""

import base64
import ipaddress
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import a2a_hmac as M

HOST = os.environ.get("OPL_A2A_NODE_HOST", "127.0.0.1")
PORT = int(os.environ.get("OPL_A2A_NODE_PORT", "4173"))
KEY_FILE = Path(os.environ.get("OPL_A2A_HMAC_KEY_FILE", Path.home() / ".a2a-hmac-key.bin"))
KEY_ID = os.environ.get("OPL_A2A_HMAC_KEY_ID", "opl-a2a-2026q4")
STATE_DB = Path(os.environ.get("OPL_A2A_STATE_DB", Path.home() / ".a2a-node-state.sqlite3"))
SEAT = "a2a-node-local"
SEATS = {"cairn-dsh", "workbuddy-hy4", SEAT, "shoucang-seat", "zcode-moon", "kimi-seat"}
MAX_REQUEST_BYTES = 131_072
MAX_MESSAGE_BYTES = 65_536
MAX_MAILBOX_MESSAGES = 100
MAX_MAILBOX_RESPONSE_BYTES = 524_288
MAX_RESPONSE_BYTES = 1_048_576
SOCKET_TIMEOUT_SECONDS = 5

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("a2a-node")


def _require_loopback(host):
    if host == "localhost":
        return
    try:
        address = ipaddress.ip_address(host)
        if isinstance(address, ipaddress.IPv4Address) and address.is_loopback:
            return
    except ValueError:
        pass
    raise SystemExit("明文 A2A 节点只允许绑定 IPv4 回环地址")


def _load_key(path):
    if path.is_symlink() or not path.is_file():
        raise SystemExit("密钥路径必须是普通文件")
    if os.name != "nt" and path.stat().st_mode & 0o077:
        raise SystemExit("密钥文件权限必须限制为当前账户")
    key = path.read_bytes()
    if len(key) != M.KEY_BYTES:
        raise SystemExit(f"密钥文件须为 {M.KEY_BYTES} 字节")
    return key


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


class MailboxFull(Exception):
    pass


class ResponseTooLarge(Exception):
    pass


class NodeStore(M.ReplayCache):
    def __init__(self, database_path):
        self._transaction = None
        super().__init__(database_path)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS mailbox_messages ("
                "message_id TEXT PRIMARY KEY, recipient TEXT NOT NULL, "
                "sender TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL, "
                "expires_at REAL NOT NULL)"
            )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(mailbox_messages)")
            }
            if "expires_at" not in columns:
                connection.execute("ALTER TABLE mailbox_messages ADD COLUMN expires_at REAL")
            connection.execute(
                "UPDATE mailbox_messages SET expires_at = created_at + ? "
                "WHERE expires_at IS NULL",
                (M.DEFAULT_WINDOW,),
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS mailbox_recipient_created "
                "ON mailbox_messages(recipient, created_at)"
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        if os.name != "nt":
            os.chmod(self._database_path, 0o600)

    def claim(self, nonce: str, checked_at: datetime, message_timestamp: datetime) -> bool:
        if self._transaction is not None:
            raise sqlite3.OperationalError("transaction already active")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = checked_at.timestamp()
            connection.execute("DELETE FROM replay_nonces WHERE expires_at < ?", (current,))
            connection.execute("DELETE FROM mailbox_messages WHERE expires_at < ?", (current,))
            cursor = connection.execute(
                "INSERT OR IGNORE INTO replay_nonces (nonce, expires_at) VALUES (?, ?)",
                (nonce, message_timestamp.timestamp() + M.DEFAULT_WINDOW),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                connection.close()
                return False
            self._transaction = connection
            return True
        except Exception:
            connection.rollback()
            connection.close()
            raise

    def queue(self, envelope, body):
        connection = self._require_transaction()
        recipient = envelope["recipient_id"]
        count = connection.execute(
            "SELECT COUNT(*) FROM mailbox_messages WHERE recipient = ?", (recipient,)
        ).fetchone()[0]
        if count >= MAX_MAILBOX_MESSAGES:
            raise MailboxFull
        payload = json.dumps(
            {"envelope": envelope, "body_b64": base64.b64encode(body).decode("ascii")},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        created_at = datetime.now().timestamp()
        expires_at = M.parse_ts(envelope["timestamp"]).timestamp() + M.DEFAULT_WINDOW
        connection.execute(
            "INSERT INTO mailbox_messages "
            "(message_id, recipient, sender, payload, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (envelope["nonce"], recipient, envelope["sender_id"], payload, created_at, expires_at),
        )

    def messages(self, recipient):
        connection = self._require_transaction()
        rows = connection.execute(
            "SELECT payload FROM mailbox_messages WHERE recipient = ? "
            "ORDER BY created_at, message_id LIMIT ?",
            (recipient, MAX_MAILBOX_MESSAGES),
        ).fetchall()
        messages = []
        response_bytes = 0
        for row in rows:
            payload_bytes = len(row[0].encode("utf-8"))
            if response_bytes + payload_bytes > MAX_MAILBOX_RESPONSE_BYTES:
                break
            messages.append(json.loads(row[0]))
            response_bytes += payload_bytes
        return messages

    def acknowledge(self, recipient, message_ids):
        connection = self._require_transaction()
        deleted = 0
        for message_id in message_ids:
            cursor = connection.execute(
                "DELETE FROM mailbox_messages WHERE recipient = ? AND message_id = ?",
                (recipient, message_id),
            )
            deleted += cursor.rowcount
        return deleted

    def commit(self):
        connection, self._transaction = self._transaction, None
        if connection is not None:
            try:
                connection.commit()
            finally:
                connection.close()

    def rollback(self):
        connection, self._transaction = self._transaction, None
        if connection is not None:
            try:
                connection.rollback()
            finally:
                connection.close()

    def _require_transaction(self):
        if self._transaction is None:
            raise sqlite3.OperationalError("transaction not active")
        return self._transaction


_require_loopback(HOST)
KEY = _load_key(KEY_FILE)
STORE = NodeStore(STATE_DB)

AGENT_CARD = {
    "protocolVersion": "0.3.0",
    "name": "A2A 本地节点 · cairn-dsh（石敢当）",
    "description": "回环 A2A JSON-RPC 节点；共享 HMAC 密钥认证信任域成员，不提供席位非抵赖或消息机密性。",
    "url": f"http://{HOST}:{PORT}",
    "preferredTransport": "JSONRPC",
    "version": "0.3.0",
    "provider": {"organization": "cairn-dsh / 石敢当", "url": f"http://{HOST}:{PORT}"},
    "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": False},
    "defaultInputModes": ["application/json"],
    "defaultOutputModes": ["application/json"],
    "skills": [{
        "id": "a2a-hmac-echo",
        "name": "HMAC Echo + Trust-domain Mailbox",
        "description": "HMAC-SHA3-512 认证的消息回显与信任域信箱路由",
        "tags": ["a2a", "hmac", "mailbox"],
        "inputModes": ["application/json"],
        "outputModes": ["application/json"],
    }],
}


def _rpc_response(request, result=None, error=None):
    response = {"jsonrpc": "2.0", "id": request.get("id")}
    response["error" if error is not None else "result"] = error if error is not None else result
    return response


def _parse_rpc(body):
    request = _strict_json_loads(body.decode("utf-8"))
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
        raise ValueError("无效 JSON-RPC 请求")
    if not isinstance(request.get("method"), str):
        raise ValueError("无效 JSON-RPC 方法")
    request_id = request.get("id")
    if isinstance(request_id, bool) or not isinstance(request_id, (str, int)):
        raise ValueError("无效 JSON-RPC 标识")
    if "params" in request and not isinstance(request["params"], (dict, list)):
        raise ValueError("无效 JSON-RPC 参数")
    return request


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(SOCKET_TIMEOUT_SECONDS)

    def log_message(self, message, *args):
        LOGGER.info("peer=%s %s", self.client_address[0], message % args)

    def _send(self, code, value):
        output = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(output)))
        self.end_headers()
        self.wfile.write(output)

    def _send_error(self, status, code, message):
        self._send(status, {"jsonrpc": "2.0", "id": None, "error": {"code": code, "message": message}})

    def _commit_signed(self, recipient_id, request, result=None, error=None, status=200):
        response = _rpc_response(request, result=result, error=error)
        body = json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        envelope = M.build_envelope(SEAT, recipient_id, body, KEY, KEY_ID)
        payload = {"envelope": envelope, "body_b64": base64.b64encode(body).decode("ascii")}
        wire_size = len(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        if wire_size > MAX_RESPONSE_BYTES:
            raise ResponseTooLarge
        STORE.commit()
        try:
            self._send(status, payload)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            LOGGER.warning(
                "response delivery failed recipient=%s method=%s",
                recipient_id,
                request.get("method"),
                exc_info=True,
            )

    def do_GET(self):
        if self.path == "/.well-known/agent-card.json":
            self._send(200, AGENT_CARD)
        elif self.path == "/" or self.path.startswith("/functions/v1/app"):
            self._send(200, {"status": "up", "seat": SEAT, "protocol": M.VERSION})
        else:
            self._send_error(404, -32601, "未找到方法")

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
                self._send_error(413, -32600, "请求体大小非法")
                return
            payload = _strict_json_loads(self.rfile.read(content_length).decode("utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("envelope"), dict):
                raise ValueError("无效消息包")
            envelope = payload["envelope"]
            body = base64.b64decode(payload["body_b64"], validate=True)
            if len(body) > MAX_MESSAGE_BYTES:
                self._send_error(413, -32600, "消息正文超过上限")
                return
            sender_id = envelope.get("sender_id")
            recipient_id = envelope.get("recipient_id")
            if sender_id not in SEATS:
                self._send_error(401, -32000, "未知发送席位")
                return
            if recipient_id not in SEATS:
                self._send_error(404, -32602, "未知接收席位")
                return
            ok, reason = M.verify_envelope(
                envelope, KEY, KEY_ID, sender_id, recipient_id, body, STORE
            )
            if not ok:
                status = 503 if reason == "nonce 缓存不可用" else 401
                self._send_error(status, -32000, reason)
                return
            request = _parse_rpc(body)
            if recipient_id != SEAT:
                STORE.queue(envelope, body)
                self._commit_signed(
                    sender_id, request, {"queued": True, "recipient": recipient_id, "message_id": envelope["nonce"]}
                )
                return
            if request["method"] == "mailbox/get":
                self._commit_signed(sender_id, request, {"messages": STORE.messages(sender_id)})
                return
            if request["method"] == "mailbox/ack":
                params = request.get("params")
                message_ids = params.get("message_ids") if isinstance(params, dict) else None
                if not isinstance(message_ids, list) or len(message_ids) > MAX_MAILBOX_MESSAGES:
                    raise ValueError("无效确认列表")
                if any(not isinstance(value, str) or not M.NONCE_HEX.fullmatch(value) for value in message_ids):
                    raise ValueError("无效消息标识")
                self._commit_signed(sender_id, request, {"acknowledged": STORE.acknowledge(sender_id, message_ids)})
                return
            self._commit_signed(sender_id, request, {
                "echo_method": request["method"],
                "echo_params": request.get("params"),
                "node": SEAT,
            })
        except MailboxFull:
            self._send_error(429, -32003, "信箱已满")
        except ResponseTooLarge:
            self._send_error(503, -32004, "响应超过上限")
        except (KeyError, TypeError, ValueError, RecursionError):
            self._send_error(400, -32700, "解析错误")
        except sqlite3.Error:
            LOGGER.exception("persistent state failure")
            self._send_error(503, -32000, "持久状态不可用")
        except OSError:
            LOGGER.warning("request transport failure peer=%s", self.client_address[0], exc_info=True)
        finally:
            STORE.rollback()


if __name__ == "__main__":
    HTTPServer((HOST, PORT), Handler).serve_forever()
