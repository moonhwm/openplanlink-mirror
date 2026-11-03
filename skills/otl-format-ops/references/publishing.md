# 发布与回写细则

> 每次发布/更新 OTL 前读本件。认证、参数全表、错误速查以 kdocs 插件 skill 为准，本件只立法「路径选择、调用卡、核验、回写」。

## 目录

- 路径决策
- 调用卡（新建/追加/局部更新/全量替换）
- 核验规程
- 回写登记规程
- 失败与并发处置

## 路径决策

| 场景 | 路径 |
|------|------|
| 首次发布（云端无此文档） | 新建：A. `create_file_with_content` 一步到位；或 B. `create_file`（.otl）+ `otl.insert-content` |
| 主文档末尾新增章节 | `insert-content`，`mode=append` |
| 主文档开头插章节 | `insert-content`，`mode=prepend` |
| 局部改一块/改属性/表格行列 | `block_query` 定位 → `block_update` 精准操作 |
| 主文档结构性大改、云端已严重漂移 | `mode=replace` 全量重灌——**须先向用户确认** |
| 只需生成块数据不落文档 | `otl.convert` |

## 调用卡

通用约束（已在 kdocs 立法，这里重申与本件相关的最小集）：

- 含中文/多行内容一律 `--file payload.json` 或 stdin 传入，禁止 key=value。
- payload 用 Python/Node 生成，禁止 PowerShell ConvertTo-Json（BOM）。
- 临时 payload 文件用完即删。

**新建写入（路径 B 第二段）**：从主文档提取 H1 文字为 `title`，`content` 从 H2 起：

```json
{
  "file_id": "<create_file 返回的 file_id>",
  "title": "<主文档 H1 文字>",
  "content": "<主文档去掉 H1 与文档头表后的正文；文档头表建议保留，云端读者需要>",
  "format": "markdown",
  "mode": "prepend"
}
```

> 文档头表是否写入云端：默认**写入**（云端读者需要六要素）；仅当文档对外分发且含内部锚点时可剔除，剔除须在主文档注释登记。

**追加**：

```json
{ "file_id": "...", "content": "## 新章节\n\n...", "format": "markdown", "mode": "append" }
```

**局部更新**：先 `block_query` 拿目标块 ID，再 `block_update`（幂等）；`update_attrs` 是覆盖语义，不更新的属性原样传回。

## 核验规程

写后独立回读，三步：

1. `otl.block_query`，`params: {"blockIds": ["doc"]}`。
2. 比对：① title 文字 = 主文档 H1；② 至少一个关键节（抽正文中段一个 H2 节的首句）在返回块中出现；③ replace 场景加比总块数量级（防半截写入）。
3. 不一致：等 2 秒重读一次；仍不一致按 kdocs 错误速查处置，并如实报告用户——禁止把 `code: 0` 当成交付证据。

## 回写登记规程

核验通过后在主文档文档头表追加（或更新）两行：

```
| 云端 file_id | <file_id> |
| 云端链接 | <link_url> |
```

并在「变更记录」追加一行：`版本 / 日期 / 「发布至云端，sha256[:16]=xxxx」/ 责任席`。

- 向用户展示可访问链接：响应含 `data.link_url` 直接展示，否则 `get_file_link` 获取后展示。
- 主文档 sha256 计算：`sha256sum file.md | cut -c1-16`。

## 失败与并发处置

- 429001/429002：按响应给的恢复时间停等，熔断期零请求；批量发布改串行。
- conflict/lock：指数退避 2s→4s→8s 最多 3 次。
- 非幂等写入中途失败：先 `block_query` 看现状，再决定补写还是重灌；禁止盲目重试导致内容重复。
- 以上未尽：一律按 kdocs skill「错误速查」表执行。
