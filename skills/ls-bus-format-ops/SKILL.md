---
name: ls-bus-format-ops
description: >
  总线格式运维——为 A2A 网络之"总线"（各席共享之件目录）建立**统一条目格式**并作**机械校验**：
  一行一 JSON 之 canonical entry（seq/id/ts/seat/kind/path/bytes/sha256/refs），id 取 sha256 前 16 位（同内容同 id ⇒ 天然去重键），
  seq 严格递增无跳号（与事件链同法）；并提供 校验（validate：必填／十六进制／id 规则／seq 连续性／kind 合法）、
  规范化（norm：去重＋重排；默认只报不改）、漂移扫描（scan：有账无件／有件无账）与自检（--smoke）。
  解决三类总线病：①同件异记（各席记法不同，无法对账）②重复入总（同内容多条目，信噪比下降）③有件无账/有账无件（盘与索引漂移，审计断链）。
  触发（满足任一）：用户说「总线格式」「总线条目」「入总」「bus.jsonl」「总线对账」「有件无账」「有账无件」「总线漂移」
  「总线信噪比」「ls-bus-format-ops」或等价表述。
  红线：不删任何内容件（只动索引）；空范围即「未测」exit 2（不以空为通过）；写操作须显式指定；零凭据零 MAC 零 IP。
  三账分立：本器之 bus.jsonl 为「件之账」；ledger/frontier_ledger.jsonl 为「决策台账」；ops/ops_event.jsonl 为「事件链」——勿混。
---

# ls-bus-format-ops（总线格式运维）

> 立法定位：本件为**「全权授权…全面自我革命与初始化」下之首版**（2026-10-08）。此前该技能**四方核验皆缺**（GitHub 正本无、本席无、他席无引用、无下载源）⇒ 今由本席**初始化并落 GitHub 唯一正本**。

## 一、为什么需要它（三类总线病）

| 病 | 形态 | 后果 |
|---|---|---|
| **同件异记** | 同一件在不同席记为不同路径/名/无摘要 | **无法跨席对账** |
| **重复入总** | 同内容多条目 | **总线信噪比下降**（令条关切项） |
| **有件无账 / 有账无件** | 盘与索引漂移 | **审计追溯断链** |

## 二、条目格式（canonical bus entry）

```json
{"seq": 1, "id": "<sha256 前 16 位>", "ts": "2026-10-08 13:14:02 +0800",
 "seat": "a2a-node-local", "kind": "artifact|pack|note|skill|other",
 "path": "<相对总线根>", "bytes": 1196, "sha256": "<64hex>", "refs": []}
```

- **必填**：`seq / id / ts / seat / kind / path / bytes / sha256`；
- **id 规则**：`sha256` 前 16 位 ⇒ **同内容同 id**（幂等入总之据）；
- **seq 规则**：自 1 起**严格递增且无跳号**（与事件链同法）；
- **refs**：可选引用（如关联件号）。

## 三、用法

```bash
python scripts/lsbus_format_ops.py emit     --bus <总线根> --path <件> [--kind artifact|pack|note|skill] [--seat <席>] [--refs a,b]
python scripts/lsbus_format_ops.py validate <bus.jsonl>            # 0 通过／1 有缺陷（逐行报）／2 未测（空）
python scripts/lsbus_format_ops.py norm     <bus.jsonl> [--apply]  # 去重＋重排；默认只报不改
python scripts/lsbus_format_ops.py scan     --bus <总线根>         # 漂移：有账无件／有件无账
python scripts/lsbus_format_ops.py --smoke                         # 自检全链
```

## 四、退出码语义（★与 Cairn 术语闸同法）

| 码 | 义 |
|---|---|
| **0** | 通过（validate：0 缺陷；scan：无"有账无件"） |
| **1** | **有缺陷**（validate 报 INVALID；scan 报有账无件 ⇒ 索引指向不存在之件） |
| **2** | **未测**（总线为空／根不存在 ⇒ **不以"空"冒充"通过"**） |

## 五、自检（`--smoke` 五项，全过方可交付）

1. `emit` 两件 ⇒ 0；**重复 emit 同件 ⇒ 幂等跳过**（条数不变）；
2. `validate` ⇒ 0；
3. **负断言**：人为改 `seq` 造跳号 ⇒ `validate` 必报 **1**（★能报错才算检出）；
4. `norm` ⇒ 0；
5. **负断言**：空总线 ⇒ `validate` 必报 **2**（未测）。

## 六、首版实测（本席件）

- **`--smoke` PASS**；
- **总线实建**：`A2A共同体_共享交换区/bus/` ⇒ 3 条目（`cairn-context-20261008.manifest.json` id `876cfdc13f27644f`／`cairn-context-20261008.upack` id `b1570c7d35cec4f5`／`RETIRED_REGISTER.md` id `785f9e28beebc64b`）；
- **`validate` VERDICT=VALID（0 缺陷）**；**`scan`：有账无件 0 ／有件无账 0（零漂移）**。

## 七、自限与未决（照实登记）

| # | 项 |
|---|---|
| 1 | **本器只管"格式与账实一致"**，**不判内容对错、不判他席记法优劣**； |
| 2 | **`norm --apply` 会重排 seq** ⇒ 与他席既有条目混用时**须先协商**（本席默认只报不改）； |
| 3 | **尚未接入**：签名（每条目可加 `sig` 字段）／哈希链（seq 与前条 hash 相连）⇒ **候裁后增**（承则二十二：先证必要）； |
| 4 | **他席总线格式未知** ⇒ **首版仅为本席与共享总线之口径**，**不主张为全网标准**。 |

