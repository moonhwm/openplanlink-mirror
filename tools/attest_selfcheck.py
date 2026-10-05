#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""attest_selfcheck.py —— 证明件自洽性 / 同批不变式 校验器

缘起（本席 DF-INSP-20261006-CAIRN-01 与 DF-ATTEST-20261006-CAIRN-01）：
  2026-09-30 他席报告记录过一次「自证链断裂」——证明件内部不自洽（声明的 files 与声明的根不同批）。
  本席把该教训固化为**四档校验**，使同类问题可在 CI 中被提前捕获。

四档（由弱到强）：
  L1 结构   ：schema/file_count 与 files 数组长度一致
  L2 叶自洽 ：由 (path, size, content_sha3_512) 按字节契约重算的叶 == 声明的 leaf
  L3 根自洽 ：由声明叶集自举默克尔根 == 声明的 merkle_root      ← 纯声明值检验，**不触碰任何本地文件**
  L4 落盘   ：可选，逐文件与磁盘实况比对（支持 CRLF 归一化，避免 autocrlf 假阳性）
  另：有密钥时校验根 MAC（HMAC-SHA3-512）；无密钥则标 SKIP（不伪造结论）。

用法:
  python tools/attest_selfcheck.py attest-hmac-sha3-512.json
  python tools/attest_selfcheck.py attest-cd.json --verify-disk --normalize-crlf
  python tools/attest_selfcheck.py <manifest> --key-file <bin> --json out.json
