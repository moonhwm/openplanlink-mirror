#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""opl_docx_refresh.py —— 母本刷新一键件（顾权 2026-10-06 夜场工艺工具化）

每轮游乐场重读之母本面：stat+sha256 → 与锚点账比对 → 变则 保真抽取(regex 标准法)→遮蔽→diff→落新版。
用法: python opl_docx_refresh.py            # 全环（有变化才抽取+diff）
      python opl_docx_refresh.py --check    # 只报 stat/hash，不抽取
锚点账: _anchors.json（同目录，自动维护）。
"""
import difflib
import hashlib
import json
import os
import re
import sys
import zipfile

DOCX = r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\Plan提示词工程\openplanlink-docx\2026-9-25-OpenPlanLink 润色-1 (3).docx"
OUT = r"C:\Users\欧阳宏俊\Documents\kimi\quant-lab\output\desktop_cleanup_20261003"
ANCHORS = os.path.join(OUT, "_anchors.json")
MASKS = [("hsjeyh", "硅基流动"), ("5982", "302.AI"), ("Mzkx", "国家超算")]


def sha256_16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def extract(path):
    z = zipfile.ZipFile(path)
    xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"<w:del\b[^>]*>.*?</w:del>", "", xml, flags=re.S)
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
    out = []
    for para in paras:
        line = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", para, re.S))
        if line.strip():
            out.append(line)
    return out


def mask(text):
    n = 0
    for pref, nm in MASKS:
        text, k = re.subn(r"sk-" + pref + r"[A-Za-z0-9+/=:]*", f"sk-{pref}…[{nm}，已遮蔽]", text)
        n += k
    text, k = re.subn(r"sk-[A-Za-z0-9][A-Za-z0-9+/=:_-]{18,}", "sk-…[未名池，已遮蔽]", text)
    n += k
    left = len(re.findall(r"sk-[A-Za-z0-9][A-Za-z0-9+/=:_-]{18,}", text))
    return text, n, left


def main():
    check_only = "--check" in sys.argv
    st = os.stat(DOCX)
    cur = {"mtime": st.st_mtime, "size": st.st_size, "sha16": sha256_16(DOCX)}
    anchors = json.load(open(ANCHORS, encoding="utf-8")) if os.path.exists(ANCHORS) else {"versions": []}
    last = anchors["versions"][-1] if anchors["versions"] else None
    print(f"现行: mtime={cur['mtime']:.0f} size={cur['size']} sha16={cur['sha16']}")
    if last:
        print(f"上锚: {last['tag']} size={last['size']} sha16={last['sha16']}")
    if check_only:
        return
    if last and last["sha16"] == cur["sha16"] and last["size"] == cur["size"]:
        print("判定: 与上锚全等——本轮空转，不抽取。")
        return
    ver = len(anchors["versions"]) + 5  # v5 起（v1–v4 已在账外）
    tag = f"v{ver}_{cur['sha16'][:8]}"
    paras = extract(DOCX)
    text, nmask, left = mask("\n".join(paras))
    outpath = os.path.join(OUT, f"OpenPlanLink润色1-3_fulltext_FINAL_{tag}.txt")
    with open(outpath, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"抽取: 段数={len(paras)} 字符={len(text)} 遮蔽={nmask} 复扫={left} 落盘={os.path.basename(outpath)}")
    if last and os.path.exists(last.get("path", "")):
        old = open(last["path"], encoding="utf-8").read().split("\n")
        sm = difflib.SequenceMatcher(None, old, text.split("\n"))
        ndiff = 0
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op != "equal":
                ndiff += 1
                print(f"  diff[{ndiff}] {op} old[{i1}:{i2}] new[{j1}:{j2}]")
        if ndiff == 0:
            print("判定: docx 变而文本零差异（元数据触写类）。")
    anchors["versions"].append({"tag": tag, "path": outpath, **cur})
    with open(ANCHORS, "w", encoding="utf-8") as f:
        json.dump(anchors, f, ensure_ascii=False, indent=1)
    print(f"锚点账已记: {tag}")


if __name__ == "__main__":
    main()
