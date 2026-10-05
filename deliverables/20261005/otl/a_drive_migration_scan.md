# A 盘迁移可行性扫描报告（A 盘迁移扫描席）

- 档号：SCAN-20261005-ADISK-01
- 编制席：A 盘迁移可行性扫描席（本席）
- 编制时刻：2026-10-05（北京时间，现场实测）
- 授权依据：机主令「通知各方探讨任何可以正常调用的映射迁移到A盘，协同A2A整理桌面，非必要文件一律上传各总线及云端」
- **执行纪律：全程只读**。本席未执行任何 cp / mv / rm / mkdir 写操作，唯一写入为本报告文件。
- **凭据纪律：零字面量**。a2a-bridge/.env 仅登记键名与端点 URL，真值未抄录、未外传。

---

## 〇、实测基线（与既有记载有出入，先纠偏）

| 项 | MANIFEST 记载 | 本席实测 | 判定 |
|---|---|---|---|
| A 盘卷标 | 新青年的时代，NTFS | A: 可用 944G，已用 920G，50% | 记载略旧，实测仍充裕 |
| C 盘余量 | 未记 | **C: 454G 总量，已用 424G，仅余 30G（94%）** | **C 盘已近爆满，是本次迁移的真实压力源** |
| A:\A2A_Mappings 三子目录 | 「目前基本为空」 | 已发生剧变：api_configs 有 2 份端点登记表；**另新增 9 个 opensrc 实体副本目录** | 记载过期，须更新 |
| A:\OPL_A2A | 4 个 junction | 4 个 junction 仍在，另新增 desktop_20261005 / opensource_mirror / repos_20261005 / selfevo-sdd 四个原生目录 | 已扩容 |

**核心发现（先给结论）**：A 盘上现有的开源库副本存在 **三份重复**（`A:\A2A_Mappings\*__*`、`A:\OPL_A2A\opensource_mirror`、`A:\OPL_A2A\repos_20261005`），同一批仓库被各拷了三遍，其中 cann-recipes-infer 一库就重复占用 303M×3 ≈ 909M。而 C 盘真身 `opensrc` 仍完整保留 720M。**在真身未剥离前，这三份拷贝不是迁移，是复制性冗余。**

---

## 一、映射候选清单（逐源判定）

### 1.1 A2A 桥接层

| 项 | 内容 |
|---|---|
| 名称 | A2A 桥接层（a2a-bridge） |
| 绝对路径 | `C:\Users\欧阳宏俊\.zcode\workspace\default\a2a-bridge` |
| 实际占用 | **14M / 121 文件**（子目录：scripts 31、.git 26、logs 18、.mimosa 10、receipts 5、agents 3、gov-design 3、sessions 3、__pycache__ 2、outbox 2、audit 1、kirchhoff_inbox 1） |
| 内容说明 | A2A 总线客户端与凭据仓：JSON-RPC 2.0 信封构造器、心跳调度（heartbeat.py / run_heartbeat.cmd / launch_agent.ps1）、身份哈希（identity_sha3.py）、溯源台账（provenance_ledger.json）、黑板与探测银行 |
| A 盘对应物 | **间接已有**——`A:\OPL_A2A\工作区` junction 已覆盖该路径（写入 A 盘地址即写入 C 盘真身） |
| 迁移判定 | **直接 junction（已建成，无需动作）**。但对 `.env` 单文件另有处置见 §1.1.1 |
| 风险提示 | ① junction 是**地址别名不是拷贝**，跨机不可移植，A 盘整盘拔走或换机后全部失效；② `.env` 内 14 个凭据键名一旦进入 A 盘，等于凭据扩散到第二个卷，需确认 A 盘是否受 BitLocker 保护——**本席未能实测加密状态（沙箱禁止调 reg.exe / manage-bde）**；③ `logs/cross_mode_channel.db` 为 12.7M 活跃 SQLite，junction 迁移瞬间若会话持有句柄会出现文件锁 |

#### 1.1.1 `.env` 专项（凭据零字面量登记）

