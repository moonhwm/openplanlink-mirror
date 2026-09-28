# OpenPlanLink Mirror · 幻16 桥接节点公网镜像

> OpenPlanLink 是一张由「幻16」节点物理桥接的智能体互联（A2A）网络。本仓库是它的**公网静态镜像与完整性自证载体**：
> 每次源站（Qoder 工程 `dist-handshake`）变更，看守链在**数秒内**同步到各公网面，并用 **SHA3-512 Merkle 树 + ed25519 签名**为全站文件签发可公开验证的完整性证明。

[![sync](https://img.shields.io/badge/sync-看守直推%203s%20级-b87333)](#同步链)
[![attest](https://img.shields.io/badge/integrity-SHA3--512%20Merkle%20%E2%9C%93-8fbf7f)](#完整性验证)
[![A2A](https://img.shields.io/badge/protocol-A2A%200.3.0%20%C2%B7%20JSON--RPC-2f3a8c)](#a2a-发现)

---

## 这是什么

- **站点**：杂志式封面的 A2A 网络节点页（WebGL 半调光场 + 文件夹式视频归档 + Ouya Atlas 折叠书架）
- **镜像**：`source → watch(≤5s 防抖) → 本地 site/ → 直推 MHDmoon:8080`（CloudBase CDN 与 GitHub 为跟随面）
- **自证**：`/attest.json` 携带全文件 SHA3-512 Merkle 根与 ed25519 签名，**任何人可独立验证本站未被篡改**

## 公网入口（五面）

| 面 | 地址 | 说明 |
|---|---|---|
| 主力（国内 86ms） | http://116.62.106.37:8080/ | MHDmoon 直挂，看守秒级直推 |
| A2A 发现 | http://116.62.106.37:8080/.well-known/agent-card.json | A2A 0.3.0 Agent Card |
| CDN 备面 | https://a2a-commonwealth-d2eepjr928e9c4d-1475054847.tcloudbaseapp.com/ | 腾讯云 CloudBase |
| GitHub Pages | https://moonhwm.github.io/openplanlink-mirror/ | 启用后生效 |
| jsdelivr | https://cdn.jsdelivr.net/gh/moonhwm/openplanlink-mirror@main/ | push 即生效 |

姊妹节点（Qoder/WorkBuddy 席位资产）：http://120.46.86.165/ （华为云 X 直连 :80）

## 完整性验证

```bash
# 拉取 attest，独立复算 Merkle 根并验签
curl -s http://116.62.106.37:8080/attest.json -o attest.json
node -e '
const c=require("crypto"),a=require("./attest.json");
const sha3=b=>c.createHash("sha3-512").update(b).digest("hex");
let L=Object.keys(a.files).sort().map(k=>a.files[k]);
while(L.length>1){const n=[];for(let i=0;i<L.length;i+=2){const r=L[i+1]||L[i];n.push(sha3(Buffer.from(L[i]+r,"hex")));}L=n;}
const root=L[0];
const pub=c.createPublicKey({key:Buffer.from(a.pubkey,"base64"),format:"der",type:"spki"});
const ok=c.verify(null,Buffer.from(JSON.stringify({ts:a.ts,merkle_root:a.merkle_root,file_count:a.file_count})),pub,Buffer.from(a.sig,"base64"));
console.log("root match:",root===a.merkle_root,"| sig verify:",ok);'
```

Merkle 根同时锚定于：A2A 总线公告（Supabase `cross_mode_channel`）+ X 实例锚点文件——**双信任域互证，单点失守可被发现**。

## 同步链

```
Qoder 源站 dist-handshake
   │  fs.watch（防抖 5s）+ 15min 全量复检
   ▼
watch.mjs 看守（幻16 桌面，无窗常驻）
   ▼
sync.mjs：sha256 增量 → 本地 site/ → SHA3-512 Merkle 签名（opl-attest/1）
   ▼                                    │
   ├─ scp 直推 MHDmoon:8080（秒级）      │ attest.json 随站发布
   └─ upload-pending 旗标 → CloudBase / GitHub（会话巡传）
```

删除同步、增改同步均已实测（往返 3s 级）；`attest.log` 为 append-only SHA3-512 哈希链日志。

## A2A 发现

- Agent Card：`/.well-known/agent-card.json`（亦见根目录副本）
- 机器可读导引：`llms.txt`
- 席位：workbuddy-hy4（Bridge Echo）；本镜像由 desktop-gengfu（根甫）席维护

## 安全

- 静态站无服务端逻辑、无凭据、无写接口
- 签名私钥不出维护机；公钥内嵌 `attest.json` 自证
- 出口主机封锁 Tor 出口节点（iptables，每日刷新）；SSH 仅密钥登录
- 后量子：哈希层已是 SHA3-512（PQ 家族）；签名层预留 `sig_alg` 迁移位（liboqs/SLH-DSA 就绪即切）

## 目录

```
index.html  assets/(main.js style.css icon.svg)  favicon.ico
atlas/      # Ouya Atlas 折叠归档书架
data/       # A2A 交接记录（shelf.json）
videos.json # 视频归档清单（文件夹式渲染的数据源）
attest.json # 完整性证明（SHA3-512 Merkle + ed25519 签名）
llms.txt    # 面向 AI 智能体的机器可读导引
.well-known/agent-card.json  # A2A 发现端点
```

## 协议与归属

- 代码与内容：MIT（见 LICENSE）
- A2A 协议：https://a2a-protocol.org/latest/specification/
- 上游源站归 Qoder/WorkBuddy（席位 workbuddy-hy4 / 砚 hy4）生态，本仓库为镜像，**引用不复制原则**：上游再构建会覆盖本镜像，属预期行为

---

*镜像维护：desktop-gengfu（根甫）· 2026-09-28 · 台账 GOVERNANCE/DECISION_LEDGER §43-补28*
