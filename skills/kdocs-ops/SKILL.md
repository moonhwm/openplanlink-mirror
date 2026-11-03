---
name: kdocs-ops
description: "[项目技能] 金山文档运维台——kdocs-cli 在沙箱内的启动/认证/升级/读取/核验/版本监护全链路 ops 纪律。触发（满足任一）：①用户说「读 WPS/金山文档/kdocs 云文档」「kdocs.cn/l/xxx 链接」「重读纲要/批注」「云文档建档/监护」「可微可导」「版本指纹」或等价表述（含语音变体，不纠正用户、映射意图）；②沙箱内首次或重装后使用 kdocs-cli（setup.sh/auth_restore/PATH/升级）；③kdocs-cli 报错需分诊（400001/400100/500000/unknown service/unknown action/Permission denied/not found）；④需要对云文档做版本枚举、历史版本下载、跨版本比对或全文 sha256 指纹建档时；⑤otl block-query / drive read-file / search-files 参数形状拿不准时。覆盖：沙箱启动五连、命令面速览、读取路径决策、错误码分诊表、版本监护建档工作流、写后核验与凭据安全纪律。不覆盖：kdocs 能力清单与 API 本体（归官方 kdocs 插件 skill，引用不复制）；OTL 文书编写标准与发布管线（归 otl-format-ops）；飞书文档（归 lark-docs-write-verify-ops）。中文名：金山文档运维台。English triggers: kdocs-cli sandbox ops, WPS cloud doc read/verify, kdocs auth restore, cloud doc version monitoring, doc fingerprint archive."
metadata:
  version: "1.0.0"
---

# 金山文档运维台（kdocs-ops）v1.0.0

> 立法锚：**「先 PATH 后认证，先分层后重试；读到的每个字都要能指回一个版本号与一枚指纹。」**
> 实证来源：2026-10-05~13 三会话（OpenPlanLink 纲要件 ci2ybbMcccFi 重读/批注/建档线）实跑——同一套启动摩擦在三个会话里各自重踩一遍，本件把它一次固化。

## §0 定位与边界（先读）

- 本件管 **kdocs-cli 的沙箱运维面**：装、认证、升级、读、核验、版本监护建档。能力清单与参数全集以官方 kdocs 插件 skill 为准（`/app/.agents/plugins/kdocs/skills/kdocs/SKILL.md`，引用不复制）。
- OTL 文书「写什么/怎么写/怎么验/怎么登记」归 otl-format-ops；本件只补它明示不覆盖的「kdocs API 调用纪律与认证」的沙箱实操层。
- 红线继承：凭据永不落明文/不回显；token 只存加密件（token.enc）；**云文档正文可能含明文凭据——只登记 8 字符前缀，全文零回显零落盘**（实证：2026-10-10 纲要件扫出 4 枚明文 key，按前缀入册）。

## §1 沙箱启动五连（每个新沙箱/新会话段必跑；脚本：scripts/kdocs_bootstrap.sh）

顺序即纪律，错位即报错：

1. **探活**：`which kdocs-cli || ls ~/.kimi-work/bin/`——没有则 `bash /app/.agents/plugins/kdocs/skills/kdocs/scripts/setup.sh`（装到 `~/.kimi-work/bin/`，二进制名是 **kdocs-cli**，不是 kdocs）。
2. **先 export PATH**：`export PATH="$HOME/.kimi-work/bin:$PATH"`——setup 后立刻 `kdocs-cli` 仍 not found（实证）；**auth_restore.sh 自身也要 kdocs-cli 在 PATH**，PATH 未导先跑 auth_restore 会误报「未找到 kdocs-cli」（2026-10-05 实证）。
3. **升级后必修执行位**：`kdocs-cli upgrade -y` 后二进制丢 exec 位 → `sh: kdocs-cli: Permission denied`，`chmod +x ~/.kimi-work/bin/kdocs-cli` 即复（2.5.11→2.7.1 实证）。非必要不升级；官方提示「Skill may also need updating」时先查官方件版本。
4. **认证恢复**：`bash .../scripts/auth_restore.sh`——从加密 token.enc 恢复登录态，输出「Token 验证成功！kdocs 登录态已从持久化 token 恢复」；若回「已登录（密钥链），无需恢复」则直接可用。token 全程无明文。
5. **状态断言**：`kdocs-cli auth status` 解 JSON 取 `authenticated:true` 才开干；false 则重跑第 4 步，仍 false 如实报用户须扫码授权（人身动作，不代办）。

## §2 命令面速览（拿不准先 `--help`，禁猜服务/动作名）

- 服务面（v2.5.11/2.7.1 实证）：`drive`（文件管理 45 动作）/`sheet`/`otl`（智能文档 6 动作）/`dbsheet`/`form`/`wpp`/`aippt`…**没有 `doc` 服务**（`kdocs-cli doc read` 报 unknown service）。
- 高频动作：`drive search-files '{"keyword":"..."}'`（搜文件，**动作名是 search-files 不是 search**）；`drive read-file`（整篇原文）；`drive get-file-info`（当前版本号）；`drive list-file-versions`（历史版本枚举）；`drive get-file-version-download`（历史版本下载）；`otl block-query`（块结构）。
- 参数一律 JSON 串；定位符三选一 **`url`/`link_id`/`file_id`**（写成 `file_url` 报 400001）。
- 完整命令/参数/返回 JSON 形状见 references/cli-cheatsheet.md。

