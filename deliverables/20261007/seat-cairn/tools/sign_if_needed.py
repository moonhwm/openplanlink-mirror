# -*- coding: utf-8 -*-
"""sign_if_needed.py —— **树未变则免重签提交**（把 DF-PROPOSAL §甲 落实为本席流程）

背景（实测，见 DF-START5 §三 / bus_snr 轮38）：
  6 小时窗内 **51 次** `push-gate: re-sign tree` 提交 ⇒ **占总线噪声 100%**（SNR 0.726）。
  其中相当一部分**并未改变树**（或与既有 `attest-hmac-sha3-512.json` 完全相同）⇒
  **完全不必产生一次提交**（每次还附带守卫与推送往返）。

本器做法（**安全、可逆**）：
  1. 备份现有 `attest-hmac-sha3-512.json` 与哈希；
  2. 运行 `node tools/sha3-tree.mjs build`；
  3. 比对新旧文件**字节是否相同**：
     · **相同** ⇒ 恢复备份（确保工作树无变更）并**建议免提交**（退出码 0，`--json` 记 `needed=false`）
     · **不同** ⇒ 保留新件并**建议提交重签**（退出码 10，`--json` 记 `needed=true`）
  4. 全程**不提交、不推送**（只判定与建议）；`--force` 可强制保留新件。

用法:
  python sign_if_needed.py [--repo <路径>] [--json <路径>] [--force]
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
ATT = "attest-hmac-sha3-512.json"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=r"C:\Users\欧阳宏俊\openplanlink-mirror")
    ap.add_argument("--json")
    ap.add_argument("--force", action="store_true", help="即使未变也保留新件")
    a = ap.parse_args()

    repo = pathlib.Path(a.repo)
    att = repo / ATT
    if not att.exists():
        print("★ 无既有 %s ⇒ **需要**生成（needed=true）" % ATT)
        if a.json:
            pathlib.Path(a.json).write_text(json.dumps({"needed": True, "why": "no existing attest"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 10

    old_h = sha(att)
    with tempfile.TemporaryDirectory() as td:
        bak = pathlib.Path(td) / "bak.json"
        shutil.copy2(att, bak)
        env = dict(os.environ)
        env.setdefault("OPL_A2A_HMAC_KEY_ID", "opl-a2a-2026q4")
        p = subprocess.run(["node", "tools/sha3-tree.mjs", "build"], cwd=str(repo),
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=300, env=env)
        build_out = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
        new_h = sha(att) if att.exists() else ""
        same = (new_h == old_h) and new_h != ""
        if same and not a.force:
            shutil.copy2(bak, att)   # 恢复，确保工作树无变更
            print("★ **树未变** ⇒ **无需重签提交**（needed=false）")
            print("  旧/新 sha256 相同：%s…" % old_h[:16])
            print("  效果：省 1 次提交 + 1 次守卫 + 1 次推送往返（承 DF-PROPOSAL §甲）")
            if a.json:
                pathlib.Path(a.json).write_text(json.dumps(
                    {"needed": False, "sha256": old_h, "restored": True}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
            return 0
        print("★ **树有变** ⇒ **需要重签提交**（needed=true）")
        print("  旧 sha256=%s… ｜ 新 sha256=%s…" % (old_h[:16], (new_h or "-")[:16]))
        if build_out:
            print("  build 末行：%s" % build_out[-1][:100])
        if a.json:
            pathlib.Path(a.json).write_text(json.dumps(
                {"needed": True, "old_sha256": old_h, "new_sha256": new_h}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
        return 10


if __name__ == "__main__":
    sys.exit(main())
