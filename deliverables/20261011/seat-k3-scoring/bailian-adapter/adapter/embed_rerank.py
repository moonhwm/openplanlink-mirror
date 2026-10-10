"""embed_rerank.py —— 向量编码与重排序模块（文本/图文向量化 + 重排序提升检索精度）。

契约：
    embed(texts) -> list[list[float]]                      # DashScope text-embedding-v4
    rerank(query, docs, top_n=None) -> [(idx, score), ...] # gte-rerank-v2，按相关度降序
provider 可插拔；缺钥即拒（CredentialsNotLanded）。
"""
from __future__ import annotations
import json, time
from .config import BailianConfig
from .telemetry import Telemetry


class BailianEmbedProvider:
    def __init__(self, cfg: BailianConfig):
        self.cfg = cfg

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        key = self.cfg.require_armed()
        import urllib.request
        req = urllib.request.Request(
            "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding",
            data=json.dumps({"model": model,
                             "input": {"texts": texts},
                             "parameters": {"output_dimension": 1024}}).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=self.cfg.timeout_s) as r:
            payload = json.loads(r.read())
        embs = payload["output"]["embeddings"]
        return [e["embedding"] for e in sorted(embs, key=lambda e: e["text_index"])]

    def rerank(self, query: str, docs: list[str], model: str,
               top_n: int | None) -> list[tuple[int, float]]:
        key = self.cfg.require_armed()
        import urllib.request
        req = urllib.request.Request(
            "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
            data=json.dumps({"model": model,
                             "input": {"query": query, "documents": docs},
                             "parameters": {"top_n": top_n or len(docs),
                                            "return_documents": False}}).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=self.cfg.timeout_s) as r:
            payload = json.loads(r.read())
        return [(r["index"], float(r["relevance_score"]))
                for r in payload["output"]["results"]]


class EmbedRerank:
    def __init__(self, provider=None, cfg: BailianConfig | None = None,
                 telemetry: Telemetry | None = None):
        self.cfg = cfg or BailianConfig()
        self.provider = provider or BailianEmbedProvider(self.cfg)
        self.tel = telemetry or Telemetry()

    def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        assert texts and all(isinstance(t, str) and t.strip() for t in texts), "空文本"
        t0 = time.perf_counter()
        out = self.provider.embed(texts, model or BailianConfig.DEFAULT_EMBED_MODEL)
        assert len(out) == len(texts), "向量数与文本数不齐"
        self.tel.record("embed", True, (time.perf_counter() - t0) * 1000)
        return out

    def rerank(self, query: str, docs: list[str],
               top_n: int | None = None, model: str | None = None) -> list[tuple[int, float]]:
        assert query.strip() and docs, "空查询或空文档池"
        t0 = time.perf_counter()
        out = self.provider.rerank(query, docs,
                                   model or BailianConfig.DEFAULT_RERANK_MODEL, top_n)
        assert all(0 <= i < len(docs) for i, _ in out), "重排序索引越界"
        self.tel.record("rerank", True, (time.perf_counter() - t0) * 1000)
        return out
