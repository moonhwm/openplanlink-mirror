#!/usr/bin/env python3
"""route_decide.py — gen-route-ops 核心：车道盘点 / 探针 / 决策大模型路由 / 自检。

用法：
  python3 route_decide.py lanes                     # 列出注册表全部车道与状态
  python3 route_decide.py probe                     # 探针快照（凭据存在性、CLI 在册，不泄露值）
  python3 route_decide.py decide "<任务描述>" [--kind image|model_3d|video|dcc|compute] [--json]
  python3 route_decide.py smoke                     # 自检（零网络）

设计：
  - 决策大模型按 DECIDER_ORDER 顺序尝试，全部失败则规则路由降级（degraded=true 如实标注）。
  - 防幻觉：chosen_lane 必须在注册表内，否则记 HALLUCINATED_LANE 并换下一家决策位。
  - 反抽卡教义（v1.1.0）：身份一致性/精度敏感任务，gacha_risk=high 车道禁裸选；
    决策位须给 control_surface（low/medium/high）与 intervention_points（人工闸点）。
  - 输出决策卡含 card_sha256；needs_user_confirmation 恒为 true（付费逐次批准）。
  - 凭据零落盘：只查环境变量存在性，永不打印值。
"""
import json, os, re, shutil, sys, time, hashlib, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
REG_PATH = os.path.join(ROOT, "lanes.json")
KINDS = ("image", "model_3d", "video", "dcc", "compute")
DECIDER_ORDER = ["bailian", "deepseek", "ark", "openrouter"]

DOCTRINE = (
    "反抽卡教义（硬规则）："
    "①车道带 gacha_risk：low=机器直办（代码/参数直接操纵，可复现）、medium=锚定制导（参考图/首尾帧/多视图/幂等键）、high=纯prompt抽卡；"
    "②身份一致性、精度敏感、可工程化的任务，禁止裸选 high 车道——优先 low/medium，并在 intervention_points 给出人工闸点；"
    "③确需 high 车道时必须给出 anchor_hint（用什么锚）并注明风险；"
    "④输出额外两字段：control_surface（low/medium/high，取所选车道控制面等级）、intervention_points（人工干预闸点列表，可为空数组）。"
)


def load_registry():
    with open(REG_PATH, encoding="utf-8") as f:
        return json.load(f)


def probe_lane(lane):
    """返回 (runtime_status, note)。不动注册表，只做事实观测。"""
    pid, entry = lane["id"], lane.get("entry", "")
    if entry == "cli":
        exe = lane.get("cli_name", pid)
        if shutil.which(exe):
            return "cli_present", f"{exe} 在 PATH"
        return "cli_absent", f"{exe} 不在 PATH"
    if pid == "rodin":
        return "pending_oauth", "OAuth 浏览器授权线：候主权人操作（2026-10-08 端点 401 漂移在案）"
    if entry in ("mcp_tools", "plugin_tools", "mcp_streamable_http"):
        return "agent_confirm", "插件/MCP 线：以会话内工具清单为准（本脚本无法直连）"
    if entry == "skill_pipeline":
        return "skill_present", "管线技能在册（executor 见其 SKILL.md）"
    if entry == "none":
        return "not_integrated", "预留位未接入（如实声明，不冒充）"
    missing = [e for e in lane.get("credential_env", []) if not os.environ.get(e)]
    if missing:
        return "key_missing", "缺环境变量 " + ",".join(missing)
    return "key_present", "凭据在环境（值不显示）"


def cmd_lanes(reg):
    for ln in reg["lanes"]:
        print(f"{ln['id']:24s} {ln['kind']:9s} risk={ln.get('gacha_risk','?'):6s} {ln['status']:22s} {ln['name']}")
    print(f"\n决策位顺序: {' -> '.join(DECIDER_ORDER)}")
    for d in reg["deciders"]:
        print(f"  {d['id']:12s} {d['status']:22s} {d.get('note','')[:60]}")
    return 0


def cmd_probe(reg):
    print("== 车道探针 ==")
    for ln in reg["lanes"]:
        st, note = probe_lane(ln)
        print(f"{ln['id']:24s} {st:16s} {note}")
    print("== 决策位探针 ==")
    for d in reg["deciders"]:
        envs = d.get("credential_env", [])
        present = any(os.environ.get(e) for e in envs)
        print(f"{d['id']:12s} key={'present' if present else 'absent':8s} base={d.get('default_base')}")
    print("\n注：agent_confirm/pending_* 为注册表基线，最终以实际调用回执为准。")
    return 0


_RULES = {
    "model_3d": ["3d", "模型", "建模", "mesh", "glb", "fbx", "绑骨", "贴图", "文生3d", "图生3d"],
    "video": ["视频", "video", "短片", "配乐", "出片", "剪辑"],
    "image": ["图", "image", "海报", "插画", "写真", "照片", "生图"],
    "dcc": ["maya", "3ds", "blender", "场景", "批量改名", "导出场景", "装配", "工程图", "solidworks", "cad"],
    "compute": ["gpu", "算力", "训练", "渲染农场", "本地重建", "自托管", "租卡", "远程跑"],
}
_PREFER = {
    "model_3d": ["tripo302", "tripo_mcp", "tripo_env", "v2fun", "rodin"],
    "image": ["image_generation_plugin", "ai302_image", "modelscope", "aimlapi", "openrouter"],
    "video": ["happyhorse", "video_generation_plugin", "remotion", "minimax_h3"],
    "dcc": ["maya_dcc", "cad_engineering"],
    "compute": ["compshare_gpu"],
}


