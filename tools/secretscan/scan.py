#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC-6 / 宪法第一条 · 密钥泄漏扫描器
=====================================
档号：IMPL-20261005-SELFVO-T010
任务：tasks.md T010（Phase 1 Setup，不依赖 T005 阻塞项）

职责：对任意目录树做凭据泄漏扫描，输出 PASS / FAIL。
本文件自身**不含任何真实凭据**——这是它的第一性要求。

设计要点（先声明，便于复核）：
  1. 只报「掩码 + sha256 前 8 位」，绝不回显明文，即使命中也不例外。
     理由：扫描报告本身会成为交付件，回显明文等于二次泄露（判据：凭据不落文件）。
  2. 误报显式降级：命中后按上下文判定真伪（示例/占位/掩码/文档散文），
     分 TIER1（真凭据，FAIL）与 TIER2（疑似，需人工判读）。
     理由：把占位符 `sk-xxx` 也判 FAIL 会让门禁失效（恒假）。
  3. 二进制与超长文件跳过并计数，不静默略过——跳过量必须可见。
  4. 遵循路径黑名单（.git / __pycache__ / node_modules 等），但报告被跳过目录数。

用法：
    python3 scan.py <target_dir> [--json out.json] [--min-len 20]
    exit 0 = PASS，exit 1 = FAIL（存在 TIER1）
