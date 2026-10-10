"""bailian-adapter —— 阿里云百炼三类能力适配层（脚手架）。

纪律：
- 零凭据落盘；API key 只经 env 读取（BAILIAN_API_KEY）。
- 缺钥即抛 CredentialsNotLanded——诚实拒绝，不伪造返回。
- 所有实弹调用经 telemetry 埋点（成功率/延迟）。
"""
from .config import BailianConfig, CredentialsNotLanded
from .decision import DecisionModel
from .embed_rerank import EmbedRerank
from .world_model import WorldModelClient, WorldMode

__all__ = [
    "BailianConfig", "CredentialsNotLanded",
    "DecisionModel", "EmbedRerank",
    "WorldModelClient", "WorldMode",
]
__version__ = "0.1.0-scaffold"
