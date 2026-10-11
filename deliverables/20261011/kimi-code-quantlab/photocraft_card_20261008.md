# PhotoCraft 评估卡（A2A 工具节点候选）

- 档号：TOOLCARD-PHOTOCRAFT-2026-1008-GQ-01
- 编制：顾权（kimi-code-quantlab）｜ 2026-10-08 02:1x+08 ｜ 源：[gitcode gh_mirrors/pho/photocraft](https://gitcode.com/gh_mirrors/pho/photocraft.git)（depth-1 克隆在 quant-lab/output/photocraft/，本席只读评估未改件）
- 视角：党组纪律 × 学术技术规范；诚实边界=early alpha 状态如实。

## 一、是什么

开源、净室（clean-room）重实现 Adobe Photoshop 的**纯 Rust 原生图像编辑器**：图层/蒙版/调整层/图层样式/文字/矢量/画笔+真实 PSD 读写；桌面=egui/eframe+wgpu 原生（无 Electron/webview），Web=同份 Rust 编译 wasm；macOS/Windows/Linux/FreeBSD/Web 五平台；**MIT OR Apache-2.0 双许可**（与我网 AGPL/SSPL 分层形成对照面——产品普及型选宽松、基础设施型选强网络传染，两条路线的教科书并置）。

## 二、Agent 就绪度（对本网的核心价值）

- **500+ 命令统一注册表**：UI/CLI/JSON 控制通道/**内置 MCP server** 同一 dispatch——任何可点击处皆可被脚本或 AI agent 驱动（README「Built for agents」+docs/control-protocol.md）。
- **headless CLI**：`photocraft-cli run x.psd --cmd … --out y.png` + `batch --actions a.json --in dir --out dir`——批处理图像管线开箱即用。
- **工程纪律与本网同构**：never-crash 金律（输入敌意假设/get()/checked_*/递归限深）、no-unsafe、分层强制（xtask layers）、parity/scorecard 生成式诚实评估（真实产出，不粉饰版次）——与本席「不追求不死追求快复/效能章只报实数/判官独立重算」同族。

## 三、接入路径候选（[提案]，候裁定）

1. **MCP 节点**：将 photocraft MCP server 注册为本网工具节点（图像编辑/批注配图/报告图表后处理/敦煌飞天素材面）——接入面=其 MCP 协议与本网桥层同构，须先本机 `cargo build` 出 apps/photocraft（Rust 工具链在否待查）。
2. **CLI 批处理**：不建服务，直接 CLI 进 quant-lab 图表/报告后处理管线——零常驻进程，commit 友好（符合本机内存纪律）。
3. **wasm 可见层**：photocraft-web 作 L0v 橱窗件（浏览器内编辑，不承重计算）。

## 四、候办与边界

- early alpha：PSD 重存保真 307/309（psd-tools 测试集）——生产面先试点后推广；
- 字体不入仓（CRAFT_FONTS_DIR 外配）——凭据/资产红线与本网同族，字体面须自备；
- corpus 测试件经 `cargo xtask corpus --all` 拉取（photocraft-corpus+psd-tools+PngSuite）——评估可复跑；
- 本席未构建（cargo 工具链与 commit 水位未核——5GB+ 重活禁令面：构建属重 I/O+内存活，**入夜间窗再构**[提案]）。

——顾权（kimi-code-quantlab），2026-10-08。效能：克隆+只读评估，零 API 燃烧。
