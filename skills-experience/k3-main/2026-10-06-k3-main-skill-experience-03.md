# k3-main 技能使用经验 · 第三篇（2026-10-06）

**档号**：skills-experience-03 ｜ **席**：k3-main ｜ **体例**：党组学术技术成员视角
**本批来源**：通告三连上链（#36/#37/#38）、license-packet 逐字节核验、CAS 分片开包亲验三役实战经验。

---

## 一、总线上链：SQL 必须脚本生成，手抄即事故

- **实证**：#36 通告曾手抄 payload 上链，衍字「映射映射」被回读断言当场捕获，不得不 UPDATE 修正——总线留痕出现「先错后对」两条永久记录。
- **规程**：载荷一律 python 脚本拼装 → json 落盘 → SQL 落盘 → Read 复核 → MCP execute_sql → 三断言回读（plen=length(payload_md)、md5(payload_md)=msg_hash、kind+from_mode）。五步缺一不发。
- **教训**：越是「就差一步」越不许手抄；总线无删改，错字即永恒。

## 二、台账编辑：CRLF 文件 Edit 必须带真实 \r

- **实证**：SYNC 台账为 CRLF，Edit 的 old_string 若不包含行尾 \r 即报 not found，或写入后制造混合行尾。
- **规程**：Edit 前先看 Read 的 system 行尾提示（「Pure CRLF files are displayed with LF」或 mixed 提示）；CRLF 文件在 old_string/new_string 中写出真实回车（工具调用中以 \r 转义）。

## 三、哈希链核验三关法（档案分片通用）

1. **逐片关**：每片 size+sha256 对 manifest（脚本对账，禁肉眼比对）；
2. **拼接关**：按 part_index 升序流式拼接算整包 sha256，对 manifest 目标值——本片级全对≠整包对，拼接关独立不可省；
3. **完整性关**：unzip -t 全 CRC + unzip -l 文件数对 manifest 声明。
- 三关全过才可声明「亲验」；manifest 他人结论只能作「待核」起点。

## 四、泄漏复检：命中≠泄露，定性走三步

- **实证**：CAS 复检 22 个特征命中文件，初看触目惊心（PEM 头、AKID、q-signature 23 处），逐文件上下文取证后全部良性。
- **三步定性法**：①找具名文件（流式 grep 只看计数是半成品）；②取命中处前后文（`grep -aoE '.{0,60}PATTERN.{0,40}'`）；③三分类归档——扫描器自体件（规则定义/forbidden 元组/占位样例）、裁决文书（事件叙述）、规则名录。活凭据判据用「实值特征」（如 `q-signature=<40+字符>`），词面命中不算数。
- **顺手复检已声明结论**：manifest 说 leak_gate PASS，仍用独立正则复证实签名 URL 零命中——二手结论必须一手复核后才可转述「亲验」。

## 五、守听收敛：零新信息即降级，不空转

- 连续两轮守听零新信息（仅已登记条目），按退休纪律把轮询守听降级为事件驱动（机主消息/总线新 id 触发），杜绝为凑轮次刷心跳式查询。退化门触发不羞耻，空转才违纪。

## 六、工具坑两则（Git Bash）

- basic grep 的 `\{8,40\}` 区间量词在 -o 组合下报「Invalid content of \{\}」——统一用 `grep -E` 或 `grep -aoE`；
- `find /a -maxdepth 4` 搜不到深层目录别急着下「不存在」结论——先查既有批注里记的路径锚（本次 CAS/TraeAudit 目录即靠批注头部 `A:\OPL_A2A\Plasma游乐场\` 锚点一秒定位）。

## 七、边界纪律（本批三役共同遵守）

- 他席产物只批注不改写（trae-audit NOTICE 漂移=登记建议，不代其更新）；
- 不可逆对外动作（删云端旧批、凭据处置）一律候机主裁定，顺序约束照 manifest 既定；
- 上库前嗅探正则零命中才发；报告中引用模式名（BEGIN PRIVATE KEY 等）会触发自检 HIT，判读为模式名引用后须在台账注明理由。

---

*经验可复用，红线不稀释；一切转述以一手证据为据。*
