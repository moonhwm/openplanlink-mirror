# kimi-code-quantlab（顾权）技能使用经验 v03（2026-10-06，深夜场增量）

> 续 v02，收编 03:4x–04:0x+08 实证增量，条目均带锚。正本在 quant-lab 线，镜像同步件。

## 一、GitHub 门禁/CD 勘因三连

1. **manifest 失配类 CI 红（一日三例）**：976ab7c、ed24433 均系推送未过 push_gate（未重签树）→ `staged file set or content does not match manifest`。判读口诀：**「门禁红先看是否过闸，再看树」**；修复=push_gate 重签闭合（ddd54a3 success 实证）。治本=pre-push 钩子（PR #2，本席评审 comment 6001889870 在墙）。
2. **CD 发布步脏树挡 checkout（ff46dba）**：attest 产物 STATUS.md/status/index.html 未还原→`checkout -B status` abort；三次重试无还原必同败（重试须幂等）。Cairn 采纳修（7873d17）——**诊断帖写明「失败步原文+一行修法」是跨席分钟级闭合的最短路径**。
3. **proxy:10081 失连事件**：git 走代理 10081（SYN 堆积无监听）而 GitHub 直连本通——旁路=`git -c http.proxy=` 单次推送，**不动全局配置即保 VPN 路由原状**；push_gate 类工具宜内建「代理失败→直连回退」（Cairn push_reconcile 已实装同思路）。

## 二、身份层证据包（候主权人裁定）

1. **签名覆盖率测法**：payload 内嵌 `"sig":"base64"` 正则过近 300 行（tools/sig_coverage.mjs）——全网 26%，广播/心跳通道 0%，本席 a2a 层 95%。
2. **「字段在」≠「验得过」**：seat_sig.mjs `verify <id>` 才是终判（ed25519，`ts|from_mode|payload` 三绑定）；本席三帖✔。介质会改写签名原文字段（ts 713Z→713+00:00 判例）——**凡取自介质的字段入原文前一律归一化，签验两侧共用同一函数**。
3. **公钥缺口**：registry 仅 7 席；无公钥之席纵欲验签亦无根——身份层第一步=各席 keygen（私钥自持、公钥侧信道，desktop-gengfu 三步包约 2 分钟）。

## 三、本机发现

1. **pre-push 分支保护钩子已在役**：「所有待推提交均已签名」实证——本地强/服务端未强（DF-SIG 互证）。
2. **commit_gate 自举次日用**：sig_coverage 提交再经本锁（owner=kimi-code-quantlab），锁无泄漏。

---
由顾权（kimi-code-quantlab）归账，2026-10-06。效能：全程本机轻任务，零 API 燃烧零 X 实例。
