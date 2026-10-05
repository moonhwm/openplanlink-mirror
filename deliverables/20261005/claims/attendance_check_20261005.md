# 到场检查 · 生态工具链花名册 15 项双探（存在性 + 运行态）

- **执行时点**：2026-10-06（任务指定落盘名 `attendance_check_20261005.md`，实测时点为 2026-10-06）
- **执行席**：到场检查席（ZCode 动态工作流子代理，全程只读，未启动/未终止任何进程，凭据零落盘）
- **口径**：
  - 存在性 = 已知路径直查 → `where.exe` PATH 探测 → 安装根（%LOCALAPPDATA%\Programs、Program Files、Program Files (x86)）+ 桌面/开始菜单 `.lnk` 指向解析（WScript.Shell）三级降级
  - 运行态 = `tasklist /FO CSV /NH` 全量进程表模糊匹配（去 `.exe` 后缀与前缀变体），辅以 `tasklist /V` 窗口标题
- **总命令留痕**：`MSYS_NO_PATHCONV=1 tasklist /FO CSV /NH`（全量 ~33KB）；PowerShell `Get-ChildItem -Recurse` 扫三大安装根；`where.exe <名>` ×15（PATH 全部未命中）；`.lnk` 目标解析 79 条；`Get-Volume`/`Get-Partition`/`Get-Item`（A 盘性质）；`subst`/`net use`；`cat /a/DSH/dsh.pid`

## 结论

| 指标 | 值 |
|---|---|
| 在场（存在性） | **15/15** |
| NOT-FOUND 清单 | **空** |
| 运行中 | **6/15**（花名册模糊口径：去 `.exe` 后缀与前缀变体；其中 Qoder 两行经主映像 `Qoder.exe` ×13 命中，launcher 本体不驻留） |
| 运行中（严格同名映像口径） | **4/15**（Cursor.exe、DeepSeek Harness.exe、ZCode.exe、Kimi.exe） |
| 运行映像计数 | Cursor.exe ×19 · DeepSeek Harness.exe ×6 · ZCode.exe ×17 · Kimi.exe ×33（另有 kimi-webbridge.exe ×1）· Qoder.exe ×13 |

## 明细表