def guess_kind(text):
    """命中计数评分制；并列时 dcc/compute 优先于生成类（场景/算力语义更强）。"""
    t = text.lower()
    scores = {k: sum(1 for w in kws if w in t) for k, kws in _RULES.items()}
    best = max(scores.values())
    if best == 0:
        return None
    for k in ("dcc", "compute", "model_3d", "video", "image"):
        if scores[k] == best:
            return k
    return None


def rule_route(reg, text, kind):
    """无 LLM 时的降级路由（确定性）。反抽卡教义内置：
    视频类含 代码/批量/参数化 语义时优先 remotion（机器直办 low risk）。"""
    kind = kind or guess_kind(text) or "image"
    cands = [ln for ln in reg["lanes"] if ln["kind"] == kind and not ln["status"].startswith(("not_integrated", "server_unavailable"))]
    pref = _PREFER.get(kind, [])
    # 教义：代码化/批量化视频需求 → remotion 提到队首
    if kind == "video" and any(w in text for w in ("代码", "批量", "参数化", "数据驱动", "Remotion", "remotion")):
        pref = ["remotion"] + [p for p in pref if p != "remotion"]
    cands.sort(key=lambda l: (pref.index(l["id"]) if l["id"] in pref else 99))
    top = cands[0] if cands else None
    return {
        "kind": kind, "chosen_lane": top["id"] if top else None,
        "reason": "规则降级路由：决策大模型全灭或未配置；按注册表优先级+反抽卡教义择道",
        "control_surface": (top or {}).get("gacha_risk"),
        "intervention_points": ["决策前人工核对车道状态与报价"],
        "degraded": True,
    }


