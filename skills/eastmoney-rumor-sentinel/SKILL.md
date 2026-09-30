---
name: eastmoney-rumor-sentinel
description: "[项目技能] 东财传闻哨兵——东方财富股吧公开面的传闻采集、词面三档判级与白话呈报。触发（满足任一）：①用户说「东财」「东方财富」「股吧」「传闻哨兵」「扫一遍股吧」「吧里在传什么」「市场情绪」或等价表述（含语音变体如「东财传闻」「古吧」，不纠正用户、映射意图）；②需要周期性监测某只股票东财股吧新增传闻帖时；③《白话市场一周》周五取材需要传闻面素材时；④股吧出现红/黄档词面信号需要升级核验（转 rumor-chain-verifier）时。覆盖：股吧列表页采集（scripts/eastmoney_sentinel.py，2026-09-05 实测底座 v1.0→v2.0）、红黄蓝词面判级、跨日去重台账、白话报告渲染、信源三级表与升级核验流程（references/source-tiers.md）、观察名单（assets/watchlist.json）。不覆盖：真伪定断（rumor-chain-verifier 的活）、证据链登记（evidence-chain-verifier 的活）、快讯/资讯源（能力占位未实测）、任何涨跌预测与评级。中文名：东财传闻哨兵。English triggers: eastmoney guba rumor watch, stock forum sentiment scan, rumor keyword triage."
metadata:
  version: "1.1.0"
---

# 东财传闻哨兵（eastmoney-rumor-sentinel）

<!-- v1.0.0（2026-09-08）：创刊。底座=guba_scan.py v1.0（2026-09-05 J105 实测固化，股吧列表页纯 HTTP 直读全 SPA 骨架），技能化演进 v2.0：多代码观察名单/红黄蓝词面判级/跨日 seen 索引/白话报告。创刊日实网首扫 300059：80 帖全量判级（黄 2/蓝 78），SELF-TEST 三夹具 PASS。 -->
<!-- v1.1.0（2026-09-09，机主宽口径令「弄吧」落地）：采集器 v2.1.0 正文扩版——①帖正文直解（spike 实证：帖页内嵌 post_article JSON，含正文/发布时间/阅读/评论/点赞/post_guba 权威标的；财富号 //caifuhao 异构站标 skipped 不抓）②正文抓取只走红/黄档信号帖（成本纪律，蓝档不抓）③跨股吧标的 cross_flag（post_guba.code≠列表吧代码即标记）④一级信源通道成文：xhcj 公告检索本地脚本口径（references/source-tiers.md §二）。SELF-TEST 五夹具 PASS；实网三扫 new=0 去重再证。 -->

## §0 定位与红线

- 本件是**采集判官**不是**判真伪官**：只做「公开面有什么帖、词面像不像传闻」；真伪定断转 rumor-chain-verifier，登记转 evidence-chain-verifier。
- **避险守则全继承**（对父场景不可降级）：首行免责锚；无目标价、无评级、不预测涨跌点位；概念翻白话；涉「内幕/听说」必示警；量化结果先白话后附来源日期。
- 金融数据与采集台账严格本地化不出项目；报告外发先过 release-gate-audit。

## §1 三拍流程

1. **采集判级**：`python3 scripts/eastmoney_sentinel.py --codes 300059[,...] [--tag 标签] [--out 采集目录] [--report 报告.md]`。观察名单默认读 assets/watchlist.json（名单修订须机主口令）；产出 <code>_yyyymmdd.jsonl 台账 + <code>_seen.txt 跨日索引 + 可选 md 报告。
2. **呈报**：md 报告按红/黄/蓝分档，首行免责锚，文末白话提示；全名单零新增如实报零，不制造「有料」假象。
3. **留痕**：每次扫描的 summary（fetched/new/error）入当轮留痕；失败如实登记不中断其他代码。

## §2 判级纪律（词面≠真伪）

- 红=监管/造假/退市/立案/内幕声称类词；黄=重组/中标/减持/业绩等基本面词；蓝=无信号词。词表见脚本 RED_WORDS/YELLOW_WORDS，修订规程见 [references/source-tiers.md](references/source-tiers.md) 第四节。
- 红/黄档需核验→升级流程（references/source-tiers.md 第二节）：拆链→一级信源取证（交易所公告/新华财经 plugin）→查无实据如实标注，禁编造补齐。

## §3 联挂与频度

- **《白话市场一周》取材源**：周五收盘周报（周报驳日报已裁决）的传闻面素材由本件供给；红色档必含示警段。
- **频度纪律**：手工跑不受限；定时化=cron 新建须机主显式口令（冻结期纪律）；静态名单不配高频 cron（cron-task-forge 口径）。
- **能力占位声明**：东财快讯/资讯第二源未实测不进技能，标记为可扩展位；xhcj-news plugin 在场即作一级信源通道，缺席显式声明降级为交易所官网直查。

## §4 诚实声明

- 采集面仅限股吧列表页公开面；帖子正文/评论不深挖（未实测），需要时先实测再扩版。
- 判级误报必然存在，不追罪；报告只呈词面信号，禁止把黄色档写成「公司确有此事」。
- 版本三段制；与 guba_scan.py v1.0 的台账契约保持兼容（同目录同格式追加）。
