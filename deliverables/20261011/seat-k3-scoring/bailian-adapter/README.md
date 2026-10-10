# 百炼三类能力适配层脚手架（bailian-adapter）

件号：K3SCORING-ADAPTER-2026-1010-01
责任席：K3·评分系统席（k3-scoring-web） · 2026-10-10
状态：**脚手架（scaffold）——接口形状与纪律已固化；实弹调用候凭据落位**

## 三类能力接口位（对应主权人 2026-10-10 指令）

| 能力类 | 模块 | 百炼侧映射（暂定） | 接口形状 |
| --- | --- | --- | --- |
| 决策模型 | `adapter/decision.py` | 文本生成（qwen 系）结构化输出 | `decide(item) -> {label, probs, confidence}` 单次前向完成分类/是非/评分，输出概率分布与置信度 |
| 向量编码与重排序 | `adapter/embed_rerank.py` | text-embedding-v4 / multimodal-embedding + gte-rerank-v2 | `embed(texts) -> vectors`；`rerank(query, docs) -> ranked` |
| 世界模型 | `adapter/world_model.py` | 接口位预留（实时交互开放式世界模型非百炼现成单品） | 三类运行模式事件协议：世界探索 / 实时导演 / 角色演绎 |

## 凭据铁律（零明文）

- 本包**零凭据**。`BAILIAN_API_KEY` 只经环境变量落位；缺钥时所有网络路径**诚实拒绝**（`CredentialsNotLanded`），不伪造、不降级冒充实弹。
- 两份百炼密钥 CSV 留存于用户本机，沙箱不可读；文件名等凭据标识按凭据铁律登记、不落文档。落位通道：`/mnt/agents/upload/credentials.env`（`set -a; . credentials.env; set +a` 模式，tripo-avatar-ops 先例）。
- 302ai key 明文外泄已登记并案（呈批：轮换候裁定）；本包不接收、不存储、不转发任何明文 key。

## 设计依据（纲要 ci2ybbMcccFi §部署建议）

适配器模式：认证、请求、解析隔离于独立模块；异常回退策略化；令牌刷新与重试在 `telemetry.py` 埋点（成功率/延迟分布），为正式路由权重调整供数。

## 验证

```bash
python3 examples/demo_offline.py     # 离线 mock 演示接口形状（不触网、不烧额度）
python3 tests/test_contract.py       # 契约测试（mock provider）
```
