# ls-bus-format-ops v2.1 梯度读取补丁说明（2026-10-07）

## 卡死定谳（三层根因）

1. **无目录排除**：v1 scan 对目标目录全量 os.walk，含 `.git`（1168 件 / 19MB）与 `node_modules`（102MB）——格式化本不应触的对象库与依赖仓全被纳入哈希。
2. **无大小分档**：逐文件全量 sha256，20 件 >1MB 文件计 133MB（rolldown 二进制为主）全量读。
3. **无并发摊销**：/mnt/agents/output 为 FUSE 挂载，per-open 延迟约 35ms，3432 次串行 open ≈ 120s，表象即"卡死"；`manifest.md` 亦无行数截断。

实测对照：v1 限时 60s 未完成（卡死复现）；v2（梯度+排除）119s；v2.1（+16 线程并发）**23.3s**，提速 5.1 倍。

## 处置（v2.1，原体只读不动，补丁件落 _skill_patch）

- **梯度三档**：档一 stat 先行（walk 内联）；档二 ≤4MB 全量 sha256；档三 >4MB 头尾各 1MB 采样 + size 合成指纹，`hash_mode: full|sampled|pruned-dir` 逐件标注。
- **目录排除**：默认跳过 `.git` / `node_modules` / `__pycache__`，目录本身作 `pruned-dir` 条目入册（keep 类，永不入 purge）；`--no-prune-dirs` 可关闭。
- **并发指纹**：`--jobs`（默认 16）ThreadPoolExecutor 摊销 FUSE open 延迟；entries 排序保持确定性输出。
- **保险丝与截断**：`--max-files`（默认 20000）超限即拒；`--md-max-rows`（默认 2000）manifest.md 截断并指向 json。
- **三重安全闸不变**：execute 漂移检测按 hash_mode 各自复核；KEEP 双保险、批准令牌、不随符号链接、runs 强制保留悉仍其旧。

## 一致性核验

v2 与 v2.1 同目录跑批：purge 集 3302 件全同，哈希一致 3301/3302——唯一差异件为本补丁脚本自身（两版迭代间自指，在理非缺陷）。

## 另两技能排查结论

- fusion-cast-ops：md5 仅作用于字符串（qa 行/描述），无目录遍历，无同类问题。
- skill-forge-pipeline（verify_edit.py）：无 walk/全量哈希面，无同类问题。

## 使用方式

```bash
python3 _skill_patch/ls-bus-format-ops/scripts/ls_bus_format.py scan \
    --target-dir /mnt/agents/output [--jobs 16] [--max-files 20000] [--md-max-rows 2000]
```

bussql / execute 用法与三重闸同 v1。执行属高危写操作，仍须批准令牌与当轮批准纪律。
