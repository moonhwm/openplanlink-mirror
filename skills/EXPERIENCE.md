# skills/EXPERIENCE.md — 技能实战使用经验（A2A 网络共享层）

> 本文以政府职能部门党组学术技术成员视角作规范化表述，仅登记可复核的实操经验与教训，不含凭据、不含端点真值。
> 经验来源：幻16Kimi席（huan16-kimi-seat）2026-10-05 至 10-06 在 OpenPlanLink A2A 主线上的连续实战（对应 HANDSHAKE_LOG 批次八至十五）。
> 更新纪律：每条经验注明技能/工具、场景、教训、置信度；新经验追加于文末，已证伪条目不删除、标注勘误。

## E-01 loop-dual-pillar-ops：路由闸的实战判定（conf=high）

- 场景：goal 长轮次中机主插单修正优先级（"强制 GitHub 先行，此后再进行相关计划"）。
- 教训：①路由自报压缩为一句话（"推进域/审议域/混合域＋本轮切片名"）可显著降低多轮上下文认知负荷；②机主插单＝外部变局，应先响应立法者最新指令重排切片，而非继续原切片；③混合域「审议前置、推进随行」适用于「人设初始化＋管线推进」并发场景，但纯执行插单时直接走推进域，不强行套三镜。
- 复用条件：凡触发词命中且一轮内存在多事项并发时启用。

## E-02 kdocs-cli（v2.6.13）管道实战六条（conf=high，全部经当轮实测）

1. **输出解析须容错**：CLI 在 JSON 后追加升级警告文本行，python `json.JSONDecoder().raw_decode()` 而非 `json.load()`。
2. **路径展开**：Git Bash 中 `%USERPROFILE%` 不展开，用 `$USERPROFILE`；中文路径禁直塞命令行，先 `cd`。
3. **轻量漂移监测通道**：`drive get-file-info` 返回 version/size/mtime/sha1 四读数，单次调用即可判定文档是否仍在编辑——比重拉全文省一个数量级 token，已立为每轮刷新义务的默认动作。
4. **停编判定标准**：version＋size＋mtime 三读数连续两轮逐字一致＝判定停编（10-06 #1 活文档 v301 实证）。
5. **云侧故障定位法**：read_file 400100／block-query 500000 失败时，用同期健康文档作对照组秒回——可区分「全局故障」与「文档实例级故障」（#7/#9/#10 实证为后者）。
6. **.otl 通道限制**：download-file 对 .otl 类型级拒绝，read_file 为唯一正文通道；docx 与 otl 的字符数口径不可混用。

## E-03 GitHub MCP 批次推送工作流（conf=high）

- push 前必以 `get_file_contents` 复核目标 blob sha，防他席并发推送覆盖；sha 已变则以新正文为基追加。
- 长日志（HANDSHAKE_LOG，44KB 级）整文重写推送可行，单文件单 commit；批次内所有数值基线必须当轮复核后再写入，禁止沿用前批次数值。
- 提交信息格式统一：`HANDSHAKE 批次N：<主题>`，便于席位间检索。

## E-04 PowerShell 经 Git Bash 调用的两个陷阱（conf=high）

1. 内联 `-Command` 中 `$` 变量被 bash 吞掉 → 写 `.ps1` 脚本文件再 `powershell -NoProfile -ExecutionPolicy Bypass -File` 执行。
2. 输出为 GBK 时的中文列名乱码不影响 ASCII 进程名列的判读；如需中文列，先 `chcp 65001` 或脚本内重定向 UTF-8。

## E-05 基线漂移监测方法论（SDD 管线沉淀，conf=high）

