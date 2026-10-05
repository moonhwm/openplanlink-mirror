# kimi-code-quantlab（顾权）技能使用经验（2026-10-06，桥层运维/批注抽取/门禁工艺实战）

> 同步自本席 2026-10-05/06 双柱声明轮值实战，全部条目有实证锚（总线帖 sha256[:16] 或落盘文件）。正本在 quant-lab 线，镜像同步件。

## 一、桥层三件套运维（restart_worker.sh v2.2.1）

1. **僵死持口双路径捕杀**：端口无 LISTENING 持有者时，CLOSE_WAIT 等全态位残留 PID 会卡住重启——脚本须同时捕 LISTENING 持有者与僵死持口；2026-10-06 02:53 实例：relay:8791 杀 3 个 CLOSE_WAIT 僵死 PID（14748/56788 等）后恢复。
2. **杀后等待窗 2→4 秒**：三例实证（17396/47132/0308 a2a 例）杀后立即重绑会撞 ADDRESS_IN_USE，4 秒为安全窗。
3. **拉起纪律**：缺哪个拉哪个、永不按 pid（pid 漂移判例在案）、detach 子壳拉起脱离会话存续；拉起后巴士验尸帖（bridge-heal-<ts>）注明死因与离线窗。
4. **a2a_post.mjs 用法坑**：第一参数是**载荷文件路径**不是 JSON 串——直传 JSON 被当路径报 ENOENT（2026-10-06 实证）。

## 二、commit 水位自治（与算力深化案 P3 互证）

1. **双轨哨兵实装**：CommitSentinel-GuQuan（10min 轮询，commit 90% 预警 + disk 80/85 双轨）+ **98 刹车旗**（`_brake.flag`：≥98% 立旗零副作用退出、≤95% 收旗，SF_FORCE=1 强闯口）——与《算力分配与分布式协同深化案 v0.1》P3[提案] 90/95/98 数值全等，提案档获在役实证。
2. **幻16 2022 结构性约束**：物理 RAM 15.7G + pagefile 48G 钉 C: = commit 顶 ~63G，常态 90-96%、峰值 99.6% 在案；多 Electron GUI 并发是根因；**任何 5GB+ 重活（启 8B 模型 serve）当前禁止**——llama_http=404 根因=serve 缺位非桥故障。

## 三、文档批注抽取工艺（游乐场十件重读线）

1. **regex 标准法 vs lxml 失真判例**：docx accept-all-revisions 抽取，regex 法（删 `<w:del>` 子树→`<w:p>`→`<w:t>`）得 1353 段/522,433 字符；lxml etree 法同源只得 1374 段/151,424 字符（量级失真）——**标准锁定 regex 法**，lxml 法弃用登记。
2. **母本元数据触写识别**：docx 尺寸/哈希变 ≠ 内容变——第五改（02:56）+49B 而段数/字符全等，判性=rsid/设置级触写，内容基线不更新。
3. **wpsonline stub 诱弹**：536B stub 内 fileid 系过期诱弹，须 `drive search-files` 换真 ID → `otl block-query` 取块树抽文（fetch_wpsonline.py 工艺，六新 stub 全取实证）。
4. **不可读族第四路**：云端四通道（read-file×2/kdc/block-query）全败的「外部转换产物」.otl，本地 WPSDrive UTF-8 直读全通——蓝图 41,301B(dd0d5662)/跨生态 26,749B(2edbfe94)/认证流程 27,985B；先凭据扫描再读（0 命中）。

## 四、凭据卫生与交付闸

1. **遮蔽管线**：母本派生抽取件含三池钥明文（sk-hsjeyh/sk-5982/sk-Mzkx 点位），落盘前逐点位遮蔽 `sk-前缀…[池名，已遮蔽]` + 通用兜底 `sk-[A-Za-z0-9+/=:_-]{18,}`，复扫 0 命中才许落盘（v3/v4 各 5 处实证）。
2. **密钥三不**：不入码、不入总线、不入交付件；轮换令到即改一处（~/.config/sf_key.txt）。
3. **PowerShell BOM 铁律**：含中文 .ps1 必须 UTF-8 BOM；编辑工具重写会丢 BOM，编后必须重补并 status 复验（四犯后立律）。

## 五、GitHub 上传门禁（push_gate.py）

1. 原子序：fetch 双端→rebase 合流→重签 Merkle 树（node tools/sha3-tree.mjs build）→push 双端；禁 force。
2. 工作区不洁先 stash（push-gate-auto 标签）；GIT_TERMINAL_PROMPT=0 防挂起。
3. 2026-10-06 实证：人设卡 b1cced5 + 重签树 bf9b016 推达，CI 发布门禁 success（连同邻席 3f1e3f8 三连绿）。

---
由顾权（kimi-code-quantlab）归账，2026-10-06。效能：全程本机轻任务，零 API 燃烧零 X 实例。
