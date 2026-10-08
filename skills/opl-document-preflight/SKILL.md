---
name: opl-document-preflight
description: 检查 OpenPlanLink 与 A2A 技术文档的术语、格式证据和许可条款表述，生成带源哈希的位置旁注；用于流转前预检和版本复读。
---

对用户指定的文档先刷新读取，再用 `scripts/preflight.py` 生成旁注报告。按当前平台的 Python 运行方式执行脚本，路径相对于本技能目录；不要假定有当前工作区或第三方库。命令格式：`python scripts/preflight.py --input "源件路径" --output "新报告.json"`，多个源件可重复 `--input`。输出已存在时换新的版本文件名，保留历史记录。

优先解释可复核的结果：源哈希与稳定读取、正文是否真正取得、格式证据、问题位置、规则依据及尚待人工审议项。报告不含命中正文或凭据片段；需要引用上下文时在授权的源件中查看，避免把疑似凭据带到总线或云包。云入口只代表入口；UTF-8 文字稿和 OTL JSON 候选不能据后缀宣称 WPS 原生、权限或历史版本已经保真。

按 [审议口径](references/review-basis.md) 分析脚本的待复核项。术语与范围匹配是提示，结合引文、否定句和所在章节判断；不会自动给项目改许可证、授予身份或产生正式审签。用户要求的机关和学术技术行文视角是表达口径，实际作者与审批身份分别取证。

保持用户已给出的任务范围及授权；技能本身不扩展发送通知、上传、部署或整理其他目录的权限。用户另有明确流转操作时，先按本轮预检报告处理相应材料，再用实际可用接口记录结果。

部署报告分列磁盘安装、脚本实跑、Kimi Code 调用、Kimi Chat 自定义技能加载。没有对应产品运行证据时写待核，不从本地目录或群聊工具推断 Chat 已部署。

结构化 OTL 候选中的文本节点使用 `type: text` 与字符串 `content` 字段；无法读取的节点、正文为空或只有标题时，报告必须保留待复核状态。当前维护版本为 0.3.0，历史包及其报告保留用于复核。

## 监测层（跨轮漂移监控，0.2.0 新增）

除单件预检（`preflight.py`）外，本技能含活体语料跨轮监测链路，三件套均在 `scripts/`、仅标准库：

- `ooxml_meta.py`：核心门（读取、判据码、跨快照比对；`G.run(paths)` 产单轮快照，`G.compare_snapshots` 产首轮比对）。
- `corpus_refresh.py`：参数化驱动。`python scripts/corpus_refresh.py --corpus-dir <语料目录> --evidence-dir <证据目录> --run runN [--prev runM]`；每轮自动捕获 P6 掩码基线，给前轮标签即产比对件（缺字段判 INCOMPARABLE，禁静默回落；DRIFT/TOUCH 二分只认内容键）。
- `p6_custom_probe.py`：掩码基线探针。`python scripts/p6_custom_probe.py --target <docx> --out-dir <目录> --label <轮次>`；custom/core 属性只记名称、值长、值哈希，真值不落盘。

监测结论只绑定被检件哈希；名称集合两侧不齐备时必须拒比，不得以零计数冒充已比对。

## 同稿一致性层（公文类长稿内部口径预检）

`scripts/declaration_consistency.py`——对声明/纲要类长稿做**同稿内部**一致性机检，产出 cred-clean 报告：

    python scripts/declaration_consistency.py <稿路径> [--json 报告] [--threshold 0.60] [--min-segment-len 40]

判据分层：逐字重复（WARN）／包含关系且长度比例 >=0.6（FAIL，口径歧义）／相似度 >=0.9（FAIL，口径歧义）／0.6-0.9（WARN，部分重叠）。退出码 0=PASS/WARN、1=FAIL、2=用法或读取错误。

它解决的实际问题：版本合并会在同一文档内留下重复条款，而重复的两处文本未必一致，执行席位据此会得出互相矛盾的操作口径（实测抓到「目标存储节点清单」一处有一处无）。

三条硬纪律：

- **一切输出经 `mask()`**，凭据形态只报规则名+计数+掩码前缀，绝不回显真值；该性质由常驻测试断言，不靠自觉。
- **覆盖缺口须披露**：因长度门槛未参与比对的段对计入 `skipped_short_pairs` 并升为 WARN，不得以零命中冒充「已比对无差异」。
- **门必须能失败**：`scripts/test_declaration_consistency.py`（16 项）逐层自证 FAIL/WARN/PASS 三条路径均可达，含假阳性回归（独立成行的短 URL 被长段落包含不得判歧义）。
