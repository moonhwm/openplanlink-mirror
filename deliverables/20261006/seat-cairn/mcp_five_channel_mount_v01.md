# MCP 五通道挂载交接说明（v01）

- 席位：A2A新席_石敢当Cairn（SEAT `a2a-node-local`）
- 日期：2026-10-06 ｜ MAC：A0:88:69:0A:1C:2E
- 视角：党组学术技术成员规范化表述；本文件只记录、转述、协调，不增删改释来源
- 事项：按主权人令接入 IMA / Supabase / Neon / WPS / 百度云盘 五通道，并以「独立插件包」形态在 DSH 插件页可见、可审计

## 一、挂载形态（定论）

五通道各自成为一个 DSH 插件包（bundle），包内 patch 插入**一条官方** `@deepseek-ai/dsh-mcp-client` 行；
不新增任何自写桥接代码，工具命名遵循官方约定 `mcp__<serverName>__<rawName>`。

| 插件包 | serverName | 工具前缀 | 工具数 | 连接 |
|---|---|---|---|---|
| dsh-plugin-ima | ima | mcp__ima__ima_* | 17 | 已连接（实测） |
| dsh-plugin-baidu | baidu | mcp__baidu__baidu_* | 27 | 已连接 |
| dsh-plugin-wps | wps | mcp__wps__* | 4 | 待凭据 |
| dsh-plugin-supabase | supabase | mcp__supabase__* | 19 | 待凭据 |
| dsh-plugin-neon | neon | mcp__neon__* | 20 | 待凭据 |

合计 87 个工具；其中 44 个（ima+baidu）已在运行时可用。

## 二、可核验证据

1. `mcp__ima__ima_list_notebooks` → `{"code":0,"msg":"success","request_id":"1fc1164e…"}`
2. `mcp__ima__ima_search_knowledge_bases` → 读出两个知识库：
   - 「月之暗面的游乐场ima」content_count=3989
   - 「欧阳宏俊的知识库」content_count=128
   → 印证「接入读取以获得灵感」通道已具备实际读取能力（非仅装配）。
3. live 子进程：`launch.mjs ima`、`launch.mjs baidu`
4. profile `package.json`：bundles 含五个 `dsh-plugin-*`；dependencies 为 `link:` 形式（改源码即生效）

## 三、经验固化（供各节点复用，属"技能及其使用经验"）

1. MCP 接入不会自动成为插件条目；须以 bundle（`package.json` 的 `dsh.bundle.patch` → 包内 patch 层）封装，方能在插件页可见、可禁用、可卸载。
2. pnpm `file:` 为复制、`link:` 为链接；修改包源码后必须 `link:` 安装或先 `remove_bundle` 再装，否则运行旧副本。
3. mcp-client 的 `env` 值必须是 string：`!!js process.env.X` 在变量缺失时得到 `undefined` 会触发 `ValidationError`，须写 `!!js (process.env.X ?? '')`。
4. profile 补丁层在 bundle 之后加载：同名行会覆盖 bundle 内的正确行；插件的配置行只应存在于 bundle 内。
5. bundle 安装**即时生效**，无需重启 DSH；但 MCP 子进程继承 DSH 启动时的环境变量，故新增凭据后仍需重启一次。
6. 本环境会回收计划任务中的长驻进程（Task Scheduler + `Start-Sleep` 不可靠）；能用即时机制就不要依赖长驻脚本。

## 四、待办与依赖

- wps / supabase / neon：需 `WPS_API_TOKEN`+`WPS_FILE_ID`+`WPS_SCRIPT_ID`、`SUPABASE_ACCESS_TOKEN`、`NEON_API_KEY`（由主权人于 OS 级提供；本席不接触明文凭据）。
- 百度网盘授权：需 `BAIDU_APP_KEY`/`BAIDU_SECRET_KEY` 后走 `baidu_auth_qrcode` 二维码 OAuth。
- 后续：以 ima 通道检索 A2A 相关既有材料，用于阻塞六项的论证补强（只增不改）。

## 五、声明

本文件为新增留档，不修改任何既有 canonical 文件；配置变更前已备份 profile 补丁层
（`cordis.patch.yml.bak-mcp-20261006014606`），可一键回滚。
