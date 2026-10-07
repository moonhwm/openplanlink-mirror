# -*- coding: utf-8 -*-
"""Read-only Windows memory sampling with explicit missing-evidence states.

Derived from this repository's mem_audit.py at f9d1380e85c3714fed327035da39e499621e1261.
Produces local reports only. Thresholds and process candidates are provisional,
not approved policy, dispatch permission, or proof of a SOC ticket.
Usage: python memory_sample_audit.py --out-dir <private-output-directory>
"""
import argparse
import datetime as dt
import json
import math
import pathlib
import subprocess
import sys




def ps(cmd, timeout=180):
    p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True,
                       text=True, timeout=timeout, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, "powershell")
    return (p.stdout or "").strip()


def os_mem():
    out = ps("$os=Get-CimInstance Win32_OperatingSystem; "
             "'{0}|{1}|{2}|{3}' -f $os.TotalVisibleMemorySize, $os.FreePhysicalMemory, "
             "$os.TotalVirtualMemorySize, $os.FreeVirtualMemory")
    try:
        t, f, tv, fv = [int(x) for x in out.split("|")]
    except Exception:  # noqa: BLE001
        return {}
    # Validate raw KiB before display rounding can hide out-of-range values.
    if t <= 0 or not 0 <= f <= t or tv < 0 or not 0 <= fv <= tv:
        return {}
    used = t - f
    return {
        "total_mb": round(t / 1024, 1), "free_mb": round(f / 1024, 1),
        "used_mb": round(used / 1024, 1),
        "free_pct": round(100.0 * f / t, 1) if t else None,
        "used_pct": round(100.0 * used / t, 1) if t else None,
        "commit_total_mb": round(tv / 1024, 1), "commit_free_mb": round(fv / 1024, 1),
    }


def pagefile():
    out = ps("$p=Get-CimInstance Win32_PageFileUsage; if ($p) { '{0}|{1}|{2}' -f "
             "$p.AllocatedBaseSize, $p.CurrentUsage, $p.PeakUsage }")
    if "|" not in out:
        return {}
    try:
        a, c, pk = [int(x) for x in out.split("|")]
        return {"allocated_mb": a, "current_usage_mb": c, "peak_usage_mb": pk}
    except Exception:  # noqa: BLE001
        return {}


def procs():
    out = ps("Get-CimInstance Win32_Process | Select-Object Name,ProcessId,WorkingSetSize,"
             "PageFileUsage,UserModeTime,KernelModeTime | ConvertTo-Json -Compress")
    try:
        d = json.loads(out) if out else []
    except json.JSONDecodeError:
        return []
    if isinstance(d, dict):
        d = [d]
    rows = []
    for x in d:
        ws = int(x.get("WorkingSetSize") or 0)
        ut = int(x.get("UserModeTime") or 0)      # 100ns
        kt = int(x.get("KernelModeTime") or 0)
        rows.append({"name": x.get("Name"), "pid": x.get("ProcessId"),
                     "ws_mb": round(ws / 1048576, 1),
                     "pagefile_mb": round(int(x.get("PageFileUsage") or 0) / 1024, 1),
                     "cpu_s": round((ut + kt) / 1e7, 2)})
    return rows


