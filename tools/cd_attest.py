#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""cd_attest.py —— 通用 SHA3-512 Merkle 树构建器（CD 用，与 tools/SHA3_TREE.md 字节契约一致）

与既有 tools/build_opl_tree.py **同一字节契约**，但：
  1. 根目录可选（默认仓库根），便于在 CI 中对整仓构建；
  2. **无钥亦可运行**：未提供密钥时只出默克尔根，`hmac_sha3_512` 记 null（CI 不依赖机密）；
  3. 额外产出一页纸 STATUS.md（提交号／文件数／根／时刻），供留痕审计与静态发布取用。

字节契约（对齐 build_opl_tree.py / sha3-tree.mjs）：
  叶   = SHA3-512(0x00 || uint32be(path_len) || path || uint64be(size) || sha3_512(content))
  父   = SHA3-512(0x01 || left || right)；奇数复制右项
  根MAC= HMAC-SHA3-512(key, "OpenPlanLink-A2A-Merkle-v1\\0" || root || uint64be(count)
              || uint16be(key_id_len) || key_id || uint16be(generated_at_len) || generated_at)

用法:
  python tools/cd_attest.py                       # 对仓库根构建，写 attest-cd.json / STATUS.md
  python tools/cd_attest.py --root . --out x.json --status y.md
  python tools/cd_attest.py --key-env OPL_TREE_KEY   # 有钥则追加根 MAC（hex 编码的 64 字节）
