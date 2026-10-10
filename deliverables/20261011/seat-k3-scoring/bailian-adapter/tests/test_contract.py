#!/usr/bin/env python3
"""test_contract.py —— 契约测试（全 mock，不触网）。"""
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from adapter import (BailianConfig, CredentialsNotLanded, DecisionModel,
                     EmbedRerank, WorldModelClient, WorldMode)
from adapter.telemetry import Telemetry
from adapter.world_model import LocalWorldBackend

fails = []
def check(name, cond):
    print(("PASS" if cond else "FAIL"), name)
    if not cond:
        fails.append(name)

# 1) 缺钥即拒
cfg = BailianConfig(api_key=None)
check("cfg unarmed", not cfg.armed)
try:
    cfg.require_armed(); check("require_armed raises", False)
except CredentialsNotLanded:
    check("require_armed raises", True)
os.environ.pop("BAILIAN_API_KEY", None)

# 2) 决策契约（probs 归一 + 置信度区间 + 键域）
class GoodP:
    def complete_json(self, s, u):
        return {"label": "否", "probs": {"是": 0.3, "否": 0.7}, "confidence": 0.8}
class BadP:
    def complete_json(self, s, u):
        return {"label": "否", "probs": {"是": 0.9, "否": 0.9}, "confidence": 1.2}
log = os.path.join(tempfile.mkdtemp(), "tel.jsonl")
dm = DecisionModel(provider=GoodP(), telemetry=Telemetry(log))
out = dm.decide("t", ["是", "否"])
check("decide ok", out["label"] == "否" and abs(sum(out["probs"].values()) - 1) < 1e-6)
try:
    DecisionModel(provider=BadP()).decide("t", ["是", "否"]); check("bad contract rejected", False)
except AssertionError:
    check("bad contract rejected", True)

# 3) 向量/重排序契约
class EP:
    def embed(self, texts, model): return [[1.0, 0.0] for _ in texts]
    def rerank(self, q, docs, model, top_n): return [(1, 0.9), (0, 0.1)]
er = EmbedRerank(provider=EP())
check("embed shape", len(er.embed(["a", "b"])) == 2)
check("rerank order", er.rerank("q", ["d0", "d1"])[0][0] == 1)

# 4) 世界模型三模式事件
wm = WorldModelClient(backend=LocalWorldBackend())
s = wm.direct(shot="lamp", cue="dusk")
check("direct state", s["mode"] == WorldMode.DIRECT.value and s["camera"]["shot"] == "lamp")
s = wm.roleplay(line_idx=1)
check("role state", s["mode"] == WorldMode.ROLEPLAY.value and s["persona"]["line_idx"] == 1)
try:
    wm.backend.apply({"type": "bogus"}); check("unknown event rejected", False)
except ValueError:
    check("unknown event rejected", True)

# 5) 埋点落账且无凭据字段
rows = open(log, encoding="utf-8").read()
check("telemetry rows", '"endpoint": "decision"' in rows)
check("telemetry no-key", "key" not in rows.lower() or "api_key" not in rows)

print("\nVERDICT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
