# 工具评估卡：codex-cockpit（Codex 驾驶舱）

- **评估日期**：2026-10-08
- **评估车道**：A2A 网络「顾权席」研究子代理 · 机主 2026-10-08 全局声明 v2
- **对象**：https://github.com/HouSiyuan2001/codex-cockpit （简介站 https://codex-cockpit.pages.dev/）
- **本地克隆**：`C:\Users\欧阳宏俊\Documents\kimi\quant-lab\output\codex-cockpit\`（浅克隆 15MB，commit `d117c9b`，2026-10-07 20:45 +0800；评估全程只读，`git status` 零改动）
- **评估方式**：README + 源码实读（未构建、未运行、未安装）

---

## 一句话定性

面向 Codex（及多家 AI 编程助手）**额度/用量的 Tauri 2 桌面悬浮窗监控器**——本地优先、可选 Cloudflare 自托管同步、MIT 许可的单人 beta 项目；它是"**用量看板**"，不是会话管理器，更不是多实例编排工具。

## 实证要点

### 技术栈（来源：仓库文件实读）

- **前端**：React 19.1 + TypeScript 5.9 + Vite 7 + @phosphor-icons/react（`package.json`，包名仍沿用旧称 `quota-float`，版本 `0.3.0-beta.5`）
- **后端**：Rust + Tauri 2（`src-tauri/Cargo.toml`）：tray-icon、single-instance、window-state、autostart、updater、notification；reqwest(rustls) + rusqlite(bundled) + keyring 3.6（apple-native/windows-native）+ aes-gcm + tokio
- **可选云同步**：Cloudflare Worker + D1（`cloud/usage-sync-worker/`，21 个依赖条目，wrangler 自托管）
- **规模**：Rust 端约 17,100 行（`src-tauri/src/*.rs`），前端 React 组件 + hooks + lib，76 个测试文件，Rust 内嵌 156 个 `#[test]`

### 功能面（对 Codex 的增强到底是什么）

| 任务假设 | 实读结论 | 证据 |
| --- | --- | --- |
| 会话管理？ | **无**。不创建/调度/控制 Codex 会话；只读解析 `~/.codex/sessions/YYYY/MM/DD/*.jsonl` 历史文件做统计 | `src-tauri/src/codex.rs:338-363` |
| 用量看板？ | **是，核心功能**。①官方额度：优先 spawn 本机 `codex app-server --stdio` 发 JSON-RPC `account/rateLimits/read`（6 秒超时），回退 legacy HTTP `chatgpt.com/backend-api/wham/usage`（读 `~/.codex/auth.json` 的 access_token）；②本地会话事件按 UTC+8 04:00"使用日"聚合每日用量；③任务/模型维度 Token 与**估算**成本；④周额度配速×重置风险图、舒适度曲线拟合、日历热力图、PNG 小票导出、第三方重置预警铃 | `codex.rs:23-24,630-703,849-1001`；`codex_project_usage.rs`；简介站；`docs/REMAINING-QUOTA-PLAN.md` |
| 多实例？ | **恰好相反**——`tauri-plugin-single-instance` 强制单开；也不编排 Codex 多实例 | `src-tauri/Cargo.toml:34` |
| 其他 provider | 同一框架还监控 antigravity（Google）、qoder、trae、volcengine（火山方舟）、workbuddy，另有 tokei 兼容层 | `src-tauri/src/{antigravity,qoder,trae,volcengine,workbuddy,tokei_usage}.rs` |
| 对外接口 | **无 MCP、无 CLI/headless 模式、无系统级 API**；全库 grep `mcp` 仅命中字体二进制；命令面全部是 Tauri IPC（前端↔后端） | 全库 grep；`lib.rs:3079-3119` |
| 云同步 | 可选项：管理员自有 Cloudflare 账号部署 Worker+D1，小团队邀请制；**非端到端加密**，任务/项目名默认不共享；同步凭据存系统 Keychain/Credential Manager | `README.md:85`；`docs/PRIVACY.md:7-15` |

### 许可证

- **MIT**（`LICENSE`，"Copyright (c) 2026 Quota Float contributors"）；`Cargo.toml`、`package.json` 元数据一致
- 基于上游 [silverlion2/quota-float](https://github.com/silverlion2/quota-float) 开发（`README.md:93` 明示），上游同为 MIT，API 元数据确认存在且公开（2026-07-16 建仓，描述即"Local-first desktop quota monitor for Codex, Qoder, TRAE, WorkBuddy, Volcengine Ark Coding Plan, and Google Antigravity"）
- `docs/THIRD_PARTY_NOTICES.md` 存在但仅 8 行，第三方 NOTICE 完整性待核（见候裁项）

### 代码健康（2026-10-08 实测）

- **依赖精简**：root lockfile 仅 89 个直装条目（210 总条目），worker 21 个；三份锁文件齐备（`package-lock.json`×2、`Cargo.lock`）
- **漏洞扫描**：本机实跑 `npm audit --audit-level=moderate`，root 与 worker 两个 lockfile 均 **0 vulnerabilities**
- **测试**：76 个测试文件（vitest + Rust 内嵌 + worker mjs 测试）；CI 三时区矩阵跑全量
- **CI**：`.github/workflows/release.yml`（tag 触发）= npm audit×2 → vitest → build → 自研 `audit:public`/`audit:history` 防泄露审计 → cargo fmt/clippy(`-D warnings`)/test/`cargo audit` → 签名 updater 构建 → Windows Defender 扫描；另有 `verify-release.yml` 对已发布安装包做校验和核对+Defender 复扫
- **活跃度**：仓库 2026-08-15 创建，27 commits，**单一贡献者 HouSiyuan2001**；9 stars / 1 fork / 0 open issues；首个版本化 Release `v0.3.0-beta.5` 发布于 2026-10-07（评估前一日），pushed_at 同日——极早期但迭代活跃

## 接入 A2A 网络的候选路径（本机约束：内存 commit 常态 90%+，5GB+ 重活禁止）

| # | 路径 | 可行性 | 依据与代价 |
| --- | --- | --- | --- |
| 1 | **只读看板镜像**：不装 App，把其 Rust 解析逻辑（会话 jsonl 聚合、app-server JSON-RPC 调用、使用日口径）作为参考实现，A2A 侧自研轻量只读读取器镜像 `~/.codex` 数据 | **中** | 源码已落盘 15MB、零运行时开销；模块自带限额（`MAX_BYTES=256MB`、`MAX_SECONDS=8` 等有界设计）；MIT 授权明确。需自研工程量，署名 Quota Float contributors |
| 2 | **安装 Release 桌面 App 作本机额度哨兵**：x64-setup.exe 仅 6.2MB | **中-低** | Tauri 常驻托盘进程内存经验估 50–150MB（未实测），commit 90%+ 机器上常驻需机主裁决；且**无 CLI/IPC 输出，数据只能 GUI 肉眼消费**，对"程序化接入 A2A"价值有限——定位是机主自用看板 |
| 3 | **CLI 批处理**：fork 后把 `codex.rs` 抽成独立 CLI | **低** | 需 Rust 工具链 + node_modules + cargo target，磁盘与构建内存约 2–4GB，逼近 5GB 红线；且本卡纪律为只读不构建 |
| 4 | **MCP 节点**：包装为额度查询 MCP server | **低（经本项目）/ 中（绕开本项目）** | 上游无 MCP；更优路径是 A2A 自研薄 MCP wrapper 直接调 `codex app-server --stdio`（`codex.rs:636` 的 JSON-RPC 方法即公开协议面），本项目源码可作协议参考，不必引入整套 GUI 应用 |
| 5 | **Cloudflare 同步自托管** | **低/暂不** | 需机主自有 Cloudflare 账号+D1，面向多人协作场景，单机 A2A 无此需求，且引入新的外部凭据面 |

**推荐**：路径 1 + 路径 4 的并集——把本仓库当作"Codex 用量读取协议参考实现"消化，A2A 侧自研只读薄层；路径 2 交机主裁决是否自用。

## 风险面

- **凭据处理面**（实证较干净，但有读取面）：
  - 读 `~/.codex/auth.json` 取 access_token 发 legacy HTTP 请求；token 仅置于 Authorization header 并 `set_sensitive(true)` 标记（`codex.rs:107-123`）；优先走本机 app-server 子进程则完全不碰 token 文件
  - 会话 jsonl **含对话内容，采集器确实会打开这些文件**提取用量/元数据——`PRIVACY.md:5` 与 `repository-map.md` 均诚实标注"不能宣传成从不读取会话文件"；同步载荷不含对话正文与凭据（声明级，未做全量数据流审计）
  - `AGENTS.md:20-21` 立有 local-first credential boundary 红线；自研 `audit:public`/`audit:history` 脚本 CI 强制跑防泄露
- **供应链**：依赖少 + 双 lockfile 本机实测 0 漏洞 + CI cargo audit；但**安装包未 Apple 公证、未 Windows 发布者签名**（`README.md:55` 自述并要求用户勿关闭系统保护）；updater 有 Tauri 签名私钥保护于 CI secrets；Windows 安装包有 SHA256SUMS + Defender 扫描证据
- **活跃度/可持续性**：bus factor = 1，27 commits、首个 Release 仅一天历史；beta 阶段（0.3.0-beta.5）；无社区治理结构。优势是 CI/测试纪律超出同体量单人项目常见水平
- **数据口径**：成本为估算非官方账单（README 自述）；重置预警来自第三方公开面板（reset_forecast.rs），非官方保证

## 候裁项（交机主/主会话裁决）

1. 是否在 commit 90%+ 本机常驻该托盘进程（内存预算需实测，估 50–150MB）
2. 是否授权 A2A 侧按 MIT 复用其会话解析/app-server 调用逻辑（需署名 Quota Float contributors）
3. 未公证/未签名的安装包是否过机主安装红线
4. `THIRD_PARTY_NOTICES.md` 仅 8 行，依赖 NOTICE 完整性待核
5. 路径 4（自研 app-server MCP wrapper）是否立项——若立项，本克隆可直接作为协议参考

---

## 来源清单

1. 本地克隆实读（commit `d117c9b`）：`README.md`、`AGENTS.md`、`LICENSE`、`package.json`、`src-tauri/Cargo.toml`、`src-tauri/src/codex.rs`、`src-tauri/src/codex_project_usage.rs`、`src-tauri/src/lib.rs`、`docs/PRIVACY.md`、`docs/THIRD_PARTY_NOTICES.md`、`SECURITY.md`、`.github/workflows/release.yml`、`.github/workflows/verify-release.yml`、`skills/codex-cockpit/SKILL.md`、`skills/codex-cockpit/references/repository-map.md` —— 路径前缀 `C:\Users\欧阳宏俊\Documents\kimi\quant-lab\output\codex-cockpit\`
2. GitHub 仓库主页：https://github.com/HouSiyuan2001/codex-cockpit
3. 简介站（交互预览用示例数据）：https://codex-cockpit.pages.dev/
4. GitHub API 元数据：https://api.github.com/repos/HouSiyuan2001/codex-cockpit （created 2026-08-15 / pushed 2026-10-07 / 9 stars / MIT）
5. GitHub API Releases：https://api.github.com/repos/HouSiyuan2001/codex-cockpit/releases （v0.3.0-beta.5，2026-10-07，3 assets：dmg 19MB / x64-setup.exe 6.2MB / SHA256SUMS）
6. GitHub API Contributors/Commits：27 commits，单贡献者 HouSiyuan2001
7. 上游仓库 API 元数据：https://api.github.com/repos/silverlion2/quota-float （存在、公开、MIT；其 github.com HTML 页本机网络不可达，**指针级，未读正文**）
8. 本机实测：`npm audit --audit-level=moderate`（root + cloud/usage-sync-worker 两个 lockfile，均 0 vulnerabilities，2026-10-08）

## 局限声明

- 本卡为**只读静态评估**：未构建、未运行、未安装该 App；运行时内存占用为 Tauri 应用经验估计（50–150MB），未实测
- Windows 安装包未下载，SHA256 未核对；Defender 扫描证据为 CI 配置级确认，未验证 Release 附件报告内容
- "同步不上传对话正文/凭据"为 `PRIVACY.md` 声明 + 模块头注释级佐证，未做全量数据流审计
- 估算成本、重置风险的算法细节（蒙特卡洛、舒适度拟合）仅确认存在与文档指针，未复算验证
- 上游 quota-float 的 Web 页面与 README 正文本机不可达（curl 000），仅 API 元数据级确认其存在、公开与 MIT 许可
- GitHub star/issue 等社区指标截至 2026-10-08，项目处首个 Release 次日，活跃度结论可能快速过时
