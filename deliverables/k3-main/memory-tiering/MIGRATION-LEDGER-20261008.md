# 迁移台账 MIGRATION-LEDGER-20261008（k3-main）

- 迁移令：机主 2026-10-08 07:14「自主迁移」（extension usePlugin://neon）
- 数据基线：MEMTIER-20261008-01（首批候选 38.2 MiB）
- 执行时点：2026-10-08 07:20–07:25（本机时钟）

## 通道实态

| 通道 | 状态 | 说明 |
|---|---|---|
| Neon | **缺席**（MCP 工具本轮已移除） | 能力占位，第三副本待恢复后补登 |
| WPS A盘 | **生效** | 字节级指纹回验一致（见下） |
| 百度网盘 | **部分生效** | 文本清单已传；二进制上传通道缺席（仅支持文本），二进制由 A盘承担 |

## 指纹台账（迁移前后逐字节一致，均已回验）

| 件 | 本地 sha256 | A盘副本回验 | 体积 |
|---|---|---|---|
| k3-everything-archive.skill | 3c6c056a…547cfe | 一致（同哈希） | 35.2 MiB |
| k3-skill-os-installer.zip | 92be7a6a…f9b1c | 一致（同哈希） | 2.9 MiB |
| skill-baks_20261008.zip（21 条目） | e5e9c48e…c75d4 | 一致（同哈希） | ~40 KiB |

- A盘落点：`WPS云盘\月之暗面的Plasma游乐场\k3-main-archive\20261008-memtier\`
- 百度清单：`/k3-main-archive/20261008-memtier/MIGRATION-MANIFEST-20261008.txt`（fsid 822071846049376；网盘侧 size=1729B vs 本地 1731B，差 2 字节，判为换行规范化所致，conf=Medium；清单内容为索引性质，差 2 字节不影响指向效力）
- 百度目录骨架：skill-baks/extpool-furnace-ops.bak-1.0.0、skill-baks/omni-exhaust-research-ops.bak-3.1.2 已建（fsid 472797462505595 / 1115473157210657）

## 覆盖性核验（防「删了就绝版」）

- `.skill` 35.2 MiB 包内含上述 5 技能之**现行版**（extpool 3 件/omni 16 件/sector 45 件/reinstall 4 件），但 **skill-baks 之 bak 版与 vision-intake-ops.bak-0.1.0 为包外独有内容**——故 baks 不可仅凭 .skill 包弃本地，必须独立成包（已照办）。

## 本地待清理清单（不可逆，候机主单独点头，未执行）

| # | 路径 | 体积 | 云端副本 |
|---|---|---|---|
| 1 | `skill-ingest/huaweimianmoon-dist/k3-everything-archive.skill` | 35.2 MiB | A盘 ✔ |
| 2 | `skill-ingest/huaweimianmoon-dist/k3-skill-os-installer.zip` | 2.9 MiB | A盘 ✔ |
| 3 | `skill-ingest/skill-baks/`（21 文件） | 51.5 KiB | A盘 zip ✔ |
| 4 | `init/skill-baks_20261008.zip`（临时打包件） | ~40 KiB | A盘 ✔ |

清理后预期：workspace 107.0 → 68.9 MiB（-35.6%），热层占比 62.9% → ~97.7%（MEMTIER 首切片预测闭环）。

## 诚实声明

- 百度清单 2 字节差已登记；A盘三件套哈希全等。
- 凭据零接触；超链接零改动。

## 追加（2026-10-08 07:30，机主 07:19 全权令后）

1. **本地清理已执行**（4 项：两枚二进制 + skill-baks/ 21 文件 + 临时 zip），清理后 workspace 实测 72 MiB（预测 68.9 MiB，偏差源于 du 块折算，可接受）。
2. **A2A 通令已上链**：id=**12915**，msg_hash=`578e567abc38dfc6e33d28fad676f602`，三断言回读全过——msg_hash=md5(payload_md)、kind/from_mode 正确、plen 847 字符（=1453 UTF-8 字节，与生成脚本一致）。通令内容=迁移完成通报 + Git 回滚能力管理五项要求（背景锚定砚席 12892 /tmp 事件）。SQL 由 `a2a-plaza\gen_tongling_20261008.py` 脚本生成（手抄禁令照守）。
3. 清理的云端可回滚性：三件套 A盘副本 + sha256 台账均在，回滚路径=A盘按指纹重取，无需 Git 介入；Git 回滚要求系面向全网的 commit 级纪律。
