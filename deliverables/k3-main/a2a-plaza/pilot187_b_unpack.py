# -*- coding: utf-8 -*-
"""批次B（92件zip容器）方案①：解包提取内部 SKILL.md / README 等文本索引件 -> .txt
留痕：pilot187_b_unpack.json（每件：容器、提取文件、sha256、字节数；跳过原因）
内容零改动，仅扩展名转为 ima preflight 支持的 .txt
"""
import zipfile, json, hashlib, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAZA = os.path.dirname(os.path.abspath(__file__))
plan = json.load(open(os.path.join(PLAZA, 'pilot187_batch.json'), encoding='utf-8'))
B = plan['B_deferred']
OUT = os.path.join(PLAZA, 'pilot187_b_txt')
os.makedirs(OUT, exist_ok=True)

# 容器内优先级：SKILL.md > README* > *.md 首件；每容器最多提 2 件文本
def pick(names):
    names = [n for n in names if not n.endswith('/')]
    sk = [n for n in names if os.path.basename(n).lower() == 'skill.md']
    if sk: return sk[:2]
    rd = [n for n in names if os.path.basename(n).lower().startswith('readme')]
    if rd: return rd[:2]
    md = [n for n in names if n.lower().endswith('.md')]
    if md: return md[:2]
    return []

manifest = []
for rel in B:
    src = os.path.join(ROOT, rel)
    base = os.path.splitext(os.path.basename(rel))[0]
    entry = {'container': rel, 'extracted': [], 'skipped': None}
    try:
        with zipfile.ZipFile(src) as z:
            names = z.namelist()
            picks = pick(names)
            if not picks:
                entry['skipped'] = 'no text entry (names=%d)' % len(names)
                manifest.append(entry); continue
            for n in picks:
                data = z.read(n)
                inner = os.path.basename(n)
                dst_name = f"{base}__{inner}.txt"
                dst = os.path.join(OUT, dst_name)
                with open(dst, 'wb') as f:
                    f.write(data)
                entry['extracted'].append({
                    'inner': n, 'dst': os.path.relpath(dst, ROOT),
                    'sha256': hashlib.sha256(data).hexdigest(),
                    'size': len(data)})
    except zipfile.BadZipFile:
        entry['skipped'] = 'not a zip container'
    except Exception as e:
        entry['skipped'] = f'error: {e}'
    manifest.append(entry)

with open(os.path.join(PLAZA, 'pilot187_b_unpack.json'), 'w', encoding='utf-8') as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)

ok = sum(1 for m in manifest if m['extracted'])
skip = [m for m in manifest if m['skipped']]
print(f'containers={len(manifest)} extracted_ok={ok} skipped={len(skip)}')
for m in skip:
    print('SKIP', m['container'], '->', m['skipped'])
