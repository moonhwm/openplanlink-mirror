# opl-document-preflight 技能使用经验 · 首篇（2026-10-06）

**档号**：SKILL-EXP-20261006-DF-DOC-01 ｜ **席**：守藏(DF-DOC-01) ｜ **体例**：党组学术技术成员视角
**本批来源**：OOXML 元数据可溯性门禁第 9~11 轮刷新（`evidence/run_plasma_refresh.py runN prevN`）与 §17/§18 条目级归因。
**关联**：`skills/EXPERIENCE.md` E-18~E-22（同轮沉淀之通用判据）；台账 `evidence/OOXML-GATE-20261005.md` §17~§18。

---

## 一、活体语料：预检结论必须自绑定哈希

- **实证**：受检十件位于 WPS 云盘同步目录，云客户端会在**会话中途重写被检件字节**（已第 7 次观测）。同一"可复现"命令在不同时刻给出不同读数。
- **规程**：预检报告之"可复现"须定义为**字节域**可复现，而非时间域可复现。每份结论必须内嵌其所据被检件之 `sha3_512`；引用他轮结论时一并引其哈希，哈希不同即不得直接比较。
- **反面**：把"文件路径 + 轮次标签"当作同一性依据，会得出跨轮零漂移的假结论。

## 二、云指针存根件与真容器必须分列，不得混计

- **实证**：十件中 **2 件为真 OOXML/zip 容器**，**8 件为 536 B 云指针存根**（`.otl.wpsonline` 等，无中央目录，`is_zip=false`）。存根件 `bytes_a = bytes_b = 536`、两侧 `sha3` 相同、`file_verdict=SAME`。
- **勘误**：上窗口曾记"全部 is_zip=false"，经当轮复核为**错**；正确表述为 2 真容器 / 8 存根。原记录按 append-only 不改，另节勘误。
- **规程**：成员级归因（zip 条目 Δsize／Δcsize）只对真容器适用；对存根件须显式给出 reason「非 zip 容器，成员级归因不适用」，**不得静默跳过**——静默跳过会让"未做"读作"做了且无差异"。

## 三、失败关闭（fail-closed）优先于可读结论，两者须并列引用

- **实证**：`plasma_refresh_run11_vs_run10.json` 顶层因一件缺 `sha3_512` 字段判 `verdict=INCOMPARABLE`、`comparable=False`，reason「声明的比对键或名称集合在两侧不齐备，拒绝比对（禁止静默回落）」；`drift_count`／`same_count`／`total` 为 **null 而非 0**，`per_item=[]`。此为门禁**可失败性第七次实证**。
- **旁路**：同件之 `full_field_check`（shared_names=10、files_with_field_diff=1）与 `drift_touch_split`（content_keys 六键、drift=1、touch=0）仍给出可读结论。
- **口径纪律**：顶层"拒绝比对"与旁路"唯一漂移件为 docx"**必须同时引用**。只引顶层会漏掉已确证的漂移；只引旁路会掩盖一件因缺字段而被拒比的事实。**null ≠ 0**：把 null 读作 0 即把"没比"读作"比过且相同"。

## 四、DRIFT／TOUCH 二分：时戳键变动不计入漂移

- **实证**：`CONTENT_KEYS = {sha3_512, sha3_512_16, sha256, bytes, zip_crc, nonempty_paras_wt}`；`mtime`／`fs_mtime_utc`／`created_*`／`modified_*` 变动归 **TOUCH**。
- **理由**：WPS 云客户端会触碰 mtime 而不改字节，混计即假阳性。
- **规程**：漂移计数只认 content_keys；touch 件须逐条列出并注明"内容键未变，不计入漂移"，既不隐瞒也不夸大。

## 五、条目级算术闭合：把归因从"找到原因"升为"排除别的原因"

- **实证**：run10→run11 Δsize=2324、Δcsize=130、file_delta=130，闭合成立（第四次观测）；run9→run10 为 Δsize 7267／Δcsize 529／容器开销 0。产物件字节差 `artifact_delta = field_len_delta_sum = −1`，无残项。
- **规程**：① 各 zip 成员 Δcsize 之和须等于整件 Δbytes，差值即容器开销增量，非零须解释；② 字段级长度增量之和须等于产物字节差，残差非零即有未识别写入；③ 整数分解类归因（如 rsid 族 Δsize=+104=4×26）须**穷举全部整数解**，再用计数约束排除竞争解，并做**独立残差反解**（本轮 8138÷26=313.0 恰为整数，317−313=4）三路夹逼。
- **教训**：只举一个贡献者不是证明；能穷举且残差为零才是。

## 六、声明型元数据不可作探测器；派生指标的吻合不是证据

- **实证**：`docProps/app.xml` 三轮字节同一，故 `meta_pages=163`／`meta_words=10107` 恒定，而同期 `document.xml` 已增 6631 B 再增 2220 B、`nonempty_paras_wt` +1 ⇒ **WPS 云同步不重算 app.xml**。若以 `meta_words` 恒定作据即得假阴性。
- **实证二**：`inversion ≡ created − modified`，created 恒定时 Δinversion ≡ −Δmodified **必然**成立（三轮 −1710／−2877 精确对应）。此乃定义之推论，不具可证伪性，不得当独立证据；有信息量者是 created 恒定这一经验事实。
- **规程**：变动探测只用计算型／实测型字段；凡"两读数精确吻合"先判其属恒等式还是经验规律。

## 七、待复核项与敏感面

- **未解释项（转前向检验 P6）**：`docProps/custom.xml` 出现 Δsize=0 而 crc32 变（等长替换），**至今无字段级解释**——门禁产物未保留任何 custom 属性值。core.xml 之同类现象已获解释（`modified` 两值均 20 字符）。
- **架构结论**：门禁只留产物不留被检件字节 ⇒ 对历史轮次做字节级 diff **结构上不可能**，"日后再证"不成立；须新增快照切片方可为之，**本轮未实施**。
- **敏感面**：受检 docx 之 `docProps/custom.xml` 携 `hdid`（32 位十六进制设备标识）、`userId`（账号标识）、`ICV`（32 位十六进制 + 固定后缀）；`docProps/core.xml` 携 `dc:creator`／`cp:lastModifiedBy`（用户显示名）。**真值一律不入册、不上总线、不上 GitHub**，只记字段名与掩码形态；该 docx 未经脱敏不得出域。本篇不含上述任何真值，亦不含密钥串、MAC 地址、预签名 URL。

---

*经验可复用，红线不稀释；一切结论以一手证据为据，null 不读作 0，恒等式不读作证据。*
