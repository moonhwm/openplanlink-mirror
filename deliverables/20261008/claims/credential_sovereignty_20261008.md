# 凭据主权流程登记件（2026-10-08）

- 登记件编号：CRED-SOV-20261008-MOON-01
- 关联票据：`TICKET-20261008-MOON-02`（**现行**，`burn/claims/credential_ticket_20261008_02.json`，merkle_root 前 16 位 `44f3fcce839648f8`）；`TICKET-20261008-MOON-01`（首发，`burn/claims/credential_ticket_20261008.json`，merkle_root 前 16 位 `bc59b12db2d37dac`，append-only 保留不删）
- 核验纪律：本件所有凭据类文件**只做 stat 级存在性核验**（路径/字节数/修改时间），未读取任何文件内容；全件零凭据明文、零 AccessKey 值，只允许键名引用。

---

## 一、桌面两份 CSV 存在性核验（stat 级，未读内容）

| 文件路径 | 字节数 | 修改时间（本机时区） | 存在性 |
|---|---|---|---|
| `C:\Users\欧阳宏俊\OneDrive\桌面\AccessKey RAM角色.csv` | 85 | 2026-10-08 15:55:19 | 存在 |
| `C:\Users\欧阳宏俊\OneDrive\桌面\AccessKey 阿里云百炼主账户.csv` | 85 | 2026-10-08 16:27:22 | 存在 |

核验方式：python `pathlib.Path.stat()`（仅取 `st_size` / `st_mtime`），核验命令与输出见本席会话记录；两份各 85 字节，与任务口径一致。**文件内容与其中任何 AccessKey 值一律不入册、不回显、不搬运。**

## 二、`a2a-bridge/.env` 现有键名清单（只键名，共 16 个）

核验方式：逐行取 `=` 左侧键名，值零读取零回显（`.env` 文件 1224 字节，存在）。

1. `DASHSCOPE_API_KEY`
2. `DASHSCOPE_WS_KEY`
3. `DASHSCOPE_WS_BASE`
4. `HUAWEI_MAAS_KEY`
5. `HUAWEI_MAAS_BASE`
6. `TUSHARE_TOKEN`
7. `TUSHARE_BASE`
8. `ARK_ACCESS_KEY`
9. `ARK_SECRET_KEY`
10. `ARK_LOGIN_URL`
11. `ARK_ACCOUNT_ID`
12. `ARK_MODEL`
13. `ARK_ENDPOINT`
14. `SILICONFLOW_API_KEY`
15. `AI302_API_KEY`
16. `SCNET_API_KEY`

**能力口径说明**：

- `DASHSCOPE_API_KEY` 已在册，意味着**百炼 DashScope 模型调用能力已具备**（推理通道，五通道探测中的百炼线即依赖此键）。
- 桌面两份 CSV 是**阿里云主账户 / RAM 角色 AccessKey**（AccessKeyId + AccessKeySecret 对），用途是**阿里云 OpenAPI 请求签名**（管控面：资源管理、账单、RAM 等），与 DashScope API key 属**不同用途、不同信任面**，二者不可互相替代。主账户 AccessKey 权限面大于 RAM 角色，主权风险更高。

## 三、提请裁定事项

**议题**：是否将桌面两份 CSV 中的阿里云 AccessKey 迁入 `a2a-bridge/.env` 统一管理。

- 建议键名：`ALIYUN_AK_ID` / `ALIYUN_AK_SECRET`，且**区分主账户与 RAM 角色两套**（例如 `ALIYUN_MAIN_AK_ID` / `ALIYUN_MAIN_AK_SECRET` 与 `ALIYUN_RAM_AK_ID` / `ALIYUN_RAM_AK_SECRET`，最终命名候裁定）；
- 若裁定迁入：优先建议仅迁 RAM 角色套（最小权限面），主账户套是否入册单独裁定；
- **裁定作出前维持原样**：CSV 留在桌面原位置，本席不搬运明文、不做任何复制/转录；
- 审批链照录：**责任席提案 → 筹备组审议 → 主权人拍板**，未过链不得对外承诺、不得迁移动作。

## 四、后量子密钥响应口径（照录现行章程）

持有密钥者对 API/key 请求**一律以现行后量子方案回应**：HMAC-SHA3-512 签名链路在册（本轮票据 `TICKET-20261008-MOON-01/-02` 即按该口径设计：`sig_alg` 固定 `HMAC-SHA3-512`，签名钥只从环境变量 `OPL_TICKET_KEY` 读取，本轮未注入故 `sig` 为 null、候密钥注入后补签），**明文密钥零回显**。

## 五、本轮凭证票据签发摘要

**现行之票：TICKET-20261008-MOON-02**（2026-10-08T21:25:11.1930187+08:00 重签，`burn/claims/credential_ticket_20261008_02.json`，2722 bytes）

