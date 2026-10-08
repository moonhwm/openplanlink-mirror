# -*- coding: utf-8 -*-
"""sig_block.py —— 「署名 + 唯一标识符」块生成器（承令条 2026-10-08 强化纪律）

令条原文要求（摘）：
    「所有修改必须**署名和唯一标识符**，不能仅仅以不可识别证伪、难以对抗性审查的『本席』为自称书写本文档」

本器产出**可对抗性审查**的署名块：**席位名 ＋ seat_key ＋ 公钥指纹（前8/后4）＋ 件 sha256 ＋ 时点 ＋ 令条锚**。
——「唯一标识符」＝ **(seat_key, pubkey_fp)** 二元组 ＋ **内容哈希**：三者任一不同即非同一署名。

用法：
    python sig_block.py --file <件路径> [--note <用途>]     # 输出署名块（含该件 sha256）
    python sig_block.py --file <件路径> --append            # 追加到件末（幂等：已有块则先提示）
性质：**不回显任何私钥/凭据**；只读公钥指纹与文件哈希。
"""
import argparse
import datetime as dt
import hashlib
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

SEAT_NAME = "A2A新席_石敢当Cairn"
SEAT_KEY = "a2a-node-local"
SEAT_DIR = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
PUB = pathlib.Path(r"C:\Users\欧阳宏俊\.ssh\cairn-commit-signing.pub")
MANDATE = "全局声明 /loop-dual-pillar-ops（2026-10-08 扩写版，内含署名与唯一标识符强化条款）"


def pub_fp_short():
    """公钥指纹（前8+后4），不读取私钥。取不到标「未提供」。"""
    try:
        if not PUB.exists():
            return "未提供", "未提供"
        out = subprocess.run(["ssh-keygen", "-lf", str(PUB)], capture_output=True, text=True, timeout=60).stdout.strip()
        fp = out.split()[1] if out else ""
        if fp.startswith("SHA256:") and len(fp) > 20:
            return fp[:15] + "…" + fp[-4:], fp
        return fp or "未提供", fp or "未提供"
    except Exception:  # noqa: BLE001
        return "未提供", "未提供"


def sha256_of(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--append", action="store_true")
    a = ap.parse_args()
    p = pathlib.Path(a.file)
    if not p.exists():
        print("★ 件不存在：%s" % p)
        return 2
    short, full = pub_fp_short()
    dig = sha256_of(p)
    ts = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S +0800")
    blk = [
        "<!-- SIG-BLOCK v1 seat=%s -->" % SEAT_KEY,
        "",
        "## 署名与唯一标识符（承令条：不以「本席」为唯一自称）",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 席位 | **%s** |" % SEAT_NAME,
        "| seat_key | `%s` |" % SEAT_KEY,
        "| 公钥指纹 | `%s`（ssh-ed25519；**私钥不出、不录**） |" % short,
        "| **本件正文 sha256（署名块之前）** | `%s` |" % dig,
        "| 署名时点 | %s |" % ts,
        "| 令条锚 | %s |" % MANDATE,
        "| 用途 | %s |" % (a.note or "—"),
        "",
        "> **唯一标识符定义（本席口径）**：**(seat_key, 公钥指纹)** 二元组 ＋ **本件内容 sha256**；",
        "> 三者任一不同即**非同一署名**。**复算规则（精确、可脚本化）**：取本文件字节中 `\\n<!-- SIG-BLOCK` 之**前**的部分（即**署名块添加前的原文**）计 sha256，应与上表「本件正文 sha256」**逐位相符**。",
        "",
    ]
    text = "\n".join(blk)
    if a.append:
        cur = p.read_text(encoding="utf-8", errors="replace")
        if "SIG-BLOCK v1" in cur:
            print("★ 该件已含署名块（幂等：未重复追加）")
            return 0
        with p.open("a", encoding="utf-8", newline="") as f:
            f.write("\n" + text)
        print("★ 已追加署名块 → %s（新 sha256 见 --file 复跑）" % p.name)
        return 0
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
