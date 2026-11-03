# 端口底账：学术及专著电子书获取（v1，2026-09-28 实证登记）

命中「学术电子书/专著/文献获取端口」类需求时直接复用本表，只补增量。

## 登记表

| # | 项目 | 类型 | 获取方式 | 关键事实（一手来源） | 合规层 | verified |
|---|---|---|---|---|---|---|
| 1 | iosifache/annas-mcp | MCP server + CLI | 搜索/下载 Anna's Archive 书籍与论文 | 搜索无需 key；下载需捐赠获 JSON API key（`ANNAS_SECRET_KEY`）；自动镜像选择（SLUM 健康探测），默认镜像 annas-archive.gl；可直接挂 MCP 客户端 | 灰色 | true |
| 2 | book-searcher-org/book-searcher | 开源聚合搜索引擎 | Z-Library + LibGen 数据库，经 IPFS cid 下载 | 按书名/作者/出版社/扩展名/语言/ISBN 检索；免登录不设限；有网页镜像群与 Pake 桌面客户端 | 灰色 | true |
| 3 | shiyi-0x7f/o-lib · olib-mobile | 开源客户端 | Z-Library 第三方 Win/Android 客户端 | 内置域名自动更新；需登录自有 Z 账号（免费账号日限 10 本）；全开源无广告 | 灰色 | true |
| 4 | OpenAlex + Unpaywall | 学术 OA 数据库/API | `api.unpaywall.org/v2/{DOI}?email=...`；OpenAlex REST | 2025 年底 Unpaywall 迁入 OpenAlex 同一数据库；DOI 进、OA 记录（is_oa/oa_status/PDF 链接）出；免费 | 合法 | true |
| 5 | Project Gutenberg / Standard Ebooks / Open Library | 公版书库 | 开放下载/API | 公版专著与经典，零版权风险。Gutenberg 腿 API 已核验：Gutendex（gutendex.com）JSON API 文档 2026-10-03 直读——`/books` 列表端点支持 search/languages/copyright/topic/author_year/mime_type/sort 参数，单书 `/books/<id>`，分页 0–32 条/页含 download_count 与 formats 直链；长期用可自托管（GitHub 有码）。Open Library/Standard Ebooks API 页本轮直读被审计拒绝，维持未核验 | 合法 | true（仅 Gutenberg 腿，2026-10-03） |
| 6 | Calibre | 开源管理软件 | 插件化格式转换（30+ 格式） | 本地书库管理中枢：抓取→入库→转换→推送设备 | 合法（工具） | true |

## 接入建议（2026-09-28 定）

1. 合法层优先做成内部 datasource 插件（纯 REST 零成本）。
2. 灰色层首接 annas-mcp（MCP 同构，接入成本最低）；其 key 若启用只存 credentials.env。
3. 合规闸：灰色层仅限个人研究自用，不进对外交付物。
4. 中文补充检索口：鸠摩搜书等聚合站（未开源核验，verified=false）。

## 一手来源

github.com/iosifache/annas-mcp · github.com/book-searcher-org/book-searcher · github.com/shiyi-0x7f/o-lib · support.unpaywall.org（合并说明）· zh.wikipedia.org「安娜的档案」· gutendex.com（Gutenberg JSON API 文档全文，2026-10-03 直读）

## 如实声明

- 灰色层（Anna's Archive / Z-Library / LibGen 系）多法域版权风险明确，本登记仅技术调研，不构成使用建议。
- 各端口连通性与下载流程未实测；实测属使用方下一阶段动作。
