# OpenPlanLink（OPL）出档前密钥泄漏扫描报告

- **扫描日期**：2026-05-05（档期 20261005）
- **扫描席位**：出档前密钥泄漏扫描席
- **纪律依据**：「凭据零字面量」——产出文件、源码、文档、日志、提交信息、A2A 投递件中一律不得出现明文 API Key / AK / SK / 访问令牌 / ima 凭据 / Server酱 SendKey / COS 预签名密钥。真值只能从环境变量或 `.env` 读取，文档中只准写**键名**。
- **总判定**：**FAIL**

---

## 一、总判定

**FAIL**

在扫描范围 2 中发现 **5 处**明文凭据命中，全部集中于同一文件 `OpenPlanLink蓝图OTL主文档_党组学术视角.otl` 第 170–174 行，为腾讯云 COS 预签名 URL 内嵌凭据（`q-ak=` 访问密钥 ID + `q-signature=` 签名值）。

同时存在**未覆盖范围**（2 个 `.docx` 为 WPS 云端占位符，云文件提供程序未运行，无法读取），故本次结论为 **FAIL（兼 PARTIAL）**：已覆盖部分存在明确违规，未覆盖部分无法判定。

**门禁结论：不予出档。** 须先清除第 170–174 行的预签名 URL 并复扫。

---

## 二、扫描范围表