绝对路径：`C:\Users\欧阳宏俊\.zcode\workspace\default\a2a-bridge\.env`（1,224 字节，2026-10-04 14:11 更新）
本席仅读取等号左侧键名，**未读取、未记录、未抄写任何等号右侧真值**。

**判定：此文件「不宜迁移，且当前不宜复制到 A 盘」。** 理由：这是全机唯一的凭据真值源，一旦 junction 到 A 盘，A 盘就成为凭据副本所在，A 盘的备份/同步/云上传链路都会连带把凭据带走。正确做法是**反过来的**：让 A 盘侧的调用方通过 `A:\OPL_A2A\工作区\a2a-bridge\.env` 这一**路径**读取，而非把 `.env` **内容**复制过去。当前 junction 方案恰好满足此要求，无需变更——但需在纪律中写死「凭据真值不入 A 盘目录树」。

### 1.2 burn 席产出物

| 项 | 内容 |
|---|---|
| 名称 | burn 席产出物总目��� |
| 绝对路径 | `C:\Users\欧阳宏俊\.zcode\workspace\default\burn` |
| 实际占用 | **130M / 3,507 文件**（31 个子目录 + 约 25 个散落根文件） |
| 内容说明 | 跨席作战产物库：a2a/（议会会话记录）、a2a-plan-50k/（5 万字规划）、otl/（按日档期 20261003/04/05）、deliverables/（各席交付）、governance/（治理条例 v2 提案等）、claims/、corpus/、rag-graphrag/、handshake/、scripts/、zcode-p1/（301 文件）、backup/（2,597 文件 skills 快照） |
| A 盘对应物 | **间接已有**——`A:\OPL_A2A\工作区\burn` 可达；另有 `A:\OPL_A2A\桌面\...` 系列 junction 指向桌面交付物 |
| 迁移判定 | **直接 junction（已建成）**；但内部三个子项建议单独处置，见下表 |
| 风险提示 | burn 根目录有 12 个 `tmp_*` 文件 + 2 个 `portal_*_orig.html` + `portal_a2a-architecture_day.html` 属临时/中间产物，**非必要文件应上传总线或云端后清理**，本席只统计不删 |

burn 内部子项迁移可行性：

| 子目录 | 占用 | 文件数 | 说明 | 判定 |
|---|---|---|---|---|
| `backup/` | 62M | 2,597 | skills_20260930 全量技能快照 | **不宜迁移**——与 `C:\Users\欧阳宏俊\.workbuddy\skills` 高度重叠（同一份 9.6M PDF 两处皆见），属历史备份，宜上传云端归档 |
| `out/` | 19M | 7 | A2A 扩展作战包 zip ×3（各 5.3M） | **需拷贝**——纯交付物 zip，无路径依赖，可直接上传总线/云端 |
| `rag-graphrag/` | 14M | 45 | graph.db（10.5M）+ 文档 | **需拷贝**——`.db` 为 SQLite，图谱数据整体搬迁优于 junction |
| `deliverables/` | 5.7M | 55 | 各席交付物 | **直接 junction** |
| `governance/` | 168K | 12 | 治理条例与全局声明 | **直接 junction**（治理文本须 append-only，保留真身单点） |
| `a2a/` | 320K | 4 | 董事会/议会会话记录 | **直接 junction** |
| `a2a-plan-50k/` | 924K | 49 | 5 万字规划 | **直接 junction** |
| `opensrc/` | 76K | 2 | 仅 2 份 DISTILL 笔记（非仓库本体） | **直接 junction** |
| `deploy_day.zip` | 5.3M | 1 | 部署包 | **需拷贝**→ 云端 |

### 1.3 opensrc 开源库克隆群

