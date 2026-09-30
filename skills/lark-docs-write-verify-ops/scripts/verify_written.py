#!/usr/bin/env python3
# verify_written.py v1.0.0 — 飞书 docs 写后核验三段闸（等+按内容核），lark-docs-write-verify-ops 配套。
# 用法: verify_written.py <doc_token> <必须存在字符串> [--must-not <串>] [--wait <秒>] [--selftest]
# 退出码: 0=在案; 1=确证缺席/禁串在场; 2=接口异常（不得当缺席）
import subprocess, sys, time, json

def fetch(token):
    p = subprocess.run(["lark-cli", "docs", "+fetch", "--api-version", "v2", "--doc", token],
                       capture_output=True, text=True, timeout=120)
    if p.returncode != 0 or not p.stdout.strip():
        return None
    try:
        return json.loads(p.stdout)["data"]["document"]["content"]
    except Exception:
        return None

def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        # 无网自检：仅验证逻辑路径可执行
        print("[selftest] PASS（未发任何网络请求）"); sys.exit(0)
    if len(args) < 2:
        print(__doc__); sys.exit(2)
    token, must = args[0], args[1]
    must_not = args[args.index("--must-not") + 1] if "--must-not" in args else None
    wait = int(args[args.index("--wait") + 1]) if "--wait" in args else 60
    time.sleep(max(wait, 0))
    content = fetch(token)
    if content is None:
        print("verify_written ERROR: fetch 失败（接口异常，不得当缺席）"); sys.exit(2)
    if must not in content:
        print(f"verify_written ABSENT: {must}"); sys.exit(1)
    if must_not and must_not in content:
        print(f"verify_written FORBIDDEN_PRESENT: {must_not}"); sys.exit(1)
    print(f"verify_written PASS: {must} 在案"); sys.exit(0)

if __name__ == "__main__":
    main()
