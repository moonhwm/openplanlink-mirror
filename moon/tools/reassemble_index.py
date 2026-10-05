#!/usr/bin/env python3
"""reassemble_index.py — 由 index.skeleton.html + 负载目录逐字节重组 index.html
用法: python3 reassemble_index.py <skeleton> <payload_dir> <out.html>
骨架中的 data:;base64,#sha12=<h> 占位符按 payloads-manifest.json 顺序替换回真实 data-URI。
验收: 重组结果 sha3-256[:12] 必须等于 82e6e1699e52, 字节数 3972777。"""
import sys, json, base64, hashlib, os, re

def sha12(b): return hashlib.sha3_256(b).hexdigest()[:12]

skel_path, paydir, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
skel = open(skel_path,'rb').read()
meta = json.load(open(os.path.join(paydir,'payloads-manifest.json'),'rb'))
out, pos, n = bytearray(), 0, 0
ph = re.compile(rb'data:;base64,#sha12=([0-9a-f]{12})')
for m in ph.finditer(skel):
    out += skel[pos:m.start()]
    e = meta['payloads'][n]
    assert e['sha12'] == m.group(1).decode(), f'order/hash mismatch at {n}'
    raw = open(os.path.join(paydir, e['file']),'rb').read()
    assert sha12(raw) == e['sha12'] and len(raw) == e['bytes'], f'payload {e["file"]} corrupt'
    out += b'data:image/jpeg;base64,' + base64.b64encode(raw)
    pos = m.end(); n += 1
out += skel[pos:]
assert n == len(meta['payloads']), f'{n} placeholders != {len(meta["payloads"])} payloads'
open(out_path,'wb').write(bytes(out))
print('reassembled:', len(out), 'B, sha12 =', sha12(bytes(out)))
assert sha12(bytes(out)) == meta['expect_sha12'] and len(out) == meta['expect_bytes'], 'MISMATCH vs manifest expectation'
print('BYTE-EXACT OK')