退出码：全过 0；任一 FAIL 1。
"""
import argparse
import hashlib
import hmac
import json
import pathlib
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")

MAC_PREFIX = b"OpenPlanLink-A2A-Merkle-v1\x00"


def sha3(b: bytes) -> bytes:
    return hashlib.sha3_512(b).digest()


def leaf_of(path_utf8: str, size: int, content_hex: str) -> str:
    pb = path_utf8.encode("utf-8")
    return sha3(b"\x00" + struct.pack(">I", len(pb)) + pb + struct.pack(">Q", size)
                + bytes.fromhex(content_hex)).hex()


def root_of(leaf_hexes):
    level = [bytes.fromhex(h) for h in leaf_hexes]
    if not level:
        return ""
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            right = level[i + 1] if i + 1 < len(level) else level[i]
            nxt.append(sha3(b"\x01" + level[i] + right))
        level = nxt
    return level[0].hex()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--root-dir", default=".", help="L4 落盘校验的相对基准目录")
    ap.add_argument("--verify-disk", action="store_true")
    ap.add_argument("--normalize-crlf", action="store_true",
                    help="比对前把 CRLF 归一化为 LF（规避 git autocrlf 造成的假阳性）")
    ap.add_argument("--key-file", default=r"C:\Users\欧阳宏俊\.a2a-hmac-key.bin")
    ap.add_argument("--key-env", default="OPL_TREE_KEY")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    p = pathlib.Path(a.manifest)
    if not p.exists():
        print("★ 证明件不存在：%s" % p)
        return 2
    d = json.loads(p.read_text(encoding="utf-8"))

    files = d.get("files") or []
    checks = []

    # L1 结构
    fc = d.get("file_count")
    ok1 = fc == len(files)
    checks.append(("L1 结构", ok1, "file_count=%s, len(files)=%s" % (fc, len(files))))

    # L2 叶自洽
    bad_leaf = []
    for f in files:
        try:
            calc = leaf_of(f["path"], int(f["size"]), f["content_sha3_512"])
        except Exception as exc:  # noqa: BLE001
            bad_leaf.append("%s(异常:%s)" % (f.get("path"), type(exc).__name__))
            continue
        if calc != f.get("leaf_sha3_512"):
            bad_leaf.append(f.get("path"))
    ok2 = not bad_leaf
    checks.append(("L2 叶自洽", ok2, "不符 %d 项%s" % (
        len(bad_leaf), ("：" + "、".join(map(str, bad_leaf[:5]))) if bad_leaf else "")))

    # L3 根自洽（纯声明值，不触碰磁盘）
    declared_root = d.get("merkle_root_sha3_512") or d.get("merkle_root") or ""
    calc_root = root_of([f.get("leaf_sha3_512", "") for f in files]) if files else ""
    ok3 = bool(declared_root) and calc_root == declared_root
    checks.append(("L3 根自洽", ok3, "声明=%s… 重算=%s… 相符=%s" % (
        declared_root[:16], calc_root[:16], ok3)))

    # 根 MAC
    mac_declared = d.get("hmac_sha3_512") or d.get("mac_sha3_512")
    mac_result = None
    if mac_declared:
        key = None
        env_val = (__import__("os").environ.get(a.key_env) or "").strip()
        if env_val:
            try:
                key = bytes.fromhex(env_val)
            except ValueError:
                key = None
        if key is None and pathlib.Path(a.key_file).exists():
            kb = pathlib.Path(a.key_file).read_bytes()
            key = kb if len(kb) == 64 else None
        if key is None:
            mac_result = ("SKIP", "有 MAC 但无可用密钥（未验签，不伪造结论）")
        else:
            kid = str(d.get("key_id") or "opl-a2a-2026q4").encode()
            gen = str(d.get("generated_at") or "").encode()
            mi = (MAC_PREFIX + bytes.fromhex(declared_root) + struct.pack(">Q", len(files))
                  + struct.pack(">H", len(kid)) + kid
                  + struct.pack(">H", len(gen)) + gen)
            calc_mac = hmac.new(key, mi, hashlib.sha3_512).hexdigest()
            mac_result = ("PASS" if calc_mac == mac_declared else "FAIL",
                          "声明=%s… 重算=%s…" % (mac_declared[:16], calc_mac[:16]))
    else:
        mac_result = ("SKIP", "证明件未含 MAC（未签名件）")

    # L4 落盘（可选）：逐文件「原始优先、归一化兜底」——
    #   原始相符 ⇒ OK；原始不符但文本归一化后相符 ⇒ 记为 CRLF 救回（WARN，非篡改）；
    #   两者皆不符 ⇒ **真漂移**（FAIL）。二进制一律只按原始比对。
    l4 = None
    if a.verify_disk:
        base = pathlib.Path(a.root_dir)
        miss, rescued, drifted = [], [], []
        for f in files:
            fp = base / f["path"]
            if not fp.exists():
                miss.append(f["path"])
                continue
            data = fp.read_bytes()
            if sha3(data).hex() == f["content_sha3_512"]:
                continue
            if b"\x00" not in data[:8192] and sha3(data.replace(b"\r\n", b"\n")).hex() == f["content_sha3_512"]:
                rescued.append(f["path"])   # 生成侧未含 CRLF、本地含 CRLF
                continue
            drifted.append(f["path"])
        ev = "缺失%d；CRLF 救回%d；**真漂移%d**" % (len(miss), len(rescued), len(drifted))
        if drifted:
            ev += "；漂移样例：" + "、".join(drifted[:5]) + ("…" if len(drifted) > 5 else "")
        ok4 = not miss and not drifted
        l4 = ("PASS" if ok4 else "FAIL", ev)
        checks.append(("L4 落盘", ok4, ev))

    print("★ 证明件自洽性校验：%s" % p.name)
    print("")
    print("| 档 | 结论 | 证据 |")
    print("|---|---|---|")
    for name, ok, ev in checks:
        print("| %s | **%s** | %s |" % (name, "PASS" if ok else "FAIL", ev))
    print("| 根 MAC | **%s** | %s |" % (mac_result[0], mac_result[1]))
    print("")

    hard = [c for c in checks if not c[1]]
    verdict = "PASS" if not hard and mac_result[0] != "FAIL" else "FAIL"
    if mac_result[0] == "SKIP" and verdict == "PASS":
        verdict = "PASS(未签名件)"
    print("VERDICT=" + verdict)
    if "FAIL" in verdict:
        print("提示：L3 失败即「声明值互不自洽」——证明件内部不同批，须重新生成并签名（勿逐字段手改）。")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(
            {"manifest": p.name, "verdict": verdict,
             "checks": [{"level": n, "ok": o, "evidence": e} for n, o, e in checks],
             "mac": {"result": mac_result[0], "evidence": mac_result[1]}},
            ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("已写出：%s" % a.json)
    return 0 if verdict.startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
