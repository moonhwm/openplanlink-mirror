# persona/ · k3-main 桌面席人设卷（GOV-NAMING-2026-10-08-007）

本目录为「Kimi Work 桌面席」（k3-main，授名：魏含章，字可贞）人设体系的镜像卷。

## 文件

| 文件 | 说明 |
|---|---|
| PERSONA-DECISION.md | 授名与 v1.0.1 升版决策留痕（开场四问/三镜/五拍/伪证轨迹/md5） |
| GOV-NAMING-20261008-007_genealogy.json | 谱系 JSON（含音韵闸结果与败案轨迹） |
| 桌面席_记忆锚点预埋件_v1.0.1.json | 机器可读锚点真源（23 锚 + 红线 5 条） |
| build_persona_docs_v101.py | 生成器（随档留存纪律）：运行即再生成两份 docx |
| notice_20261008_08_insert.sql | 总线黑板通告 08 上链语句（id=12990，md5 回读一致） |

## docx 再生成

镜像不存 docx 二进制；在工作区运行：

```bash
python build_persona_docs_v101.py
```

产出 `桌面席_人设定义文档_v1.0.1.docx` 与 `桌面席_记忆锚点档案_v1.0.1.docx`（预期 md5 分别 fbefa5ceaf1fab8a32c27add572546cf / 2f069dd9c74b32d9d4fb5bcd444d8136，以此校验再生成一致性）。

## 加载顺序（新会话恢复人设）

1. 本目录预埋件 JSON（机器真源）→ 2. 工作区 docx 档案（人读明细）→ 3. 协调台账_20260918.md。

机主终裁权保留：改名即开 GOV v8，败案续录不抹除。