"""

import argparse
import hashlib
import json
import os
import re
import sys

# Windows GBK 控制台编不出 ✓/✗ 一类符号，而 report() 的 ✗ 分支只在 TIER1>0 时执行——
# 即「恰在检出真凭据」这条最关键的分支上抛 UnicodeEncodeError，报告与 JSON 双双丢失。
# 处置：保持控制台原编码（中文报告对人可读），只把不可编码字符降级转义。
# 门禁绝不因输出编码而中断；机器可读权威件仍由 --json 以 UTF-8 显式落盘。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass

# ---------------------------------------------------------------- 模式库
# 每条：(名称, 正则, 严重度)
# 严重度 "P0" = 真凭据形态（命中即 FAIL）；"P1" = 需人工判读
#
# ★ 自指规避：模式库自身不得携带任何可被自己命中的字面量。
#   正则一律用字符串**拼接**构造，使源码中不出现完整的
#   云厂商 AK 前缀/网关 key 前缀/PEM 头 等字面样本——否则扫描器会把自己判成 FAIL
#   （首版实测 TIER1=3 即此，属工程缺陷而非误报）。
_AK = "AK" + "IA"          # → 云厂商 AKI* 前缀（拼接构造，源码不留完整字面量）
_SK = "s" + "k-"           # → 网关 key 前缀（同上）
_PEM_ANY = (r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRI" + r"VATE KEY-----")

PATTERNS = [
    # --- P0：主流 LLM 网关 key ---
    ("openai_style", r"\b" + _SK + r"[A-Za-z0-9_\-]{28,}", "P0"),
    ("anthropic_style", r"\bsk-ant-[A-Za-z0-9_\-]{24,}", "P0"),
    ("siliconflow_302", r"\b" + _SK + r"[A-Za-z0-9]{40,}\b", "P0"),
    # --- P0：云厂商 AK/SK ---
    ("aws_ak", r"\b" + _AK + r"[0-9A-Z]{16}\b", "P0"),
    ("aliyun_ak", r"\bLTAI[A-Za-z0-9]{12,24}\b", "P0"),
    ("tencent_ak", r"\bAKID[A-Za-z0-9]{13,40}\b", "P0"),
    # --- P0：私钥块（用拼接构造，避免自指） ---
    ("private_key_block", _PEM_ANY, "P0"),
    # --- P0：授权头 ---
    ("bearer_token", r"\bBearer\s+[A-Za-z0-9_\-\.=]{24,}", "P0"),
    ("basic_auth_url", r"://[^/\s:]+:[^/\s@]{6,}@", "P0"),
    # --- P0：超算 / 专用网关（base64 尾缀形态） ---
    ("scnet_style", r"\b" + _SK + r"[A-Za-z0-9+/]{24,}={0,2}\b", "P0"),
    # --- P1：形态可疑但常为占位 ---
    ("generic_hex64", r"\b[0-9a-fA-F]{64}\b", "P1"),
    ("jwt_like", r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b", "P1"),
    ("sendkey_like", r"\bsendkey\b", "P1"),
]

# 上下文降级词：命中行含其一，TIER 降为 P1（不判 FAIL）
# 注意：这里的词只在「**键名/说明性上下文**」中生效，不能在「值本体」中生效。
# 首版把 "example" 一刀切降级，导致某云厂商官方示例 AK 被放行——
# 自检阳性对照当场抓到（判据 76：selftest 失败先疑测试假设）。
BENIGN_CTX = [
    "sha256", "sha3", "sha512", "md5", "digest", "fingerprint", "指纹",
    "示例", "占位", "样例", "placeholder", "dummy", "fake",
    "your-", "xxx", "***", "REDACTED", "已遮", "掩码", "环境变量",
    "os.environ", "getenv", "API_KEY", "_KEY", "键名",
    "test", "assert", "fixture", "TODO", "FIXME", "待填",
]

# 命中值的**本体**若自带示例标记，且不是纯占位符，则仍判 TIER1
#（云厂商官方示例 AK 必须判 FAIL——示例密钥同样在泄露面）
# 纯占位符（xxx / *** / ${VAR}）优先级更高，一律降 P1：否则门禁恒真、形同虚设。
PLACEHOLDER = re.compile(r"(x{3,}|\*{3,}|<[^>]{0,20}>|\$\{[^}]+\})", re.I)
VALUE_MARKERS = re.compile(
    r"(EXAMPLE|SAMPLE|DUMMY|FAKE|CHANGEME|YOUR[_-]?KEY|REPLACE[_-]?ME)", re.I)


def _tier_for(matched: str, tier: str, window: str) -> str:
    """定级优先级：纯占位 > 值本体示例标记 > 上下文键名叙述。

    首版两处缺陷均由阳性对照自检当场抓出：
      ①上下文含 "example" 一律降级 → AWS 官方示例密钥被放行；
      ②把 xxx 也当示例标记 → 占位符反被判 FAIL，门禁恒真。
    """
    if PLACEHOLDER.search(matched):
        return "P1"
    if VALUE_MARKERS.search(matched):
        return tier
    low = window.lower()
    if any(b.lower() in low for b in BENIGN_CTX):
        return "P1"
    return tier

SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist-info", ".idea",
    ".codebuddy", ".specify", "site-packages",
}
BINARY_EXT = {
    ".zip", ".7z", ".rar", ".gz", ".tar", ".bz2", ".xz", ".exe", ".dll",
    ".so", ".dylib", ".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif",
    ".pdf", ".docx", ".xlsx", ".pptx", ".mp4", ".mp3", ".wav", ".sqlite",
    ".db", ".bin", ".iso", ".woff", ".woff2", ".ttf", ".eot",
}
MAX_SCAN_BYTES = 4 * 1024 * 1024  # 单文件超过 4MB 跳过并计数

TIERS = {"P0": [], "P1": []}


def mask(secret: str) -> str:
    """生成掩码：只露首 4 与末 4，长度不足则全掩。"""
    n = len(secret)
    if n <= 10:
        return "*" * n
    return "%s…%s(%d字符)" % (secret[:4], secret[-4:], n)


def digest8(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8", "replace")).hexdigest()[:8]


def looks_benign(line: str) -> bool:
    low = line.lower()
    return any(b.lower() in low for b in BENIGN_CTX)


def scan_text(text: str, fname: str, lineno: int, out):
    for name, pat, tier in PATTERNS:
        for m in re.finditer(pat, text):
            s = m.group(0)
            window = text[max(0, m.start() - 120):m.end() + 120]
            tier_use = _tier_for(s, tier, window)
            out[tier_use].append({
                "file": fname,
                "line": lineno,
                "pattern": name,
                "mask": mask(s),
                "sha256_8": digest8(s),
                "verdict": "真凭据形态-FAIL" if tier_use == "P0" else "疑似-需人工判读",
            })


def scan_file(path: str, root: str, out, stats):
    try:
        if os.path.getsize(path) > MAX_SCAN_BYTES:
            stats["too_big"] += 1
            return
    except OSError:
        stats["unreadable"] += 1
        return
    ext = os.path.splitext(path)[1].lower()
    # Office 容器：解包内文扫描——密钥多藏在正文而非文件名
    if ext in (".docx", ".xlsx", ".pptx"):
        if scan_office(path, root, out, stats):
            return
        # 解包失败不得静默：区分「不是 zip」与「被独占锁定」两种事实
        stats["office_locked_or_bad"] = stats.get("office_locked_or_bad", 0) + 1
        stats["locked_names"].append(os.path.relpath(path, root))
        return
    if ext in BINARY_EXT:
        stats["binary_skipped"] += 1
        return
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        stats["unreadable"] += 1
        return
    stats["text_files"] += 1
    rel = os.path.relpath(path, root)
    for i, line in enumerate(lines, 1):
        if line.strip():
            scan_text(line, rel, i, out)


def scan_office(path: str, root: str, out, stats) -> bool:
    '[withdrawn-document]'
    import zipfile
    rel = os.path.relpath(path, root)
    try:
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist()
                     if n.endswith(".xml") and (
                         n.startswith("word/") or n.startswith("xl/")
                         or n.startswith("ppt/") or n.startswith("docProps"))]
            for n in names:
                raw = z.read(n).decode("utf-8", "replace")
                # 段落/单元格边界转为换行，便于给出行号
                txt = re.sub(r"</(w:p|c|row|a:p)>", "\n", raw)
                txt = re.sub(r"<[^>]+>", "", txt)
                for i, line in enumerate(txt.split("\n"), 1):
                    if line.strip():
                        scan_text(line, "%s!%s" % (rel, n), i, out)
    except Exception:
        return False
    stats["office_unpacked"] = stats.get("office_unpacked", 0) + 1
    stats["text_files"] += 1
    return True


def scan_dir(root: str):
    out = {"P0": [], "P1": []}
    stats = {"text_files": 0, "binary_skipped": 0, "too_big": 0,
             "unreadable": 0, "skipped_dirs": 0, "dirs": 0,
             "office_unpacked": 0, "office_locked_or_bad": 0, "locked_names": []}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if os.path.basename(dirpath) in SKIP_DIRS:
            stats["skipped_dirs"] += 1
            continue
        stats["dirs"] += 1
        for fn in filenames:
            scan_file(os.path.join(dirpath, fn), root, out, stats)
    return out, stats


def report(out, stats, root, verbose=True):
    n0, n1 = len(out["P0"]), len(out["P1"])
    if verbose:
        print("=" * 74)
        print("SC-6 密钥泄漏扫描 · 宪法第一条门禁")
        print("=" * 74)
        print("  目标      : %s" % root)
        print("  文本文件  : %d   （其中 Office 解包 %d）"
              % (stats["text_files"], stats.get("office_unpacked", 0)))
        if stats.get("office_locked_or_bad"):
            print("  ⚠ Office 未能解包（被独占锁定或非 zip）：%d 件 —— 其正文未经本轮扫描"
                  % stats["office_locked_or_bad"])
            for nm in stats.get("locked_names", [])[:6]:
                print("      · %s" % nm[:78])
            print("    （判据 87：报结构事实，不猜测其内容；须待锁定释放后复扫）")
        print("  二进制跳过: %d   超大跳过: %d   不可读: %d   跳过目录: %d"
              % (stats["binary_skipped"], stats["too_big"],
                 stats["unreadable"], stats["skipped_dirs"]))
        print("-" * 74)
        if n0:
            print("  TIER1 真凭据形态（FAIL）：%d" % n0)
            seen = set()
            for h in out["P0"]:
                k = (h["file"], h["line"], h["pattern"])
                if k in seen:
                    continue
                seen.add(k)
                print("    ✗ %s:%d" % (h["file"], h["line"]))
                print("      模式=%s  %s  sha256前8=%s"
                      % (h["pattern"], h["mask"], h["sha256_8"]))
        else:
            print("  TIER1 真凭据形态：无")
        print("-" * 74)
        print("  TIER2 疑似需人工判读：%d" % n1)
        if n1 and verbose:
            byfile = {}
            for h in out["P1"]:
                byfile.setdefault(h["file"], 0)
                byfile[h["file"]] += 1
            for f, c in sorted(byfile.items(), key=lambda x: -x[1])[:12]:
                print("    · %-60s %d 处" % (f[:60], c))
        print("-" * 74)
        verdict = "FAIL" if n0 else "PASS"
        print("  判定 = %s" % verdict)
        print("  （本报告只含掩码与 sha256 前 8 位，不含任何凭据明文）")
    return ("FAIL" if n0 else "PASS"), n0, n1


def selftest():
    """阳性对照（判据 13：幂等须阳性对照 / 判据 76：selftest 失败先疑测试假设）

    每个用例在**独立临时目录**中单独扫描——否则一份真凭据会污染
    同批次其余用例的判定（这正是首版只打印 1 行的原因：真凭据用例
    把整批的 got_fail 拉成 True，另两例的 False 预期随即不成立）。

    ★★ 凭据纪律：本函数内的样本一律用**运行时确定性拼接**生成，
       源码中不得出现任何真实或可还原的凭据明文。
       首版曾把真实硅基流动 Key 与 AWS 示例 Key 直接写进源码，
       随即被本扫描器自身检出（TIER1=7）——工具抓到使用者，
       这正是 SC-6 门禁存在的意义。样本现由 _synth() 现场合成。
    """
    import tempfile

    def _synth(prefix: str, n: int, tail: str = "") -> str:
        """由 前缀 + 确定性填充 + 后缀 现场合成测试样本，源码零明文。"""
        return prefix + ("A" * n) + tail

    cases = [
        ("clean_envref.py", "KEY = os.environ['SILICONFLOW_API_KEY']\n", False),
        ("placeholder.py", "KEY = 'sk-" + "x" * 32 + "'\n", False),
        ("hex_digest.py", "sha256 = '" + "e3b0c44298fc1c14" * 2
         + "9afbf4c8996fb92427ae41e4649b934ca495991b7852b855'\n", False),
        ("synth_llm.py", "KEY = '" + _synth("sk-", 40) + "'\n", True),
        # 云厂商 AK 形态：前缀 + 恰好 16 位大写字母数字，合成串须严格 16 位
        # （首版源串仅 14 位、误拼 21 位，两次都 TIER1=0 —— 是测试假设错，判据 76）
        ("synth_aws.py", "AK = '" + _AK + "SYNTHKEY1234567890"[:16] + "'\n", True),
        ("synth_pem.py", "-----BEGIN RSA " + "PRIVATE KEY-----\nMIIE...\n", True),
    ]
    ok = True
    for name, content, expect_fail in cases:
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, name), "w", encoding="utf-8") as f:
                f.write(content)
            out, _ = scan_dir(td)
            got_fail = len(out["P0"]) > 0
        good = (got_fail == expect_fail)
        ok = ok and good
        print("  %s %-18s 期望 fail=%-5s 实得 fail=%-5s  TIER1=%d TIER2=%d"
              % ("✓" if good else "✗", name, expect_fail, got_fail,
                 len(out["P0"]), len(out["P1"])))

    # --- Office 容器阳性对照：密钥藏在 document.xml 正文，扩展名须解包 ---
    import zipfile
    with tempfile.TemporaryDirectory() as td:
        dp = os.path.join(td, "leaky.docx")
        with zipfile.ZipFile(dp, "w") as z:
            z.writestr("word/document.xml",
                       '<?xml version="1.0"?><w:document><w:body>'
                       '<w:p><w:r><w:t>KEY = "' + _synth("sk-", 40) + '"</w:t></w:r></w:p>'
                       '</w:body></w:document>')
        out, st = scan_dir(td)
        got = len(out["P0"]) > 0
        ok = ok and got
        print("  %s %-18s 期望 fail=%-5s 实得 fail=%-5s  （Office 解包 %d）"
              % ("✓" if got else "✗", "leaky.docx", True, got,
                 st.get("office_unpacked", 0)))

    print("  → %s" % ("全部符合预期" if ok else "存在不符预期用例"))
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("SC-6 扫描器自检（阳性对照）")
        sys.exit(0 if selftest() else 1)

    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", default=".")
    ap.add_argument("--json", dest="jsonout")
    a = ap.parse_args()

    if not os.path.exists(a.target):
        print("目标不存在：%s" % a.target)
        sys.exit(2)
    if os.path.isfile(a.target):
        out = {"P0": [], "P1": []}
        stats = {"text_files": 0, "binary_skipped": 0, "too_big": 0,
                 "unreadable": 0, "skipped_dirs": 0, "dirs": 0}
        scan_file(a.target, os.path.dirname(a.target) or ".", out, stats)
        verdict, n0, n1 = report(out, stats, a.target)
    else:
        out, stats = scan_dir(a.target)
        verdict, n0, n1 = report(out, stats, a.target)

    if a.jsonout:
        with open(a.jsonout, "w", encoding="utf-8") as f:
            json.dump({"verdict": verdict, "tier1": len(out["P0"]),
                       "tier2": len(out["P1"]), "stats": stats,
                       "findings": out}, f, ensure_ascii=False, indent=2)
        print("  → JSON: %s" % a.jsonout)
    sys.exit(1 if verdict == "FAIL" else 0)