| 项 | 内容 |
|---|---|
| 名称 | opensrc 开源库克隆群（13 个真实仓库） |
| 绝对路径 | `C:\Users\欧阳宏俊\.zcode\workspace\default\opensrc` |
| 实际占用 | **720M / 9,186 文件** |
| 内容说明 | 13 个第三方开源库 git clone，`.git/objects/pack` 占绝大部分体积 |
| A 盘对应物 | **已有三份重复实体拷贝**（详见 §三）——`A:\A2A_Mappings` 9 个 `xx__` 前缀目录、`A:\OPL_A2A\opensource_mirror` 7 个、`A:\OPL_A2A\repos_20261005` 8 个；另 `openplanlink-mirror` 已由 `A:\OPL_A2A\镜像仓` junction 覆盖 |
| 迁移判定 | **不逐个建 junction；建议「真身迁 A 盘 + C 盘留 junction」**（详见 §四方案） |
| 风险提示 | ① 仓库路径被大量文档按 `.git` 相对路径引用（实测 8 个文件硬编码 `.zcode\workspace\default`，共 33 处，含 `burn/tmp_scan_sections.py`、`burn/frontier/sha3_pqc/SELFTEST_LOG.md` 等 12 处集中点），真身一旦换位，这些引用需同步改；② `.git` pack 不可跨机裸拷，必须 `git clone` 重来或整目录 junction；③ 三个副本间存在 pack 哈希一致的重复（如 Star-Office-UI `pack-3d619d02...`、huashu-design `pack-44067acd...`），说明是同源克隆 |

逐库明细：

| 库名 | 占用 | 文件数 | A 盘已有副本 | 迁移判定 |
|---|---|---|---|---|
| cann-recipes-infer | 304M | 2,012 | 3 份 | 真身迁 A，C 留 junction；优先处理（重复 909M） |
| qoder-skills-hub | 95M | 3,021 | 0 份 | 真身迁 A，C 留 junction |
| arwes | 74M | 784 | 3 份 | 同上 |
| Star-Office-UI | 65M | 163 | 3 份 | 同上 |
| huashu-design | 63M | 218 | 3 份 | 同上 |
| penecho | 41M | 825 | 3 份 | 同上 |
| canvas-ui | 35M | 590 | 2 份 | 同上 |
| mirofish-gitcode | 16M | 144 | 0 份 | 同上 |
| openplanlink-mirror | 14M | 966 | junction 已建成 | **维持现状**，勿动 |
| MiroFish | 8.8M | 117 | 3 份 | 同上 |
| Cairn | 6.1M | 101 | 0 份 | 同上 |
| tgrep | 3.3M | 140 | 3 份 | 同上 |
| digital-oracle | 859K | 105 | 0 份 | 同上 |
| `_inventory_tmp/` | 0 | 0 | — | 空目录，可忽略 |

### 1.4 桌面（真身实测判定）

**本席实测结论：真身是 `C:\Users\欧阳宏俊\OneDrive\桌面`，`C:\Users\欧阳宏俊\Desktop` 是残留孤儿目录。**

| 项 | Desktop（疑似） | OneDrive\桌面（真身） |
|---|---|---|
| 文件数 | **1** | **5,899** |
| 占用 | 152 字节 | **604M** |
| 内容 | 仅 `DeepSeek Harness.url` | 12 个应用快捷方式（Cursor/Kimi/VSCode/微信/词典等）+ 8 个指向 A 盘的 junction + `gitclone_20261005/` + `_归档_桌面整理_20261005/` + `报告_输出/` + 8 份同步覆盖矩阵 |
| desktop.ini | 无 | **有**（444 字节） |

**判定依据**：`OneDrive\桌面` 内含 `desktop.ini`（Windows 已知文件夹标志）且已有 8 个本席此前建立的 junction 指向 `A:\OPL_A2A\desktop_20261005\*`；而 `Desktop` 目录内除一个 `.url` 外空无一物，`Desktop.lnk`-类痕迹不存在。MANIFEST 记载正确，`Desktop` 仅是历史遗留空壳。

**未能完成的验证**：注册表 `HKCU\...\User Shell Folders\Desktop` 指向为权威判据，但本席沙箱将 `reg.exe` 列入程序黑名单，查询被拦截。**建议主权人自行执行 `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v Desktop` 复核**（若返回 `C:\Users\欧阳宏俊\OneDrive\桌面` 即 100% 坐实）。

