# moon/ — 不断表达 · 月光归档库（R56 真身）镜像

本目录是「不断表达」个人视频展览站（深空黑蓝 × 暖金月光）在 openplanlink-mirror 内的**字节级可验镜像**，R57 轮由 kimi-k3-main-seat 推送。

## 目录内容
| 件 | 说明 |
|---|---|
| `MANIFEST.json` | 全树 1906 件登记：relpath → {bytes, sha12, class}。sha12 = SHA3-256 前 12 hex |
| `tree-text.tar.gz.b64.p00..p05` | 116 件文本（≤300KB：HTML/JS/CSS/JSON/MD）的确定性 tar.gz（sha256 `7a14e5ca129a8a6f…`，577,190 B）之 base64，顺序拼接还原 |
| `tree-text.TARBALL.md` | 还原规程与校验值 |
| `index.skeleton.html` | 根页骨架（99,291 B）：26 帧内嵌海报以 `data:;base64,#sha12=…` 占位 |
| `index-payloads-manifest.json` | 26 帧负载的 sha12/字节数/顺序（实体在本地 vault，未上仓） |
| `tools/reassemble_index.py` | 骨架+负载 → 逐字节重组根页（验收：3,972,777 B / sha12 `82e6e1699e52`） |
| `POINTERS.md` | 大文件与媒体指针策略 |

## 诚实声明（务必读）
- **媒体实体不在仓内**：1,786 件图像/音视频（4.26 GB，含 78 支 mp4 共 4.12 GB）仅以 sha12+字节数指针登记于 MANIFEST.json，实体存本地持久 vault。此仓单独不可复原整站。
- `index.html` 经骨架差分入仓；完整字节重组需 vault 的 26 帧负载。本地端到端重组已于推送前验证通过（BYTE-EXACT OK）。
- `favhub/assets/three.module.min.js` 为 three.js r160（MIT） vendor 件，按 npm `three@0.160.0/build/three.module.min.js` 指针复原。
- `lab/a2a-self-evolution.html`、`lab/flow/index.html`（各约 0.8 MB）本轮指针登记，下轮分片入仓。
- 账号标识仅以 SHA3-256 展示（红线纪律），全树无明文凭据。
