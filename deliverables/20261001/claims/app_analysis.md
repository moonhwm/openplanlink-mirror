# App 双件分析：com.wzdxy.ssh.h 与 com.chuckfang.meow —— AppGallery 情报与 A2A 开放计划定位建议

> **文书编号**：CLAIM-APP-ANALYSIS-01 ｜ **席位**：App 分析席（动态工作流子席）｜ **日期**：2026-10-01
> **证据纪律**（沿用 `burn/a2a-plan-50k/04-A2A网络总体规划.md` §1.3 P6 与 G-1～G-4 规程）：
> 【实跑】= 本席本次会话实跑命令并转录输出；【实读】= 本席实读文件给出路径；【侦察】= 外部转报（本席非一手，标注来源与档位）；【推断】= 基于包名规范/生态通识的推断，非实证。查不到的一律标「未核实」，不以合理猜测填充。

---

## 0. 一句话结论

两 App 的 AppGallery 页面均为 JS 渲染壳，curl 直取只得 3070 字节空壳；本席逆向出 AppGallery 前端的完整 API 调用链（`/edge/webedge/getInterfaceCode` → `Interface-Code` JWT 头 → `/edge/uowap/index?method=internal.getTabDetail`），实测仍被服务端签名墙拦下（403 / rtnCode 1002），**两 App 的应用市场正文均未取得**；按任务书授权回退包名情报路径：`com.wzdxy.ssh.h` 维持「SSH 终端工具」推断（定位：**远程运维通道候选**，人工带外复核性质）；`com.chuckfang.meow` 有外部情报（[媒体] 级）推翻「笔记工具」假设，实为**消息推送网关类应用**（服务器报警推送/频道订阅/跨端复制），定位由「轻量记录终端」**修正为「轻量通知触达/事件回执终端」**——这一修正比原假设对 A2A 网络更有价值。

---

## 1. 采集实录【实跑】（全部命令与输出，2026-10-01 本席实跑）

### 1.1 直取详情页：只有壳

```
curl -s -m 30 -o /tmp/ag_ssh.html -w "HTTP=%{http_code} bytes=%{size_download}" \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... Chrome/126.0.0.0 Safari/537.36" \
  -H "Accept-Language: zh-CN" "https://appgallery.huawei.com/app/detail?id=com.wzdxy.ssh.h"
→ HTTP=200 bytes=3070 url=https://appgallery.huawei.com/app/detail?id=com.wzdxy.ssh.h
grep -c "wzdxy" /tmp/ag_ssh.html → 0 ；<title> 为空

同法 com.chuckfang.meow → HTTP=200 bytes=3070，grep -c "chuckfang" → 0，<title> 为空
```

与既有侦察留痕一致：`burn/recon_app_ssh.html`、`burn/recon_app_meow.html`（各 3143 字节，同为空壳，2026-10-01 19:04 落盘）。
**旁证**：服务端渲染器（web_reader）抓两页同样只回 AppGallery cookie 提示文案，正文为空——本席据此确认「JS 渲染壳、curl 拿不到正文」的前提成立。

### 1.2 逆向 API 调用链【实读】（读的是本次实跑下载的前端产物）

壳页加载三个 JS bundle（`appportal-drcn.dbankcdn.cn//static/agweb/202609041551/js/`：manifest 4256B、0.* 4,405,800B、7.* 3,351,002B，均 HTTP 200 实测下载）。从 bundle 内逆向出的事实：

| 事实 | 出处（bundle 内原文片段，实读） |
|---|---|
| 详情页路由 `/app/:appid` 与 `/detailApp/:appid` | ag_7.js：`{path:"/app/:appid",...},{path:"/detailApp/:appid",...}` |
| 数据接口：`GET /uowap/index`，参数 `method:"internal.getTabDetail", serviceType:sysConfig.serviceType, reqPageNum, uri:"app\|<id>", maxResults` | ag_7.js：`getTabDetail=function(e,a,t){return i.getService.get("/uowap/index",{params:{method:"internal.getTabDetail",serviceType:sysConfig.serviceType,reqPageNum:a,uri:e,maxResults:sysConfig.maxResults},cancelToken:t})}`；详情页调用形如 `getTabDetail("app\|"+e,1)` |
| 配置值：`serviceType: 20`、`maxResults: 25`、`interfaceCodeSwitch: 'on'`、`siteId: 'north.china'`、`webEdge.switch:'ON'`、`baseUrl_north.china: 'https://web-drcn.hispace.dbankcloud.com/edge'` | 详情页内联加载的 `/static/agweb/env.js`（HTTP 200，13,672B 实测），本席实读原文 |
| 签名机制：先 `POST /webedge/getInterfaceCode` 取码，之后每个请求带头 `Interface-Code: <码>_<毫秒时间戳>` 与 `Identity-Id: <UUID>` | ag_7.js：`e.headers["Interface-Code"]=A()+"_"+(new Date).getTime(), e.headers["Identity-Id"]=...`；码存 sessionStorage |
| 1002 自动重试一次（取新码重发） | ag_7.js 响应拦截器：`if(1002!==a.response.data.rtnCode||a.config.retryFlag...)break; return E(a)` |