| # | 路径 | 文件数 | 是否覆盖 | 扫描方式 |
|---|---|---|---|---|
| 1 | `C:\Users\欧阳宏俊\.zcode\workspace\default\burn\otl\20261005\` | 3 | 是 | Grep 工具，7 条正则逐条（纯文本 .md/.otl） |
| 2 | `C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\Plan提示词工程\openplanlink-docx\` | 12（4 .otl + 1 .txt + 2 .docx + 5 .wpsonline） | 部分 | 文本文件（.otl/.txt）走 Grep 7 条正则；.docx 无法读取；.wpsonline 按指令跳过 | 
| 3 | `A:\OPL_A2A\selfevo-sdd\`（.specify/ 与 specs/） | 31 | 是 | Grep 工具，7 条正则逐条（含 .md/.json/.ps1/.yml） |
| 4 | `A:\OPL_A2A\MAPPING_MANIFEST.md` | 1 | 是 | Grep 工具，7 条正则逐条 |
| — | 合计 | 47 | 41 覆盖 / 6 未覆盖 | — |

### 范围 2 文件明细

| 文件 | 大小 | 覆盖状态 |
|---|---|---|
| `OpenPlanLink蓝图OTL主文档_党组学术视角.otl` | 41,301 B | 已覆盖 —— **命中** |
| `外部灵感融合简报_党组学术视角.otl` | 18,631 B | 已覆盖 —— 零命中 |
| `认证流程章节_MFA与GitHook与编码校验_党组学术视角.otl` | 27,985 B | 已覆盖 —— 零命中 |
| `跨生态A2A协作网络体系建设方案_党组学术视角.otl` | 26,749 B | 已覆盖 —— 零命中 |
| `_extract_tmp.txt` | 35,799 B | 已覆盖 —— 零命中 |
| `2026-9-25-OpenPlanLink 润色-1 (3).docx` | 2,604,232 B | **未覆盖** —— 云端占位符，`os error 362 云文件提供程序未运行` / `Permission denied` |
| `ima与A2A约束下开源协议补充论证.docx` | 37,280 B | **未覆盖** —— 同上（未单独读取验证，按同目录同机制推断） |
| 5 个 `.otl.wpsonline` | 各 536 B | 按指令跳过（云端存根，无正文） |

---

## 三、七条正则逐条命中结果

| # | 正则 | 范围1 | 范围2 | 范围3 | 范围4 | 合计 |
|---|---|---|---|---|---|---|
| 1 | `sk-[A-Za-z0-9]{16,}` | 0 | 0 | 0 | 0 | **0** |
| 2 | `AKID[A-Za-z0-9]{10,}` \| `AKIA[A-Za-z0-9]{10,}` | 0 | **5** | 0 | 0 | **5** |
| 3 | `(?i)(secret\|token\|apikey\|api_key\|sendkey\|password\|passwd)\s*[:=]\s*["']?[A-Za-z0-9_\-]{12,}` | 0 | 0 | 0 | 0 | **0** |
| 4 | `[A-Za-z0-9+/]{40,}={0,2}`（疑似 base64） | 10（误报） | 22（误报） | 0 | 0 | **0 真命中** |
| 5 | `q-signature=\|q-ak=\|X-Amz-Credential=` | 0 | **5** | 0 | 0 | **5** |
| 6 | `gh[pousr]_[A-Za-z0-9]{20,}` | 0 | 0 | 0 | 0 | **0** |
| 7 | `-----BEGIN [A-Z ]*PRIVATE KEY-----` | 0 | 0 | 0 | 0 | **0** |

### 正则 4 误报说明

范围 1 的 10 处命中经核验全部为 **git pack SHA1 哈希**（`a_drive_migration_scan.md:212–224`，如 `pack-f494a5ea696966dfc14147ea25b38b85bc45bac1.pack`）与 **URL 路径**（`self_evolution_research.md:10`）。范围 2 的 22 处命中为 CSDN / 博客园 / 微软 Learn / news.jschina 等公开引用 URL 及长 URL 编码串。**均非凭据**，判定为误报，不计入命中数。

注：正则 2 与正则 5 命中的是同一批 5 行（`q-ak=AKID...` 同时满足两条），故**去重后真实命中位置为 5 行**。

---

## 四、命中清单

**唯一命中文件**：
`C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\Plan提示词工程\openplanlink-docx\OpenPlanLink蓝图OTL主文档_党组学术视角.otl`

**密钥类型**：腾讯云 COS 预签名 URL 内嵌凭据（`q-ak` = COS 访问密钥 ID / SecretId；`q-signature` = 请求签名值）

| 行号 | 所在对象 | 密钥类型 | 掩码片段 |
|---|---|---|---|
| 170 | `claims-deep-audit.zip` 预签名 URL | COS AK（q-ak） | `AKID***` |
| 170 | 同上 | COS 签名（q-signature） | `ccae***` |
| 171 | `multi-dimensional-option-scoring.zip` 预签名 URL | COS AK（q-ak） | `AKID***` |
| 171 | 同上 | COS 签名（q-signature） | `ecdc***` |
| 172 | `diffusion-dynamics-extension.zip` 预签名 URL | COS AK（q-ak） | `AKID***` |
| 172 | 同上 | COS 签名（q-signature） | `c60e***` |
| 173 | `web-security-audit.zip` 预签名 URL | COS AK（q-ak） | `AKID***` |
| 173 | 同上 | COS 签名（q-signature） | `deae***` |
| 174 | `seo-copywriting-guide.zip` 预签名 URL | COS AK（q-ak） | `AKID***` |
| 174 | 同上 | COS 签名（q-signature） | `cadd***` |

**凭据去重后共 6 个唯一真值**：1 个 AK（5 行复用同一 AK）+ 5 个各不相同的 q-signature。

**风险评估**：
- 5 条 URL 共用同一 COS 桶 `workbuddy-bga-1258344699`、同一 region `ap-beijing`、同一对象前缀 `attachments/`。
- 签名时效 `q-key-time=1790383046;1798159046`，**当前时间戳已远超该窗口，签名应已失效**——但这不构成免罚理由：预签名 URL 一旦在有效期内被传播即可被任意下载，且 AK 本身为长期有效标识。
- 该 AK 与「凭据零字面量」纪律直接冲突：文档中只准写**键名**（如 `COS_SECRET_ID`），真值须从环境变量或 `.env` 读取。

**处置建议**：
1. 删除第 170–174 行整条预签名 URL，改为登记键名与对象路径的指针（例如 `COS 附件：claims-deep-audit.zip，桶 workbuddy-bga-1258344699，凭据取自 COS_SECRET_ID / COS_SECRET_KEY 环境变量`）。
2. 若这 5 个 zip 附件仍需分发，改用「桶 + 对象键」形式由接收方自行签名，或生成新签名并只在受控通道传递、文档中仅留占位符。
3. **评估该 AK 是否需轮换**：它已明文落盘于交付件，且同桶下可能存在其他预签名 URL 未被本轮正则覆盖。建议在腾讯云控制台轮换此密钥对。
4. 因该 AK 明文出现在文档中，**同批交付件（含由该文档派生的 docx / 导出件）应一并复扫**。

---

## 五、未覆盖范围说明

| 文件 | 原因 | 建议 |
|---|---|---|
| `2026-9-25-OpenPlanLink 润色-1 (3).docx`（2,604,232 B） | WPS 云端占位符。Grep 返回 `ripgrep exited with code 2 ... 云文件提供程序未运行 (os error 362)`；`head -c 16` 读取返回 `Permission denied`。**docx 本质为 ZIP 压缩二进制（OOXML），即便可读，纯文本正则扫描亦不适用**，必须解压后扫描 `word/document.xml` 等 part | 启动 WPS 云服务使文件本地化 → 解压 → 扫描 `word/document.xml`、`word/footnotes.xml`、`word/header*.xml` 及 `docProps/`；或**在 WPS 中人工核**第 5 节命中的同一批 COS 预签名 URL 是否也被复制进该文档 |
| `ima与A2A约束下开源协议补充论证.docx`（37,280 B） | 同目录同机制，推断同为云端占位符 | 同上 |
| 5 个 `.otl.wpsonline` | 按扫描指令明示跳过（536 B 云端存根，无正文） | 如后续云端存根落地为真实内容，须补扫 |

**覆盖统计**：47 个文件中 **41 个已覆盖（87%）**，**6 个未覆盖（13%）**。已覆盖部分零命中不能外推为全量零命中。

---

## 六、复扫建议

1. **修复后必复扫**。按第 4 节处置建议改写第 170–174 行后，重跑本报告正则 2 与正则 5（`AKID` / `q-signature=` / `q-ak=` / `X-Amz-Credential=`），确认归零。
2. **扩扫正则**。本轮 7 条正则未覆盖以下形态，建议追加：
   - `(?i)sendkey\s*[:=]`（Server酱 SendKey）
   - `(?i)ima[_-]?(apikey|api[_-]key|access[_-]?token)\s*[:=]`（ima 凭据）
   - `LTAI[0-9A-Za-z]{12,}`（ima/腾讯系长标识）
   - `(?i)authorization\s*:\s*(bearer|basic)\s+\S+`
   - `sk-ant-[A-Za-z0-9\-]{16,}`（Anthropic 系）
   - `xox[baprs]-[A-Za-z0-9-]{10,}`（Slack）
3. **docx 专项**。为范围 2 两个 .docx 建立解压扫描流程（解包 → 扫 `word/*.xml` + `docProps/*`），纳入常规出档门禁，不再以「压缩二进制不适用」豁免。
4. **同步扫描派生物**。`_extract_tmp.txt` 系 docx 抽取产物，本轮零命中，可作为 docx 正文的替代表征——但抽取可能不完整（图片内嵌文字、批注、修订痕迹会丢失），不能替代原文件核验。
5. **范围外提示**。扫描中顺带发现 `A:\OPL_A2A\desktop_20261005\` 下多个脚本含 `q-ak=` / `q-signature=` 字样（如 `opl_collab_modes.py:545`、`opl_pointer_send.py:159,168`），经核验均为**检测规则样例与正则字面量**（使用 `AKIA****`(AWS 官方公开示例值，已掩码)、`deadbeef` 等公开示例值），非真实凭据，**不计入本报告命中数**。该目录不在本轮扫描范围内，如后续纳入范围请注意区分「规则字面量」与「真实取值」两类命中，避免误报。
6. **归档与留痕**。本报告本身严格遵守纪律：仅记录**键名**与**掩码片段**（前 4 字符 + `***`），未抄录任何完整真值。

---

## 七、扫描方法与执行纪律合规声明

- 全部模式搜索经 **Grep 工具**执行（`output_mode: content`，带 `-n` 行号），未使用 Bash grep。
- 一次 Bash 调用只跑一条命令，未使用 `&&` / `;` 串联。
- 未执行任何临时 `.py` 脚本；计算需求以单条命令完成。
- 未使用 `os.unlink()` / `os.remove()` 删除任何文件——**本席位为纯扫描席，不修改被扫描文件**，修复动作交由产出席执行。
- 报告经 Write 工具落盘，并回读校验。

---

*报告结束。判定 **FAIL**，门禁不予放行。*
