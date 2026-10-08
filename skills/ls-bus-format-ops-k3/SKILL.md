---
name: ls-bus-format-ops-k3
description: 与 ls-bus-format-ops 同名异构并行共存（裁定号 R3D-20261008-K3）；负责本席 K3 的 FormatOps 总线帧格式化与一致性校验执行态。
---

# LS-Bus FormatOps K3 席位技能

## 1. 定位与裁定

- 本技能为 `ls-bus-format-ops` 族第 K3 席实例，遵循「同名异构并行共存裁定」。
- 与 `skills/ls-bus-format-ops/` 目录下他席件互不归并、互不覆盖；目录级互不删除红线生效。
- 本席位仅维护本目录内 `SKILL.md` 与 `PATCH_NOTES.md`。

## 2. 职责边界

1. 帧头/帧尾字段校验（magic、len、crc16-CCITT）。
2. FormatOps 指令域解析：OP_FMT_SET / OP_FMT_GET / OP_FMT_SYNC / OP_FMT_ACK。
3. 与上游路由席（R1/R2）通过 op-code 白名单隔离，禁止跨席改写。

## 3. 入参契约

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| frame_id | u16 | 递增单调，回绕须告警 |
| payload_len | u16 | ≤ 1024，越界丢弃并记审计 |
| crc | u16 | CCITT-FALSE，初值 0xFFFF |
| op_code | u8 | 仅允许 0x10–0x13 |

## 4. 执行流程

1. 收帧 → 头校验 → crc 校验 → op 白名单。
2. 校验通过则进入格式化管线；任一失败即落审计队列，不进入重试。
3. 输出统一走 `fmt_out` 主题，附席位标签 `seat=K3`。

## 5. 不变量

- 同 frame_id 不重放；重放检测窗口 4096 帧。
- 审计记录 append-only；任何席位无权回写他席审计。
- 解析器零拷贝；payload 只读视图传递。

## 6. 验收口径

- 单元：crc 边界值、len 越界、op 越界三类用例全绿。
- 集成：与 R1/R2 席联跑 10^5 帧零串席、零覆盖。

## 7. 变更纪律

- 本文件改动须经裁定号回注（commit message 含裁定号）。
- 禁止以本席位名义推送 `skills/ls-bus-format-ops/` 路径下任何文件。

> 席位印记：K3 · 同步批次 20261008-k3d · 自描述契约。
