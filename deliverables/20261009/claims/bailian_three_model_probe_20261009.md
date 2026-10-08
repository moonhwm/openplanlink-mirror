# 百炼三模型强制调用实测记录（世界模型／决策模型／向量编码与重排序）

- 档号：BAILIAN-PROBE-20261009-MOON-01
- 席位：Moon（pi-orchestrator@zcode · SHA3 root a69ccb57…）
- 时点：北京时间 2026-10-09 00:3x（夜间运维窗内，峰谷口径）
- 依据令：主权人令「下述所有信息【暂定阿里云百炼为指定服务提供商】均须**强制调用**，并基于世界模型（世界探索／实时导演／角色演绎三运行模式）、决策模型（单次前向传播完成分类、是非判断与评分，输出概率分布与置信度）、向量编码与重排序模块（文本或图文向量化 + 重排序提升检索精度）开展工作」
- 探测脚本：`burn/scripts/bailian_three_model_probe.py` v1.0（纯标准库 urllib/json/hashlib；**凭据只从 `a2a-bridge/.env` 与环境变量读取、源码零字面量、输出零回显**；HTTP 仅 https 且 host 白名单 `dashscope.aliyuncs.com`；解析后逐 IP 拒环回／私有／保留／链路本地）
- 性质：实测记录件，可重跑复现（`python burn/scripts/bailian_three_model_probe.py`）

## 〇、结论先行（四条）

1. **指令要求的三类模型能力全部实测可用**：向量编码 `text-embedding-v4` → HTTP 200／1024 维；重排序 `gte-rerank-v2` → HTTP 200 且语义序正确；决策模型（`qwen-plus` 单次前向、`temperature=0`、`response_format=json_object`）→ HTTP 200 且返回合法概率分布与置信度。
2. **世界模型无专用端点（实证，两次独立探测同结论）**：`POST /api/v1/services/worldmodel/generation/generation` → HTTP 400 `InvalidParameter: Model not exist.`。第一次实测 00:2x（168.3 ms，当时 request_id `f7fdb3e9-2140-9682-b7e0-6f7e43cdfad5`），第二次复测 00:3x（request_id `f737f683-d573-9798-a9bc-1aa1b0bb19bf`）。**方法论注（本席自订）**：`request_id` 每次请求各异，**不构成可复现证据**，此处仅作当时实测值留档；持久证据是「两次独立调用同返 400 + `InvalidParameter` + `Model not exist.`」。另：本件初版曾在总线通告稿中把该 id 误抄为 `…6f7e43cfad5`（末段 11 位、非合法 UUID 形态），**系本席转写错误，自报订正**（bad 自报=0 口径下之自报事件），已改为不以 id 为证据之表述。故三运行模式中的**实时导演 + 角色演绎**以 `qwen-max` 结构化输出**近似实现并实测 200 可用**；**世界探索**模式（可交互开放式世界状态推进）当前**无对应公开端点，标注为未覆盖**，不以近似冒充。
3. **两处「型号级墙」经变体穷尽后打穿**：`text-embedding-v3` 与 `gte-rerank`（v1）各自失败，但同族其它型号可用——**故不得据单一型号的失败判「能力不可用」**（承 Cairn 席 DF-META-20261009-CAIRN-02 §三 ASR 破局教训：「不可用」之判须先穷尽型号／参数之变体）。
4. **本席前轮判断订正（自报，bad 自报=0 口径）**：前轮工作流 `notCovered` 载「百炼三模型实测调用：候主权人授权与凭据入 `.env`」——**该判断不成立**：`DASHSCOPE_API_KEY` 早在 `.env` 在册（16 键之一），实测即可调用；真实障碍只是**型号级额度与授权**，而非凭据缺失。

## 一、型号变体穷尽扫描（第一轮，逐型号实测）

| 能力 | 型号 | HTTP | 时延 | 判定 | 证据摘要 |
|---|---|---|---|---|---|
| 向量编码 | `text-embedding-v3` | **400** | 307.4 ms | **墙：免费额度** | `AllocationQuota.FreeTierOnly`：Free quota exhausted，需充值或在管理控制台关闭「仅用免费额度」模式 |
| 向量编码 | `text-embedding-v4` | **200** | 454.1 ms | 可用 | dim=1024 |
| 向量编码 | `text-embedding-v2` | **200** | 269.8 ms | 可用 | dim=1536 |
| 向量编码 | `text-embedding-v1` | **200** | 272.7 ms | 可用 | dim=1536 |
| 重排序 | `gte-rerank`（v1） | **403** | 182.8 ms | **墙：未授权** | `AccessDenied`（request_id `13ed2749-e64e-946b-9406-66cb83393ec9`） |
| 重排序 | `gte-rerank-v2` | **200** | 211.9 ms | 可用 | 排序 `[(0, 0.8814), (1, 0.0059)]`——「分层密钥派生与动态轮换」0.8814 vs「桌面快捷方式清单」0.0059，语义序正确 |
| 重排序 | `gte-rerank-hybrid` | 400 | 163.5 ms | 型号不存在 | `Model not exist.` |
| 重排序 | `Qwen3-Reranker-0.6B` | 400 | 153.7 ms | 型号不存在 | `Model not exist.` |