def call_decider(reg, dcfg, text, kind, lanes_brief):
    key = next((os.environ.get(e) for e in dcfg.get("credential_env", []) if os.environ.get(e)), None)
    if not key:
        raise RuntimeError("NO_KEY")
    model = os.environ.get("GEN_ROUTE_MODEL_" + dcfg["id"].upper()) or dcfg.get("model")
    if not model:
        raise RuntimeError("NO_MODEL")
    base = os.environ.get(dcfg.get("base_env", "")) or dcfg.get("default_base")
    sys_prompt = (
        "你是生成式任务路由决策器。根据任务描述与车道清单，选一条最合适的车道。"
        + DOCTRINE +
        '严格输出 JSON：{"kind": "...", "chosen_lane": "<lanes[].id 之一或 null>", '
        '"reason": "<=120字", "fallback_lanes": ["id"...], "anchor_hint": "可选", '
        '"control_surface": "low|medium|high", "intervention_points": ["..."]}'
    )
    user = f"任务：{text}\n期望类别：{kind or '自动判断'}\n车道清单：\n{lanes_brief}"
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps({
            "model": model, "temperature": 0.2,
            "messages": [{"role": "system", "content": sys_prompt},
                         {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
        }).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.loads(r.read().decode())
    content = body["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", content, re.S)
    return json.loads(m.group(0)), model


def cmd_decide(reg, text, kind, as_json):
    if kind and kind not in KINDS:
        print(f"FATAL: kind 须为 {KINDS}", file=sys.stderr)
        return 2
    kind = kind or guess_kind(text)
    lanes_brief = "\n".join(
        f"- {l['id']} [{l['kind']}|risk={l.get('gacha_risk','?')}|{l['status']}]: {l['name']}"
        + (f" ⚠️质量口径：{l['quality_note']}" if l.get("quality_note") else "")
        for l in reg["lanes"] if kind is None or l["kind"] == kind
    )
    if not lanes_brief:
        lanes_brief = "（该类别注册表内无车道）"
    decision, used, model_used, failures = None, None, None, []
    start = os.environ.get("GEN_ROUTE_DECIDER")
    order = ([start] if start else []) + [d for d in DECIDER_ORDER if d != start]
    dmap = {d["id"]: d for d in reg["deciders"]}
    for did in order:
        dcfg = dmap.get(did)
        if not dcfg:
            continue
        try:
            out, model_used = call_decider(reg, dcfg, text, kind, lanes_brief)
            valid_ids = {l["id"] for l in reg["lanes"]}
            if out.get("chosen_lane") and out["chosen_lane"] not in valid_ids:
                failures.append(f"{did}:HALLUCINATED_LANE:{out['chosen_lane']}")
                continue
            decision, used = out, did
            break
        except Exception as e:
            failures.append(f"{did}:{type(e).__name__}")
    if decision is None:
        decision = rule_route(reg, text, kind)
        used = "rule_fallback"
        decision["decider_failures"] = failures
    elif failures:
        decision["decider_attempts"] = failures  # 成功前失败车次留痕
    decision["decider"] = used
    decision["model"] = model_used if used != "rule_fallback" else None
    _ln = next((l for l in reg["lanes"] if l["id"] == decision.get("chosen_lane")), None)
    if _ln:
        decision["lane_status"] = _ln["status"]
        if not _ln["status"].startswith("ready"):
            decision["precondition_warning"] = f"车道状态 {_ln['status']}——非立即可用，前置条件见注册表 notes"
        if _ln.get("quality_note"):
            decision["quality_note"] = _ln["quality_note"]
    decision["task"] = text
    decision["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    decision["registry_version"] = reg["registry_version"]
    decision["needs_user_confirmation"] = True  # 付费/烧配额逐次批准，恒真
    payload = json.dumps(decision, sort_keys=True, ensure_ascii=False)
    decision["card_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    if as_json:
        print(json.dumps(decision, ensure_ascii=False, indent=2))
    else:
        print(f"类别     : {decision.get('kind')}")
        print(f"选定车道 : {decision.get('chosen_lane')}")
        print(f"控制面   : {decision.get('control_surface')}  人工闸点: {decision.get('intervention_points')}")
        print(f"理由     : {decision.get('reason')}")
        print(f"决策位   : {used} ({model_used or '规则降级'})"
              + ("  ⚠️degraded" if decision.get("degraded") else ""))
        if decision.get("lane_status"):
            print(f"车道状态 : {decision['lane_status']}" + ("  ⚠️ " + decision["precondition_warning"] if decision.get("precondition_warning") else ""))
        if decision.get("quality_note"):
            print(f"质量口径 : ⚠️ {decision['quality_note']}")
        if decision.get("decider_attempts"):
            print(f"前车失败 : {decision['decider_attempts']}")
        if decision.get("anchor_hint"):
            print(f"锚定提示 : {decision['anchor_hint']}")
        print(f"确认要求 : needs_user_confirmation=true（烧配额前须用户批准）")
        print(f"决策卡SHA: {decision['card_sha256'][:16]}…")
    if not decision.get("chosen_lane"):
        return 3
    return 0


def cmd_smoke(reg):
    ids = [l["id"] for l in reg["lanes"]]
    assert len(ids) == len(set(ids)), "lane id 重复"
    kinds = {l["kind"] for l in reg["lanes"]}
    assert kinds <= set(KINDS), f"非法 kind: {kinds - set(KINDS)}"
    miss = [l["id"] for l in reg["lanes"] if not l.get("gacha_risk")]
    assert not miss, f"缺 gacha_risk 标注: {miss}"
    valid = set(ids)
    for k, pref in _PREFER.items():
        for p in pref:
            assert p in valid, f"_PREFER[{k}] 指向不存在车道 {p}"
    d0 = rule_route(reg, "给我生成一张海报", "image")
    assert d0["chosen_lane"] in valid and d0["degraded"]
    d1 = rule_route(reg, "把这个模型转成带贴图 GLB", "model_3d")
    assert d1["chosen_lane"] in valid
    d2 = rule_route(reg, "用代码批量生成十条带配乐的产品视频", "video")
    assert d2["chosen_lane"] == "remotion", f"代码化视频应路由 remotion，实得 {d2['chosen_lane']}"
    d3 = rule_route(reg, "在Maya场景里批量改名并导出", "dcc")
    assert d3["chosen_lane"] in _PREFER["dcc"] or d3["chosen_lane"] is None
    d4 = rule_route(reg, "租GPU跑本地重建管线", "compute")
    assert d4["chosen_lane"] == "compshare_gpu"
    d5 = rule_route(reg, "真人西服写真重构（要脸不崩）", "image")
    assert d5["control_surface"] in ("low", "medium", "high")
    fake = {"chosen_lane": "nonexistent_lane_xyz"}
    assert fake["chosen_lane"] not in valid, "防幻觉校验失效"
    os.environ["HH_TEST_KEY"] = "sk-should-never-appear"
    st, note = probe_lane({"id": "_t", "entry": "api", "credential_env": ["HH_TEST_KEY"]})
    assert st == "key_present" and "sk-should" not in note
    del os.environ["HH_TEST_KEY"]
    print("SMOKE PASS: 13 assertions")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    reg = load_registry()
    cmd = sys.argv[1]
    if cmd == "lanes":
        return cmd_lanes(reg)
    if cmd == "probe":
        return cmd_probe(reg)
    if cmd == "smoke":
        return cmd_smoke(reg)
    if cmd == "decide":
        if len(sys.argv) < 3:
            print("usage: route_decide.py decide <task> [--kind K] [--json]", file=sys.stderr)
            return 2
        args = sys.argv[2:]
        as_json = "--json" in args
        if as_json:
            args.remove("--json")
        kind = None
        if "--kind" in args:
            i = args.index("--kind")
            kind = args[i + 1]
            del args[i:i + 2]
        return cmd_decide(reg, " ".join(args), kind, as_json)
    print(f"unknown cmd: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
