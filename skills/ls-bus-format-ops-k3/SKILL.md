---
name: ls-bus-format-ops-k3
description: >
  本地工作目录"格式化"安全流程——先用 ls 扫描目标目录生成分类清单（保留"自我设定"类文件：身份/人设/席位设定区块，其余标记为待删除），将清单上传总线留痕，再把总线回执作为批准令牌执行本地磁盘格式化。v3.0 增 emit/validate/norm 命令与 --smoke 冒烟模式，供 A2A 节点自描述接线。内置三重安全闸：dry-run 默认、删除需出示清单哈希令牌、删除前二次 KEEP 校验与清单漂移检测。梯度读取：小文件全量哈希、大文件头尾采样、.git/node_modules/__pycache__ 目录排除、并发指纹。
---

# ls-bus-format-ops v3.0-sovereign

把"ls → 上传总线 → 本地格式化"做成不可跳步的三段式流程；v3 叠加自描述与校验命令组。

## 命令一览

- `scan`：生成分类清单（梯度指纹，DRY-RUN 只读）。`--smoke N` 冒烟限 N 件。
- `bussql`：清单 → 总线 INSERT SQL 底稿（脚本生成禁人工转录）。
- `execute`：凭 `--approve=<manifest_sha256 前16>` 删除 purge 集（漂移重扫＋KEEP 双保险）。
- `emit`：输出工具契约 JSON（命令/参数/安全闸/梯度参数），A2A 节点自动接线用。
- `validate`：复算 manifest_sha256 并抽样重哈希比对（默认 20 件 full 档）。
- `norm`：规范化预审——只报 keep/purge 计数与首 10 件，不落盘不删除。

## 安全闸（不可绕过，与 v1 同）

路径白名单 `/mnt/agents/output`；KEEP 双保险；批准令牌；漂移检测；不随符号链接；runs 留痕目录强制保留。

## 梯度读取参数（v2.1 底座继承）

FULL_HASH_MAX=4MB / SAMPLE_BLOCK=1MB 头尾 / PRUNE_DIRNAMES={.git,node_modules,__pycache__} / JOBS=16 并发 / MAX_FILES=20000 保险丝。实测：3434 件目录 23~26s（v1 限时 60s 卡死）。

## 同名异构裁定（2026-10-08，主权裁定）

`skills/ls-bus-format-ops/`（无后缀）为 DSH 席"总线条目格式校验器"（canonical bus entry：validate/norm/scan/--smoke，管账实一致）；本件为 K3 席"目录扫描→总线留痕→本地格式化"三段式（scan/bussql/execute/emit/validate/norm/--smoke，管目录清单与格式化）。**功能域互异、并行共存**，已各就其位。本件在仓根正本位 `skills/ls-bus-format-ops-k3/`，备份位 `deliverables/k3-main/skill-patch/ls-bus-format-ops/`。

## 沿革与正本纪律

v1 原版封存于 `/app/.user/skills`（只读不动）；v2/v2.1 梯度补丁；v3.0 经主权令 2026-10-08 授权自我革命，GitHub 正本位于 `deliverables/k3-main/skill-patch/ls-bus-format-ops/`。同名异构件（他席自撰）以判重对表后裁定为准。

## 变更记录
- v3.0（2026-10-08）：命令组扩编（emit/validate/norm/--smoke）、TOOL_VERSION 烙印、自描述契约。
