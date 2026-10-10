"""telemetry.py —— 调用埋点（纲要 §部署建议：成功率/延迟分布量化，供路由权重调整）。"""
from __future__ import annotations
import json, time
from pathlib import Path


class Telemetry:
    """追加式 JSONL 埋点。只记元数据（端点/耗时/成败/重试数），永不记凭据与载荷明文。"""

    def __init__(self, log_path: str | Path | None = None):
        self.log_path = Path(log_path) if log_path else None

    def record(self, endpoint: str, ok: bool, latency_ms: float,
               retries: int = 0, note: str = "") -> dict:
        row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "endpoint": endpoint, "ok": ok,
               "latency_ms": round(latency_ms, 1), "retries": retries, "note": note}
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row
