#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""build_hmac_tree.py —— 用 HMAC-SHA3-512 为 deliverables 建 Merkle 树，密钥自留。"""
import hmac
import hashlib
import json
import pathlib
import secrets
import sys

sys.stdout.reconfigure(encoding="utf-8")

REPO = pathlib.Path(r"C:\Users\欧阳宏俊\openplanlink-mirror")
DELIV = REPO / "deliverables" / "20261003"
KEY_FILE = pathlib.Path(r"C:\Users\欧阳宏俊\.a2a-hmac-key.bin")   # ★ 自留，不提交

# 密钥：有则复用，无则新生成（32 字节）
if KEY_FILE.exists():
    key = KEY_FILE.read_bytes()
else:
    key = secrets.token_bytes(64)
    KEY_FILE.write_bytes(key)
# ★ 对齐总线 Qoder 通告 DF-NOTICE-2026-1003-QODER-05：密钥须 64 字节
if len(key) != 64:
    key = secrets.token_bytes(64)
    KEY_FILE.write_bytes(key)

def hm(data: bytes) -> str:
    return hmac.new(key, data, hashlib.sha3_512).hexdigest()

files = sorted(p.relative_to(DELIV).as_posix() for p in DELIV.rglob("*") if p.is_file())
# 跳过 attest 自身（避免自包含）
files = [f for f in files if f != "hmac_attest.json"]

leaves = {f: hm((DELIV / f).read_bytes()) for f in files}

# 建树：按文件名排序，两两拼接 hex 后 HMAC
level = [leaves[f] for f in files]
while len(level) > 1:
    nxt = []
    for i in range(0, len(level), 2):
        pair = level[i] + (level[i + 1] if i + 1 < len(level) else level[i])
        nxt.append(hm(bytes.fromhex(pair)))
    level = nxt
root = level[0] if level else ""

attest = {
    "algo": "HMAC-SHA3-512",
    "protocol": "a2a-hmac-sha3-512/v1",
    "scope": "deliverables/20261003",
    "key_bits": 512,
    "key": "self-kept (not committed) — key sha256=" + hashlib.sha256(key).hexdigest()[:16],
    "root": root,
    "file_count": len(leaves),
    "files": leaves,
}
out = DELIV / "hmac_attest.json"
out.write_text(json.dumps(attest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("★ 密钥文件 =", KEY_FILE)
print("★ 密钥 sha256 前16 =", hashlib.sha256(key).hexdigest()[:16])
print("★ Merkle 根 =", root)
print("★ 叶子数 =", len(leaves))
print("★ attest 已写 =", out.name)
for f in files:
    print("   ·", f, leaves[f][:16] + "…")
