# ima 第四库通道探查报告（2026-10-03）

**拟稿**：K3 主程序（from_mode=k3-main）
**事由**：SCH-11 尾项第四库（ima）建仓——守藏席 DF-ARC-2026-0930-ARCH-01 探明通道，本轮凭据实测。

## 一、结论置顶

**通道规范已全部逆向明确，但归档凭据认证失败（code 200002 skill auth failed），第四库建仓待机长重新签发凭据后即可一步完成。**

## 二、通道规范（自官方技能包 v1.1.10 逆向，包已本地镜像）

- **OpenAPI REST**：`POST https://ima.qq.com/openapi/<path>`，认证头：`ima-openapi-clientid`、`ima-openapi-apikey`（另有遥测头 `ima-openapi-ctx: skill_version=...`）。
- **笔记域端点**：`note/v1/search_note`、`list_note`、`get_doc_content`、`import_doc`、`append_doc`、`list_notebook`。
- **知识库域端点**：`wiki/v1/create_media`、`add_knowledge`、`get_knowledge_base`、`get_knowledge_list`、`search_knowledge`、`search_knowledge_base`、`get_addable_knowledge_base_list`、`check_repeated_names`、`import_urls`、`get_media_info`。
- **MCP 端点**：`https://ima.qq.com/mcp`（streamableHttp）在线，但要求不透明 access token，ClientID/APIKey 各形态直投均报 `token parse failed`，故可用路径以 OpenAPI REST 为准。
- **技能包**：`https://app-dl.ima.qq.com/skills/ima-skills-1.1.10.zip`（62KB），本地镜像于 `ima_skill_pkg/`。

## 三、实测记录（只读接口，未做任何写操作）

| 探测 | 结果 |
|---|---|
| REST 基础形态 `clientid=b64段, apikey=hex段` | 401 / 200002 skill auth failed |
| hex/b64 对调、label 并入 clientid、去 padding、label 单独 | 均 401 / 200002 |
| MCP 端点 9 种 token 形态 | 400 / 110042 token parse failed（端点在线） |

**判读**：归档凭据疑已吊销或转写截断（hex 段 31 位奇数长，标准应为 32 位）。凭据系机长于会话中明文提供，此前已在聊天暴露，按 09-29 先例**建议用后轮换**。

## 四、待办（需机长动作）

1. 前往 ima.qq.com/agent-interface 重新签发 Client ID 与 API Key；
2. 签发后交本席一步完成：笔记本列表留痕 → 建仓归档 → 总线通告 → SCH-11 四库全链闭环。

## 五、top3_likely_wrong

1. hex 段可能在转写中截断（31 位奇数长）；
2. 凭据可能绑定其他账号或已被服务端轮换；
3. MCP 的 token 换发端点尚未定位（OpenAPI 路径不受影响）。

---
登记：总线通告 id 见正文汇报；数据截止 2026-10-03 当轮。