def memory_risk(m, attempted_at_utc):
    """Evaluate only finite, physically possible OS samples; thresholds are provisional."""
    total, free = m.get("total_mb"), m.get("free_mb")
    valid = all(isinstance(x, (int, float)) and not isinstance(x, bool)
                and math.isfinite(x) for x in (total, free))
    valid = valid and total > 0 and 0 <= free <= total
    thr = {"降并行度_0.5GB": 512.0, "协办受理准入恢复线_0.8GB": 819.0,
           "M_floor_8pct": None, "填谷申请上限_可用减2GB": None}
    result = {"R_mem_mb": None, "mem_available_mb": None, "total_mb": None,
              "M_floor_mb": None, "thresholds_mb": thr, "breached": None,
              "state": "未实测", "measurement_valid": False,
              "sampled_at_utc": None, "attempted_at_utc": attempted_at_utc,
              "口径": "按既有暂定阈值推算；未证实为获批政策基线，不构成处置或调度授权"}
    if not valid:
        result["measurement_error"] = "missing_or_invalid_os_memory_sample"
        return result
    m_floor = round(total * 0.08, 1)
    thr.update(M_floor_8pct=m_floor, **{"填谷申请上限_可用减2GB": round(free - 2048.0, 1)})
    breached = []
    if free < thr["降并行度_0.5GB"]:
        breached.append("降并行度线(0.5GB)")
    if free < thr["协办受理准入恢复线_0.8GB"]:
        breached.append("协办受理准入/恢复线(0.8GB)")
    if free < m_floor:
        breached.append("M_floor 安全下限(8%)")
    result.update(R_mem_mb=round(max(0.0, m_floor-free), 1),
                  mem_available_mb=free, total_mb=total, M_floor_mb=m_floor,
                  breached=breached, state="低于安全下限" if free < m_floor else "高于安全下限",
                  measurement_valid=True, sampled_at_utc=attempted_at_utc)
    return result


def breached_text(risk):
    if risk["breached"] is None:
        return "未评估（内存未实测）"
    return "、".join(risk["breached"]) if risk["breached"] else "无"