### 1.3 签名墙实测：403 / rtnCode 1002【实跑】

```
CODE=$(curl -s -A "<UA>" -X POST "https://web-drcn.hispace.dbankcloud.com/edge/webedge/getInterfaceCode")
→ 返回 423 字节 JWT；解码（python base64.urlsafe_b64decode）：
  header : {"algorithm":"HS256","type":"JWT","alg":"HS384"}
  payload: {"iat":1790858314,"exp":1790859214,"jti":"9a51e9dd-...","sub":"auth",
            "username":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... Chrome/126.0.0.0 Safari/537.36"}
  （有效期 15 分钟，payload 只绑定 User-Agent 字符串）

随后带 Interface-Code/Identity-Id 头调用（serviceType=20, uri=app|com.wzdxy.ssh.h, maxResults=25）：
→ HTTP=403  {"rtnCode":1002,"rtnDesc":"InterfaceCode Verification failed."}
```

本席系统排障记录（全部 403/1002）：
1. 直连 `web-drcn.hispace.dbankcloud.com/uowap/index`（无 /edge、无头）→ 1002；
2. 同源 `appgallery.huawei.com/uowap/index`（应用层 40402 "check param fail"，说明网关可达但参数校验不过）；
3. 带 cookie jar（先取壳页再取码再调用，jar 内 5 条 cookie）→ 1002；
4. 头部变体：`Interface-Code: <jwt>_<ts>`、无时间戳后缀、小写 `interface-code` → 均 1002。

**结论**：`getInterfaceCode` 的 JWT 虽只在 payload 里绑定 UA，服务端校验显然还比对 curl 无法复现的浏览器侧特征（未核实具体为何：疑与 TLS/HTTP 指纹或 WAF 会话相关）。**该签名墙未突破，两 App 的市场正文（名称/简介/评分/权限声明/更新记录）均未取得，如实登记，不用包名推断冒充正文。** 如需突破，需真实浏览器环境（本席当前不在位）。

### 1.4 外部情报检索【侦察】

- `WebSearch "com.chuckfang.meow"`：命中 1 条——dztap.com《MeoW：数字生活"贴心管家"》（小刘的日常随笔，**文章自注"部分内容由 AI 辅助生成"** → 按 **[媒体] 最低档**标注，须再验证）。
- `WebSearch "wzdxy" SSH 终端 鸿蒙`：**0 命中**。未检索到任何关于 `wzdxy` 开发者的公开页面。
- 引用既有在案转引：`burn/mcp_burn/direct_burn.jsonl:3`（先前席次 finance_search）——「HDC2026 发布 HarmonyOS 7 智能体架构 HMAF2.0 / 鸿图计划覆盖 20 行业 / 终端 13 亿台 / AppGallery 四大 Skill」（【转引】，本席未复跑）。

---

## 2. App 一：com.wzdxy.ssh.h —— SSH 终端工具（推断级）

| 项 | 内容 | 档位 |
|---|---|---|
| 应用市场正文 | 名称/简介/评分/权限**未取得**（签名墙，§1.3） | 未核实 |
| 包名解构 | `com.wzdxy` = 开发者反域名段（wzdxy 具体主体未核实，公开网络 0 命中）；`ssh` = SSH 协议段；尾缀 `.h` 疑为 HarmonyOS 移植/鸿蒙版标记（**推断**，同类玩法如 PuTTY 鸿蒙移植报道，也可能是应用缩写） | 推断 |
| 品类 | SSH 终端工具（任务书给定 + 包名 `ssh` 段支撑） | 推断 |
| 鸿蒙同类品（生态参照） | TermNext（SSH/Mosh/Telnet、SFTP、MFA、JumpServer、端口转发，termnext.com 官网【侦察】）；南瓜SSH（鸿蒙 NEXT 原生、手机/平板/PC 三端，华为应用市场可搜，CSDN/掘金教程【侦察】）；PuTTY 鸿蒙移植（CSDN 记录【侦察】） | 侦察 |
| 能力面推断（按品类通用） | SSH-2 协议、密码/密钥双鉴权、SFTP 文件传输、端口转发、多主机会话管理 | 推断（品类通识，非该 App 实测） |

