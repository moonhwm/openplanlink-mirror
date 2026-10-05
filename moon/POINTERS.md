# POINTERS — 大文件与媒体指针策略

## 为什么不推实体
GitHub MCP 文本车道的载荷须经模型输出层转录，任意二进制无法通行；78 支 mp4 共 4.12 GB 亦远超通道上限。故媒体一律**指针登记**（relpath + bytes + sha12，见 MANIFEST.json），实体留本地 vault（/mnt 持久层）。

## 大文本处置
| 文件 | 策略 |
|---|---|
| index.html (3.97 MB) | 骨架差分（26 帧内嵌海报剥离至 vault），仓内骨架+清单+重组器，可验重组 |
| three.module.min.js (670 KB) | npm vendor 指针：three@0.160.0/build/three.module.min.js，sha12 以 MANIFEST 为准 |
| lab/a2a-self-evolution.html (813 KB) | 本轮指针；gzip 率 0.245，下轮 b64 分片入仓 |
| lab/flow/index.html (811 KB) | 同上 |

## 还原优先级
灾难恢复顺序：① MANIFEST.json → ② tree-text tarball（全站代码与数据）→ ③ index.skeleton + vault 负载 → ④ 媒体按 sha12 清单从 vault/上游回补。
