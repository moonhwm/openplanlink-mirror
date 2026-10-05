# Codex CLI 安装探测日志 — 2026-10-05

席位：Codex安装席（Moon 工作区动态 workflow 子代理）
执行环境：Windows 10.0.26340 x64，宿主 Bash 工具实际解释器为 `/usr/bin/bash`（环境声明 cmd.exe，实测不符，见末尾备注）。

## 1. 探测（步骤1）

| 命令 | 返回 | 结论 |
|---|---|---|
| `codex --version` | `codex-cli 0.160.0` | 已在 PATH |
| `where codex` | `C:\Users\欧阳宏俊\AppData\Roaming\npm\codex`<br>`C:\Users\欧阳宏俊\AppData\Roaming\npm\codex.cmd` | 入口为 npm 全局 bin |
| `npm ls -g --depth=0` | `├── @openai/codex@0.160.0`（另有 `@cloudbase/cli@3.8.4`、`@deveco/deveco-cli@1.3.0-stable`） | @openai/codex 已全局安装 |

## 2. 安装（步骤2）— 未执行

@openai/codex@0.160.0 已在（步骤1三证），`npm install -g @openai/codex` 与 `npx` 替代探测均按任务口径跳过（替代探测仅限 npm 不可用/网络失败场景）。零重试、零伪装。

## 3. 复验与登录态探测（步骤3）— 只探测不代登

- 版本复验：`codex --version` 首次探测即当前值 `codex-cli 0.160.0`（未安装新版本，无二次复验必要）。
- `codex login status` → **`Logged in using ChatGPT`**（原样转出，未代登、未触碰凭据）。
- 配置路径存在性检查（bash `[ -e ]`，**只查存在性，未读任何内容**）：
  - `C:\Users\欧阳宏俊\.codex` → EXISTS
  - `C:\Users\欧阳宏俊\.codex\auth.json` → EXISTS
  - `C:\Users\欧阳宏俊\.codex\config.toml` → EXISTS

## 4. ChatGPT 6 Astra Max（步骤4）

无凭据，本席不探测登录。按主权人口径登记：**「20美元档疑似无法正常启动，待核」**。

## 备注

- Bash 工具按 cmd 语法执行 if-exist 检查失败一次（退出码 2，`syntax error near unexpected token '('`），实为 bash 解释器；换 bash 语法后成功。对探测结论无影响。
- 凭据纪律：全程未写入、未读取任何凭据明文；auth.json 仅确认存在。
