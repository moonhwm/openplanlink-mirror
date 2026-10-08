# 阿里云百炼四能力官方执行就绪核查

作者：Codex；独立认证文档复核：Codex 辅助审查席。技术发送者：`codex-review-20261005`。

唯一 ID：OPL-ALIBABA-OFFICIAL-READINESS-20261009-033017-663bfa66。

观察时间：2026-10-09 03:30:17 +08:00（对应 2026-10-08 19:30:17 UTC）。这是当前公开官方资料的观察记录，后续执行仍须核验当时的账号、地域、模型资格、价格和服务状态。

范围：该文档审查席仅访问公开官方文档，未读取用户的两个 AccessKey CSV，未调用鉴权、管理、付费推理或 RTC 接口，未创建 API Key，未修改 Git 工作区。本文提供接入依据和有限请求提案，不是实际执行、账户开通或费用回执。

## 1. 凭证与 API Key 管理

AccessKey ID/Secret 用于阿里云管理 OpenAPI 签名，不能原样放进模型推理的 API Key/Bearer 位置。百炼按量模型调用需要专用 API Key；Token Plan/Coding Plan 的专用 Key 是另一个产品范围。永久 Key 在创建对话框与 API Host 一同显示，关闭后不能再次查看完整值；执行器应直接写入受管私有凭证存储，仅输出非敏感状态。各地域 Key、模型列表和端点不能跨地域混用。[官方获取 API Key](https://help.aliyun.com/en/model-studio/get-api-key)

本轮已核实管理产品是 **ModelStudio，API version 2026-02-10**。官方 SDK 中心给出的北京管理 endpoint 是 **https://modelstudio.cn-beijing.aliyuncs.com**。Python 包名为 `alibabacloud-modelstudio20260210`；旧 `bailian20231229` 客户端没有同名管理方法不能证明产品缺少接口。管理域名与 `{WorkspaceId}.{region}.maas.aliyuncs.com` 推理域名不同。[官方 SDK 中心](https://troubleshooting.api.aliyun.com/api-tools/sdk/ModelStudio?language=typescript-tea&version=2026-02-10)

`CreateApiKey` 的 REST 方法是 `POST /modelstudio/apikeys`。已核实字段为 `workspaceId`、`description`、`auth.type`（`All` 或 `Custom`）、`auth.accessIps`、`auth.modelAccessScope.allowAllModels` 和 `auth.modelAccessScope.accessibleModels`。限定专用 Key 应显式使用 `Custom`、`allowAllModels=false`，只选当前任务获准的精确模型；IP 条件必须依据实际合法出口配置，不能猜测。该文档审查席未发出此请求，也未核实用户账户是否允许创建。[官方 CreateApiKey](https://troubleshooting.api.aliyun.com/api/ModelStudio/2026-02-10/CreateApiKey)

RAM 中 `modelstudio:CreateApiKey`、`modelstudio:DeleteApiKey` 的资源级别为 `*`，不能将不适用的 Workspace ARN 拼进这两项而宣称权限已收窄。`ListApiKeys` 是独立的 `modelstudio:ListApiKeys` 权限，不等于推理成功或资格开通。[官方 RAM 权限表](https://api.aliyun.com/document/ModelStudio/2026-02-10/ram)、[ListApiKeys](https://api.aliyun.com/document/ModelStudio/2026-02-10/ListApiKeys)

官方 Agent 接入资料提供 `aliyun-cli-modelstudio` 插件及 `modelstudio:ListWorkspaces / CreateApiKey / DeleteApiKey` 自定义权限路径。实际执行者可先执行获准的只读 RAM、业务空间核验，取得确切空间与区域，再走受管专用 Key 创建；不能把未知权限当全权限。该 RAG 接入指南的自动创建功能不能证明本次四类模型均已授权，也无需为本任务安装其整套 Skill。[官方 CLI 接入说明](https://help.aliyun.com/zh/model-studio/rag/agent-cli)

`CreateTokenPlanKey` 使用 `/tokenplan/api-keys`，创建的是 UAC Key，不能作为上述按量 `CreateApiKey` 的同义接口。该管理接口官方明确采用 `ACS3-HMAC-SHA256` AccessKey 签名及 `x-acs-action / x-acs-version` 等公共请求头，拒绝 Bearer 模型 Key；优先使用匹配版本的官方 SDK 处理签名。[官方 TokenPlan Key API](https://help.aliyun.com/zh/model-studio/create-token-plan-key)

官方 `bl auth generate-access-token` 支持 AK/SK 和可选 STS security token，但安装页仅描述 CLI 访问令牌；未明确其 TTL、所有推理端点兼容性或 HappyOyster 主 Key 身份。该文档审查席没有生成令牌。另一条 `/api/v1/tokens` 临时 API Key 路径由已有永久百炼 Key 的 Bearer 鉴权签发，默认 60 秒、可设 1–1800 秒并继承权限，两条流程不能混为一谈。[官方 CLI 鉴权](https://help.aliyun.com/zh/model-studio/cli/installation)、[临时 API Key](https://help.aliyun.com/zh/model-studio/generate-temporary-api-key)

官方人工入口：[北京 API Key 控制台](https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key)。模型 Key 创建前仍需相应账户/页面权限；未开通的权限应由合法账户管理员处理，本文不授予权限。

## 2. 地域与主机绑定

当前官方推荐 workspace 专用域名，创建 Key 或业务空间列表中的 **API Host** 是执行器应保存和核验的绑定依据。`dashscope.aliyuncs.com` 自 2026-09-30 起不再支持新特性，既有兼容接口建议迁移；它并非所有现有接口立即失效。不同地域各有 API Key 和模型列表，不能仅替换地域字符串就认定支持该模型。[官方地域说明](https://help.aliyun.com/zh/model-studio/regions)

| 地域 | Region ID | workspace 推理主机模板 |
| --- | --- | --- |
| 华北2（北京） | cn-beijing | `{WorkspaceId}.cn-beijing.maas.aliyuncs.com` |
| 新加坡 | ap-southeast-1 | `{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com` |
| 美国（弗吉尼亚） | us-east-1 | `{WorkspaceId}.us-east-1.maas.aliyuncs.com` |

下文选用已有公开文档直接支持的地域和路径。实际 Workspace ID、API Host、Key 引用、RAM 权限和模型资格均未由该文档审查席实测；不能填入文档示例空间或把未知计为零。

## 3. Embedding：text-embedding-v4

用户简称 `embedding-v4` 对应的精确 ID 是 **text-embedding-v4**。北京的 OpenAI 兼容入口是 `POST https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/embeddings`，`Content-Type: application/json`，`Authorization: Bearer <受管专用 API Key>`。v4 每请求最多 10 条输入、每条最多 8192 tokens；`dimensions` 支持最低 64，`encoding_format` 仅支持 `float`。[官方同步 Embedding API](https://help.aliyun.com/en/model-studio/text-embedding-synchronous-api)

有限 synthetic 提案：一次请求、一个原创短词、64 维；没有读取用户原文。

```json
{"model":"text-embedding-v4","input":"alpha","dimensions":64,"encoding_format":"float"}
```

成功验证必须检查真实响应 `data` 一项、`index=0`、`embedding` 为 64 个有限数值，并保存真实 request ID/`usage.total_tokens` 的脱敏回执。可仅输出维度、验证结果和向量摘要；无需落盘全部向量。降低维度减少返回体，计费仍按输入 tokens。北京原价 **0.5 元/百万输入 tokens**，新加坡国际 **0.514 元/百万**；北京免费额度有 90 天有效条件，未核实账户剩余额度不能当免费。[官方模型价格](https://help.aliyun.com/en/model-studio/model-pricing)

## 4. Rerank：qwen3-rerank

精确 ID **qwen3-rerank** 的北京入口是 `POST https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-api/v1/reranks`，JSON/Bearer 专用 Key。该型号的 `query`、`documents` 和 `top_n` 位于请求顶层；不包在原生接口的 `input`/`parameters` 中。官方 API 表列每请求最多 500 个文档、query/文档限制 4000 tokens。`return_documents` 未列为 qwen3-rerank 支持参数，不在有限请求中发送。[官方 Rerank API](https://help.aliyun.com/en/model-studio/text-rerank-api)

有限 synthetic 提案：一次请求、两个原创短词候选、仅返回一项。

```json
{"model":"qwen3-rerank","query":"alpha","documents":["alpha","beta"],"top_n":1}
```

成功验证检查真实响应顶层 `results` 一项、`index` 在输入范围内、`relevance_score` 为有限数值，并保存实际返回 model、request ID/usage 的脱敏回执；不伪造分数或保证某项必为第一。无需 `max_tokens`。北京原价 **0.5 元/百万输入 tokens**，新加坡国际 **0.74942 元/百万**；输出不计费，北京免费额度仍须账户与有效期核验。top_n 限制返回数量，不会免除已参与排序的输入计费。[官方模型价格](https://help.aliyun.com/en/model-studio/model-pricing)

模型详情页将 qwen3-rerank 总上下文列为 30000，API 文档另有更细的 query/文档限制；本提案远低于两者，不据此扩张请求大小或替换成 qwen3.7 型号。[qwen3-rerank 模型详情](https://help.aliyun.com/zh/model-studio/qwen3-rerank)

## 5. 决策模型：两个当前官方范围必须分开

当前 SystemOne API 是结构化分类、评分、是非判断接口，不生成文本；支持 `state` 和 `questions`，不使用普通 Chat messages，也不需要 `max_tokens`。专用 API 文档列出的 model 是 **decision-model-preview**；北京与新加坡分别为 workspace 域名的 `/compatible-mode/v1/systemone`，使用 **Bearer 专用 API Key**。[官方决策 API](https://help.aliyun.com/zh/model-studio/decision-model-api)

另一个当前官方微调指南明确列出用户指定的 **decision-model-preview-2026-09-24**，称可直接调用/微调，前提同时要求**联系商务经理开通授权**。该指南的推理示例/FAQ 使用 `https://dashscope.aliyuncs.com/compatible-mode/v1/systemone`（新加坡为 `dashscope-intl.aliyuncs.com`），`Authorization` 直接承载 API Key，**不加 Bearer**。该范围与专用 API 文档的 alias/workspace/Bearer 说明有差异，不能拼装混合请求，不能把 dated ID 静默替换为 alias。[官方决策微调指南](https://help.aliyun.com/zh/model-studio/decision-model-tuning-guide)

专用 API 页没有将 dated ID 列为允许的 model。该文档审查席不能仅凭两页推导 dated ID 必定接受 workspace/Bearer。执行精确 dated 通路前应取得该账户开通回执，并确认使用哪份文档对应的网关/鉴权；未成功返回前保持未实测。

有限问题结构提案（`model` 必须按已核实的通路填 alias 或 exact dated ID，一次请求、一问、两个选项）：

```json
{"model":"decision-model-preview-2026-09-24","state":"alpha","questions":{"label":{"type":"choice","instructions":"Select the matching word.","criteria":{"alpha":"The word alpha.","beta":"The word beta."}}}}
```

这是请求体提案，未发出；不会自证 dated ID 的权限或鉴权。模型详情页列最大输入 65536、生成文本输出 0、北京与新加坡 RPM 1200/TPM 200 万，价格为**限时免费**但未给活动终止时间；免费活动与账户开通资格都需执行前复核。微调指南的“0 元/千 token”属于微调计费，不能用来保证其部署免费。[决策模型详情](https://help.aliyun.com/zh/model-studio/decision-model-preview)

## 6. 世界模型：HappyOyster 是 World + RTC 链路

HappyOyster 使用 backend 主 API Key 创建 World、查询状态和换取 ticket；客户端使用临时 `token` 与一次性 `ticket` 进入 RTC 体验。仅得到创建请求 HTTP 200 或 `status=generating` 不等于构建完成、RTC 推理成功或视频完成。跨模型/跨账号 World 无权复用；体验结束后须释放会话，若要求视频还需验证作品 ready。[官方概览](https://help.aliyun.com/zh/model-studio/happyoyster-overview)、[官方接入流程](https://help.aliyun.com/zh/model-studio/happyoyster-integration-flow)

| 精确 App/模型 ID | 官方文档地域 | 资格/输入 | 官方原价示例 |
| --- | --- | --- | --- |
| happyoyster-1.0-adventure | 北京、新加坡、弗吉尼亚 | 必须首帧；该型号页未标明邀测，账户资格仍未知 | 北京创建 0.05 元/次；480p 体验 0.2 元/秒 |
| happyoyster-1.0-directing | 新加坡、弗吉尼亚 | 普通模式首帧可选；该型号页未标明邀测，账户资格仍未知 | 弗吉尼亚有图创建 0.05 元/次、无图 2 元/次；480p 体验 0.35 元/秒 |
| happyoyster-1.0-acting | 新加坡、弗吉尼亚 | **明确邀测阶段**；必须首帧 | 弗吉尼亚创建 0.05 元/次；480p 体验 0.2 元/秒 |

地域/价格/资格来源：[Adventure](https://help.aliyun.com/zh/model-studio/happyoyster-1-0-adventure)、[Directing](https://help.aliyun.com/zh/model-studio/happyoyster-1-0-directing)、[Acting](https://help.aliyun.com/zh/model-studio/happyoyster-1-0-acting)。表中价格不是本账户账单；RPM 的官方“—”代表未给数值，不能当零或不限流。

Adventure 北京创建入口：`POST https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1/worlds`，JSON/Bearer **主 API Key**。必填 `perspective`（first_person 或 third_person）、非空 `prompt`（最多 2000 字符）、`firstFrameImage`（URL 或完整 base64 Data URI 二选一）。首帧 JPG/JPEG/PNG/WebP、严格小于 6 MB、横屏宽高比 1.5–2.0；应使用合法原创 synthetic 图，不能复制文档截断 base64 或读取私有素材。默认异步，需后续每 3–5 秒查询构建状态，`ready` 才能取得 ticket。[Adventure 创建 API](https://help.aliyun.com/zh/model-studio/happyoyster-adventure-create-world-api-reference)

Directing 与 Acting 均提供新加坡和弗吉尼亚入口，使用的相同 `/api/v2/apps/{精确AppID}/openapi/v1/worlds` 路径，均只允许主 Key。Directing `creationModel=simple` 可使用短原创 prompt 与 `resolution=480p`；`aspectRatio`/`maxExperienceTimeSec` **固定 null**，不能编造该字段可限制体验秒数。Acting 必须首帧，aspectRatio 9:16 或 16:9 并与图匹配。[Directing 创建 API](https://help.aliyun.com/zh/model-studio/happyoyster-directing-create-world-api-reference)、[Acting 创建 API](https://help.aliyun.com/zh/model-studio/happyoyster-acting-create-world-api-reference)

世界模型没有文本输出 token 上限：费用边界需要一次创建、有限状态查询、真实 RTC 会话时长与可靠结束/释放；创建次数与体验秒数分别计费。账户、区域、主 Key、资格与 RTC SDK 能力未核实前，不能将提案标为执行成功。默认 60 秒、最长 1800 秒的临时 Key 和有效 30 分钟的一次性 ticket 是鉴权有效期，**不等于免费体验或费用上限**。[HappyOyster 鉴权](https://help.aliyun.com/zh/model-studio/happyoyster-auth-setup)

## 7. 执行器下一步与实际证据字段

1. 使用已授权的受管 AK/RAM 身份做只读身份/权限/业务空间核验；错误、AccessDenied、未知或没有响应不得升级为空账户或可调用。
2. 选定实际地域和 Workspace/API Host，按上述精确字段创建/配置限定专用模型 Key；管理结果的明文 Key 直接进入私有凭证存储，禁止在终端、报告或 Git 输出。
3. 先核验该 Key 的公开模型目录。目录请求成功仅证明目录可读，不算四能力执行；精确 dated decision 和 Acting 的资格仍要独立核验。
4. 在已有授权范围内执行每能力一次 synthetic 有限请求，拒绝将认证头随重定向发送到其他主机；按接口真实结构验证响应，失败保留失败阶段，不伪造 request ID、分数、向量、RTC 帧或账单。
5. HappyOyster 实际体验/视频若为验收目标，必须完成 ready、ticket、RTC 启停与相应作品状态验证；仅创建 World 应标记 `world_created` 阶段。

建议公开回执仅含：观察/执行时区、provider、精确 model ID、region、endpoint 模板、synthetic 输入摘要、阶段、HTTP/业务状态、响应形状、request ID 摘要、真实 usage、是否完成 RTC 结束以及账单核验状态。API Key/AK、账号私有 ID、完整素材/向量、用户原文均不应出现。费用未取得账单时为 unknown/null；额度不可用或未知都不能假定免费。

该文档审查席结果：`documentation_review_complete=true`；`credentials_read=false`；`api_key_created=false`；`inference_performed=false`；`rtc_performed=false`；`actual_cost=null`。这些字段仅描述该文档审查席文档审查，不汇总或代替实际执行者的接口核验，也不代表整个夜间协同目标完成。

## 8. HappyOyster 无客户端的有限检查补充

补充观察时间：2026-10-09 03:35:21 +08:00；本节仍为公开官方资料核查，没有发出世界模型请求。

Adventure 北京 World 列表入口是 `GET https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1/worlds?page=1&pageSize=1`，使用主 Key Bearer。pageSize 正数有效，上限 100；只验证 `code=0` 与列表/分页结构，公开输出不得包含已有 World 名称、用户素材或其私有 ID。空列表不是错误，更不能当生成完成。[官方 Adventure 列表 API](https://help.aliyun.com/zh/model-studio/happyoyster-adventure-query-world-list-api-reference)

若执行器在已有授权范围内创建一次 World，最小原创结构如下。`<complete synthetic PNG>` 是明确占位，必须在私有执行器内替换为合法完整图片编码，不能直接发送或当已准备素材。

```json
{"async":true,"perspective":"third_person","prompt":"A quiet geometric world with a blue cube.","firstFrameImage":{"base64":"data:image/png;base64,<complete synthetic PNG>"}}
```

构建状态使用 `GET /api/v2/apps/happyoyster-1.0-adventure/openapi/v1/worlds/build-status?encryptedWorldId=<该次真实响应ID>`，每 3–5 秒有限轮询。ID 来自创建的真实响应，不能由列表旧资源替代；记录 generating/ready/failed，超时保持未完成，ready 只证明该 World 构建就绪。[官方 Adventure 构建状态 API](https://help.aliyun.com/zh/model-studio/happyoyster-adventure-query-world-build-status-api-reference)

官方 `get-travel-credential` 明确不创建 Travel；Travel 在客户端进入房间成功时才创建。该凭证接口还核验 World 对应规格购买和容量，未购买返回 `403007`，容量暂不可用返回 `403008`。没有 RTC 客户端时，将本轮限定为 createWorld + build-status，避免额外创建 Travel；这仍不满足 RTC 视频体验验收。[官方 Adventure 体验凭证 API](https://help.aliyun.com/zh/model-studio/happyoyster-adventure-get-travel-credential-api-reference)

实际体验需要 SDK `startTravel`；`endTravel` 成功或异常退出会断开连接、停止内部轮询并释放会话资源。Android SDK 当前 Adventure `maxExperienceTimeSec` 只接受 **60 / 90 / 120**，默认 60；这是一项最大时长上限，不是最小计费时长，传 1 或 3 等无支持档位会被服务端拒绝。Directing/Acting 不使用这个上限。不能用临时凭证过期代替可靠结束会话。[官方 Android SDK API](https://help.aliyun.com/zh/model-studio/happyoyster-android-sdk-api-reference)

官方世界模型计费明确：创建按次数，体验按输出视频秒数，失败请求不产生费用，所有地域无免费额度。北京 Adventure 一次成功创建目录价 0.05 元；未进入 Travel 的检查没有本轮启动的 RTC 会话。最低计费秒数、舍入规则、该账户折扣和实际账单该文档审查席未核实，不给出“精确最低体验价”或“实际费用零”的承诺。[官方世界模型计价](https://help.aliyun.com/zh/model-studio/model-pricing)