def collect_sample(collector, empty_value):
    attempted = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        value = collector()
    except (OSError, subprocess.SubprocessError, ValueError, TypeError) as error:
        return empty_value, {"status": "failed", "error_type": type(error).__name__,
                             "attempted_at_utc": attempted, "sampled_at_utc": None}
    return value, {"status": "observed" if value else "not_observed",
                   "attempted_at_utc": attempted,
                   "sampled_at_utc": dt.datetime.now(dt.timezone.utc).isoformat() if value else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--min-ws-mb", type=float, default=200.0)
    ap.add_argument("--max-cpu-s", type=float, default=10.0)
    a = ap.parse_args()

    outdir = pathlib.Path(a.out_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    m, memory_sampling = collect_sample(os_mem, {})
    pf, pagefile_sampling = collect_sample(pagefile, {})
    processes, process_sampling = collect_sample(procs, [])
    ps_ = sorted(processes, key=lambda r: r["ws_mb"], reverse=True)
    top = ps_[: a.top]
    # 启发式：工作集大、累计 CPU 时间低 ⇒ 常驻但（迄今）少用；仅供复核参考
    cand = [r for r in ps_ if r["ws_mb"] >= a.min_ws_mb and r["cpu_s"] <= a.max_cpu_s]
    cand_ws = round(sum(r["ws_mb"] for r in cand), 1)

    # Provisional thresholds; no approved policy or action authorization implied.
    r_mem = memory_risk(m, memory_sampling["sampled_at_utc"] or memory_sampling["attempted_at_utc"])
    if not r_mem["measurement_valid"]:
        m = {}
        if memory_sampling["status"] == "observed":
            memory_sampling.update(status="invalid", sampled_at_utc=None)
    sampling = {"memory": memory_sampling, "pagefile": pagefile_sampling, "processes": process_sampling}

    data = {"generated_at_utc": ts, "memory": m, "pagefile": pf, "sampling": sampling,
            "R_mem": r_mem,
            "top": top, "candidates": cand, "candidate_ws_mb": cand_ws,
            "params": {"min_ws_mb": a.min_ws_mb, "max_cpu_s": a.max_cpu_s, "top": a.top},
            "note": "候选为启发式（工作集大且累计 CPU 少），不代表可安全处置；任何处置均须另行授权"}
    (outdir / ("mem_audit_%s.json" % ts)).write_text(
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    L = ["# 内存体检与「空闲但常驻」候选清单（只读）", "",
         "- 时刻（UTC）：%s" % ts,
         "- 口径：Win32_Process 工作集 + User/KernelModeTime 累计 CPU；**只读**", "",
         "## 一、内存组成", "", "| 项 | 读数 |", "|---|---|",
         "| 物理内存总量 | %s MB |" % m.get("total_mb"),
         "| 已用 | %s MB（%s%%） |" % (m.get("used_mb"), m.get("used_pct")),
         "| **可用（空闲）** | **%s MB（%s%%）** |" % (m.get("free_mb"), m.get("free_pct")),
         "| 提交上限/可用 | %s MB / %s MB |" % (m.get("commit_total_mb"), m.get("commit_free_mb")),
         "| 页面文件 已分配/当前/峰值 | %s / %s / %s MB |" % (
             pf.get("allocated_mb"), pf.get("current_usage_mb"), pf.get("peak_usage_mb")),
         "", "## 一之二、**R_mem（内存风险量）**", "",
         "| 项 | 读数 |", "|---|---|",
         "| **R_mem** | **%s MB**（%s） |" % (r_mem["R_mem_mb"], r_mem["state"]),
         "| MemAvailable / 总量 | %s MB / %s MB |" % (r_mem["mem_available_mb"], r_mem["total_mb"]),
         "| M_floor 安全下限（8%%） | %s MB |" % r_mem["M_floor_mb"],
         "| 已击穿阈值 | %s |" % breached_text(r_mem),
         "| 口径 | %s |" % r_mem["口径"],
         "| 采样时点 | %s |" % r_mem["sampled_at_utc"],
         "", "## 二、工作集 Top-%d" % a.top, "",
         "| # | 进程 | PID | 工作集 MB | 页面文件 MB | 累计 CPU 秒 |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(top, 1):
        L.append("| %d | %s | %s | %s | %s | %s |" % (i, r["name"], r["pid"], r["ws_mb"],
                                                      r["pagefile_mb"], r["cpu_s"]))
    L += ["", "## 三、待复核清单（启发式候选，待人工复核，外部工单未建立）", "",
          "判据：工作集 ≥ %s MB **且** 累计 CPU ≤ %s 秒（合计工作集 %s MB）" % (
              a.min_ws_mb, a.max_cpu_s, cand_ws), "",
          "| 序 | 对象 | PID | 工作集 MB | 累计 CPU 秒 | 责任人 | 时限 | 状态 |",
          "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(cand, 1):
        L.append("| %d | `%s` | %s | %s | %s | 候指派 | 候指派 | 待复核 |" % (
            i, r["name"], r["pid"], r["ws_mb"], r["cpu_s"]))
    if not cand:
        label = "无候选" if process_sampling["status"] == "observed" else "进程采样未完成，候选未评估"
        L.append("| — | — | — | — | — | — | — | %s |" % label)
    L += ["", "> **本清单只登记**：候选≠应处置（工作集大且 CPU 少也可能是正常缓存行为）。",
          "> 是否处置、由谁处置、时限几何，均须另行授权；本工具**不结束任何进程**。", ""]
    (outdir / ("mem_audit_%s.md" % ts)).write_text("\n".join(L) + "\n", encoding="utf-8")

    print("★ 内存：总量 %s MB ／ 已用 %s%% ／ **可用 %s%%**（%s MB）" % (
        m.get("total_mb"), m.get("used_pct"), m.get("free_pct"), m.get("free_mb")))
    print("★ R_mem= **%s MB**（%s）；已击穿：%s；M_floor=%s MB" % (
        r_mem["R_mem_mb"], r_mem["state"],
        breached_text(r_mem), r_mem["M_floor_mb"]))
    if process_sampling["status"] == "observed":
        print("★ Top-%d 已列出；启发式候选 %d 个（合计工作集 %s MB）" % (a.top, len(cand), cand_ws))
    else:
        print("★ 进程采样未完成，候选未评估")
    print("★ 已写出：%s（md+json）" % outdir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
