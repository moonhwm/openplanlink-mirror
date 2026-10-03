#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""a2a_hmac.py —— A2A 消息认证 HMAC-SHA3-512（对齐总线 Qoder DF-NOTICE-2026-1003-QODER-05）。

契约：
  - 算法 HMAC-SHA3-512；协议标识 a2a-hmac-sha3-512/v1；输出 64 字节 = 128 位小写 hex。
  - 认证输入 = UTF8("OpenPlanLink-A2A-HMAC-v1\\u0000") || JCS(无 tag 包络)。
  - JSON 按 RFC 8785 JCS 规范化；正文摘要按原始字节 SHA3-512。
  - 密钥 64 字节；HMAC 比较用常量时间；时间窗默认 300 秒；nonce 至少 128 位。
"""
import hashlib
import hmac
import secrets
import decimal
from datetime import datetime, timezone

VERSION = "a2a-hmac-sha3-512/v1"
DOMAIN_PREFIX = b"OpenPlanLink-A2A-HMAC-v1\x00"
DEFAULT_WINDOW = 300
KEY_BYTES = 64


# ---------- RFC 8785 JCS ----------
def jcs(obj):
    """RFC 8785 JSON Canonicalization Scheme。"""
    if obj is None:
        return "null"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        return _jcs_number(obj)
    if isinstance(obj, str):
        return _jcs_string(obj)
    if isinstance(obj, list):
        return "[" + ",".join(jcs(v) for v in obj) + "]"
    if isinstance(obj, dict):
        keys = sorted(obj.keys())
        return "{" + ",".join(_jcs_string(k) + ":" + jcs(obj[k]) for k in keys) + "}"
    raise TypeError("JCS 不支持类型: %r" % type(obj))


def _jcs_string(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == '\\':
            out.append('\\\\')
        elif ch == '\b':
            out.append('\\b')
        elif ch == '\t':
            out.append('\\t')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\f':
            out.append('\\f')
        elif ch == '\r':
            out.append('\\r')
        elif o < 0x20:
            out.append('\\u%04x' % o)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _jcs_number(n):
    """RFC 8785 数字规范化：无前导/尾随零、无小数点尾零、无科学计数法、-0→0。"""
    if isinstance(n, bool):
        return "true" if n else "false"
    if isinstance(n, int):
        return str(n)
    if isinstance(n, float):
        if n != n or n in (float("inf"), float("-inf")):
            raise ValueError("JCS 不允许 NaN/Infinity")
        if n == 0.0:
            return "0"
        d = decimal.Decimal(repr(n)).normalize()
        s = format(d, "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s
    raise TypeError("JCS 数字不支持类型: %r" % type(n))


# ---------- 摘要与时间 ----------
def sha3_512_hex(data: bytes) -> str:
    return hashlib.sha3_512(data).hexdigest()


def now_rfc3339() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_ts(s: str) -> datetime:
    # RFC 3339 允许 "Z" 或 "+08:00"；统一成 fromisoformat 能吃的形式
    if s.endswith(("Z", "z")):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


# ---------- 建 / 验 ----------
def _auth_input(env_without_tag: dict) -> bytes:
    return DOMAIN_PREFIX + jcs(env_without_tag).encode("utf-8")


def compute_tag(env_without_tag: dict, key: bytes) -> str:
    return hmac.new(key, _auth_input(env_without_tag), hashlib.sha3_512).hexdigest()


def build_envelope(sender_id: str, recipient_id: str, body: bytes, key: bytes, key_id: str) -> dict:
    if len(key) != KEY_BYTES:
        raise ValueError("HMAC 密钥必须 %d 字节" % KEY_BYTES)
    env = {
        "version": VERSION,
        "key_id": key_id,
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "timestamp": now_rfc3339(),
        "nonce": secrets.token_hex(16),  # 128 位
        "body_sha3_512": sha3_512_hex(body),
    }
    env["tag"] = compute_tag(env, key)
    return env


def verify_envelope(env: dict, key: bytes, key_id: str, recipient_id: str,
                    body=None, now=None, seen_nonces=None, window=DEFAULT_WINDOW):
    """返回 (ok, reason)。失败关闭：任一检查不过即 False，不做静默降级。"""
    if now is None:
        now = datetime.now(timezone.utc).astimezone()
    seen = seen_nonces if seen_nonces is not None else set()

    if env.get("version") != VERSION:
        return False, "version 不匹配"
    if env.get("recipient_id") != recipient_id:
        return False, "接收方错配"
    if env.get("key_id") != key_id:
        return False, "错误 key_id"
    try:
        ts = parse_ts(env.get("timestamp", ""))
    except Exception:
        return False, "timestamp 解析失败"
    if abs((now - ts).total_seconds()) > window:
        return False, "时间窗超界"
    nonce = env.get("nonce", "")
    if len(nonce) < 32:  # 128 位 = 32 个 hex 字符
        return False, "nonce 太短"
    if nonce in seen:
        return False, "重复 nonce"
    if body is not None:
        if env.get("body_sha3_512") != sha3_512_hex(body):
            return False, "正文摘要不匹配"
    env_no_tag = {k: v for k, v in env.items() if k != "tag"}
    expected = compute_tag(env_no_tag, key)
    if not hmac.compare_digest(expected, env.get("tag", "")):
        return False, "tag 不匹配"
    seen.add(nonce)
    return True, "ok"


def platform_supported() -> bool:
    """对应 .NET 的 HMACSHA3_512.IsSupported。Python：sha3_512 存在即可用。"""
    try:
        hashlib.sha3_512(b"x")
        return True
    except Exception:
        return False


if __name__ == "__main__":
    import json
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print("platform_supported =", platform_supported())
    k = secrets.token_bytes(KEY_BYTES)
    e = build_envelope("cairn-dsh", "workbuddy-hy4", b"hello", k, "k-20261003-1")
    print(json.dumps(e, ensure_ascii=False, indent=2))
    ok, r = verify_envelope(e, k, "k-20261003-1", "workbuddy-hy4", body=b"hello")
    print("verify =", ok, r)