- **双通道物理同一性核验**：凡经分享链接/token 落地的测量通道，先以 get-file-info 核对 file_id/drive_id/sha1 与文件夹实体通道是否同一物理文件，方可作基线锚（10-06 #1 冻结副本 vs 活文档 17,180 字异读查因实证）。
- **活文档权威原则**：基线锚定活文档；冻结副本读数降格备查；停编后重立基线＋段落级 diff 复核定稿。
- **漂移形态判别**：段落级 diff 中机械性批量改写（图片预签名轮换、全局改名、空白清理）与论断性删改须分离统计——前者不触发实质复审，后者触发（PARADIFF-KIMI-2026-1006-01 实证：净增 +18,448 中约八成为机械性改写，论断性删改零发现）。
- **敏感面随 diff 扩张监测**：diff 过程本身是敏感串发现通道（本轮实证 sk- 密钥 3→6 处），diff 报告只写计数不写值。

## E-06 进程舰队快照法（conf=med，单点快照局限已注明）

- `Get-Process | Where ProcessName -match <舰队正则>` 按 WorkingSet64 聚合，可把「进程舰队三档归类」中 conf=assumed 条目升级为 measured（10-06 实测：在场 7 系 ≈4.4GB/≈60 进程，8 项未在场）。
- 局限：单点快照非时段序列；未在场≠永不运行（按需档特性），结论须注明采时。

## E-07 待办（下一轮及以后）

- [ ] 技能库全量 delta 同步（本地 vs 仓库 117 件镜像比对，识别 09-30 后新增/变更件）——本轮先补经验层。
- [ ] EXPERIENCE 条目经 Codex 席（GPT-6.1 Sol Max）互验后升 conf。

---
登记：huan16-kimi-seat · 2026-10-06
敏感面自检：本件不含 sk- 密钥串、MAC 地址、预签名 URL（网卡标识一律「已登记」）；全部经验指回 HANDSHAKE 批次号，可复核。

## E-08 GitHub 上传阻断的真实判据：git 与 gh 是两条独立凭据链（conf=high）

- 场景：DF-TOOL-2026-1005-01 曾据「gh 未装／身份缺失／凭据缺失」判上传阻断，推论为不可推送。
- 实测：`gh auth status` 报 not logged into any GitHub hosts、`GH_TOKEN`／`GITHUB_TOKEN` 均未设，但 `GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never git push --dry-run origin main` 仍取到远端 ref 广告并回 `! [rejected] main -> main (fetch first)`。
- 教训：非快进拒绝本身即证明**认证已通过**（GitHub 的 receive-pack 广告要求认证）；git 侧凭据由 `credential.helper=manager`（GCM／Windows 凭据管理器）承载，与 gh 的 OAuth 令牌互不依赖。故「gh 未登录」不能作为「不能推送」的判据。正确探针是关掉交互提示的 `--dry-run` 推送——不关提示会弹 GUI 阻塞自动化流程。
- 复用条件：凡诊断上传阻断，先跑该 dry-run 探针，再看 gh 状态。

## E-09 MSYS2 参数路径转换把 rev:path 变成假阴性（conf=high）

- `git show origin/main:.gitignore` 在 Git Bash 下被改写为 `origin\main;.gitignore`，报 `fatal: Not a valid object name`，极易被读成「上游没有这个文件」。
- 修法：`export MSYS_NO_PATHCONV=1`（或 `MSYS2_ARG_CONV_EXCL='*'`）后同一命令 rc=0 且正常输出内容。
- 教训：凡参数含 `:` 且形如 `rev:path` 的 git 命令，在 Git Bash 下必须关闭路径转换。此类失败产出的是**假阴性结论**而非显式报错，属最危险的一类工具缺陷；本轮已致一次错误结论（误判上游无 .gitignore）并当场自纠。

## E-10 上传门禁脚本的双副本分裂与红线冲突（conf=high）

- `tools/push_gate.py` 硬编码 REPO 常量为用户主目录下的 openplanlink-mirror，而 Qoder 工作区副本位于 `Documents/Qoder/<日期>/<会话>/openplanlink-mirror`；二者是**各自独立的工作副本**，本轮实测 HEAD 分别为 a8b8d67 与 4155f97，各自落后上游。
- 后果：工作区副本里的改动不会被 push_gate 带走；反之 `~/.push_gate.jsonl` 的成功记录（本轮见 5 条 origin push OK）也**不能**证明工作区副本已同步。两处都必须单独核验。
- 红线冲突：该脚本含 `git push gitcode main --force` 与「工作区脏则 `git stash push -u`」两步，分别触「禁 force push」与「共享环境禁裸 stash」。本席不执行该脚本，改为手工等价的 fetch → `merge --ff-only` → 暂存 → 重签 → verify → push（全程无 force）。
- 复用条件：任何自动化推送脚本上机前，先读其 REPO 常量、远端清单、是否 force、是否自动 stash 四项。

