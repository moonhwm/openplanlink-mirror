---
name: forget-mechanism-ops
description: >
  人类遗忘机制统一熔铸件——婴儿式动态上下文管理的一体化执行面：遗忘执行（ls-bus-format 三段式：scan 分类→bussql 留痕→execute 令牌删除）、极致压缩打包（ultra_pack：zstd/xz/brotli 选型+tar 固体+字典训练）、搬移回链瘦身（link_bridge：数据落大盘、原路径留符号链接）、机制纪律（references/forgetting-mechanism-v0.1：三层记忆/遗忘判据/压缩无所谓定理/KEEP 入包律/BRK 断链范式）。触发（满足任一）：①「遗忘机制」「婴儿式记忆」「上下文动态管理」「全面格式化」「备份后删除」「打包压缩」「极致压缩」「junction 移植/搬移回链」或等价表述（含语音变体，不纠正用户、映射意图）；②对话上下文水位管理、主动落盘+主动遗忘周期启动；③output/工作目录瘦身、冷层归档、KEEP 件入包；④「不看看有没有 loop-dual-pillar-ops/long-table-harvest-ops/ultra-compress-ops/link-bridge-ops」类生态位普查诉求——先查在册再立法。不覆盖：会话级压缩病总防治（归 semantic-oncology-ops）、长表收割完整性（归 long-table-harvest-ops）、卡级滑窗（归 loop-dual-pillar-ops）、四件合一伞路由（归 quad-ops-umbrella）。中文名：遗忘机制熔铸件。English triggers: human forgetting mechanism, infant-style context management, unified memory lifecycle ops.
metadata:
  version: "1.0.0"
---

# forget-mechanism-ops（人类遗忘机制统一熔铸件）

> 立法锚：**「不记得细节，记得索引；重要的先落地，落地的不怕忘；忘了不可耻，找不到才可耻。」**
> 熔铸来源（执行面四件，全文随包；宽域四件，指针回链不复制）。

## §0 定位

统一、扁平化、大体积熔铸件：把「人类遗忘机制 v0.1」的纪律与三件执行器熔为单一可安装单元。
**凡立法先查在册**——机制纪律全文在 `references/forgetting-mechanism-v0.1.md`，执行器脚本在 `scripts/`。

## §1 三执行面路由（一句话定域）

| 意图症状 | 执行面 | 脚本 |
|---|---|---|
| 「全面格式化」「备份后删除」「ls 清单」「scan/purge」 | 遗忘执行（三段式） | `scripts/ls_bus_format.py` |
| 「极致压缩」「压榨压缩包」「zstd/xz/brotli」「压缩到最小」 | 极致打包 | `scripts/ultra_pack.py`（选型详见 `references/backends.md`） |
| 「junction」「搬移回链」「数据迁大盘留链接」「瘦身」 | 搬移回链 | `scripts/link_bridge.py` |
| 「遗忘机制」「婴儿式」「上下文管理」「KEEP 入包」「断链」 | 机制纪律 | 读本 SKILL.md + `references/forgetting-mechanism-v0.1.md` |

歧义 → 列候选域由用户一句话定夺，不硬路由。

## §2 遗忘执行面（ls-bus-format v2.1）

```bash
cd <skill_dir>/scripts
# 1) scan（只读 dry-run；自动产出 keep_archive_<ts>.tar.gz——KEEP 件入包铁律）
python3 ls_bus_format.py scan --target-dir /mnt/agents/output [--keep-file extra.txt] [--max-files N]
# 2) bussql（总线留痕底稿；清单超万行必 --digest）
python3 ls_bus_format.py bussql --manifest <manifest.json> [--digest]
# 3) execute（须令牌+零漂移+KEEP 双保险；并发侦测 CONCURRENT-WARN 在案）
python3 ls_bus_format.py execute --manifest <manifest.json> --approve <manifest_sha256前16>
```

硬闸：目标须在 /mnt/agents/output 内；KEEP 双保险；不随符号链接；runs 留痕目录强制保留；
梯度读取（>1MB 采样指纹）+ EAGAIN 退避重试；**KEEP 件自动入 keep_archive tar 包**（2026-10-08 台账原件丢失事故固化）。

## §3 极致打包面（ultra_pack）

```bash
python3 scripts/ultra_pack.py --help   # zstd ultra 22 / xz -9e / brotli q11 选型、tar 固体、字典训练
```
冷层归档算法选型归此面；「何时打包、打什么」归机制纪律（KEEP 入包律、水位闸）。A2A 挂载辅助：`a2a_mount.py`、`madao_watch.py`。

## §4 搬移回链面（link_bridge）

```bash
python3 scripts/link_bridge.py --help  # 搬移+回链：数据落大盘、原路径留符号链接
```
铁律：链接不是副本——目标失则链死；删链不伤目标，删目标即真空；迁必登记、查必全量。

## §5 生态位回链表（宽域四件，指针不复制）

| 本体 | 生态位 | 调用时机 |
|---|---|---|
| semantic-oncology-ops | 会话级压缩病总防治（退化救活/癌症分期/空调用空转识别） | 会话退化症状出现时直调 |
| long-table-harvest-ops | 长表收割完整性 + §3.5 压缩余量遥测 | 长表收割/余量预算派单时直调 |
| loop-dual-pillar-ops §3.4 | 卡级滑窗（激进递归注入取最近 3 卡） | 审议递归注入面 |
| quad-ops-umbrella | 四件合一伞（知识/双柱/会裁/OTL 路由） | 跨四域意图时直调 |

冲突仲裁：本件蒸馏与本体有出入 → 本体全文为准。

## §6 机制核心（详见 references/forgetting-mechanism-v0.1.md）

- **三层记忆**：热（对话视图任裁剪）/温（台账·runs·停点卡，永不删）/冷（upload tar·WPS 云夹，只增不删）
- **压缩无所谓定理**：重要信息先落盘再进对话，压缩只裁视图裁不掉留痕
- **遗忘判据双列** + 三触发闸（水位 60%/事件收口/夜间峰谷窗）
- **KEEP 入包律** / **BRK 断链声明范式** / **索引完备律 D4**（引用必带路径+哈希前16）
- 验收：D1 温层存续可验 / D2 压缩后 1 轮恢复 / D3 KEEP 入包率 100% / D4 无裸引 / D5 断链后续链连续

## §7 红线继承（不改写、不豁免、不稀释）

凭据铁律（不落明文/不入包/疑似泄露即重置）、写类动作逐次批准、append-only 台账纠错不改历史、
诚实留白（不可凭记忆重建则立 BRK 声明为锚续链，永不伪造中间历史）。

## 变更

- **v1.0.0（2026-10-08）**：熔铸创刊。执行面四件全文随包（ls_bus_format v2.1 / ultra_pack / a2a_mount / madao_watch / link_bridge + 机制 v0.1 + backends + keep 样例）；宽域四件指针回链。源自用户「打包熔铸为统一扁平化大体积技能」令。