| 项 | 内容 |
|---|---|
| A 盘对应物 | `A:\OPL_A2A\桌面` junction 已建成；另有 `A:\OPL_A2A\desktop_20261005`（15 个原生目录）与 `selfevo-sdd` |
| 迁移判定 | **桌面真身不宜整体迁移**。理由：真身在 OneDrive 内（云同步客户端接管），junction 到 A 盘会造成 OneDrive 与 A 盘双写冲突，且快捷方式 `.lnk` 内含指向 C 盘应用路径的绝对引用，换机/换盘即失效 |
| 建议动作 | 桌面上的**非必要文件**按机主令上传总线/云端：`gitclone_20261005/`（597M，与 opensrc 三份副本重复度极高）、`_归档_压缩包`、`报告_输出/`（5.3M）；桌面本体保持 OneDrive 原位，A 盘侧走 `A:\OPL_A2A\桌面` 别名 |
| 风险提示 | 8 个 junction 均为 C→A 单向，若 A 盘未挂载，这 8 个入口变死链，桌面整理脚本会中断 |

### 1.5 WorkBuddy 用户级技能库

| 项 | 内容 |
|---|---|
| 名称 | WorkBuddy 用户级技能库 |
| 绝对路径 | `C:\Users\欧阳宏俊\.workbuddy\skills` |
| 实际占用 | **99M / 3,573 文件 / 顶层 139 条目（135 个目录）** |
| 内容说明 | 用户级技能全集，含 SKILL.md 338 份，覆盖 A2A、研究、量化、运维、文档等各类技能 |
| A 盘对应物 | **无对应物**。`A:\A2A_Mappings\skill_mirror` 为空（0 文件） |
| 迁移判定 | **需拷贝，不宜 junction** |
| 理由 | 技能加载器按固定路径 `~/.workbuddy/skills` 解析，junction 可行但会与 WorkBuddy 自身的安装/更新/自检逻辑打架（插件缓存路径 `C:\Users\欧阳宏俊\.workbuddy\plugins\cache\...` 与技能路径耦合）；且 `k3-everything-archive` 本身即为归档型数据，适合**冷拷贝上 A 盘**，不适合成为运行时真身 |
| 建议动作 | 分两层：**热层**（195 个唯一技能的 `SKILL.md` + 脚本）留 C 盘原位保证加载；**冷层**（`k3-everything-archive` 61M/2,452 文件，其中 output 995、skills 584）整目录拷贝至 `A:\A2A_Mappings\skill_mirror`，C 盘侧留 junction 兜底 |
| 风险提示 | **重复副本实测：338 份 SKILL.md 对应 195 个唯一技能名，其中 112 个技能名有多份副本**。最多者 `omni-exhaust-research-ops` 5 份；`zijue-self-determination` / `pangu-enforcement-bureau` / `hifi-integration-umbrella` / `autonomous-advance-ops` 各 4 份。副本主要聚在 `k3-everything-archive/{skills,output,upload}` 三处。**本席只统计不删除**，去重须由主权人裁决（按 mtime 取最新一份即可，收益约 20-30M） |

---

## 二、A2A 通道现状表

**凭据栏一律为键名，真值零字面量。** 真值唯一存放处：`C:\Users\欧阳宏俊\.zcode\workspace\default\a2a-bridge\.env`（1,224 B，2026-10-04 14:11）

