#!/usr/bin/env python3
"""SHA3-256 身份与完整性工具（守藏席约定：身份散列只用 SHA3-256，不用 SHA3-512）。

用法：
  python3 sha3_256.py text "待散列串"        # 打印 SHA3-256
  python3 sha3_256.py file <路径> [...]      # 打印文件 SHA3-256（逐个）
  python3 sha3_256.py manifest <目录>        # 生成 sha3-256 清单（相对路径<TAB>哈希）
  python3 sha3_256.py verify-seat "待核验串"  # 与 canonical 席位锚点比对（不明文存储任何账号）
  python3 sha3_256.py selftest              # 已知答案测试（公开测试向量）

约定（R29 起）：任何账号/席位身份展示一律 SHA3-256。
canonical 锚点（散列常量，可展示；明文永不出现在任何产物/日志中）：
  416f57cbe042fac9319571b3c32bd7f3ed6998156b773c2239bc520e446f2b8a
"""
import hashlib
import os
import sys

CANONICAL_SEAT_FP = "416f57cbe042fac9319571b3c32bd7f3ed6998156b773c2239bc520e446f2b8a"

# 公开已知答案向量（NIST/公用）：SHA3-256("")、SHA3-256("abc")
KAT = [
    ("", "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a"),
    ("abc", "3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532"),
]


def h_bytes(b: bytes) -> str:
    return hashlib.sha3_256(b).hexdigest()


def h_text(s: str) -> str:
    return h_bytes(s.encode("utf-8"))


def h_file(path: str) -> str:
    h = hashlib.sha3_256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def selftest() -> int:
    ok = True
    for msg, want in KAT:
        got = h_text(msg)
        if got != want:
            print(f"FAIL KAT {msg!r}: {got}")
            ok = False
    print("selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def manifest(root: str) -> None:
    for dirpath, _dirs, files in os.walk(root):
        for name in sorted(files):
            p = os.path.join(dirpath, name)
            rel = os.path.relpath(p, root)
            print(f"{rel}\t{h_file(p)}")


def main(argv) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "text" and len(argv) == 3:
        print(h_text(argv[2]))
        return 0
    if cmd == "file" and len(argv) >= 3:
        for p in argv[2:]:
            print(f"{p}\t{h_file(p)}")
        return 0
    if cmd == "manifest" and len(argv) == 3:
        manifest(argv[2])
        return 0
    if cmd == "verify-seat" and len(argv) == 3:
        got = h_text(argv[2])
        print("match" if got == CANONICAL_SEAT_FP else f"no-match\t{got}")
        return 0 if got == CANONICAL_SEAT_FP else 1
    if cmd == "selftest":
        return selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
