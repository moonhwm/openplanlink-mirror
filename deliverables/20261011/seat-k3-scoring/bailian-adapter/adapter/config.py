"""config.py —— 认证与端点配置（隔离层）。

凭据只经环境变量 BAILIAN_API_KEY 落位；两份百炼密钥 CSV 留存用户本机，
沙箱不可读，须先经 credentials.env 机制落位（tripo-avatar-ops 先例）。
凭据标识按凭据铁律登记，不落文档。
"""
from __future__ import annotations
import os


class CredentialsNotLanded(RuntimeError):
    """凭据未落位——诚实拒绝实弹调用（不伪造、不降级冒充）。"""


class BailianConfig:
    """百炼接入配置。零凭据硬编码；缺钥对象可建、调用即拒。"""

    DEFAULT_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEFAULT_DECISION_MODEL = "qwen-plus"      # 决策模型占位（单次前向结构化输出）
    DEFAULT_EMBED_MODEL = "text-embedding-v4"
    DEFAULT_RERANK_MODEL = "gte-rerank-v2"

    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 timeout_s: float = 30.0, max_retry: int = 2):
        self.api_key = api_key or os.environ.get("BAILIAN_API_KEY") or None
        self.base_url = base_url or os.environ.get("BAILIAN_BASE_URL") or self.DEFAULT_BASE
        self.timeout_s = timeout_s
        self.max_retry = max_retry

    @property
    def armed(self) -> bool:
        """是否已凭据落位（可实弹）。"""
        return bool(self.api_key)

    def require_armed(self) -> str:
        if not self.api_key:
            raise CredentialsNotLanded(
                "BAILIAN_API_KEY 未落位：请经 env / credentials.env 机制注入，"
                "严禁明文写入代码、文档、页面或日志。")
        return self.api_key