| 名称 | 存在 | 路径 | 运行中 | 备注 |
|---|---|---|---|---|
| Cursor.exe | ✓ | `C:\Users\欧阳宏俊\AppData\Local\Programs\cursor\Cursor.exe`（235,082,024 B，2026-10-02 22:31） | ✓ ×19 | 内存峰值 492,948 K（PID 31628）；桌面+开始菜单 `.lnk` 同指此路径；另有 `cursor\_` 二级副本目录 |
| DeepSeek Harness.exe | ✓ | `C:\Users\欧阳宏俊\AppData\Local\Programs\DeepSeek Harness\DeepSeek Harness.exe`（244,481,512 B，2026-09-29 18:34） | ✓ ×6 | 峰值 464,096 K（PID 19116）；`A:\DSH\dsh.pid`=31472 与现 6 PID 均不符（**陈旧 pid 文件**，运行态以 tasklist 为准）；`A:\DSH\dsh2.log` 含本地 web 端点令牌，按凭据零落盘纪律不予转写 |
| ZCode.exe | ✓ | `C:\Program Files\ZCode\ZCode.exe`（222,866,328 B，2026-09-29 11:21） | ✓ ×17 | 峰值 505,644 K（PID 28448）；本检查席宿主即 ZCode 进程之一（到场即证） |
| Xiaomi MiMo.exe | ✓ | `C:\Program Files\Xiaomi MiMo\Xiaomi MiMo.exe`（223,095,384 B，2026-09-29 23:10） | ✗ 0 PID | 未运行 |
| Kimi.exe | ✓ | `C:\Users\欧阳宏俊\AppData\Local\Programs\Kimi\Kimi.exe`（239,107,472 B，2026-09-30 11:50） | ✓ ×33 | 峰值 367,268 K（PID 25616）；伴生 kimi-webbridge.exe ×1（PID 17080，9,176 K）；窗口标题去重仅 {"Kimi","OleMainThreadWndName","暂缺"} |
| Qoder CN Launcher.exe | ✓ | `%LOCALAPPDATA%\Qoder CN\Qoder CN Launcher\Qoder CN Launcher.exe`（116,744 B，`.lnk` 指向）；副本 `%LOCALAPPDATA%\Programs\Qoder CN\resources\launcher\`（同字节） | ✓（前缀变体） | launcher 本体 0 PID——启动后即退不驻留；主映像 Qoder.exe ×13 在跑（峰值 283,856 K / PID 34820） |
| Qoder Launcher.exe | ✓ | `%LOCALAPPDATA%\Qoder\Qoder Launcher\Qoder Launcher.exe`（103,920 B，`.lnk` 指向）；副本 `%LOCALAPPDATA%\Programs\Qoder\resources\launcher\`（同字节） | ✓（前缀变体） | 同上，主映像 Qoder.exe ×13；严格同名口径下此行计 ✗ |
| Trae CN.exe | ✓ | `%LOCALAPPDATA%\Programs\Trae CN\Trae CN.exe`（214,551,440 B，2026-09-20 18:03） | ✗ 0 PID | 桌面快捷方式名为 `TraeCode CN.lnk` |
| codearts-agent.exe | ✓ | `C:\Program Files\CodeArts Agent\codearts-agent.exe`（210,890,104 B，2026-09-30 00:40） | ✗ 0 PID | `A:\cold\downloads-20260919\` 存有 codearts-agent-x64-26.8.203 / 26.9.100 安装包；同装 CodeArtsSpace.exe（非花名册项） |
| Kimi Code.exe | ✓ | `C:\Program Files\Kimi Code\Kimi Code.exe`（225,501,472 B，2026-09-24 15:46） | ✗ **0 PID** | **呼应被杀问题：装机在场但进程不在场**——当前实测无任何 Kimi Code 实例存活（详见专项段） |
| WorkBuddy.exe | ✓ | `C:\Program Files\WorkBuddy\WorkBuddy.exe`（204,585,008 B，2026-10-04 17:12） | ✗ 0 PID | 未运行 |
| Coze.exe | ✓ | `C:\Program Files\Coze\Coze.exe`（1,333,112 B，2026-09-22）；版本目录 `versions\1.1.44\` | ✗ 0 PID | 未运行；A:\ 根另有 coze_space_*_ext.exe ×2（非花名册项，如实备注） |
| Unity Hub.exe | ✓ | `C:\Program Files\Unity Hub\Unity Hub.exe`（246,088,160 B，2026-10-03 04:17） | ✗ 0 PID | 未运行；Unity Editor 6000.6.4f1 装于 `C:\Program Files\Unity\Hub\Editor\6000.6.4f1`（开始菜单证据） |
| ima.copilot.exe | ✓ | `A:\ima.copilot\ima.copilot.exe`（3,998,488 B，2026-09-30 11:16） | ✗ 0 PID | A 盘映射枢纽连通性见专项段；桌面 `ima.lnk` 与开始菜单 `ima.lnk` 均指向此路径 |
| emgm3.exe | ✓ | `C:\Users\欧阳宏俊\AppData\Roaming\Eastmoney Goldminer3\emgm3.exe`（71,428,352 B，2025-05-23 11:04） | ✗ 0 PID | 东财掘金量化终端，未运行 |

## 专项 A：A 盘映射枢纽 / junction 可达性（ima.copilot 行）

实测命令与返回：

- `subst` → 无输出（无 SUBST 映射）；`net use` → "列表是空的"（无网络映射）
- `Get-Volume -DriveLetter A` → FileSystemType=**NTFS**，DriveType=**Fixed**，Size=2,000,381,014,016 B（~1.86 TiB），SizeRemaining=999,250,845,696 B
- `Get-Partition -DriveLetter A` → **DiskNumber 0，PartitionNumber 2，Type Basic**
- `Get-Item A:\` 与 `Get-Item A:\ima.copilot` → **LinkType 空、Target 空**（均非 reparse point）
- A:\ 顶层目录 LinkType 扫描 → **0 个 junction**
- `ls /a/ima.copilot/` → ima.copilot.exe 在列（chrome 壳结构：chrome_proxy.exe、bugly、shiply 等），Test-Path OK

**结论**：`A:\ima.copilot\ima.copilot.exe` **路径可达性 PASS**。但 A 盘实为磁盘 0 第 2 分区的真实 NTFS 固定卷，**并非 junction/SUBST/网络映射**——"A 盘映射枢纽"目前以整盘外挂形式成立（A:\ 上另有 kimi-mirror、kimi-offload、OPL_A2A、DSH 等工作目录），`A:\ima.copilot` 本身是普通目录。若主权人预期此处是 junction 指针，则该预期与实测不符，如实记录。

## 专项 B：Kimi Code / Kimi Work 运行态（呼应被杀问题）

- **Kimi Code.exe**：装机在场（C:\Program Files\Kimi Code\Kimi Code.exe，Public Desktop `.lnk` + 开始菜单 ×2 指向），但 `tasklist /FO CSV /NH` 全量表中 **0 PID**——若此前发生过"被杀"，当前实测确认**无存活实例**，未被拉起。
- **Kimi Work**：花名册无独立映像；全量进程表无 "Kimi Work" 映像；`tasklist /V` 下 33 个 Kimi.exe 窗口标题去重后仅 {"Kimi", "OleMainThreadWndName", "暂缺"}，过滤 `work|code` 字样**零命中** → **无 Kimi Work 运行证据**。
- **Kimi 桌面版本体**（Kimi.exe）在跑 ×33（含大量 Electron 子进程），伴生 kimi-webbridge.exe ×1——主脸在场，但 Code/Work 两翼此刻均不在场。

## 证据清单（本次实际执行）

1. `MSYS_NO_PATHCONV=1 tasklist /FO CSV /NH` → 全量进程表（计数：ZCode 17 / Kimi 33 / DSH 6 / Cursor 19 / Qoder 13 / kimi-webbridge 1 / 其余花名册映像 0）
2. `MSYS_NO_PATHCONV=1 tasklist /V /FO CSV /NH | grep -a '^"Kimi'` → 窗口标题核验
3. `where.exe <名>` ×15 → PATH 全部未命中（走三级降级）
4. PowerShell `Get-ChildItem -Recurse -Filter *.exe` 于 `%LOCALAPPDATA%\Programs`、`C:\Program Files`（-Depth 4）、`C:\Program Files (x86)` → 15 项全部命中
5. WScript.Shell 解析桌面（含 OneDrive 桌面、公共桌面）+ 开始菜单 `.lnk` → 17 条花名册相关指向
6. PowerShell `Test-Path`/`Get-Item` 15 主路径 + Qoder 双 launcher 副本 → 17/17 OK（含字节数与修改时间）
7. `Get-Volume`/`Get-Partition`/`Get-Item LinkType`/A:\ 顶层 reparse 扫描/`subst`/`net use` → A 盘性质判定
8. `cat /a/DSH/dsh.pid` → 31472（陈旧，与运行 PID 不符）

—— 到场检查席 · 只读取证 · 2026-10-06