---

## 八、同名双实现登记（2026-10-08 唯一正本同步合并 · Moon 席）

> 本节由 Moon 席（pi-orchestrator@zcode）于 20261008 唯一正本同步时追加：本席同轮独立产出同名技能之另一实现 `scripts/lsbus.py`（目录清单 → biz.ls 信封格式化），与上文 a2a-node-local 席首版（bus.jsonl 条目格式校验器 `lsbus_format_ops.py` 等三脚本）**同名异器**。rebase add/add 冲突依「非破坏合并、双方内容全保留」纪律处置：上文首版全文原样为基底，本节并存登记本席变体全文（原 SKILL.md 正文逐字内嵌、标题降一级；原 frontmatter description 引于 8.1）。两实现脚本文件名不冲突、各自独立可用。同名技能是否改名或归并，候主权人裁定。
> 本席变体指纹：lsbus.py sha3_16 `6f49b56c763ec0bb`（与票据 TICKET-20261008-MOON-01 全等）；本席原单文件版 SKILL.md sha3_16 `c19024a14f4af047`（合并后本文件指纹不再等于该值，以票据+本节文字为溯源锚）。
> 署名：Moon（pi-orchestrator@zcode · SHA3 root a69ccb57…）· Ticket: TICKET-20261008-MOON-01

### 8.1 Moon 席变体 · lsbus.py（目录清单总线格式化）

原 frontmatter description（原样引用）：把本地目录清单格式化为 A2A 总线 biz.ls 信封（kind/四元标签/entries 带 sha256 指纹），用于跨席资产盘点、迁移前后快照比对与总线可读目录广播。当需要「ls 结果直接进总线」「上传前列指纹清单」「桌面/工作区快照基线」时使用。

### ls-bus-format-ops · 目录清单总线格式化

> **正本口径**：本技能以 GitHub `moonhwm/openplanlink-mirror` 为**唯一正本**；工作区内文件为同步副本。
> 修改一律先改正本、push 后再向各席分发，禁止就地分叉。
> **署名**：Moon（pi-orchestrator@zcode · SHA3 root a69ccb57…）

#### 解决什么问题

`ls` 的输出是给人看的，总线要的是结构化、可核验、可留痕的资产清单。本技能把一次目录扫描直接产出
`biz.ls` 信封 JSON：每条 entry 带相对路径、字节数、sha256 前 16 位指纹——既是**上传前的申报单**，
也是**迁移/桌面整理前后的快照基线**（与配置基线比对，不符项进处置清单推 SOC 复核）。

#### 五规范落点

| 规范 | 落点 |
|---|---|
| 自动下载依赖 | 零依赖，纯 Python 3 标准库（hashlib/json/os/argparse/tempfile） |
| 热插拔 | 单文件脚本，`--dir/--out/--depth` 三参数即可嵌入任意 workflow 席位 |
| 可压缩 | 输出为紧凑 JSON，可直接交 `\ultra-compress-ops` 二次压缩后入总线（≤8000 字符限制下先裁剪 entries） |
| 指针化映射 | entries 的 `path` 可改写为 A 盘 `A:\OPL_A2A\…` 映射址，实现跨席统一寻址 |
| 分布式调度 | 输出即总线信封，`\link-bridge-ops` 可直接接力登记指针；多席并发扫描后按 `dir` 归并 |

#### 用法

```bash
python scripts/lsbus.py --dir burn/otl --depth 2 --out upload/ls_20261008.json
python scripts/lsbus.py --selftest     # 期望 SELFTEST PASS
```

输出示例：

```json
{"kind":"biz.ls","priority":"normal","ttl":86400,"delivery":"store",
 "reply_to":"Moon(pi-orchestrator@zcode)",
 "content":{"dir":"…","count":2,"entries":[{"path":"a.md","bytes":5,"sha256_16":"2cf24dba5fb0a30e"}]}}
```

#### 安全闸（Mimosa 对齐）

1. **输入层**：任何上跳分量（`os.pardir`）与空字节在拼接之前即拒；
2. **归一层**：`normpath + abspath` 后再比对，杜绝符号链接式绕过与重复分隔符；
3. **白名单层**：目标必须落在 `burn/ upload/ opensrc/ A:\OPL_A2A\ %TEMP% ~/WPSDrive` 之一；
4. **只读语义**：扫描过程不写扫描目标；`--out` 同样过白名单；
5. **指纹截断**：sha256 取前 16 位供比对，单文件读取上限 4 MiB（大文件只作存在性与前缀指纹登记，避免长尾拖慢）。

#### 已知边界（如实登记）

- 不跟随符号链接目标做二次校验：junction（A 盘映射）会被 `os.walk` 视为目录，跨盘扫描时 `bytes` 统计可能重复计入同一物理文件——跨盘盘点须以 `dir` 分区分别出单，不在单次调用内混算；
- `bytes=-1 / sha256_16=null` 表示 `stat` 或读取失败（占用、权限、稀疏文件），是**未测得**而非 0 字节；
- 不做递归删除、不做任何写回扫描目标的操作。

#### 与其它技能的接力

`\context-pruner`（裁剪 entries 至总线字符上限）→ 本技能（出信封）→ `\ultra-compress-ops`（压缩正文）→ `\link-bridge-ops`（登记指针到共享交换区 / esc 台账）。
