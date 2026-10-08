#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P6 掩码基线探针（opl-document-preflight 监测层，参数化版）。

目的：复合文档（如 docx）的 docProps/custom.xml 发生等长替换（Δsize=0 而
zip_crc 变）时，无字段级留存则不可归因。本探针建立掩码基线：每个 custom
属性只记名称、值字节长、值 sha3_512_16；core.xml 的 creator/lastModifiedBy
/created/modified/revision 同法。真值一律不落盘。

用法：
  python scripts/p6_custom_probe.py --target <docx路径> --out-dir <输出目录> --label <轮次标签>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import zipfile
import xml.etree.ElementTree as ET

CUST_NS = ("{http://schemas.openxmlformats.org/officeDocument/2006/"
           "custom-properties}")


def h16(b: bytes) -> str:
    return hashlib.sha3_512(b).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser(description="P6 掩码基线探针")
    ap.add_argument("--target", required=True, help="被检复合文档路径")
    ap.add_argument("--out-dir", required=True, help="产物输出目录")
    ap.add_argument("--label", required=True, help="轮次标签，如 run15")
    args = ap.parse_args()

    target = pathlib.Path(args.target)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rec = {"schema": "p6-custom-probe/1", "label": args.label,
           "file": target.name,
           "sha3_512_16": h16(target.read_bytes()),
           "bytes": target.stat().st_size, "custom": [], "core": []}
    with zipfile.ZipFile(target) as z:
        names = set(z.namelist())
        if "docProps/custom.xml" in names:
            root = ET.fromstring(z.read("docProps/custom.xml"))
            for prop in root.findall(CUST_NS + "property"):
                name = prop.get("name")
                val_el = list(prop)
                raw = (ET.tostring(val_el[0], encoding="unicode")
                       if val_el else "")
                vb = raw.encode("utf-8")
                rec["custom"].append({"name": name, "value_len": len(vb),
                                      "value_sha3_16": h16(vb)})
        if "docProps/core.xml" in names:
            root = ET.fromstring(z.read("docProps/core.xml"))
            for el in root.iter():
                tag = el.tag.split("}")[-1]
                if tag in ("creator", "lastModifiedBy", "created",
                           "modified", "revision"):
                    vb = (el.text or "").encode("utf-8")
                    rec["core"].append({"field": tag, "value_len": len(vb),
                                        "value_sha3_16": h16(vb)})
    op = out_dir / f"p6_custom_props_{args.label}.json"
    op.write_text(json.dumps(rec, ensure_ascii=False, indent=2),
                  encoding="utf-8")
    print(f"-> {op.name} custom={len(rec['custom'])} core={len(rec['core'])} "
          f"bytes={rec['bytes']} sha3_16={rec['sha3_512_16']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