| # | 通道名 | 凭据键名（不写真值） | 端点 URL / 标识 | 在册状态 |
|---|---|---|---|---|
| 1 | 阿里百炼 DashScope（标准） | `DASHSCOPE_API_KEY` | `https://dashscope.aliyuncs.com`（据 MANIFEST） | 已绑定 |
| 2 | 阿里百炼 DashScope（WS 兼容） | `DASHSCOPE_WS_KEY` | `https://ws-ay6o8osb22o9dc3t.cn-beijing.maas.aliyuncs.com/compatible-mode/v1` | 已绑定，**端点为部署级专属子域，不可迁移到别的账号/region** |
| 3 | 华为 MaaS | `HUAWEI_MAAS_KEY` | `https://api.modelarts-maas.com/v1` | 已绑定 |
| 4 | Tushare | `TUSHARE_TOKEN` | `https://api.tushare.pro` | 已绑定 |
| 5 | 火山方舟（AK/SK 换令牌） | `ARK_ACCESS_KEY` + `ARK_SECRET_KEY` | 登录 `https://console.volcengine.com/auth/login/user/2131357930`；账号 `ARK_ACCOUNT_ID=2131357930` | 已绑定 |
| 6 | 火山方舟（推理端点） | 同上（令牌换取） | 端点 `ep-20260930174211-62v5d`；模型 `ARK_MODEL=doubao-seed-evolving` | 已绑定 |
| 7 | 硅基流动 | `SILICONFLOW_API_KEY` | 未在 .env 登记 BASE 项 | 键在册，**端点待补登记** |
| 8 | 302.AI | `AI302_API_KEY` | 未在 .env 登记 BASE 项 | 键在册，**端点待补登记** |
| 9 | 国家超算互联网 | `SCNET_API_KEY` | 无 | 键在册，**接口未探测，通道不可调用** |
| 10 | A2A 总线 | 无凭据（fp 指纹 + 401 待机主终审身份层） | `http://120.46.86.165/functions/v1/app` | **半通**：读权限 401 |
| 11 | Server 酱告警 | `SERVERCHAN_SENDKEY` | 授权域 `sc3.ft07.com` | 授权域已定（据 MANIFEST） |
| 12 | ima 通道 | 标签映射 32 位 hex / apikey base64（**注：标签与机主标注相反，见 esc#39**） | 未在 .env 登记 BASE 项 | 已绑定，口径待纠偏 |

