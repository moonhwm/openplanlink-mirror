"""decision.py —— 决策模型适配器（面向高频业务判断的结构化决策模型）。

契约：单次前向传播完成分类 / 是非判断 / 评分，输出概率分布 + 置信度。
    decide(item) -> {"label": str, "probs": {label: p, ...}, "confidence": float}
provider 可插拔：默认 BailianProvider（需凭据落位）；测试用 MockProvider。
"""
from __future__ import annotations
import json, time
from .config import BailianConfig
from .telemetry import Telemetry


class BailianProvider:
    """OpenAI 兼容端点结构化输出（dashscope compatible-mode）。脚手架：懒加载、缺钥即拒。"""

    def __init__(self, cfg: BailianConfig, model: str | None = None):
        self.cfg = cfg
        self.model = model or BailianConfig.DEFAULT_DECISION_MODEL

    def complete_json(self, system: str, user: str) -> dict:
        key = self.cfg.require_armed()  # 缺钥在此诚实拒绝
        import urllib.request  # 零三方依赖；后续可换 dashscope SDK
        req = urllib.request.Request(
            f"{self.cfg.base_url}/chat/completions",
            data=json.dumps({
                "model": self.model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            }).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=self.cfg.timeout_s) as r:
            payload = json.loads(r.read())
        return json.loads(payload["choices"][0]["message"]["content"])


_SYSTEM = (
    "你是结构化决策模型。对输入事项单次前向完成判断，只输出 JSON："
    '{"label": 最可能类别, "probs": {每类: 概率}, "confidence": 0..1 置信度}。'
    "probs 之和须为 1；confidence 反映证据强度，证据不足须压低。"
)


class DecisionModel:
    def __init__(self, provider=None, cfg: BailianConfig | None = None,
                 telemetry: Telemetry | None = None):
        self.cfg = cfg or BailianConfig()
        self.provider = provider or BailianProvider(self.cfg)
        self.tel = telemetry or Telemetry()

    def decide(self, item: str, labels: list[str]) -> dict:
        """单次前向：分类/是非/评分。labels 为候选类别（是非判断传 ['是','否']）。"""
        t0 = time.perf_counter()
        retries = 0
        while True:
            try:
                out = self.provider.complete_json(
                    _SYSTEM, f"候选类别：{labels}\n事项：{item}\n输出 JSON。")
                break
            except Exception:
                retries += 1
                if retries > self.cfg.max_retry:
                    self.tel.record("decision", False,
                                    (time.perf_counter() - t0) * 1000, retries - 1)
                    raise
                time.sleep(0.6 * retries)  # 指数退避
        self._validate(out, labels)
        self.tel.record("decision", True, (time.perf_counter() - t0) * 1000, retries)
        return out

    @staticmethod
    def _validate(out: dict, labels: list[str]) -> None:
        assert isinstance(out.get("label"), str), "缺 label"
        probs = out.get("probs")
        assert isinstance(probs, dict) and probs, "缺 probs"
        s = sum(float(v) for v in probs.values())
        assert abs(s - 1.0) < 0.02, f"probs 归一失败 sum={s}"
        assert 0.0 <= float(out.get("confidence", -1)) <= 1.0, "confidence 越界"
        for k in probs:
            assert k in labels, f"probs 键 {k!r} 越出候选类别"
