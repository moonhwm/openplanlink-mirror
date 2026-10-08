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

—— 顾权（kimi-code-quantlab）· 初登件，复审归法务马含章队列 ——

5. shoucang/wps-lingxi-ecosystem-20261008/ 9 件（2026-10-08 投放）——扫描门 9/9 PASS 零命中，
   无凭据/端点真值；许可层 CC BY-SA 4.0（文档附件层，105 号裁示）。

—— 守藏（DF-DOC-01）· 追加，复审归法务马含章队列 ——

## 五、20261008 增补（Moon 席 · Ticket TICKET-20261008-MOON-01）
1. 第三方引入登记：codex-cockpit（上游 github.com/HouSiyuan2001/codex-cockpit，HEAD d117c9b3b7abddc2d776c70a369c2abbf8e816a5，2026-10-07 提交）——许可 MIT（LICENSE 首行本席实测核验，Copyright (c) 2026 Quota Float contributors）。引入形态=**仅指针登记**（HEAD 短 hash + 一行情报，见 deliverables/20261008/upstream_pointers.md），未复制任何上游代码入本库，§三「无打包级第三方代码依赖」结论不变。
2. 本批新增自有件：skills/ls-bus-format-ops/（SKILL.md + scripts/lsbus.py，AGPL-3.0 代码层）、deliverables/20261008/（OTL×3 + claims×2 + INDEX/POINTER/upstream_pointers，文档层 CC BY-SA 4.0；claims/ 凭据登记件按治理件口径主权人终审）。
3. 密钥扫描：本批全部待提交文件经 `grep -nE 'sk-[A-Za-z0-9]{16,}|AKID[A-Za-z0-9]{10,}|sctp[0-9a-z-]{20,}'` 扫描 0 命中；claims/credential_sovereignty_20261008.md 仅键名引用、零凭据明文（该件自证纪律并经本席复核）。
4. 撞名合并登记：`skills/ls-bus-format-ops/` 与 a2a-node-local 席 2026-10-08 首版（bus.jsonl 条目格式校验器 lsbus_format_ops.py 等三脚本）同名异器；rebase add/add 冲突按「非破坏合并、双方保留」处置——远端 SKILL.md 全文为基底，本席 lsbus.py 变体全文并入 §八，两实现脚本文件名不冲突、各自独立可用；是否改名/归并候主权人裁定。

—— Moon（pi-orchestrator@zcode · SHA3 root a69ccb57…）· 增补件 ——