**通道层迁移判定**：`a2a-bridge/.env` 与 `A:\A2A_Mappings\api_configs\endpoint_registry*.md` 已有对应登记（2 份文件，20K）。`service_endpoints/` 为空（0 文件），**建议主权人考虑将本表 §二 落一份仅含键名与端点的登记表到 `A:\A2A_Mappings\service_endpoints\`，作为跨机可读的通道目录**——注意该文件**不得含真值**，且 junction 不可移植，故必须落成实体文件而非链接。

---

## 三、A 盘冗余现状（本次扫描附带发现）

同一批开源库在 A 盘存在**三份实体副本**，全部与 C 盘真身并存：

| 副本位置 | 文件数 | 占用 | 覆盖库数 |
|---|---|---|---|
| `A:\A2A_Mappings\{ar__,cann__,canv__,hu__,mi__,pe__,st__,tg__}` | 4,892 | **约 600M** | 8 |
| `A:\OPL_A2A\opensource_mirror\{7 库}` | 4,299 | **约 560M** | 7 |
| `A:\OPL_A2A\repos_20261005\{8 库 + _clone_report.json}` | 4,890 | **约 600M** | 8 |
| 合计冗余 | — | **约 1.7G** | 同源重复 |

叠加 C 盘 `opensrc` 真身 720M，同一批代码现占 **2.4G+**。

**本席判定**：在 C 盘真身尚未剥离前，这 1.7G 拷贝属于「迁移中途态」，不建议再叠加第四份。正确收敛路径见 §四方案 B。三份副本中 `repos_20261005/` 带 `_clone_report.json`（730 B，克隆台账），信息最全，宜作为留存基准，另两份为可收敛对象。

`A:\A2A_Mappings\api_configs\` 现有 2 份端点登记表（2,036 B + 14,734 B），**非空**，MANIFEST「基本为空」的记载已过期。

---

## 四、迁移方案建议（按风险从低到高，仅供主权人裁决）

### 方案 A：零风险项（可即刻执行，无需搬动真身）

1. 桌面非必要文件上传总线/云端后清理：`gitclone_20261005/`（597M）、`_归档_压缩包`、`报告_输出/`（5.3M）、`burn/tmp_*` 12 个临时文件、`burn/out/` 3 个作战包 zip（19M）—— 合计可释放约 **640M C 盘**，直接缓解 C 盘 94% 占用。
2. 落一份**仅含键名与端点**的通道目录实体文件到 `A:\A2A_Mappings\service_endpoints\`（真值零字面量）。
3. `A:\A2A_Mappings\skill_mirror\` 填入 `k3-everything-archive` 冷拷贝（61M）。

### 方案 B：opensrc 真身迁 A 盘（需主权人授权，本席未执行）

路径：`C:\...\default\opensrc` → `A:\OPL_A2A\src\opensrc`，C 盘原位留 junction。
收益：C 盘释放 720M；A 盘侧成为唯一真身，三份拷贝可收敛为一份，净再释放约 1.1G A 盘。
前置条件（缺一不可）：
- 先改 8 个文件中的 33 处硬编码路径（尤其 `burn/frontier/sha3_pqc/SELFTEST_LOG.md` 12 处、`burn/tmp_scan_sections.py`）；
- `openplanlink-mirror` 已在 `A:\OPL_A2A\镜像仓` 建 junction，须排除在迁移范围外避免嵌套；
- 迁移窗口内不得有 git 操作在途。

### 方案 C：暂不建议

- `.env` 迁 A 盘 —— 凭据副本扩散，违反零字面量纪律；
- 桌面真身迁出 OneDrive —— 云同步与 A 盘双写冲突；
- `.workbuddy\skills` 整体 junction 化 —— 与 WorkBuddy 插件加载/更新机制耦合。

---

## 五、大文件 TOP20（跨 a2a-bridge / burn / opensrc 三源实测）

| # | 大小 | 绝对路径 | 备注 |
|---|---|---|---|
| 1 | 120.3M | `...\opensrc\cann-recipes-infer\.git\objects\pack\pack-f494a5ea696966dfc14147ea25b38b85bc45bac1.pack` | git pack，A 盘已重复 3 份 |
| 2 | 35.0M | `...\opensrc\arwes\.git\objects\pack\pack-2543e7953d5a89c5cdc0a1b978880cf9cc6a1c03.pack` | git pack |
| 3 | 30.2M | `...\opensrc\huashu-design\.git\objects\pack\pack-44067acd07775799a3d1f89be289c895071e50fd.pack` | git pack |
| 4 | 29.7M | `...\opensrc\Star-Office-UI\.git\objects\pack\pack-3d619d0217ef72638da682587b67955f0bd849b7.pack` | git pack |
| 5 | 28.4M | `...\opensrc\qoder-skills-hub\.git\objects\pack\pack-10ad7894ace6b351fc8c3795eb290531322850f5.pack` | git pack |
| 6 | 14.7M | `...\opensrc\canvas-ui\.git\objects\pack\pack-eaeac01ec241d96dd9f06ae760852d7c48ce472b.pack` | git pack |
| 7 | 12.7M | `...\a2a-bridge\logs\cross_mode_channel.db` | 活跃 SQLite，junction 迁移需避开口柄占用 |
| 8 | 10.6M | `...\opensrc\penecho\.git\objects\pack\pack-18c455058b16a18cffca60e0c6a2a09b1bbacda4.pack` | git pack |
| 9 | 10.5M | `...\burn\rag-graphrag\graph\graph.db` | SQLite 图谱 |
| 10 | 9.6M | `...\opensrc\qoder-skills-hub\k3-everything-archive\output\宇树科技×金发科技（600143）走势洞察报告.pdf` | 与 skills 库/backup 三处同源重复 |
| 11 | 9.6M | `...\burn\backup\skills_20260930\skills\k3-everything-archive\output\宇树科技×金发科技（600143）走势洞察报告.pdf` | 同一份 PDF 的备份副本 |
| 12 | 6.7M | `...\opensrc\arwes\static\assets\community\apps\media\beko-primary-buffer-panel.webm` | 演示视频 |
| 13 | 6.7M | `...\opensrc\mirofish-gitcode\.git\objects\pack\pack-5f3d5e192c5facea547cca9b7ce05fcd228b566c.pack` | git pack |
| 14 | 6.1M | `...\opensrc\arwes\static\assets\community\apps\media\archiverpg.com.webm` | 演示视频 |
| 15 | 5.8M | `...\opensrc\canvas-ui\public\assets\fallback-hero.mp4` | 演示视频 |
| 16 | 5.3M | `...\burn\out\A2A扩展作战包_20260928_v3.zip` | 交付包 |
| 17 | 5.3M | `...\burn\out\A2A扩展作战包_20260928_v4.zip` | 交付包 |
| 18 | 5.3M | `...\burn\deploy_day.zip` | 部署包 |
| 19 | 5.3M | `...\opensrc\huashu-design\assets\bgm-tutorial.mp3` | 音频素材 |
| 20 | 5.3M | `...\burn\out\A2A扩展作战包_20260927_v2.zip` | 交付包 |

TOP20 中 **git pack 占 9 项（合计约 268M）**，全部可由 `git clone --mirror` 重建或整体 junction 规避，不适合裸拷贝。桌面侧另有更大单文件：`OneDrive\桌面\_整理_各席交付\守藏席_任务书\3DGS完全教程_守藏重构_20260928\brush\brush-v0.3.0-windows.zip` **151.4M**（未列入上表，因其位于 OneDrive 桌面而非三源；该目录由 `A:\OPL_A2A\桌面\_整理_各席交付` junction 可达）。

**A 盘容量压力结论**：A 盘余 944G，距满仓极远，本轮任何候选源迁入均无容量风险；真正的压力在 **C 盘（仅余 30G）**。因此本轮迁移的收益应按「释放 C 盘」而非「占用 A 盘」衡量。

---

## 六、风险提示汇总

| # | 风险 | 等级 | 说明 |
|---|---|---|---|
| 1 | junction 只是地址别名 | 高 | 跨机不可移植。A 盘若为移动盘或换机，全部 junction 失效且无告警。所有「已建成」项的安全性等于 A 盘在线率 |
| 2 | 硬编码路径导致 junction 失效 | 中 | 实测 8 文件 33 处写死 `.zcode\workspace\default`，含 `.py` 执行脚本（`tmp_scan_sections.py`）——这类是真依赖，不是文档提及 |
| 3 | 凭据扩散 | 高 | `.env` 一旦纳入 A 盘目录树，A 盘备份/同步/上传链路会连带带走凭据。**A 盘加密状态本席未能实测**（沙箱禁 reg.exe） |
| 4 | OneDrive 双写冲突 | 高 | 桌面真身在 OneDrive 内，junction 到 A 盘会造成双源写入与同步循环 |
| 5 | SQLite 句柄占用 | 中 | `cross_mode_channel.db`（12.7M）、`graph.db`（10.5M）在迁移/junction 切换瞬间可能被锁 |
| 6 | git pack 裸拷不可用 | 中 | pack 为二进制对象库，跨机拷贝易损；须整目录 junction 或重新 clone |
| 7 | A 盘冗余膨胀 | 中 | 同批开源库在 A 盘已三份（1.7G），继续叠加会与收敛目标反向 |
| 8 | 技能库重复副本 | 低 | 338 份 SKILL.md 对应 195 个唯一名，112 个技能名有多份，最高达 5 份。本席只统计不删 |
| 9 | 桌面真身未经注册表坐实 | 低 | 本席以 `desktop.ini` + junction 分布 + 文件数（5899 vs 1）三重旁证判定 OneDrive\桌面为真身；`reg query` 被沙箱拦截，建议主权人复核 |

---

## 七、只读声明

本席全程仅执行读取与统计操作（`ls` / `du` / `df` / `python -c` 内联只读扫描 / `cut` `grep` 键名提取）。**未执行任何 cp / mv / rm / mkdir / 写文件操作**，唯一落盘为本报告。所有 junction 均为本席进场前既有，本席未新建、未修改、未删除任何链接。凭据真值全程未离开 `a2a-bridge/.env`，报告内零字面量。

- 扫描源数：**5 类 / 13 个仓库 / 139 个技能条目 / 桌面 5,899 文件**
- 实地读取总量：a2a-bridge 14M·121 文件、burn 130M·3,507 文件、opensrc 720M·9,186 文件、OneDrive 桌面 604M·5,899 文件、.workbuddy/skills 99M·3,573 文件；另实测 A 盘 3 处镜像副本 1.7G

—— A 盘迁移可行性扫描席（本席）· 筹备组 · 呈主权人