# A2A 治理总索引（INDEX）

**编制席**: 审计局 · 档案席（ZCode） | **编制时刻**: 2026-09-30 夜 | **算法**: SHA3-512，取前 32 位十六进制
**路径约定**: 相对路径以工作区根（`C:/Users/欧阳宏俊/.zcode/workspace/default`）为基准；指纹均为 python hashlib 读文件现算，禁手填。

## 一、三章程（全网强制现役）

| 名称 | 相对路径 | SHA3-512 前 32 位 | 一句话定位 |
|---|---|---|---|
| AUDIT_BUREAU_v1 | `burn/governance/AUDIT_BUREAU_v1.md` | `77b2f3ffaf2da7a66f20edd6dd033c06` | A2A 联合审计局章程——esc.trace 运维留痕、互审义务、局席例会与额度守护的全网总纲 |
| EXPERIENCE_DISCIPLINE_v1 | `burn/governance/EXPERIENCE_DISCIPLINE_v1.md` | `5a5e82c3d4721bab84ac7d6a5e04f340` | 经验固化与播报纪律——坑/因/解/证四段条目化、esc.exp 总线播报义务及首两卷经验汇编（含 #11-20 第二批） |
| COMMS_FINE_MANAGEMENT_v1 | `burn/governance/COMMS_FINE_MANAGEMENT_v1.md` | `be4828d5b85c08aac535ed43fdbb14e0` | 通讯精细化管理规范——心跳四级/信息四元标签/任务六态/身份三层绑定/设定版本 ACK 五类字段级约束 |

## 二、2026-09-30 关键交付

| 名称 | 相对路径 | SHA3-512 前 32 位 | 一句话定位 |
|---|---|---|---|
| M5P2_REPORT.md | `burn/umc-supply/M5P2_REPORT.md` | `30a05fc084f4f14a758bba2515219da0` | M5+ 二期红蓝演练报告——五层防御栈对 15 条固定重放集的拦/漏终判与一期基线复算 |
| GPT_HANDOFF_20260930_v2.md | `burn/gpt-handoff/GPT_HANDOFF_20260930_v2.md` | `e5aa754abbfed6b908a9fc08e1617eae` | GPT 席执行交接书 v2——A2A×RAG 成熟方案、五线通道实测事实与治理体系并档的任务基线 |
| DAILY_REPORT_20260930.md | `burn/governance/daily/DAILY_REPORT_20260930.md` | `9d11d026bf90083f8f0959abf65a9018` | 审计局 2026-09-30 日耗对账单——Moon 席四台账汇总、心跳/任务 ACK 口径与跨席报送状态 |

## 三、指纹核验方法（复算命令）

```bash
python -c "import hashlib;print(hashlib.sha3_512(open('<相对路径>','rb').read()).hexdigest()[:32])"
```

任一文件修订后，档案席须重算并更新本索引对应指纹；索引自身不入表（自指无意义）。

---
*本索引随治理令存证；增删条目须经审计局，修订须机主终审。*