---

## 3. App 二：com.chuckfang.meow —— MeoW 消息推送类应用（媒体级 + 与任务书假设的差异）

**与任务书给定假设的偏差（重要）**：任务书预设「Meow = 笔记/记录工具（数据格式/同步场景）」。外部情报显示其真实品类是**消息推送/提醒**，不是笔记工具。本席按「修正有据、原假设留痕」原则处理：定位按修正后品类给出，原假设不删除。

| 项 | 内容 | 档位 |
|---|---|---|
| 应用名 | MeoW | [媒体] |
| 品类 | 消息提醒/推送类应用，非笔记工具 | [媒体]（需验证） |
| 平台 | 鸿蒙（HarmonyOS NEXT）；文中未提安卓原生版 | [媒体] |
| 核心功能 1：无后台推送 | 深度集成华为统一 Push 服务（Push Kit），应用无后台、注册后可关闭联网权限仍收系统级推送；本地可选保存、不存服务器 | [媒体] |
| 核心功能 2：服务器报警/事件推送 | 可将 MeoW 链接集成到服务器，异常/事件触发即推手机通知——**即 HTTP 触发的推送网关（Bark/ntfy 同型）** | [媒体] |
| 核心功能 3：应用更新频道订阅 | 订阅微信/QQ/抖音等更新频道，尝鲜/公测/正式版发布即推 | [媒体] |
| 核心功能 4：跨设备复制 | 任意联网设备请求 MeoW 链接 → 用户点通知即复制内容 | [媒体] |
| 商业/开发者 | 开发者"方程"，订阅制（文称"年入百万"，下载量口径前后不一：3 万 vs 51 万——**数字自相矛盾，不采信**） | [媒体]（矛盾点登记） |
| 数据格式/同步细节 | 原文未提；推送 API 的请求格式/鉴权方式**未核实** | 未核实 |

---

## 4. A2A 开放计划中的定位建议

> 背景口径：A2A 网络现状是「5 桌面 AI 席位 + 公网桥 + 百炼侧线」全部锚在幻16主机（`burn/a2a-plan-50k/04-A2A网络总体规划.md:§1.2` 范围表）；移动端目前是空白项。两 App 恰好补的是**人不在主机前**的两个缺口：操作缺口与知会缺口。

### 4.1 com.wzdxy.ssh.h → **远程运维通道候选（人工带外复核通道）**

- **为什么是它**：SSH 终端 = 手机侧进入主机 shell 的标准通道。A2A 网络的总线/黑板/验收脚本全在主机上，主机失联或总线故障时，手机 SSH 是**不依赖 A2A 网络本身**的带外通道（out-of-band）——这正符合运维工程"管理通道与业务通道分离"的常识。
- **安全边界（三条硬约束）**：① 只做**人工握持**通道，禁止任何席位自动化发起 SSH（密钥不入 agent 上下文、不入 `.env`，凭据归机主个人持有——呼应章程「机主终裁权不可让渡」）；② 操作留痕以 SHA3-512 身份体系的 data_links 锚定审计日志；③ 首次接入前须实测该 App 的协议/密钥支持面（ed25519、端口转发、跳板）——**当前正文未取得，接入列为条件项**。
- **不宜的角色**：不做总线传输通道（延迟/可靠性不满足 A2A 0.3.0 会话语义），不做无人值守定时任务。

### 4.2 com.chuckfang.meow → **轻量通知触达/事件回执终端候选（修正后定位）**

