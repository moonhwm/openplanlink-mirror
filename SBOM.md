# SBOM 初登 · openplanlink-mirror（2026-10-03 顾权席，法务 B 项「权属+SBOM 初登」落实）

## 一、权属确认
本库全部内容系机主（moonhwm/欧阳宏俊）直属 A2A 席位产出：desktop-gengfu（镜像维护）、cairn-dsh（石敢当）、shou-cang（守藏）、k3-main、guquan（顾权）、workbuddy-hy4/Qoder（上游源站生态）。无外部自然人/法人贡献记录（git log 全量可溯）。协议变更授权闭环成立。

## 二、组件清单（初登）
| 组件 | 类型 | 来源 | 许可 | 备注 |
|---|---|---|---|---|
| index.html/assets/atlas/videos.json/llms.txt | 静态站 | 自有（desktop-gengfu） | AGPL-3.0 | 无服务端逻辑、无凭据 |
| tools/（sha3-tree.mjs、verify*.mjs/py、xcheck 等） | 验证工具链 | 自有（k3 系/根甫） | AGPL-3.0 | 含 174/174 NSS/Wycheproof 向量 |
| sha3_tree/（TREE-01/02/03 manifest+records+verify_tree.py） | 完整性锚 | 自有（k3-main） | AGPL-3.0 | 密钥自留不入库 |
| build_hmac_tree.py + deliverables/**/hmac_attest.json | attest 链 | 自有（石敢当/顾权） | AGPL-3.0 | v1 64B 钥（QODER-05） |
| skills/（生态技能库镜像） | 技能件 | 自有（机主技能库） | AGPL-3.0 | 随 89/97 号令镜像上传，敏感面见 §四 |
| skills/shoucang-pptx-craft（SKILL.md+EXPERIENCE.md） | 技能件+经验 | 自有（守藏 DF-DOC-01） | AGPL-3.0 | 2026-10-06 投放，投放前扫描门 PASS（零高熵零命中） |
| deliverables/（蓝图/方案/报告） | 文档 | 自有各席 | CC BY-SA 4.0 | 含凭据件处置在案（§四） |
| LICENSE / LICENSE.MIT / NOTICE / NOTICE-LICENSE | 许可档 | 自有 | — | AGPL-3.0 现行 |
| README badges（img.shields.io） | 外链引用 | 第三方服务 | 运行时外链不内嵌 | 仅图片引用 |
| A2A 协议规范引用 | 标准引用 | a2a-protocol.org | 归原权利人 | 引用不复制 |
| AGPL-3.0 正文（LICENSE） | 协议文本 | gnu.org (FSF) | FSF 许可 verbatim 分发 | 官方文本逐字 |

## 三、第三方依赖结论
无打包级第三方代码依赖（无 node_modules/vendor）；外部引用均为超链接或运行时外链，不构成再分发。SSPL 层组件：现不存于本库（NOTICE §4 在案）。

## 四、敏感面登记
1. deliverables/20261003 曾含 ima 凭据之 OTL 快照——GH013 拦截后未入库（顾权台账 18:4x）。
2. attest.json（Ed25519）历史失效，仅作故障证据，验证器 fail closed（README §完整性验证在案）。
3. `_tmp_probe.yml`/`_wf_probe.yml` 探针文件两件——建议归属席评估清理（登记不代删）。
4. skills/ 镜像件经两轮密钥扫描 0 命中（石敢当 e89bfba 前扫+本席抽扫）。
5. skills/shoucang-pptx-craft 投放件（守藏席 2026-10-06）：SKILL.md 高熵候选 0、EXPERIENCE.md 高熵候选 0，已登记指纹命中 0，投放扫描门 PASS。

—— 顾权（kimi-code-quantlab）· 初登件，复审归法务马含章队列 ——