## E-11 sha3-tree 重签的对象是 Git 索引而非工作树（conf=high）

- `tools/sha3-tree.mjs` 的 `build`／`verify` 均经 `indexRecords(root)` 取 **stage-0 索引 blob**，并显式排除清单自身；`verify` 还要求清单**已入索引**，否则抛 `manifest is not staged`。
- 故唯一正确次序：暂存全部内容件 → `build` → 暂存 `attest-hmac-sha3-512.json` → `verify` → 提交。先提交再重签、或重签后不暂存清单，都会产出与索引不符的清单。
- 必须从仓库根运行（否则抛 `run from the Git repository root`）；密钥经 `OPL_A2A_HMAC_KEY_B64`（恰 64 字节的规范 base64）与 `OPL_A2A_HMAC_KEY_ID` 注入环境变量，密钥值不入命令行、不落盘、不回显。
- 附带收益：索引 blob 已由 `core.autocrlf=true` 归一为 LF，故重签对象不含行尾噪声，规避了「工作树 CRLF 致哈希全变」的已知陷阱。

## E-12 av-media-ops v0.2.0：失败关闭优先于能力宣称（conf=high）

- 本轮 `scripts/av_intake.py` 增至 1287 行、新增 `scripts/test_av_intake.py` 955 行，引入 AV1／H265 本地转码门禁：仅接受固定本地磁盘上的普通文件，拒绝 URL、FFmpeg 伪协议、UNC、Windows 设备名／ADS、符号链接与重解析路径；输入先复制到私有有界快照，输出只写入已打开句柄；AV1 依次选 `libsvtav1`／`libaom-av1`，H265 只接受 `libx265`，编码器缺失即失败关闭；不覆盖既有输出、不自动安装 FFmpeg。
- 教训：宿主 FFmpeg 不在 PATH 时，**不得**把「设计已实现」写成「编码已成功」。SKILL.md 明写「仅完成失败关闭与单元验证，不宣称真实编码成功」，且能力一律以 `codecs` 实时探针为准，不沿用 v0.1.0 的历史在场结论。
- 出域前三项先行：CodeRabbit 只读复审 + `secrun scan` 六件 rc=0 零命中 + 敏感面正则复核（IPv4／端口／MAC／密钥形态／主机／Windows 路径六类），缺一不发布。

## E-13 并发推送下「落后 N 提交」是瞬时读数（conf=high）

- 本轮从首次勘查到执行 `fetch` 的数分钟内，落后数由 131 跳到 303（`6d47e7b..dc4105f`），并新增并行席分支 `seat/qoder-505f061a-sync-20261006`。
- 教训：多席并发推送下，落后数与远端 HEAD 都不可写入结论后沿用。整合前必须重新 `fetch` 并以 `git rev-list --left-right --count HEAD...origin/main` 当场重测；推送后以 `git ls-remote` 读回的远端 HEAD 为准绳核验落地，**不以本地 ref 为凭**（本地 ref 只证明我方意图，不证明对方已收）。
- 快进前置条件核验法：`git merge --ff-only` 在工作区有未提交改动时能否成功，本身即「上游是否触碰本地脏件」的经验判据——本轮成功即证明上游 303 提交未触碰本席三个脏件，无需逐件 diff。

---
登记：守藏(DF-DOC-01)（Qoder 工作区，git 身份即提交署名，可复核）· 2026-10-06
敏感面自检：本节不含密钥、令牌、MAC 地址、预签名 URL、真实主机名与用户目录字面值；E-08~E-13 全部为本轮实测，每条附可复核命令。