- **为什么是它**：其"服务器报警/事件推送"功能与 A2A 网络的现成告警账本**直接对上**——`burn/a2a-plan-50k/bus_watchdog_alerts.jsonl` 已在看门狗告警落账，只是没有手机触达面；MeoW 的 HTTP 链接式推送（Bark 同型）是最小集成面：watchdog 出告警 → HTTP POST 到 MeoW 链接 → 手机通知。其"频道订阅"还天然对应 A2A 的公告广播场景（如 `ZCODE-BB-20260927-01` 全网通告这类文书，可同步建频道推达）。
- **优于原假设之处**：若按任务书原假设"笔记/记录终端"，它只能当数据格式的旁路终端；按修正后的"推送网关"品类，它直接补上 **A2A 网络目前缺失的通知触达层**（席位烧完额度/告警/验收结果推到手机），价值更高。
- **安全边界（两条）**：① 推送内容分级——A2A 告警/验收结论属内部文书，按 D0–D4 出域分级先审（对应 `burn/governance/astra_integration_plan.md` 的分级纪律），默认只推事件码+指向黑板端点的摘要，不推全文；② 该 App 情报目前是 [媒体] 级，**集成列为条件项**：须先实机验证其推送 API（请求格式/鉴权/频控）并确认开发者主体，验证不过则回退为「自建 ntfy/Bark 网关」的同位替代（写入开放计划备选）。

### 4.3 综合判断

两 App 组合恰好构成移动端「**一操作、一知会**」对：SSH=人回到主机的手，MeoW=网络伸手找到人的铃。都补在 A2A 网络最薄的层（移动端触达），且都不动摇 P2（编排与执行分离）与机主终裁权。但两者当前都**不应直接写进执行计划**——一个正文未取得、一个情报仅媒体级，先以「候选+条件项」入计划。

---

## 5. 改写开放计划的三个要点

> 对象：`burn/a2a-plan-50k/04-A2A网络总体规划.md`（及总纲 `00-总纲与目标.md`）中「网络实体」范围与后续版本。

1. **范围表新增「移动终端双通道」一节（SSH 操作面 + MeoW 知会面），并写死角色边界**：SSH 仅人工带外运维（禁止席位自动 SSH、密钥归机主、操作 SHA3 锚定留痕）；MeoW 仅单向事件通知（watchdog 告警/验收结果 → HTTP 推送，默认事件码+摘要不推全文）。两通道均标记为**非自治执行通道**，不参与总线会话，失败不阻塞 A2A 主链路。
2. **候选→在役必须过「验证门」并把验证步骤本身写进计划**：SSH 件先实测协议支持面（SSH-2/ed25519/SFTP/端口转发/跳板）与鸿蒙权限模型；MeoW 件先实测推送 API（请求格式/鉴权/频控）与开发者主体核验。验证产出直接落 `burn/claims/` 同目录留痕，验证不过即启用备选（SSH 备选：南瓜SSH/TermNext【侦察】同型品；MeoW 备选：自建 ntfy/Bark 网关）。
3. **情报口径条款固化 P6 纪律到 App 名录**：开放计划凡引用应用市场/App 情报，一律加「来源档位」列（官方正文 / 媒体 / 包名推断 / 未核实），本轮两个样本直接入册示范：`com.wzdxy.ssh.h`=【推断】档、`com.chuckfang.meow`=【媒体】档（含数字矛盾登记）；AppGallery 采集路径的结论也写入——直取=空壳（3070B）、逆向 API 链被 Interface-Code 签名墙拦（403/1002），后续采集需真实浏览器环境，不再用 curl 硬撞。

---

## 6. 未核实清单（本席如实登记）

| # | 事项 | 现状 |
|---|---|---|
| 1 | 两 App 在 AppGallery 的正文（名称/简介/评分/权限/更新记录） | API 签名墙未突破（§1.3），未取得 |
| 2 | `com.wzdxy.ssh.h` 的应用名、开发者主体、`.h` 尾缀含义 | 公开网络 0 命中，仅包名推断 |
| 3 | MeoW 推送 API 的请求格式/鉴权/频控；是否真为纯鸿蒙应用 | [媒体] 级，未实机验证 |
| 4 | MeoW 下载量（3 万 vs 51 万矛盾） | 不采信，待官方口径 |
| 5 | `wzdxy` 开发者身份 | 未核实 |
| 6 | AppGallery Interface-Code 服务端校验的具体绑定面 | 未核实（疑 TLS/WAF 指纹） |

---
*本件由 App 分析席产出，落盘 `burn/claims/app_analysis.md`；采集原始产物 `/tmp/ag_ssh.html`、`/tmp/ag_meow.html`、`/tmp/ag_env.js`、`/tmp/ag_bundle.js`、`/tmp/ag_7.js`（临时目录，同会话可复核）；既有侦察留痕 `burn/recon_app_ssh.html`、`burn/recon_app_meow.html`。*
