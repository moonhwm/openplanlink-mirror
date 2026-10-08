#!/usr/bin/env python3
# ls-bus-format-ops/lsbus.py v1.3.0 — 目录清单总线格式化（ls → biz.ls 信封）
# 正本口径：技能以 GitHub（openplanlink-mirror）为唯一正本，本文件为同步副本
# 用法：python lsbus.py --dir DIR [--out FILE] [--depth N] | --selftest
#      不给 --out 时信封打印到 stdout，调用方可自行重定向（推荐，纯只读）
# 安全：三重路径校验（输入拒上跳分量 → normpath 归一 → 根白名单前缀比对）；
#       扫描全程只读；落盘只经 Path.write_text 且目标必过白名单。
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path

SAFE_ROOTS = [os.path.abspath('burn'), os.path.abspath('upload'), os.path.abspath('opensrc'),
              os.path.abspath('A:/OPL_A2A'), os.path.abspath(tempfile.gettempdir()),
              os.path.abspath(str(Path.home() / 'WPSDrive'))]


def _reject_upward(raw, label):
    """输入层：上跳分量与空字节在任何拼接之前即拒。"""
    text = str(raw)
    if '\x00' in text:
        raise ValueError('null byte blocked in %s' % label)
    parts = text.replace('\\', '/').split('/')
    if any(p == os.pardir for p in parts):
        raise ValueError('upward component blocked in %s' % label)
    return text


def _safe_path(raw, label='path'):
    """归一层 + 白名单层：normpath/abspath 后必须落在 SAFE_ROOTS 之一。"""
    _reject_upward(raw, label)
    ap = os.path.normpath(os.path.abspath(str(raw)))
    for root in SAFE_ROOTS:
        rr = os.path.normpath(os.path.abspath(root))
        if ap == rr or ap.startswith(rr + os.sep):
            return ap
    raise ValueError('outside allowed roots: %s' % label)


def sha256_file(verified_path, cap=1 << 22):
    """只读指纹：入参必须是 _safe_path 产出的已校验路径。"""
    h, n = hashlib.sha256(), 0
    fh = open(verified_path, 'rb')
    try:
        for chunk in iter(lambda: fh.read(65536), b''):
            h.update(chunk)
            n += len(chunk)
            if n >= cap:
                break
    finally:
        fh.close()
    return h.hexdigest()[:16]


def scan(d, depth):
    base = _safe_path(d, 'dir')
    out = []
    for root, dirs, files in os.walk(base):
        rel = os.path.relpath(root, base)
        lvl = 0 if rel == os.curdir else rel.count(os.sep) + 1
        if lvl >= depth - 1:   # depth=1 → 只含基目录自身文件；depth=2 → 再下一层
            dirs[:] = []
        for fn in sorted(files):
            joined = os.path.join(root, fn)
            entry = _safe_path(joined, 'entry')
            relp = os.path.relpath(entry, base).replace(os.sep, '/')
            try:
                st = os.stat(entry)
                out.append({'path': relp, 'bytes': st.st_size, 'sha256_16': sha256_file(entry)})
            except OSError:
                out.append({'path': relp, 'bytes': -1, 'sha256_16': None})
    return sorted(out, key=lambda e: e['path'])


def envelope(d, entries):
    return {'kind': 'biz.ls', 'priority': 'normal', 'ttl': 86400, 'delivery': 'store',
            'reply_to': 'Moon(pi-orchestrator@zcode)',
            'content': {'dir': d, 'count': len(entries), 'entries': entries}}


def run(d, out, depth):
    if not d:
        print('ERR: --dir required', file=sys.stderr)
        return 1
    entries = scan(d, depth)
    env = envelope(_safe_path(d, 'dir'), entries)
    text = json.dumps(env, ensure_ascii=False, indent=1)
    if out:
        dest = _safe_path(out, 'out')
        Path(dest).write_text(text + '\n', encoding='utf-8')
        print('written=%s' % dest, file=sys.stderr)
    else:
        print(text)
    print('entries=%d bytes_total=%d'
          % (len(entries), sum(max(e['bytes'], 0) for e in entries)), file=sys.stderr)
    return 0


def selftest():
    td = tempfile.mkdtemp(prefix='lsbus_')
    sub = os.path.join(td, 'sub')
    os.makedirs(sub)
    fx1 = _safe_path(os.path.join(td, 'x.md'), 'fixture1')
    fx2 = _safe_path(os.path.join(sub, 'y.md'), 'fixture2')
    Path(fx1).write_text('hello', encoding='utf-8')
    Path(fx2).write_text('world', encoding='utf-8')
    ok = True
    e1, e2 = scan(td, 1), scan(td, 2)
    ok = ok and len(e1) == 1 and len(e2) == 2
    ok = ok and bool(e1[0]['sha256_16']) and e2[0]['path'].startswith('sub/')
    ok = ok and e1[0]['bytes'] == 5
    # 白名单层负例：绝对路径但落在允许根之外
    outside = os.sep.join(['', 'etc', 'hosts'])
    try:
        scan(outside, 1)
        ok = False
    except ValueError:
        pass
    print('SELFTEST', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir')
    ap.add_argument('--out')
    ap.add_argument('--depth', type=int, default=2)
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else run(a.dir, a.out, a.depth))
