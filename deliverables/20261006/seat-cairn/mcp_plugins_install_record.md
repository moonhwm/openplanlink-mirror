# DSH MCP 插件安装记录（IMA / WPS / Supabase / Neon / 百度网盘）

日期：2026-10-06 ｜ 形态：**五个独立 DSH 插件包（bundle）**，插件页可见、可禁用、可卸载

## 一、插件页可见的五个插件

| 插件包 | 服务 | 工具前缀 | 工具数 | 连接状态 |
|---|---|---|---|---|
| `dsh-plugin-ima` | IMA（腾讯 ima 知识库） | `mcp__ima__*` | 17 | ✅ **已连接并实测可用** |
| `dsh-plugin-baidu` | 百度网盘知识库（社区 MIT 实现） | `mcp__baidu__*` | 27 | ✅ **已连接** |
| `dsh-plugin-wps` | WPS 多维表格 | `mcp__wps__*` | 4 | ⏸ 待凭据 |
| `dsh-plugin-supabase` | Supabase（只读） | `mcp__supabase__*` | 19 | ⏸ 待凭据 |
| `dsh-plugin-neon` | Neon Serverless Postgres | `mcp__neon__*` | 20 | ⏸ 待凭据 |

插件源码：`C:\Users\欧阳宏俊\.dsh\profiles\desktop\plugins\<包名>\`
（每包 = `package.json`（含 `dsh.bundle.patch`）+ `cordis.patch.yml` + `index.js`；
包内 patch 插入一条官方 `@deepseek-ai/dsh-mcp-client` 行，不含任何自写桥接代码）

**端到端实证**：`mcp__ima__ima_list_notebooks` 返回 `{"code":0,"msg":"success","request_id":"1fc1164e…"}`。

## 二、MCP 服务器本体（npm 包，已安装）

位置 `C:\Users\欧阳宏俊\.dsh\mcp-servers\`（pnpm + npmmirror 镜像）

| 服务 | 包 | 版本 |
|---|---|---|
| IMA | `ima-mcp` | 1.0.0（已就地修复 5 处 ESM 相对导入缺 `.js`，原文件留 `.bak`） |
| WPS | `wps-mcp` | 1.1.0 |
| Supabase | `@supabase/mcp-server-supabase` | 0.13.0 |
| Neon | `@neondatabase/mcp-server-neon` | 0.4.1（0.6.x 依赖树在镜像上抓不稳；`zod ^3.25.76` override） |
| 百度网盘 | `baidu-netdisk-knowledge-mcp` | 0.1.0（源码构建于 `C:\Users\欧阳宏俊\.dsh\mcp-vendor\`） |

统一由 `launch.mjs` 拉起：从环境变量注入凭据；缺凭据即安全退出（`exit=4`），**不影响 harness 启动**。

## 三、凭据（只走环境变量，不落盘）

| 插件 | 环境变量 |
|---|---|
| ima | （可选）`IMA_OPENAPI_APIKEY` / `IMA_OPENAPI_CLIENTID` |
| wps | `WPS_API_TOKEN` / `WPS_FILE_ID` / `WPS_SCRIPT_ID` |
| supabase | `SUPABASE_ACCESS_TOKEN` |
| neon | `NEON_API_KEY` |
| baidu | （授权时）`BAIDU_APP_KEY` / `BAIDU_SECRET_KEY` / `BAIDU_REDIRECT_URI` |

> **要点**：MCP 子进程继承 **DSH 进程启动时**的环境变量。因此设置新环境变量后需重启一次 DSH 才会被继承；
> 单纯安装/禁用插件则**无需重启**（bundle 即时生效）。

## 四、关键实现经验（踩坑记录）

1. **MCP 接入不是「一张卡片」**：`dsh-mcp-client` 的行才是本体；要靠 bundle 才能成为插件页可见、可管理的条目。
2. **`file:` 安装是复制、`link:` 是链接**：改源码后必须 `link:`（或用 `remove_bundle` + 重装），否则运行的是旧副本。
3. **config 的 `env` 值必须是 string**：`!!js process.env.X` 在变量缺失时得到 `undefined` → `ValidationError`；
   必须写 `!!js (process.env.X ?? '')`。
4. **profile 补丁层在 bundle 之后加载**：同名行会覆盖 bundle 内正确的行——
   插件的配置行必须只存在于 bundle 内，profile `cordis.patch.yml` 不要重复。
5. **本环境会回收计划任务里的长驻进程**：自动重启不宜依赖 Task Scheduler + `Start-Sleep`；插件走 bundle 后已无需重启。

## 五、卸载 / 回滚

```powershell
# 在设置-插件页禁用，或：
#   plugin_manager remove_bundle <包名>
# 完全回滚（移除五个插件与配置）：
foreach ($p in 'ima','wps','supabase','neon','baidu') { Remove-Item "C:\Users\欧阳宏俊\.dsh\profiles\desktop\plugins\dsh-plugin-$p" -Recurse -Force }
```
MCP 服务器本体保留在 `.dsh\mcp-servers`，不影响 harness。

## 六、验证脚本

```powershell
$node = 'C:\Users\欧阳宏俊\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe'
cd C:\Users\欧阳宏俊\.dsh\mcp-servers
& $node probe_mcp.mjs      # ima/wps/supabase/neon 握手（含工具清单）
& $node probe_one.mjs 'C:\Users\欧阳宏俊\.dsh\mcp-vendor\baidu-netdisk-knowledge-mcp\dist\cli.js'   # 百度网盘
```
