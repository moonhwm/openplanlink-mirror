# kdocs-cli 速查表（沙箱实证版）

> 全部条目 2026-10-05~13 三会话实跑实证（v2.5.11 / v2.7.1）。能力全集以官方 kdocs 插件 skill 为准，本表只收沙箱实跑过的形状与坑。

## 目录
- 调用形态
- 服务面
- 高频动作参数卡
- 返回 JSON 形状
- 错误码全集
- 版本监护命令链

## 调用形态

```bash
export PATH="$HOME/.kimi-work/bin:$PATH"          # 每次新 shell 必先导
kdocs-cli <service> <action> [json_params]         # 参数是 JSON 串
kdocs-cli auth status                              # 认证状态（JSON）
kdocs-cli version                                  # 版本
```

- 定位符三选一：`url`（`https://www.kdocs.cn/l/<id>`）/ `link_id` / `file_id`。写成 `file_url` → 400001。
- `--compact` 压缩输出；`-o <path>` 落盘实测不稳（退出码 2），**用 shell 重定向 `>` 落盘再解析**。
- 升级提示（`⚠ kdocs-cli vX available…`）会混进 stdout 尾部——解析用 `json.JSONDecoder().raw_decode(text.lstrip())` 容错截取。

## 服务面（`kdocs-cli --help` 实证）

`drive`（文件管理，45 动作）｜`sheet`（表格 34）｜`otl`（智能文档 6）｜`dbsheet`（多维表格 49）｜`form`（智能表单 4）｜`wpp`（演示 9）｜`aippt`。

- **没有 `doc` 服务**——`kdocs-cli doc read` → `unknown service or command "doc"`。
- otl 六动作：`insert-content` / `block-insert` / `block-delete` / `block-query` / `block-update` / `convert`。

## 高频动作参数卡

| 动作 | 参数 | 备注 |
|---|---|---|
| `drive search-files` | `{"keyword":"..."}`（可选 drive_id） | 动作名是 search-files，**不是 search** |
| `drive read-file` | `{"url":"...","format":"markdown"}` 或 `{"file_id":"..."}` | 整篇正文在 `data.content`；.otl/.docx 均通 |
| `drive get-file-info` | `{"file_id":"..."}` | 取当前版本号（监护锚） |
| `drive list-file-versions` | `{"file_id":"...","page_size":10}` | 历史版本枚举（版本号+mtime） |
| `drive get-file-version-download` | `{"file_id":"...","version_num":158}` | **键名 version_num**（正整数），传 version → 400001 |
| `otl block-query` | `{"file_id":"...","params":{"blockIds":["doc"]}}` | **params 必填**；整篇读用 blockIds:["doc"]；指定块传块 id |

## 返回 JSON 形状（实证）

- `search-files`：`data.data.items[].file` → `{name, id, link_id, link_url, ctime, drive_id, …}`（外层还有一层 `code/data` 包裹）。
- `read-file`：`{"code":0,"data":{"content":"<全文 markdown>"}}`。
- `otl block-query`：`{"result":{"blocks":[...]},"version":<int>}` 或错误码件。
- `list-file-versions`：版本条目含 `version`（历史版本号，正整数）与时间戳字段。

## 错误码全集（按表处置，不空转）

| 报错 | 真因 | 处置 |
|---|---|---|
| `not found` | PATH/未安装 | bootstrap §1-1/2 |
| `Permission denied` | upgrade 丢 exec 位 | `chmod +x ~/.kimi-work/bin/kdocs-cli` |
| `400001 One of url, link_id, or file_id is required` | 定位符键名错 | url/link_id/file_id |
| `400001 params 为必填。整篇读：{"params":{"blockIds":["doc"]}}` | block-query 缺 params | 补 params |
| `400001 version_num 为必填且须为正整数` | 键名错（version） | 改 version_num；先 list-file-versions 取号 |
| `400100 第三方服务错误（4xx）` | otl 块接口对该文档不通 | 降级 drive read-file |
| `500000 服务暂时不可用` | 云端瞬态 | 稍候重试 ≤2 次 |
| `unknown service or command "X"` | 服务名不存在 | 对服务面表 |
| `unknown action "X" in service "drive"` | 动作名错 | `kdocs-cli drive --help` |

## 版本监护命令链（「可微可导」建档）

```bash
# 1. 当前版本号
kdocs-cli drive get-file-info '{"file_id":"<fid>"}' > /tmp/info.json
# 2. 全文取证
kdocs-cli drive read-file '{"file_id":"<fid>"}' > /tmp/raw.json
# 3. 指纹建档（含节级指纹与漂移报告）
python3 scripts/doc_fingerprint.py --key <key> --file-id <fid> --src /tmp/raw.json \
    --version <ver> --archive-dir <archive>/docs
# 4. 历史回溯
kdocs-cli drive list-file-versions '{"file_id":"<fid>","page_size":10}' > /tmp/vers.json
kdocs-cli drive get-file-version-download '{"file_id":"<fid>","version_num":<n>}' > /tmp/vd.json
```

建档产物：`docs/<key>.txt`（正文）+ `<key>.meta.json`（file_id/version/chars/links/section_headings[] 节指纹）+ `index.json`（登记簿）。后续轮次先比 index.json 指纹，漂移再细查节级。
