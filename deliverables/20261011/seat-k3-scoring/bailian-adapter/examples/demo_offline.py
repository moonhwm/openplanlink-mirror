#!/usr/bin/env python3
"""demo_offline.py —— 离线 mock 演示接口形状（不触网、不烧额度、不需凭据）。"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from adapter import DecisionModel, EmbedRerank, WorldModelClient, CredentialsNotLanded


class MockDecisionProvider:
    def complete_json(self, system, user):
        return {"label": "是", "probs": {"是": 0.72, "否": 0.28}, "confidence": 0.64}


class MockEmbedProvider:
    def embed(self, texts, model):
        return [[float(len(t)), 1.0, 0.0] for t in texts]

    def rerank(self, query, docs, model, top_n):
        # mock：按与 query 的字符重叠度打分
        q = set(query)
        scored = sorted(((i, len(q & set(d)) / max(len(q), 1)) for i, d in enumerate(docs)),
                        key=lambda x: -x[1])
        return scored[: top_n or len(docs)]


def main():
    print("== 决策模型（mock）==")
    dm = DecisionModel(provider=MockDecisionProvider())
    print(dm.decide("该院校博士点是否支撑申博衔接？", ["是", "否"]))

    print("== 向量编码与重排序（mock）==")
    er = EmbedRerank(provider=MockEmbedProvider())
    vecs = er.embed(["断头路风险评估", "导师指导舒适度"])
    print("embed dims:", [len(v) for v in vecs])
    print("rerank:", er.rerank("申博衔接", ["博士点覆盖", "城市宜居", "衔接导师资源"]))

    print("== 世界模型（本地回退）==")
    wm = WorldModelClient()
    print("explore ->", wm.explore())
    print("direct  ->", wm.direct(shot="lamp", cue="dusk"))
    print("role    ->", wm.roleplay(line_idx=2))

    print("== 缺钥诚实拒绝 ==")
    try:
        DecisionModel().decide("x", ["是", "否"])
    except CredentialsNotLanded as e:
        print("CredentialsNotLanded:", e)


if __name__ == "__main__":
    main()