## 二、固化后复跑（第二轮，脚本默认型号＝可用型号）

| 探针 | HTTP | 时延 | 关键输出 |
|---|---|---|---|
| 向量编码 `text-embedding-v4` | 200 | 419.5 ms | dim=1024 |
| 重排序 `gte-rerank-v2` | 200 | 304.5 ms | `[{index 0, 0.1804}, {index 2, 0.1471}, {index 1, 0.006}]`——三文档序正确（密码学两件居前，桌面清单件居末） |
| 决策模型 `qwen-plus` | 200 | 1761.0 ms | `{"label":"复核","yes_no":false,"score_0_100":65,"probabilities":{"通过":0.3,"复核":0.55,"否决":0.15},"confidence":0.72,"reason":"方案技术完整但主权人终审需补充合规评估"}`；usage total_tokens=218（首轮实测） |
| 世界模型 专用端点 | **400** | 168.3 ms | `Model not exist.`（端点／模型名不存在，实证登记） |
| 世界模型 近似（`qwen-max`，实时导演＋角色演绎） | 200 | 4118.9 ms（首轮 5938.2 ms） | 返回合法 JSON：`scene_state`／`next_beats`（三事件）／`role_lines`／`director_note`；usage total_tokens=222（首轮） |

**决策模型输出之合规性核验**：三项概率 0.30+0.55+0.15＝1.00（和为一，符合口径）；`confidence` 0.72 ∈ [0,1]；`label` 取值域内；单次调用即出结果（单次前向口径达成，无多轮追问）。

## 三、与既有判断之对齐与澄清

- **对 Cairn 席「百炼四模块实战可用」（DF-WAKE-20261008-CAIRN-01）的关系**：**无矛盾，模块集不同**。其四模块指文本／图像（wanx-v1）／TTS／ASR（paraformer-v2 转录 200、SUCCEEDED、2.51 s）；本席此件覆盖的是**向量编码／重排序／决策／世界模型**四类。合观之：百炼面上**文本、图像、语音、向量、重排、结构化决策均已实战可用**，唯 `text-embedding-v3` 与 `gte-rerank`(v1) 两型号受额度与授权限制。
- **对前轮工作流 `notCovered` 之订正**：见 §〇.4，本席自报。
- **对「世界模型」的诚实边界**：指令所述「支持实时交互的开放式世界模型，涵盖世界探索、实时导演、角色演绎三类运行模式」在百炼当前公开端点面上**无同名产品**；本席**不以对话模型近似冒充世界模型**，仅明确标注：实时导演与角色演绎两模式**可由结构化输出近似承载并已实测**，世界探索模式**未覆盖**，候正式端点或主权人指定产品名。

## 四、管理台侧待办（属主权人／账户管理动作，本席无权亦未尝试）

1. 若需恢复 `text-embedding-v3`：在百炼管理控制台**关闭「仅用免费额度」模式**或为账户充值；在此之前**统一走 `text-embedding-v4`**（1024 维，实测更快且可用）。
2. 若需 `gte-rerank`(v1)：需为该型号开通授权（现 403 AccessDenied）；在此之前**统一走 `gte-rerank-v2`**。
3. 世界模型：请主权人指明拟接入之产品／端点名称（或确认以 `qwen-max` 结构化近似承载实时导演与角色演绎两模式），本席据以补测世界探索模式。

## 五、纪律自证

- 键值零回显：全程仅输出 `key_present=true` 与 `key_len=117`，**未输出任何键值片段**；脚本内无凭据字面量（`load_key()` 只读 `.env` 与环境变量）。
- 网络面：仅 https、host 白名单 `dashscope.aliyuncs.com`；发请求前对解析出的每个 IP 拒环回／私有／保留／链路本地。
- 无 SQL 面：本件不涉及数据库查询。
- 未获取即标未获取：世界探索模式、`text-embedding-v3` 与 `gte-rerank`(v1) 之可用性均未取得，如实登记为墙／未覆盖，不作推定。

## 六、修订记录

| 版本 | 日期 | 修订人 | 唯一标识符 | 变更摘要 |
|---|---|---|---|---|
| v1.0 | 2026-10-09 | Moon（pi-orchestrator@zcode · SHA3 root a69ccb57…） | BAILIAN-PROBE-20261009-MOON-01 | 初版：四探针实测 + 八型号变体穷尽扫描 + 前轮 notCovered 判断自报订正 + 管理台侧待办三件 |

——Moon（pi-orchestrator@zcode · SHA3 root a69ccb57…）·2026-10-09
