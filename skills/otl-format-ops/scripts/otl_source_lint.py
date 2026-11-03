#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otl_source_lint.py — OTL 主文档静态闸（otl-format-ops 配套）

裁定依据：references/markdown-subset.md。纯标准库，可直接运行。

用法：
    python3 otl_source_lint.py <file.md> [--json]
    python3 otl_source_lint.py --self-test

退出码：0 = 零 error（warning 不阻塞）；1 = 有 error；2 = 用法错误。
"""
import json
import re
import sys
from datetime import datetime

REQUIRED_FIELDS = ["文档标识", "版本", "状态", "更新日期", "责任席", "关联锚点"]
STATUS_WORDS = {"草案", "现行", "归档"}
CHANGELOG_RE = re.compile(r"^#{2,3}\s+(变更记录|CHANGELOG|更新记录)\s*$", re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)[^)]*\)")
IMG_HTML_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.IGNORECASE)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BOX_CHARS = re.compile(r"[┌┍┎┏┐┑┒┓└┕┖┗┘┙┚┛├┝┞┟┠┡┢┣┤┥┦┧┨┩┪┫┬┭┮┯┰┱┲┳┴┵┶┷┸┹┺┻┼┽┾┿╀╁╂╃╄╅╆╇╈╉╊╋═║╒╓╔╕╖╗╘╙╚╛╜╝╞╟╠╡╢╣╤╥╦╧╨╩╪╫╬─━│┃]")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def lint_text(text, name="<text>"):
    """对主文档文本执行全部检查，返回 (errors, warnings)。每项为 dict。"""
    errors, warnings = [], []

    def err(code, line, msg):
        errors.append({"code": code, "line": line, "msg": msg})

    def warn(code, line, msg):
        warnings.append({"code": code, "line": line, "msg": msg})

    lines = text.split("\n")

    # ---- 状态机：围栏代码块 ------------------------------------------------
    in_fence = False
    fence_marker = None
    fence_start = 0
    fence_lines = set()       # 处于围栏内的行号（1 起）
    headings = []             # (line_no, level, title)
    h1_lines = []

    for i, raw in enumerate(lines, start=1):
        m = FENCE_RE.match(raw)
        if m:
            marker = m.group(1)[0] * 3
            if not in_fence:
                in_fence, fence_marker, fence_start = True, marker, i
            elif raw.strip().startswith(fence_marker):
                in_fence, fence_marker = False, None
            fence_lines.add(i)
            continue
        if in_fence:
            fence_lines.add(i)
            continue

        hm = HEADING_RE.match(raw)
        if hm:
            level = len(hm.group(1))
            headings.append((i, level, hm.group(2).strip()))
            if level == 1:
                h1_lines.append(i)

        # W01 裸 Tab
        if "\t" in raw:
            warn("W01", i, "正文含裸 Tab 字符，缩进请用列表层级")
        # W02 超长行
        if len(raw) > 300:
            warn("W02", i, f"单行 {len(raw)} 字符超 300，云端阅读与 diff 不友好")
        # E06 制表图裸露（剔除行内代码段后检测）
        stripped = INLINE_CODE_RE.sub("", raw)
        bm = BOX_CHARS.search(stripped)
        if bm:
            err("E06", i, f"制表字符「{bm.group(0)}」裸露在围栏代码块外，写入 OTL 会错位；整段请用 ```text 围栏包裹")
        # E07 图片源
        for src in IMAGE_RE.findall(raw) + IMG_HTML_RE.findall(raw):
            if src.startswith("data:"):
                if len(src) > 100_000:
                    warn("W04", i, f"base64 图片 {len(src)} 字符超 10 万，主文档防膨胀，请改公网直链")
            elif src.startswith("http://"):
                warn("W03", i, f"图片使用 http://（{src[:60]}…），建议 https://")
            elif not src.startswith("https://"):
                err("E07", i, f"图片源「{src[:60]}」非 https:// 公网直链或 data: URI，OTL 无法取图")

    # E08 围栏未闭合
    if in_fence:
        err("E08", len(lines), f"围栏代码块自第 {fence_start} 行起未闭合")

    # ---- E01 H1 规则 -------------------------------------------------------
    first_nonempty = next((i for i, l in enumerate(lines, start=1) if l.strip()), None)
    if first_nonempty is None:
        err("E01", 0, "文档为空")
        return errors, warnings
    if not lines[first_nonempty - 1].startswith("# "):
        err("E01", first_nonempty, "首个非空行必须是一级标题（# 文档标题）")
    if len(h1_lines) != 1:
        err("E01", h1_lines[1] if len(h1_lines) > 1 else first_nonempty,
            f"H1 必须恰好一个（当前 {len(h1_lines)} 个）；正文标题请从 ## 起")

    # ---- E05 标题层级 ------------------------------------------------------
    prev = 1
    for line_no, level, _title in headings:
        if line_no in h1_lines[:1]:
            prev = 1
            continue
        if level > prev + 1:
            err("E05", line_no, f"标题跳级：H{prev} 之后直接 H{level}，请逐级加深")
        prev = level

    # ---- E02 文档头六要素 ---------------------------------------------------
    first_h2 = next((ln for ln, lv, _ in headings if lv == 2), None)
    header_region_end = first_h2 if first_h2 else len(lines) + 1
    fields = {}
    for i in range(first_nonempty + 1, header_region_end - 1 + 1):
        raw = lines[i - 1]
        if not raw.strip().startswith("|"):
            continue
        cells = [c.strip() for c in raw.strip().strip("|").split("|")]
        if not cells or all(set(c) <= set("-: ") for c in cells):
            continue  # 分隔行
        if cells[0] == "字段":
            continue  # 表头行
        if len(cells) >= 2:
            fields[cells[0]] = (i, cells[1])
    missing = [f for f in REQUIRED_FIELDS if f not in fields]
    if missing:
        err("E02", first_nonempty, f"文档头表缺少必填字段：{'、'.join(missing)}（须紧随 H1 的表格中六要素齐备）")
    else:
        # E03 状态词
        ln, val = fields["状态"]
        if val not in STATUS_WORDS:
            err("E03", ln, f"状态「{val}」不在词表内（草案/现行/归档）")
        # E04 日期（模板占位符 YYYY-MM-DD 豁免）
        ln, val = fields["更新日期"]
        if val == "YYYY-MM-DD":
            pass
        elif not DATE_RE.match(val):
            err("E04", ln, f"更新日期「{val}」不是 YYYY-MM-DD 格式")
        else:
            try:
                datetime.strptime(val, "%Y-%m-%d")
            except ValueError:
                err("E04", ln, f"更新日期「{val}」不是有效日期")

    # ---- E09 变更记录 -------------------------------------------------------
    if not any(CHANGELOG_RE.match(l.strip()) for l in lines):
        err("E09", 0, "缺少「## 变更记录」节（亦接受 CHANGELOG/更新记录）")

    return errors, warnings


GOOD_SAMPLE = """# 示例项目文书

