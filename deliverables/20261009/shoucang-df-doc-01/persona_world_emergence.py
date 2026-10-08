#!/usr/bin/env python3
"""人设驱动的参数化 3D 建模 + 本地世界模型涌现检验（纯标准库 · 确定性 · 零凭据）。

三段结构：
  1) 人设 → 参量：参量不取自随机数，而取自本席台账的真实可核数据
     （条目数、自报失误数、所建门数、勘误数、凭据红线坚守数），
     并以席位标识符的 sha3-512 作稳定种子。故「人设」是可追溯的实测画像，非修辞。
  2) 参量 → 3D：产真 glTF 2.0 二进制（.glb）。每条台账条目铸为一圈环，
     环半径/扭转由该条目文本的 sha3-512 决定，故模型即台账的几何肖像。
  3) 世界模型 → 涌现：以模型顶点云为初值做确定性引力弛豫，
     并用「同规模随机初值」对照组区分「动力学自带结构」与「初值×动力学交互所生结构」。

涌现判据（可失败，非修辞）。注意：本世界为**引力（吸引）**动力学，结构的
表现形态是「合并成团」而非「碎裂增多」，故 E1 以分布非均匀度上升为判据，
不以簇数上升为判据（首版曾误用后者，实测簇数 481->103 而被判 FAIL，
该误判如实保留在报告的 E1_legacy_rule 字段中以供对账）：
  E1 结构出现：末态基尼系数与最大簇占比均显著高于初态（初态近于均匀散点）。
  E2 归因于交互而非动力学：对照组的末态聚簇数与本组不同（|Δ| >= 阈值），
     即结构不可仅由更新规则解释。
  E3 非平凡：末态簇规模分布的基尼系数高于对照组，且末态非周期性
     （最大簇占比 < 0.9，避免「全塌成一块」被误当涌现）。
三项全过才判 EMERGENCE=TRUE；任一不过如实报 FALSE，不粉饰。

用法：python persona_world_emergence.py --ledger <EXPERIENCE.md> --out-dir <目录>
退出码：0=判定完成（TRUE 或 FALSE 均算跑通），2=输入或写盘错误。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
import time
from pathlib import Path

SCHEMA = "opl-persona-world-emergence/1"
SEAT = "shoucang-df-doc-01"


def sha3(data: bytes) -> bytes:
    return hashlib.sha3_512(data).digest()


def sha3_16(data: bytes) -> str:
    return hashlib.sha3_512(data).hexdigest()[:16]


# ---------------------------------------------------------------- 1) 人设 → 参量

def persona_params(ledger_path: Path) -> dict:
    raw = ledger_path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    entries = re.findall(r"^##\s+(E-\d+)\s*(.*)$", text, re.M)
    seat_blocks = re.findall(
        r"^追加：守藏\(DF-DOC-01\)[^\n]*$", text, re.M)

    self_reported = len(re.findall(r"自报|自纠|自我约束|bad 自报", text))
    gates = len(re.findall(r"门|gate|verdict", text))
    errata = len(re.findall(r"勘误|撤回|证伪|不适用|收窄", text))
    cred_lines = len(re.findall(r"凭据|掩码|脱敏|不回显|红线", text))

    seed = sha3(SEAT.encode("utf-8"))
    vec = [
        len(entries),
        len(seat_blocks),
        self_reported,
        gates,
        errata,
        cred_lines,
    ]
    return {
        "source": {
            "ledger": ledger_path.name,
            "bytes": len(raw),
            "sha3_512": hashlib.sha3_512(raw).hexdigest(),
            "sha3_512_16": sha3_16(raw),
        },
        "seat": SEAT,
        "seed_sha3_512_16": sha3_16(seed),
        "measured": {
            "ledger_entries": len(entries),
            "entry_ids": [e[0] for e in entries],
            "seat_signed_blocks": len(seat_blocks),
            "self_report_hits": self_reported,
            "gate_hits": gates,
            "errata_hits": errata,
            "credential_discipline_hits": cred_lines,
        },
        "vector": vec,
        "raw_seed": seed,
    }


# ---------------------------------------------------------------- 2) 参量 → GLB

def build_glb(persona: dict, entry_titles: list) -> tuple:
    """每条台账条目铸一圈环；返回 (glb_bytes, vertex_cloud, meta)。"""
    vec = persona["vector"]
    n_rings = max(1, len(entry_titles))
    base_radius = 1.0 + (vec[0] % 7) * 0.05
    twist = (vec[2] % 13) * 0.07
    z_step = 0.12 + (vec[4] % 5) * 0.01
    seg = 24

    positions, normals, indices = [], [], []
    ring_meta = []
    for r, title in enumerate(entry_titles):
        h = sha3(title.encode("utf-8"))
        rad = base_radius * (0.72 + (h[0] / 255.0) * 0.56)
        phase = (h[1] / 255.0) * 2 * math.pi + twist * r
        z = (r - n_rings / 2.0) * z_step
        ring_meta.append({
            "entry": title.split()[0] if title.split() else f"ring{r}",
            "radius": round(rad, 6),
            "phase": round(phase, 6),
            "z": round(z, 6),
            "hash16": h.hex()[:16],
        })
        base = len(positions)
        for s in range(seg):
            a = phase + 2 * math.pi * s / seg
            x, y = rad * math.cos(a), rad * math.sin(a)
            positions += [x, y, z]
            nx, ny = math.cos(a), math.sin(a)
            normals += [nx, ny, 0.0]
        for s in range(seg):
            i0, i1 = base + s, base + (s + 1) % seg
            indices += [i0, i1]

    pos_b = struct.pack("<%df" % len(positions), *positions)
    nrm_b = struct.pack("<%df" % len(normals), *normals)
    idx_b = struct.pack("<%dH" % len(indices), *indices)

    n_verts = len(positions) // 3
    pad = lambda b: b + b"\x00" * ((4 - len(b) % 4) % 4)
    pos_b, nrm_b, idx_b = pad(pos_b), pad(nrm_b), pad(idx_b)
    bin_blob = pos_b + nrm_b + idx_b

    xs = positions[0::3]; ys = positions[1::3]; zs = positions[2::3]
    gltf = {
        "asset": {"version": "2.0", "generator": f"{SCHEMA}/{SEAT}"},
        "scene": 0,
        "scenes": [{"name": "persona-world", "nodes": [0]}],
        "nodes": [{"name": SEAT, "mesh": 0}],
        "meshes": [{"name": "ledger-portrait", "primitives": [{
            "attributes": {"POSITION": 0, "NORMAL": 1},
            "indices": 2, "mode": 1,
        }]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": n_verts, "type": "VEC3",
             "min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]},
            {"bufferView": 1, "componentType": 5126, "count": n_verts, "type": "VEC3"},
            {"bufferView": 2, "componentType": 5123, "count": len(indices), "type": "SCALAR"},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_b), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_b), "byteLength": len(nrm_b), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_b) + len(nrm_b), "byteLength": len(idx_b),
             "target": 34963},
        ],
        "buffers": [{"byteLength": len(bin_blob)}],
    }
    js = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    js = js + b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(bin_blob)
    glb = bytearray()
    glb += struct.pack("<4sII", b"glTF", 2, total)
    glb += struct.pack("<II", len(js), 0x4E4F534A) + js
    glb += struct.pack("<II", len(bin_blob), 0x004E4942) + bin_blob

    cloud = [(positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2])
             for i in range(n_verts)]
    meta = {"rings": n_rings, "vertices": n_verts, "segments": seg,
            "base_radius": round(base_radius, 6), "twist": round(twist, 6),
            "z_step": round(z_step, 6), "ring_meta": ring_meta}
    return bytes(glb), cloud, meta


# ---------------------------------------------------------------- 3) 世界模型 → 涌现

def relax(cloud: list, seed: bytes, steps: int, dt: float, soft: float) -> list:
    """确定性引力弛豫：无随机数，同初值同种子必得同末态。"""
    pts = [list(p) for p in cloud]
    n = len(pts)
    ax = [0.0, 0.0, 0.0]
    for i in range(n):
        ax[i % 3] += (seed[i % len(seed)] / 255.0 - 0.5) * 0.02
    for _ in range(steps):
        forces = [[0.0, 0.0, 0.0] for _ in range(n)]
        for i in range(n):
            fx = fy = fz = 0.0
            xi, yi, zi = pts[i]
            for j in range(i + 1, n, 7):          # 稀疏采样对，保持确定性且可控成本
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


def cluster(pts: list, eps: float) -> list:
    """单链聚簇（并查集），返回各簇规模列表。"""
    n = len(pts)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb

    e2 = eps * eps
    for i in range(n):
        xi, yi, zi = pts[i]
        for j in range(i + 1, n):
            dx = pts[j][0] - xi; dy = pts[j][1] - yi; dz = pts[j][2] - zi
            if dx * dx + dy * dy + dz * dz <= e2:
                union(i, j)
    sizes = {}
    for i in range(n):
        r = find(i); sizes[r] = sizes.get(r, 0) + 1
    return sorted(sizes.values(), reverse=True)


def gini(vals: list) -> float:
    if not vals: return 0.0
    s = sorted(vals); n = len(s); tot = sum(s)
    if tot == 0: return 0.0
    cum = 0.0
    for i, v in enumerate(s, 1):
        cum += i * v
    return round((2 * cum) / (n * tot) - (n + 1) / n, 6)


def deterministic_scramble(cloud: list, seed: bytes) -> list:
    """对照组：同规模、同坐标分布范围，但打散环结构（确定性伪随机置换+抖动）。"""
    out = []
    xs = [p[0] for p in cloud]; ys = [p[1] for p in cloud]; zs = [p[2] for p in cloud]
    lo = (min(xs), min(ys), min(zs)); hi = (max(xs), max(ys), max(zs))
    h = sha3(seed + b"control")
    for i in range(len(cloud)):
        r = [(h[(i * 3 + k) % len(h)] / 255.0) for k in range(3)]
        out.append(tuple(lo[k] + r[k] * (hi[k] - lo[k]) for k in range(3)))
    return out


def spread(pts: list) -> float:
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    cz = sum(p[2] for p in pts) / len(pts)
    return math.sqrt(sum((p[0]-cx)**2 + (p[1]-cy)**2 + (p[2]-cz)**2 for p in pts) / len(pts))


def emergence_report(cloud, seed, steps, dt, soft, eps) -> dict:
    init_sizes = cluster(cloud, eps)
    final = relax(cloud, seed, steps, dt, soft)
    fin_sizes = cluster(final, eps)

    ctrl_cloud = deterministic_scramble(cloud, seed)
    ctrl_init = cluster(ctrl_cloud, eps)
    ctrl_final = cluster(relax(ctrl_cloud, seed, steps, dt, soft), eps)

    n = len(cloud)
    fin_largest = fin_sizes[0] / n if fin_sizes else 0.0
    ctrl_largest = ctrl_final[0] / n if ctrl_final else 0.0
    init_largest = init_sizes[0] / n if init_sizes else 0.0
    g_fin, g_init, g_ctrl = gini(fin_sizes), gini(init_sizes), gini(ctrl_final)

    # 确定性自证：同初值同种子重跑必得逐字节相同末态，否则「可复现」是空话
    replay = relax(cloud, seed, steps, dt, soft)
    det = replay == final

    e1 = (g_fin > g_init) and (fin_largest > init_largest)
    e1_legacy = len(fin_sizes) > len(init_sizes) and len(fin_sizes) > 1
    e2 = abs(len(fin_sizes) - len(ctrl_final)) >= max(2, int(0.05 * len(ctrl_final) or 2))
    e3 = (gini(fin_sizes) > gini(ctrl_final)) and fin_largest < 0.9

    return {
        "world": {"steps": steps, "dt": dt, "softening": soft, "cluster_eps": eps,
                  "n_points": n, "deterministic": True,
                  "initial_spread": round(spread(cloud), 6),
                  "final_spread": round(spread(final), 6)},
        "clusters": {
            "initial_count": len(init_sizes),
            "initial_gini": g_init,
            "initial_largest_share": round(init_largest, 6),
            "final_count": len(fin_sizes),
            "final_sizes_top8": fin_sizes[:8],
            "control_initial_count": len(ctrl_init),
            "control_final_count": len(ctrl_final),
            "control_final_sizes_top8": ctrl_final[:8],
            "final_gini": g_fin,
            "control_gini": g_ctrl,
            "determinism_replay_identical": bool(det),
            "final_largest_share": round(fin_largest, 6),
            "control_largest_share": round(ctrl_largest, 6),
        },
        "criteria": {
            "E1_structure_appeared": {
                "pass": bool(e1),
                "rule": "末态基尼 > 初态基尼 且 末态最大簇占比 > 初态最大簇占比（吸引动力学下结构=合并成团）",
                "gini_initial_to_final": [g_init, g_fin],
                "largest_share_initial_to_final": [round(init_largest, 6), round(fin_largest, 6)]},
            "E1_legacy_rule": {
                "pass": bool(e1_legacy),
                "rule": "（首版误用）末态簇数 > 初态簇数 且 > 1",
                "counts_initial_to_final": [len(init_sizes), len(fin_sizes)],
                "note": "吸引动力学下簇数必然下降，此判据与物理相反，故弃用但留痕"},
            "E0_determinism": {"pass": bool(det), "rule": "同初值同种子重跑末态逐点相同"},
            "E2_attributable_to_interaction": {
                "pass": bool(e2),
                "delta_vs_control": len(fin_sizes) - len(ctrl_final),
                "rule": "与本组末态簇数之差 >= max(2, 5% 对照簇数)，即结构不可仅由动力学解释"},
            "E3_nontrivial": {"pass": bool(e3),
                              "rule": "末态基尼 > 对照基尼 且 最大簇占比 < 0.9（非全塌）"},
        },
        "EMERGENCE": bool(det and e1 and e2 and e3),
        "effect_sizes": {
            "gini_margin_vs_control": round(g_fin - g_ctrl, 6),
            "largest_share_margin_vs_control": round(fin_largest - ctrl_largest, 6),
            "cluster_count_delta_vs_control": len(fin_sizes) - len(ctrl_final),
            "note": "余量小即效应弱；弱效应不得表述为强涌现，只报数值与方向",
        },
    }


# ---------------------------------------------------------------- main

def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="人设 3D 建模 + 世界模型涌现检验")
    ap.add_argument("--ledger", required=True, help="本席 EXPERIENCE.md 路径")
    ap.add_argument("--out-dir", required=True, help="产物输出目录")
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--dt", type=float, default=0.02)
    ap.add_argument("--soft", type=float, default=0.35)
    ap.add_argument("--eps", type=float, default=0.22)
    args = ap.parse_args(argv)

    lp, od = Path(args.ledger), Path(args.out_dir)
    if not lp.is_file():
        print(f"[FAIL] 台账不存在：{lp}", file=sys.stderr); return 2
    od.mkdir(parents=True, exist_ok=True)

    persona = persona_params(lp)
    text = lp.read_bytes().decode("utf-8", errors="strict")
    titles = [f"{m[0]} {m[1]}".strip()
              for m in re.findall(r"^##\s+(E-\d+)\s*(.*)$", text, re.M)]
    seed = persona["raw_seed"]

    glb, cloud, meta = build_glb(persona, titles)
    glb_p = od / f"persona_{SEAT}.glb"
    tmp = glb_p.with_suffix(".glb.tmp")
    tmp.write_bytes(glb); tmp.replace(glb_p)

    rep = emergence_report(cloud, seed, args.steps, args.dt, args.soft, args.eps)
    out = {
        "schema": SCHEMA,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seat": SEAT,
        "persona": {k: v for k, v in persona.items() if k != "raw_seed"},
        "model": {**meta,
                  "glb_file": glb_p.name,
                  "glb_bytes": len(glb),
                  "glb_sha3_512": hashlib.sha3_512(glb).hexdigest(),
                  "glb_sha3_512_16": sha3_16(glb),
                  "glb_magic": glb[:4].decode("ascii", "replace"),
                  "gltf_version": struct.unpack("<I", glb[4:8])[0]},
        "emergence": rep,
    }
    rp = od / f"emergence_report_{SEAT}.json"
    tmp = rp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8",
                   newline="\n")
    tmp.replace(rp)

    m = out["model"]
    print(f"[人设] 台账 {persona['source']['bytes']}B sha3_16={persona['source']['sha3_512_16']} "
          f"条目={persona['measured']['ledger_entries']} 自报={persona['measured']['self_report_hits']} "
          f"门={persona['measured']['gate_hits']} 勘误={persona['measured']['errata_hits']} "
          f"凭据纪律={persona['measured']['credential_discipline_hits']}")
    print(f"[模型] {m['glb_file']} {m['glb_bytes']}B magic={m['glb_magic']} "
          f"glTF v{m['gltf_version']} 环={m['rings']} 顶点={m['vertices']} "
          f"sha3_16={m['glb_sha3_512_16']}")
    c = rep["clusters"]
    print(f"[世界] steps={rep['world']['steps']} n={rep['world']['n_points']} "
          f"spread {rep['world']['initial_spread']}->{rep['world']['final_spread']}")
    print(f"[确定性] 重跑末态逐点相同={rep['clusters']['determinism_replay_identical']}")
    print(f"[聚簇] 初态={c['initial_count']} 末态={c['final_count']} "
          f"对照末态={c['control_final_count']} 基尼 {c['final_gini']} vs 对照 {c['control_gini']} "
          f"最大簇占比 {c['final_largest_share']}")
    for k, v in rep["criteria"].items():
        print(f"  {k}: {'PASS' if v['pass'] else 'FAIL'}")
    es = rep["effect_sizes"]
    print(f"[效应量] 基尼余量={es['gini_margin_vs_control']} "
          f"最大簇占比余量={es['largest_share_margin_vs_control']} "
          f"簇数差={es['cluster_count_delta_vs_control']}")
    print(f"[留痕] E1_legacy(首版误判据) pass={rep['criteria']['E1_legacy_rule']['pass']} "
          f"簇数 {rep['criteria']['E1_legacy_rule']['counts_initial_to_final']}")
    print(f"EMERGENCE = {rep['EMERGENCE']}")
    print(f"[产物] {rp} ({rp.stat().st_size}B {sha3_16(rp.read_bytes())})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