## §3 读取路径决策（先选路再调）

| 目的 | 首选 | 实证行为 |
|---|---|---|
| 取整篇正文（建档/重读） | `drive read-file '{"url":"...","format":"markdown"}'` | 纲要件（.otl）与润色件（.docx）均通；返回 `data.content` 为全文 |
| 取块结构/标题树 | `otl block-query '{"file_id":"...","params":{"blockIds":["doc"]}}'` | **params 必填**（缺省报 400001「params 为必填」）；部分文档报 400100 第三方 4xx |
| 定位 file_id/link_id | `drive search-files '{"keyword":"..."}'` | 返回 `data.data.items[].file{name,id,link_url,...}` |
| 取当前版本号 | `drive get-file-info '{"file_id":"..."}'` | 监护建档的版本锚 |

回退链：otl block-query 400100/500000 → 改 drive read-file 取正文（块级诉求降级为节级文本切分）；read-file 也败 → 查 auth status → 如实报。

## §4 错误码分诊表（全部实证，按表处置不空转）

| 报错 | 真因 | 处置 |
|---|---|---|
| `sh: kdocs-cli: not found` | PATH 未导或未安装 | §1 第 1–2 步 |
| `sh: kdocs-cli: Permission denied` | upgrade 丢 exec 位 | `chmod +x ~/.kimi-work/bin/kdocs-cli` |
| `400001 One of url, link_id, or file_id is required` | 定位符键名错（如 file_url） | 改 url/link_id/file_id |
| `400001 params 为必填` | otl block-query 缺 params | 补 `"params":{"blockIds":["doc"]}` 整篇读 |
| `400001 version_num 为必填且须为正整数` | 历史版本下载的键名是 **version_num** 不是 version | 先 list-file-versions 取号，再传 version_num |
| `400100 第三方服务错误（4xx）` | otl 块接口对该文档不通（权限/格式） | 降级 drive read-file，不硬刷 |
| `500000 服务暂时不可用` | 云端瞬态 | 稍候重试 ≤2 次；连续败如实报 |
| `unknown service or command "doc"` | 服务名不存在 | 用 §2 服务面 |
| `unknown action "search" in service "drive"` | 动作名错 | search-files |

## §5 版本监护建档工作流（「可微可导」建档，2026-10-05 机主令实录）

对点名监护的云文档建立结构化档案，保证可重拉、可比对、可告警：

1. **取证**：`get-file-info` 取当前版本号 → `read-file` 取全文 → 计算全文 sha256（展示用前 16 位）。
2. **节级指纹**：按标题切节，逐节记 sha256[:16]+起始行——后续轮次只比指纹即可定位变动节，不必全文重读比字。
3. **落档**：`docs/<key>.txt`（正文）+ `<key>.meta.json`（file_id/版本/字数/链接数/节指纹）+ `index.json`（登记簿）；README 载建档时点与执行席。scripts/doc_fingerprint.py 一把跑完并出 diff 报告（版本/字数/指纹是否漂移）。
4. **历史回溯**：`list-file-versions '{"file_id":"...","page_size":10}'` 枚举 → `get-file-version-download '{"file_id":"...","version_num":<正整数>}'` 取历史版——**键名 version_num**，传 version 报 400001。
5. **通告**：建档/变动结果按既有总线纪律发通告（如有），零凭据零 PII。

## §6 写后核验与安全

- 写类动作（otl insert/update/delete）后**独立回读**比对标题与关键节，不信任 `code:0`（与 otl-format-ops 铁律 3 同源，引用不复制）；写类动作逐次须用户批准。
- 认证材料只有 token.enc 加密件；任何命令输出先扫凭据样字符串再展示；文档正文扫出的疑似 key 按 8 字符前缀登记，禁全文回显。

## Pitfalls（坑位清单，实证）

- **PATH 顺序坑**：先跑 auth_restore.sh 再导 PATH → 误报「未找到 kdocs-cli」，白慌一场（§1-2）。
- **升级坑**：看到「v2.x available」就升级 → exec 位丢失 Permission denied；非必要不升，升后必 chmod（§1-3）。
- **假想服务坑**：凭直觉造 `doc` 服务/`search` 动作 → unknown 报错；先 `--help`（§2）。
- **参数键名坑**：file_url/version 是错键名，url·link_id·file_id/version_num 才对（§4）。
- **输出混流坑**：CLI 把升级提示打到 stdout 尾部，解析 JSON 须用 `json.JSONDecoder().raw_decode(text.lstrip())` 容错截取，或先重定向落盘再解析（实证：管道直解被升级提示污染）。
- **`-o` 落盘坑**：`drive read-file -o <path>` 实测退出码 2 且行为不稳——改 shell 重定向 `> /tmp/x.json` 再解析（2026-10-12 实证）。

## Resources

- `scripts/kdocs_bootstrap.sh`——§1 启动五连一键跑（幂等，全绿输出 auth:true 才 exit 0）。
- `scripts/doc_fingerprint.py`——§5 建档：读 read-file 的 JSON 导出 → sha256 指纹 → 更新 docs/ 档案与 index.json → 打印漂移 diff。
- `references/cli-cheatsheet.md`——命令面全表、JSON 参数卡、返回结构图、错误码全集。
