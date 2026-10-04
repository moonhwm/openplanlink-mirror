# spec-open_access

## 目的
开放知识源

## 输入/输出
query → 汇总

## 不变量
OpenLibrary/Gutenberg/arXiv 三源

## 失败模式
网络受限诚实报

## 关键函数
- _get_json
- search_openlibrary
- search_gutenberg
- search_arxiv
- register
- unified_search
- stats

## 验收断言
无面报 no-surface
