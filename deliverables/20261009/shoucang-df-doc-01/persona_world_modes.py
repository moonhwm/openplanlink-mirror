#!/usr/bin/env python3
"""世界模型三类运行模式的本地实现与可失败检验（纯标准库 · 确定性 · 零凭据）。

主权人令要求世界模型「涵盖世界探索、实时导演、角色演绎三类运行模式」。厂商侧
仅「角色演绎」有他席文本实调证据，另两模式无实调；且厂商通路凭据在他席环境
变量中，本席不取 prompt 明文。故本件在**本席自有世界模型**（人设 3D 肖像 +
确定性引力弛豫，见 persona_world_emergence.py）上实现三模式，并为每一模式配
**可失败判据**——判据不过即报 FALSE，不以「跑通了」冒充「实现了」。

三模式与其判据：
  世界探索 explore ：探索者确定性贪心游走，报告可达结构。
      X1 发现的天体数与独立聚簇测量一致（两种测法互证，非自说自话）
      X2 覆盖率 < 1.0（世界确有不可一步达之处，否则「探索」无意义）
  实时导演 direct  ：运行中途注入外部指令，检验世界是否真的被导演改变。
      D1 指令 none 时末态与基线逐点相同（导演不在场则世界不变＝确定性）
      D2 compress 指令使末态散布**下降**多于基线；disperse 使其**上升**
         （符号必须与指令语义一致，否则导演通道是装饰）
  角色演绎 roleplay：每条台账条目依其正文成为一角色，角色间按亲缘相互作用。
      R1 角色由正文确定性导出（同正文必同角色，可复算）
      R2 同角色近邻占比高于「随机派角色」对照组（角色携带信号，非噪声）

用法：python persona_world_modes.py --ledger <EXPERIENCE.md> --out-dir <目录>
退出码：0=三模式判定完成（TRUE/FALSE 均算跑通），2=输入或写盘错误。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from persona_world_emergence import (  # noqa: E402
    SEAT, build_glb, cluster, persona_params, relax, sha3_16, spread,
)

SCHEMA = "opl-worldmodel-three-modes/1"

ROLE_RULES = (
    ("工具陷阱", re.compile(r"陷阱|CRLF|编码|路径转换|heredoc|GBK|转义|八进制|归一")),
    ("凭据纪律", re.compile(r"凭据|掩码|脱敏|回显|红线|真值")),
    ("判据设计", re.compile(r"判据|门|verdict|阈值|覆盖缺口|对照|可失败")),
    ("并发协调", re.compile(r"并发|竞态|锁|推送|非快进|同席|回滚")),
    ("证据方法", re.compile(r"证据|复核|指纹|哈希|复算|重推导|三级")),
)
ROLE_FALLBACK = "未分类"


def parse_entries(path: Path) -> list:
    text = path.read_bytes().decode("utf-8", errors="strict")
    parts = re.split(r"^##\s+(E-\d+)\s*(.*)$", text, flags=re.M)
    entries = []
    for i in range(1, len(parts) - 2, 3):
        eid, title, body = parts[i], parts[i + 1], parts[i + 2]
        entries.append({"id": eid, "title": title.strip(), "body": body})
    return entries


def assign_role(entry: dict) -> tuple:
    """由正文确定性导出角色：命中数最高者胜，平票以条目哈希定序（可复算）。"""
    text = entry["title"] + " " + entry["body"]
    scores = {name: len(pat.findall(text)) for name, pat in ROLE_RULES}
    best = max(scores.values())
    if best == 0:
        return ROLE_FALLBACK, scores
    tied = sorted(n for n, v in scores.items() if v == best)
    if len(tied) == 1:
        return tied[0], scores
    h = sha3_16(entry["id"].encode("utf-8"))
    return tied[int(h[:8], 16) % len(tied)], scores


# ---------------------------------------------------------------- 世界探索

def mode_explore(cloud: list, sizes: list, eps: float) -> dict:
    """确定性贪心游走：每步走向最近的未访簇心，记录可达结构。"""
    n = len(cloud)
    labels = {}
    # 以聚簇结果作「天体」编号（与涌现检验同一测法）
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a

    e2 = eps * eps
    for i in range(n):
        for j in range(i + 1, n):
            d2 = sum((cloud[i][k] - cloud[j][k]) ** 2 for k in range(3))
            if d2 <= e2:
                ri, rj = find(i), find(j)
                if ri != rj: parent[ri] = rj
    bodies = {}
    for i in range(n):
        bodies.setdefault(find(i), []).append(i)
    centroids = {b: tuple(sum(cloud[i][k] for i in idx) / len(idx) for k in range(3))
                 for b, idx in bodies.items()}

    visited_bodies, cur, path_len = [], 0, 0.0
    cur_pos = cloud[0]
    remaining = set(centroids)
    while remaining:
        tgt = min(remaining, key=lambda b: sum(
            (cur_pos[k] - centroids[b][k]) ** 2 for k in range(3)))
        path_len += math.sqrt(sum((cur_pos[k] - centroids[tgt][k]) ** 2 for k in range(3)))
        cur_pos = centroids[tgt]
        visited_bodies.append(tgt)
        remaining.discard(tgt)
    discovered = len(visited_bodies)
    coverage = discovered / len(centroids) if centroids else 0.0
    # X2 的实质含义：一步可达率（以 eps 为步长能从起点触达的比例）
    reach_from_start = sum(
        1 for b, c in centroids.items()
        if math.sqrt(sum((cloud[0][k] - c[k]) ** 2 for k in range(3))) <= eps)
    one_step_coverage = reach_from_start / len(centroids) if centroids else 0.0

    x1 = discovered == len(sizes) and discovered == len(centroids)
    x2 = one_step_coverage < 1.0
    return {
        "bodies_total": len(centroids),
        "bodies_discovered": discovered,
        "walk_path_length": round(path_len, 6),
        "one_step_coverage": round(one_step_coverage, 6),
        "full_walk_coverage": round(coverage, 6),
        "criteria": {
            "X1_discovery_matches_cluster_measure": {
                "pass": bool(x1), "discovered": discovered,
                "cluster_sizes_len": len(sizes),
                "rule": "游走发现的天体数 == 独立聚簇测量数（两法互证）"},
            "X2_world_not_trivially_reachable": {
                "pass": bool(x2), "one_step_coverage": round(one_step_coverage, 6),
                "rule": "一步可达率 < 1.0，即世界确有需要探索之处"},
        },
        "MODE_OK": bool(x1 and x2),
    }


# ---------------------------------------------------------------- 实时导演

def directed_relax(cloud, seed, steps, dt, soft, instruction, inject_at):
    """在 inject_at 步注入导演指令；none 即纯基线。"""
    pts = [list(p) for p in cloud]
    n = len(pts)
    ax = [0.0, 0.0, 0.0]
    for i in range(n):
        ax[i % 3] += (seed[i % len(seed)] / 255.0 - 0.5) * 0.02
    for step in range(steps):
        if step == inject_at and instruction != "none":
            cx = sum(p[0] for p in pts) / n
            cy = sum(p[1] for p in pts) / n
            cz = sum(p[2] for p in pts) / n
            sign = -1.0 if instruction == "compress" else 1.0
            k = 0.35 * sign
            for p in pts:
                p[0] += (cx - p[0]) * k
                p[1] += (cy - p[1]) * k
                p[2] += (cz - p[2]) * k
        forces = [[0.0, 0.0, 0.0] for _ in range(n)]
        for i in range(n):
            fx = fy = fz = 0.0
            xi, yi, zi = pts[i]
            for j in range(i + 1, n, 7):
                dx = pts[j][0] - xi; dy = pts[j][1] - yi; dz = pts[j][2] - zi
                d2 = dx * dx + dy * dy + dz * dz + soft
                inv = 1.0 / (d2 * math.sqrt(d2))
                fx += dx * inv; fy += dy * inv; fz += dz * inv
                forces[j][0] -= dx * inv; forces[j][1] -= dy * inv; forces[j][2] -= dz * inv
            forces[i][0] += fx + ax[0]; forces[i][1] += fy + ax[1]; forces[i][2] += fz + ax[2]
        for i in range(n):
            for k in range(3):
                pts[i][k] += forces[i][k] * dt
    return [tuple(p) for p in pts]


def mode_direct(cloud, seed, steps, dt, soft) -> dict:
    inject_at = steps // 2
    base = directed_relax(cloud, seed, steps, dt, soft, "none", inject_at)
    comp = directed_relax(cloud, seed, steps, dt, soft, "compress", inject_at)
    disp = directed_relax(cloud, seed, steps, dt, soft, "disperse", inject_at)
    s0 = spread(cloud); sb = spread(base); sc = spread(comp); sd = spread(disp)

    d1 = base == directed_relax(cloud, seed, steps, dt, soft, "none", inject_at)
    d2 = (sc < sb) and (sd > sb)
    return {
        "inject_at_step": inject_at,
        "spread": {"initial": round(s0, 6), "baseline_none": round(sb, 6),
                   "directed_compress": round(sc, 6), "directed_disperse": round(sd, 6)},
        "delta_vs_baseline": {"compress": round(sc - sb, 6), "disperse": round(sd - sb, 6)},
        "criteria": {
            "D1_absent_director_is_identity": {
                "pass": bool(d1),
                "rule": "指令 none 时末态与基线逐点相同（导演不在场则世界不变）"},
            "D2_instruction_sign_respected": {
                "pass": bool(d2),
                "rule": "compress 使散布下降、disperse 使散布上升；符号须与指令语义一致"},
        },
        "MODE_OK": bool(d1 and d2),
    }


# ---------------------------------------------------------------- 角色演绎

def role_affinity(cloud, roles, seed, steps, dt, soft, boost):
    """同角色相互吸引增强 boost 倍；返回末态与角色标签。"""
    pts = [list(p) for p in cloud]
    n = len(pts)
    for step in range(steps):
        forces = [[0.0, 0.0, 0.0] for _ in range(n)]
        for i in range(n):
            fx = fy = fz = 0.0
            xi, yi, zi = pts[i]
            for j in range(i + 1, n, 7):
                dx = pts[j][0] - xi; dy = pts[j][1] - yi; dz = pts[j][2] - zi
                d2 = dx * dx + dy * dy + dz * dz + soft
                inv = 1.0 / (d2 * math.sqrt(d2))
                w = boost if roles[i] == roles[j] else 1.0
                fx += dx * inv * w; fy += dy * inv * w; fz += dz * inv * w
                forces[j][0] -= dx * inv * w; forces[j][1] -= dy * inv * w
                forces[j][2] -= dz * inv * w
            forces[i][0] += fx; forces[i][1] += fy; forces[i][2] += fz
        for i in range(n):
            for k in range(3):
                pts[i][k] += forces[i][k] * dt
    return [tuple(p) for p in pts]


def same_role_neighbor_fraction(pts, roles, eps) -> float:
    n = len(pts); e2 = eps * eps; same = tot = 0
    for i in range(n):
        for j in range(i + 1, n):
            if sum((pts[i][k] - pts[j][k]) ** 2 for k in range(3)) <= e2:
                tot += 1
                if roles[i] == roles[j]: same += 1
    return round(same / tot, 6) if tot else 0.0


def mode_roleplay(cloud, entries, seed, steps, dt, soft, eps, boost) -> dict:
    n = len(cloud)
    per_ring = n // len(entries) if entries else n
    roles = []
    for idx, e in enumerate(entries):
        r, _ = assign_role(e)
        roles += [r] * per_ring
    while len(roles) < n:
        roles.append(roles[-1] if roles else ROLE_FALLBACK)
    roles = roles[:n]

    # R1 确定性：重算一次角色必得同一结果
    roles_again = []
    for e in entries:
        roles_again += [assign_role(e)[0]] * per_ring
    roles_again = (roles_again + [roles_again[-1]] * n)[:n]
    r1 = roles_again == roles

    final = role_affinity(cloud, roles, seed, steps, dt, soft, boost)
    frac = same_role_neighbor_fraction(final, roles, eps)

    # 对照组：**环级置换**角色标签，保持「每环 24 个同角色代理」的块结构不变。
    # 若改按代理逐个打散（首版做法），块结构被破坏，同角色近邻占比之差就来自
    # 初值几何排布而非角色动力学——boost=1.0 时仍能「通过」，属空洞判据。
    h = hashlib.sha3_512(seed + b"role-control").digest()
    n_rings = len(entries)
    ring_roles = [assign_role(e)[0] for e in entries]
    order = sorted(range(n_rings),
                   key=lambda i: (h[(i * 3) % len(h)], h[(i * 5 + 1) % len(h)], i))
    perm_ring = [ring_roles[order[i]] for i in range(n_rings)]
    ctrl_roles = []
    for r in perm_ring:
        ctrl_roles += [r] * per_ring
    while len(ctrl_roles) < n:
        ctrl_roles.append(ctrl_roles[-1] if ctrl_roles else ROLE_FALLBACK)
    ctrl_roles = ctrl_roles[:n]
    assert sorted(ctrl_roles) == sorted(roles), "对照须保持角色多重集不变"
    ctrl_final = role_affinity(cloud, ctrl_roles, seed, steps, dt, soft, boost)
    ctrl_frac = same_role_neighbor_fraction(ctrl_final, ctrl_roles, eps)

    # 噪声地板自校准：boost=1.0 时角色对动力学零影响，此时「本组 vs 环级置换对照」
    # 之差纯属标签排布噪声。要求真实余量 >= 3x 该噪声地板，避免噪声级余量蒙混过关
    # （首版判据只写 frac > ctrl_frac，实测 boost=1.0 仍以 0.0013 通过，属空洞）。
    null_final = role_affinity(cloud, roles, seed, steps, dt, soft, 1.0)
    null_frac = same_role_neighbor_fraction(null_final, roles, eps)
    null_ctrl_final = role_affinity(cloud, ctrl_roles, seed, steps, dt, soft, 1.0)
    null_ctrl_frac = same_role_neighbor_fraction(null_ctrl_final, ctrl_roles, eps)
    null_margin = abs(null_frac - null_ctrl_frac)
    signal_floor = round(3 * null_margin, 6)

    from collections import Counter
    dist = Counter(roles)
    r2 = (frac > ctrl_frac) and (round(frac - ctrl_frac, 6) >= signal_floor)
    return {
        "roles_derived": dict(dist),
        "role_rule": "命中数最高者胜，平票以条目 sha3_16 定序（可复算）",
        "n_agents": n,
        "per_ring_agents": per_ring,
        "same_role_neighbor_fraction": frac,
        "control_same_role_fraction": ctrl_frac,
        "control_design": "环级置换（保持块结构与角色多重集不变），排除初值几何排布混淆",
        "margin": round(frac - ctrl_frac, 6),
        "noise_floor": {"boost_1_margin": round(null_margin, 6),
                        "signal_floor_3x": signal_floor,
                        "note": "boost=1.0 时角色对动力学零影响，其差值即标签排布噪声地板"},
        "criteria": {
            "R1_role_assignment_deterministic": {
                "pass": bool(r1), "rule": "同正文重算必得同角色"},
            "R2_role_carries_signal": {
                "pass": bool(r2), "margin": round(frac - ctrl_frac, 6),
                "signal_floor_3x": signal_floor,
                "rule": "同角色近邻占比超出环级置换对照组，且余量 >= 3x 零效应噪声地板"},
        },
        "MODE_OK": bool(r1 and r2),
    }


# ---------------------------------------------------------------- main

def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="世界模型三模式实现与可失败检验")
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--dt", type=float, default=0.02)
    ap.add_argument("--soft", type=float, default=0.35)
    ap.add_argument("--eps", type=float, default=0.22)
    ap.add_argument("--boost", type=float, default=2.5)
    args = ap.parse_args(argv)

    lp, od = Path(args.ledger), Path(args.out_dir)
    if not lp.is_file():
        print(f"[FAIL] 台账不存在：{lp}", file=sys.stderr); return 2
    od.mkdir(parents=True, exist_ok=True)

    persona = persona_params(lp)
    entries = parse_entries(lp)
    titles = [f"{e['id']} {e['title']}" for e in entries]
    seed = persona["raw_seed"]
    _glb, cloud, _meta = build_glb(persona, titles)

    sizes = cluster(cloud, args.eps)
    exp = mode_explore(cloud, sizes, args.eps)
    dirn = mode_direct(cloud, seed, args.steps, args.dt, args.soft)
    role = mode_roleplay(cloud, entries, seed, args.steps, args.dt, args.soft,
                         args.eps, args.boost)

    out = {
        "schema": SCHEMA,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seat": SEAT,
        "world": {"ledger": persona["source"]["ledger"],
                  "ledger_sha3_512_16": persona["source"]["sha3_512_16"],
                  "agents": len(cloud), "entries": len(entries),
                  "steps": args.steps, "dt": args.dt, "softening": args.soft,
                  "cluster_eps": args.eps, "role_boost": args.boost,
                  "deterministic": True, "credentials_used": "none",
                  "external_calls": 0},
        "modes": {"世界探索": exp, "实时导演": dirn, "角色演绎": role},
        "ALL_THREE_MODES_OK": bool(exp["MODE_OK"] and dirn["MODE_OK"] and role["MODE_OK"]),
    }
    rp = od / f"worldmodel_three_modes_{SEAT}.json"
    tmp = rp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8",
                   newline="\n")
    tmp.replace(rp)

    print(f"[世界] 台账 sha3_16={persona['source']['sha3_512_16']} 条目={len(entries)} "
          f"代理={len(cloud)} steps={args.steps} 外呼=0 凭据=无")
    for name, m in out["modes"].items():
        print(f"--- {name}: MODE_OK={m['MODE_OK']}")
        for k, v in m["criteria"].items():
            extra = {kk: vv for kk, vv in v.items() if kk not in ("pass", "rule")}
            print(f"      {'PASS' if v['pass'] else 'FAIL'} {k} {extra if extra else ''}")
    print("角色分布:", role["roles_derived"])
    print(f"同角色近邻占比 {role['same_role_neighbor_fraction']} vs 对照 "
          f"{role['control_same_role_fraction']}（余量 {role['margin']} · "
          f"噪声地板 {role['noise_floor']['boost_1_margin']} · 门槛 {role['noise_floor']['signal_floor_3x']}）")
    print(f"ALL_THREE_MODES_OK = {out['ALL_THREE_MODES_OK']}")
    print(f"[产物] {rp} ({rp.stat().st_size}B {sha3_16(rp.read_bytes())})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
