#!/usr/bin/env python3
"""reassemble_index.py — 由 index.skeleton.html + 负载目录逐字节重组 index.html
用法: python3 reassemble_index.py <skeleton> <payload_dir> <out.html>
骨架中的 data:;base64,#sha12=<h> 占位符按 payloads-manifest.json 顺序替换回真实 data-URI。
验收: 重组结果 sha3-256[:12] 必须等于 82e6e1699e52, 字节数 3972777。"""
import sys, json, base64, hashlib, os, re
from pathlib import Path

def sha12(b): return hashlib.sha3_256(b).hexdigest()[:12]

# 路径闸（2026-10-09 本席自修，范式同 burn/skills-sample/ls-bus-format-ops/scripts/lsbus.py v1.4）：
# 输入层拒上跳分量与空字节 → normpath/abspath 归一 → 写目标再过根白名单前缀比对。
# 修前缺陷：out_path 直接取自 sys.argv[3] 未校验即落盘，属任意路径写（Mimosa L3 高危，认定成立）。
OUT_ROOTS = [os.path.abspath('moon'), os.path.abspath('deliverables'),
             os.path.abspath(os.curdir), os.path.abspath(os.environ.get('TEMP', os.curdir))]

def _reject_upward(raw, label):
    text = str(raw)
    if '\x00' in text:
        raise ValueError('null byte blocked in %s' % label)
    if any(part == os.pardir for part in text.replace(chr(92), '/').split('/')):
        raise ValueError('upward component blocked in %s' % label)
    return text

def _safe_out(raw):
    """写目标：三重校验后必须落在 OUT_ROOTS 之一。"""
    _reject_upward(raw, 'out')
    ap = os.path.normpath(os.path.abspath(str(raw)))
    for root in OUT_ROOTS:
        rr = os.path.normpath(os.path.abspath(root))
        if ap == rr or ap.startswith(rr + os.sep):
            return ap
    raise ValueError('outside allowed out roots: out')

def _safe_in(raw, label):
    """读目标：拒上跳分量与空字节后归一（读面不设白名单，但不得越出所指目录树之上）。"""
    _reject_upward(raw, label)
    return os.path.normpath(os.path.abspath(str(raw)))

skel_path, paydir, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
skel = Path(_safe_in(skel_path, 'skeleton')).read_bytes()
meta = json.loads(Path(_safe_in(os.path.join(paydir, 'payloads-manifest.json'), 'manifest')).read_bytes().decode('utf-8'))
out, pos, n = bytearray(), 0, 0
ph = re.compile(rb'data:;base64,#sha12=([0-9a-f]{12})')
for m in ph.finditer(skel):
    out += skel[pos:m.start()]
    e = meta['payloads'][n]
    assert e['sha12'] == m.group(1).decode(), f'order/hash mismatch at {n}'
    raw = Path(_safe_in(os.path.join(paydir, e['file']), 'payload')).read_bytes()
    assert sha12(raw) == e['sha12'] and len(raw) == e['bytes'], f'payload {e["file"]} corrupt'
    out += b'data:image/jpeg;base64,' + base64.b64encode(raw)
    pos = m.end(); n += 1
out += skel[pos:]
assert n == len(meta['payloads']), f'{n} placeholders != {len(meta["payloads"])} payloads'
Path(_safe_out(out_path)).write_bytes(bytes(out))
print('reassembled:', len(out), 'B, sha12 =', sha12(bytes(out)))
assert sha12(bytes(out)) == meta['expect_sha12'] and len(out) == meta['expect_bytes'], 'MISMATCH vs manifest expectation'
print('BYTE-EXACT OK')
