# spec-cd_attest

## 目的
CD 交付证明构建器：对给定根目录构建 SHA3-512 默克尔树，产出机器可读证明、一页纸状态与自包含静态状态页。

## 输入/输出
- 输入：`--root`（默认仓库根）、可选 `--key-file` / `--key-env`（64 字节密钥 hex）、`--key-id`
- 输出：`--out`（JSON 证明）、`--status`（Markdown 一页纸）、`--html`（自包含静态页）
- 排除：`.git`、`node_modules`、`__pycache__`、`.venv`、以及自身产物 `attest-cd.json` / `STATUS.md`

## 不变量
- 字节契约与 `tools/SHA3_TREE.md`、`tools/build_opl_tree.py` 一致：叶 = SHA3-512(0x00‖u32be(pathlen)‖path‖u64be(size)‖sha3_512(content))；父 = SHA3-512(0x01‖left‖right)，奇数复制右项
- `file_count == len(files)`（自洽）
- **无密钥亦可运行**：`hmac_sha3_512` 记 null，绝不伪造 MAC
- 只读仓库；不改动任何被证明文件

## 失败模式
- 根目录不存在 → 退出码 2
- `--key-env` 值非 hex → 回落为「未签名」而非报错
- 静态页模板中的 `%` 与 `%`-格式化冲突（历史缺陷）→ 已改 `@@TOKEN@@` 占位符替换

## 关键函数
- sha3
- leaf
- merkle_root
- git_head
- main

## 验收断言
- `file_count` 与 `files` 数组长度相等
- 生成后 `--html` 无外部引用、无 `<script>`、标签配对、无残留占位符
- 同输入重复运行的默克尔根一致（除 `generated_at` 与 MAC 外）
