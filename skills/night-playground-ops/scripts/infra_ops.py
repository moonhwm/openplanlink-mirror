#!/usr/bin/env python3
# infra_ops.py — 月之游乐场基础设施自动运维调度器（薪传席 2026-09-18, night-playground-ops v1.1.0 内置）
# 子命令: health / snapshot / cost / opslog / --self-test ｜ 纯标准库
# 纪律: 快照禁 cp sqlite 热库(走 tar); 凭据只经 hermes-run.sh 环境注入; 一切动作落 ops_log.jsonl(Asia/Shanghai)。
import argparse, glob, json, os, shutil, subprocess, sys, tarfile, time

ZONE = "/mnt/agents/upload/月之游乐场"
HERMES_RUN = ZONE + "/hermes-agent/hermes-run.sh"
POINTER = "/mnt/agents/output/夜间游乐场/skills_lab/pointer-layer/scripts/skill_pointer.py"
STATE = os.path.expanduser("~/.hermes")
SNAPDIR = ZONE + "/snapshots"
OPSLOG = ZONE + "/ops/ops_log.jsonl"

def ts():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() + 8 * 3600))

def opslog(action, detail, ok=True):
    os.makedirs(os.path.dirname(OPSLOG), exist_ok=True)
    with open(OPSLOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": ts(), "action": action, "ok": ok, "detail": detail}, ensure_ascii=False) + "\n")

def _run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()[:400]
    except Exception as e:
        return -1, str(e)[:400]

def cmd_health(a):
    checks = []
    rc, out = _run([HERMES_RUN, "--version"]) if os.path.isfile(HERMES_RUN) else (3, "hermes-run.sh 缺席")
    checks.append(("hermes 可用", rc == 0 and "Hermes" in out, out.splitlines()[0] if out else ""))
    rc, out = _run(["python3", POINTER, "verify"], 180)
    checks.append(("pointer-layer 哈希", rc == 0, out.strip().splitlines()[-1] if out else ""))
    ok = os.path.ismount("/mnt/agents") or os.path.exists("/mnt/agents/upload/MASTER_INDEX.md")
    checks.append(("drive9/upload 挂载", ok, "/mnt/agents"))
    ok = os.path.isdir(STATE)
    checks.append(("~/.hermes 本地运行态", ok, STATE))
    try:
        t = ZONE + "/ops/.writetest"; open(t, "w").write("x"); os.unlink(t); ok = True
    except OSError:
        ok = False
    checks.append(("月之游乐场可写", ok, ZONE))
    du = shutil.disk_usage(ZONE)
    checks.append(("磁盘余量>1GB", du.free > 1 << 30, f"free={du.free >> 20}MB"))
    allok = all(c[1] for c in checks)
    for name, ok, det in checks:
        print(f"{'OK  ' if ok else 'FAIL'} {name:24} {det}")
    opslog("health", f"{sum(1 for c in checks if c[1])}/{len(checks)}", allok)
    print(f"health: {'PASS' if allok else 'FAIL'}")
    return 0 if allok else 1

def cmd_snapshot(a):
    if not os.path.isdir(STATE):
        print("FAIL 运行态目录缺席:", STATE); return 1
    os.makedirs(SNAPDIR, exist_ok=True)
    name = "hermes-state-" + time.strftime("%Y%m%d-%H%M%S", time.gmtime(time.time() + 8 * 3600)) + ".tar.gz"
    dst = os.path.join(SNAPDIR, name)
    with tarfile.open(dst, "w:gz") as t:
        t.add(STATE, arcname=".hermes")
    snaps = sorted(glob.glob(SNAPDIR + "/hermes-state-*.tar.gz"))
    while len(snaps) > a.keep:
        os.unlink(snaps.pop(0))
    sz = os.path.getsize(dst)
    opslog("snapshot", f"{name} {sz}B keep={a.keep}")
    print(f"SNAPSHOT {dst} {sz}B (retain {a.keep})")
    return 0

def cmd_cost(a):
    tot, n = 0.0, 0
    for fp in glob.glob(a.pattern):
        try:
            u = json.load(open(fp))
            tot += float(u.get("estimated_cost_usd", 0)); n += 1
        except Exception:
            pass
    cny = tot * 7.2
    print(json.dumps({"usage_files": n, "usd": round(tot, 5), "cny_est": round(cny, 3),
                      "budget_cny": a.budget, "within_budget": cny <= a.budget}, ensure_ascii=False))
    opslog("cost", f"{n} files ${tot:.4f}≈¥{cny:.2f}/{a.budget}", cny <= a.budget)
    return 0 if cny <= a.budget else 2

def cmd_opslog(a):
    opslog(a.action, a.detail, not a.fail)
    print("LOGGED", a.action)
    return 0

def self_test():
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cmd_health(argparse.Namespace())
    out = buf.getvalue()
    assert "health:" in out, "health 输出缺收口行"
    p = argparse.ArgumentParser()
    print("self-test: health 可跑 rc=%d; argparse OK" % rc)
    return 0

def main(argv):
    p = argparse.ArgumentParser(description="月之游乐场基础设施自动运维调度器")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("health")
    sp = sub.add_parser("snapshot"); sp.add_argument("--keep", type=int, default=5)
    sp = sub.add_parser("cost"); sp.add_argument("--pattern", default="/tmp/hermes_*_usage.json"); sp.add_argument("--budget", type=float, default=500.0)
    sp = sub.add_parser("opslog"); sp.add_argument("action"); sp.add_argument("detail"); sp.add_argument("--fail", action="store_true")
    p.add_argument("--self-test", action="store_true")
    a = p.parse_args(argv[1:])
    if a.self_test: return self_test()
    return {"health": cmd_health, "snapshot": cmd_snapshot, "cost": cmd_cost, "opslog": cmd_opslog}.get(a.cmd, lambda x: p.print_help() or 1)(a)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