| 字段 | 内容 |
|------|------|
| 文档标识 | OTL-TST-001 |
| 版本 | v0.1.0 |
| 状态 | 草案 |
| 更新日期 | 2026-10-01 |
| 责任席 | 测试席 |
| 关联锚点 | otl-format-ops |

## 第一节

正文段落，含 [公网链接](https://example.com)。

### 子节

```text
┌────┐
│ 图 │
└────┘
```

![示意图](https://example.com/a.png)

## 变更记录

| 版本 | 日期 | 变更摘要 | 责任席 |
|------|------|----------|--------|
| v0.1.0 | 2026-10-01 | 初版 | 测试席 |
"""

BAD_SAMPLE = """# 标题一

| 字段 | 内容 |
|------|------|
| 文档标识 | X |
| 版本 | v1 |
| 状态 | 随便 |
| 更新日期 | 昨天 |
| 责任席 | 某 |
| 关联锚点 | 某 |

# 标题二

正文。

### 跳级标题

┌───┐ 裸露制表图

![本地图](images/a.png)

```text
未闭合的围栏
"""


def self_test():
    ok = True
    e1, _ = lint_text(GOOD_SAMPLE, "GOOD")
    if e1:
        ok = False
        print("SELF-TEST FAIL: GOOD 样本不应有 error，实际：", json.dumps(e1, ensure_ascii=False))
    e2, _ = lint_text(BAD_SAMPLE, "BAD")
    got = {e["code"] for e in e2}
    want = {"E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08", "E09"}
    # BAD 的文档头六要素齐全（值非法），故 E02 不触发属预期，从 want 剔除
    want.discard("E02")
    missing = want - got
    if missing:
        ok = False
        print("SELF-TEST FAIL: BAD 样本未触发预期检查：", sorted(missing), "实际：", sorted(got))
    print("SELF-TEST", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    if "--self-test" in flags:
        return 0 if self_test() else 1
    if len(args) != 1:
        print(__doc__)
        return 2
    path = args[0]
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"无法读取 {path}: {e}")
        return 2
    errors, warnings = lint_text(text, path)
    if "--json" in flags:
        print(json.dumps({"file": path, "ok": not errors,
                          "errors": errors, "warnings": warnings},
                         ensure_ascii=False, indent=2))
    else:
        for e in errors:
            print(f"[{e['code']}] 行{e['line']}: {e['msg']}")
        for w in warnings:
            print(f"[{w['code']}] 行{w['line']}: {w['msg']}")
        print(f"{'FAIL' if errors else 'PASS'} — {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
