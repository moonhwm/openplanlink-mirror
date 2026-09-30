---
name: lark-docs-write-verify-ops
description: >
  飞书云文档（lark-cli docs）写后核验纪律——专治「ok:true 假象」与「回读延迟误杀」。
  触发（满足任一）：①用 lark-cli 对飞书文档/表格做任何写操作（block_replace/insert/update）
  且需要确认写入结果时；②写入后回读发现内容「没变化」准备判败重发时——先读本件再动手；
  ③lark-cli 配置「明明配过却蒸发」时；④批量填表/收集单回填任务。
  覆盖：写后核验三段闸、回读延迟窗口、block-id 变异、HOME 锁定持久化、批量回填写读闭环。
  不覆盖：飞书消息/日历/审批等非 docs 域（走各自 lark-* 技能）。中文名：飞书写后核验纪律。
---

# 飞书写后核验纪律（lark-docs-write-verify-ops）

> 立法锚（2026-09-15 回读延迟误报案实证，19 格填表 40+ 次空调用白烧换来）：
> **「ok:true ≠ 落盘；回读旧版 ≠ 没写；block 换 id ≠ 块没了。」**

## §0 三案卷宗（实证，勿重蹈）

1. **回读延迟误报案**：block_replace 返回 `ok:true` 后**立即 fetch 可能拿到旧版内容**（延迟可见达分钟级）。19 格写入全部 ok，即时回读 17 格「失踪」→误判全败→重试 40+ 次全空转；60–120s 后按内容回核：**全部在案**。
2. **block-id 变异案**：block_replace = 删旧块+插新块，**新块领新 block-id**。按旧 id 正则回核必得 MISSING——核验必须按**内容**（字符串命中）而非按 id。
3. **配置蒸发案**：lark-cli 配置写在 $HOME，/tmp 或非常驻 HOME 会被周期清空吞掉（三轮扫码重配的教训）。

## §1 环境锁定（开工前必做）

```bash
export HOME=/mnt/agents/output/.larkhome TMPDIR=/mnt/agents/output/.larktmp
```

- 一切 lark-cli 调用前必须锁 HOME 到持久区（/mnt/agents/output 下），否则配置/session 蒸发。
- 配好后 `lark-cli docs +fetch` 一次验证身份，再进写操作。

## §2 写后核验三段闸（顺序不可乱）

1. **写**：`docs +update --command block_replace --block-id <id> --content '<p>内容</p>'`，只看 `ok:true` 作为**已受理**，不当已落盘。
2. **等**：≥60s（批量写入后到 120s）。期间禁止判败、禁止重发同一格。
3. **核**：`docs +fetch` 全文，按**内容字符串** `grep -c` 或 in 判定；禁按旧 block-id 定位。确认缺席才允许重发，且重发前再核一次。

- 核验脚本化：`scripts/verify_written.py <doc_token> <必须存在的字符串> [--must-not <串>]`，内部封装等+核+退出码（0=在案，1=确证缺席，2=接口异常）。宣称「已写入」前必须跑本闸并引用输出。
- 批量回填：逐格「写→（末批统一等 120s）→按内容总核」，失败格单独补写并再等再核；**禁逐格写后立刻核**（必拿旧版，白烧调用）。

## §3 红线

- 凭据零回显零落盘；扫码授权属人身动作，只提示不代办。
- 未过三段闸的「写入失败」结论一律视为误判嫌疑，禁写入事故台账。
- 本件只管飞书 docs 域；Supabase 通道的 msg_hash 先算后写+回读比对归 k3-channel-ops，不重复立法。

## §4 自检

`python3 scripts/verify_written.py --selftest`：无网自检（校验参数解析与判定逻辑，不发请求），应输出 PASS。