"""
import argparse
import hashlib
import hmac
import json
import os
import pathlib
import struct
import subprocess
import sys
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")

EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
EXCLUDE_FILES = {"attest-cd.json", "STATUS.md"}


def sha3(b: bytes) -> bytes:
    return hashlib.sha3_512(b).digest()


def leaf(path_utf8: str, size: int, content_digest_hex: str) -> str:
    pb = path_utf8.encode("utf-8")
    data = b"\x00" + struct.pack(">I", len(pb)) + pb + struct.pack(">Q", size) + bytes.fromhex(content_digest_hex)
    return sha3(data).hex()


def merkle_root(leaf_hexes):
    level = [bytes.fromhex(h) for h in leaf_hexes]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            right = level[i + 1] if i + 1 < len(level) else level[i]
            nxt.append(sha3(b"\x01" + level[i] + right))
        level = nxt
    return level[0].hex() if level else ""


def git_head(repo: pathlib.Path) -> str:
    try:
        p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, timeout=30)
        return (p.stdout or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="attest-cd.json")
    ap.add_argument("--status", default="STATUS.md")
    ap.add_argument("--html", default=None, help="输出自包含静态状态页（无外部依赖，可直接发布）")
    ap.add_argument("--key-file", default=r"C:\Users\欧阳宏俊\.a2a-hmac-key.bin")
    ap.add_argument("--key-env", default="OPL_TREE_KEY", help="存放 64 字节密钥 hex 的环境变量名")
    ap.add_argument("--key-id", default="opl-a2a-2026q4")
    a = ap.parse_args()

    root_dir = pathlib.Path(a.root).resolve()
    files = []
    for p in sorted(root_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root_dir).as_posix()
        if any(part in EXCLUDE_DIRS for part in p.relative_to(root_dir).parts):
            continue
        if rel in EXCLUDE_FILES:
            continue
        files.append((rel, p))

    entries = []
    for rel, p in files:
        data = p.read_bytes()
        cd = sha3(data).hex()
        entries.append({"path": rel, "size": len(data), "content_sha3_512": cd,
                        "leaf_sha3_512": leaf(rel, len(data), cd)})

    root = merkle_root([e["leaf_sha3_512"] for e in entries])
    generated_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    key = None
    env_val = os.environ.get(a.key_env, "").strip()
    if env_val:
        try:
            key = bytes.fromhex(env_val)
        except ValueError:
            key = None
    if key is None:
        kf = pathlib.Path(a.key_file)
        if kf.exists() and kf.stat().st_size == 64:
            key = kf.read_bytes()

    mac = None
    key_fp = None
    if key and len(key) == 64:
        kid = a.key_id.encode("utf-8")
        gen = generated_at.encode("utf-8")
        mac_input = (b"OpenPlanLink-A2A-Merkle-v1\x00" + bytes.fromhex(root)
                     + struct.pack(">Q", len(entries))
                     + struct.pack(">H", len(kid)) + kid
                     + struct.pack(">H", len(gen)) + gen)
        mac = hmac.new(key, mac_input, hashlib.sha3_512).hexdigest()
        key_fp = sha3(key).hex()[:16]

    head = git_head(root_dir)
    manifest = {
        "schema": "opl-hmac-sha3-512-tree/1",
        "generated_at": generated_at,
        "tree_algorithm": "sha3-512",
        "mac_algorithm": "hmac-sha3-512" if mac else None,
        "leaf_encoding": "0x00 || uint32be(path_utf8_len) || path_utf8 || uint64be(size) || sha3_512(content)",
        "node_encoding": "0x01 || left_digest || right_digest; duplicate odd right node",
        "root": str(root_dir),
        "commit": head,
        "key_id": a.key_id if mac else None,
        "key_fingerprint_sha3_512_16": key_fp,
        "file_count": len(entries),
        "merkle_root_sha3_512": root,
        "hmac_sha3_512": mac,
        "files": entries,
    }

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 一页纸状态（供留痕审计 / 静态发布）
    lines = [
        "# OpenPlanLink A2A · 交付状态（CD 自动生成）",
        "",
        "- 生成时刻（UTC）：%s" % generated_at,
        "- 提交：`%s`" % (head or "（非 git 目录）"),
        "- 文件数：**%d**" % len(entries),
        "- 默克尔根（SHA3-512）：`%s`" % root,
        "- 根 MAC（HMAC-SHA3-512）：%s" % ("`%s`" % mac if mac else "**未签名**（无密钥，仅结构完整性）"),
        "- 密钥指纹前 16：%s" % (key_fp or "—"),
        "- 构建器：`tools/cd_attest.py`（契约见 `tools/SHA3_TREE.md`）",
        "",
        "> 本页由 CD 工作流在每次 `main` 推送后自动重生成；数值可经 `tools/verify_opl_tree.py` 复算。",
    ]
    pathlib.Path(a.status).write_text("\n".join(lines) + "\n", encoding="utf-8")

    if a.html:
        import html as _html
        mac_txt = mac if mac else "未签名（无密钥，仅结构完整性）"
        page = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenPlanLink A2A · 交付状态</title>
<style>
:root{color-scheme:light dark}
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;padding:2rem;line-height:1.6}
main{max-width:52rem;margin:0 auto}
h1{font-size:1.35rem;margin:0 0 .25rem}
p.sub{opacity:.7;margin:0 0 1.5rem;font-size:.9rem}
table{border-collapse:collapse;width:100%;margin:0 0 1.5rem}
th,td{border:1px solid rgba(128,128,128,.35);padding:.5rem .6rem;text-align:left;vertical-align:top;font-size:.92rem}
th{width:11rem;background:rgba(128,128,128,.12)}
code{font-family:ui-monospace,Consolas,monospace;font-size:.85em;word-break:break-all}
footer{opacity:.65;font-size:.82rem;border-top:1px solid rgba(128,128,128,.3);padding-top:.8rem}
</style>
</head>
<body><main>
<h1>OpenPlanLink A2A · 交付状态</h1>
<p class="sub">CD 自动生成（每次 main 推送重建）· 无外部依赖、无脚本、无凭据</p>
<table>
<tr><th>生成时刻（UTC）</th><td><code>@@GEN@@</code></td></tr>
<tr><th>提交</th><td><code>@@COMMIT@@</code></td></tr>
<tr><th>文件数</th><td><strong>@@COUNT@@</strong></td></tr>
<tr><th>默克尔根<br>(SHA3-512)</th><td><code>@@ROOT@@</code></td></tr>
<tr><th>根 MAC<br>(HMAC-SHA3-512)</th><td><code>@@MAC@@</code></td></tr>
<tr><th>构建器</th><td><code>tools/cd_attest.py</code>（契约见 <code>tools/SHA3_TREE.md</code>）</td></tr>
</table>
<footer>本页由 CI/CD 自动重生成；数值可经 <code>tools/verify_opl_tree.py</code> 复算。本页不含任何凭据、密钥或个人信息。</footer>
</main></body></html>
"""
        for token, value in (
            ("@@GEN@@", _html.escape(generated_at)),
            ("@@COMMIT@@", _html.escape(head or "（非 git 目录）")),
            ("@@COUNT@@", str(len(entries))),
            ("@@ROOT@@", _html.escape(root)),
            ("@@MAC@@", _html.escape(mac_txt)),
        ):
            page = page.replace(token, value)
        hp = pathlib.Path(a.html)
        hp.parent.mkdir(parents=True, exist_ok=True)
        hp.write_text(page, encoding="utf-8")

    print("★ 文件数 =", len(entries))
    print("★ merkle_root =", root)
    print("★ 根MAC =", mac or "（未签名）")
    print("★ 已写 =", out, "/", a.status, ("/ " + a.html) if a.html else "")


if __name__ == "__main__":
    main()