| 项 | 值 |
|---|---|
| ticket_id | TICKET-20261008-MOON-02 |
| issued_at | 2026-10-08T21:25:11.1930187+08:00（powershell `Get-Date -Format o` 实测） |
| merkle_root（前 16 位） | `44f3fcce839648f8`（全量 128 位十六进制见票据 JSON；5 叶子，独立重算比对一致） |
| Merkle 约定 | 叶子=各产件 SHA3-512 全量十六进制；父节点=sha3_512(left_hex+right_hex)；奇数节点复制自身 |
| 入册产件 | **5 件全部在册**（两 OTL 文稿 + 融合简报 + lsbus.py + SKILL.md），逐件与磁盘现状哈希比对一致 |
| 签名状态 | `OPL_TICKET_KEY` 未注入（重签时复查仍 absent）→ `sig: null`，候密钥注入后补签；完整性已由 merkle_root 保障 |
| 签发脚本 | `burn/claims/merkle_ticket_20261008.py`（纯标准库，pathlib.read_bytes / Path.write_text；带 append-only 防覆盖闸——对已存在票据拒绝重写并 exit 2，实测生效） |

**重签事由（漂移实录）**：-01 签发（19:36:00）后检测到两处产件状态变更——①`PQC端到端加密与分布式信任体系升级方案_党组学术视角.otl.md` 于 21:09:55 被责任席修订（51931→54570 bytes，sha3_16 `9427d7993509b918`→`7f8b33651ea21b67`；修订后 §4.2 脚本块已含 SHA3-512 纯哈希与 AES-256-GCM 计时代码）；②`外部素材融合与治理条款简报.otl.md` 已生成（-01 中为 pending，现 sha3_16 `d0bb047086fa509d`，42932 bytes）。票据内容随之变更，按 append-only 口径递增尾号重签 -02，**-01 保留不删**（2336 bytes，根 `bc59b12db2d37dac` 与其在册 4 叶子自洽，为该时点的诚实记录）。

**首发票：TICKET-20261008-MOON-01**（2026-10-08T19:36:00.4849976+08:00，`burn/claims/credential_ticket_20261008.json`，2336 bytes）

| 项 | 值 |
|---|---|
| merkle_root（前 16 位） | `bc59b12db2d37dac`（4 叶子；融合简报 pending 不入树） |
| 签名状态 | `OPL_TICKET_KEY` 未注入 → `sig: null` |

---

**署名**：Moon（pi-orchestrator@zcode · SHA3 root a69ccb57…）

## 修订记录

| 版本 | 日期 | 修订人 | 修订内容 |
|---|---|---|---|
| v1 | 2026-10-08 | Moon（pi-orchestrator@zcode） | 初版：桌面双 CSV stat 级核验入册；.env 16 键名清单；ALIYUN_AK_* 迁移议题提请裁定；后量子密钥响应口径照录；关联票据 TICKET-20261008-MOON-01 签发摘要 |
| v2 | 2026-10-08 | Moon（pi-orchestrator@zcode） | 响应独立复核 high 意见：①核对确认该意见指向 PQC OTL 文稿旧版（sha3_16 `9427d7993509b918`）之 §4.2/§10.2，非本票据/登记件缺陷——现行版（`7f8b33651ea21b67`）§4.2 脚本块 L207-247 已含 SHA3-512 纯哈希（L227-232）与 AES-256-GCM 加解密（L234-246）计时代码，M1/M2（现 L491-492）测法引用与之一致；②本席两文件三项自检通过（凭据明文扫描 CLEAN、sig=null 未伪造、merkle_root 与 artifacts 重算一致）；③检测到产件漂移（PQC OTL 修订 + 融合简报生成），票据重签为 TICKET-20261008-MOON-02（根 `44f3fcce839648f8`，5 叶子），-01 append-only 保留；④签发脚本增设防覆盖闸并实测生效；⑤桌面双 CSV 复查未动（各 85 bytes，mtime 未变），OPL_TICKET_KEY 复查仍未注入 |
| v3 | 2026-10-09 | Moon（pi-orchestrator@zcode · SHA3 root a69ccb57…） | 回应独立复核 low 意见（该批唯一未处置项）：修订记录原仅四列、缺「唯一标识符」列，与本批融合简报所立追责三件套五列体例不自洽。按 append-only 纪律**不改写 v1/v2 既有行**，改为追加下方《唯一标识符对照表》补齐该维度；并同步登记票据链已延至 TICKET-20261008-MOON-03（根 `546d43b398a20c27`，覆盖十件）、本登记件现行指纹 `1a388440c365b3c9` |

### 修订记录之唯一标识符对照表（v3 增补）

| 版本 | 日期 | 修订人（署名） | 唯一标识符 | 修订内容摘要 |
|---|---|---|---|---|
| v1 | 2026-10-08 | Moon（pi-orchestrator@zcode · SHA3 root a69ccb57…） | CRED-SOV-20261008-MOON-01 | 初版：双 CSV stat 级核验、.env 16 键名清单、ALIYUN_AK_* 议题提请裁定 |
| v2 | 2026-10-08 | Moon（pi-orchestrator@zcode · SHA3 root a69ccb57…） | CRED-SOV-20261008-MOON-01（v2） | 回应复核 high 意见之核对；票据重签 -02（根 `44f3fcce839648f8`） |
| v3 | 2026-10-09 | Moon（pi-orchestrator@zcode · SHA3 root a69ccb57…） | CRED-SOV-20261008-MOON-01（v3） | 补「唯一标识符」列（本表）+ 票据链延至 -03 之同步登记 |

> 唯一标识符口径（承主权人令）：不得仅以不可识别证伪、难以对抗性审查的「本席」自称；每处修改须带席位全称 + 可核验标识（`pi-orchestrator@zcode` 与 SHA3 root 指纹 `a69ccb57…`）+ 条目登记号。文末署名为「本席」之增补，主权人保留意见与所有权力。
