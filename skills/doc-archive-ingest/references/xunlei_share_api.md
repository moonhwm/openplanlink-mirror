# 迅雷云盘分享链接只读枚举与比对接口参考

> data_cutoff=2026-09-14，conf=estimated+。来源：2026-09-13 与 2026-09-14 两席
> 实战（两条不同分享链接均走通，沈知微席核验 18/21 件字节级比对、缄钥席复跑
> 全链路成功）+ 开源对照 alist `drivers/thunder`（Go 驱动，签名常量与算法的
> 维护中上游）。**estimated 含义**：端点与错误码语义来自实战实返，签名常量
> 来自开源驱动默认值——两者都可能随客户端升级漂移，开跑前先到 alist 仓库
> 核对最新值。**逆向接口，随时可能失效；每次开跑前重新核对。**

## 目录

- [1. 定位与红线](#1-定位与红线)
- [2. 退化门纪律：浏览器停转 → API 直探](#2-退化门纪律浏览器停转--api-直探)
- [3. 已验证请求流（两步）](#3-已验证请求流两步)
- [4. 错误阶梯（实返登记）](#4-错误阶梯实返登记)
- [5. 签名算法与常量（alist 对照）](#5-签名算法与常量alist-对照)
- [6. 一致性比对模式](#6-一致性比对模式)
- [7. 漂移处置](#7-漂移处置)

## 1. 定位与红线

- **用途**：他人/自己生成的迅雷云盘分享链接（`pan.xunlei.com/s/<share_id>?pwd=<pass_code>`）
  的**只读枚举**（文件清单/字节数），以及与既有母本（如对象存储桶）的**一致性比对**。
- **性质**：公开分享 + 官方 Web/移动端自用 API 的只读调用，**无登录、无账号风险**
  （与注入客户端/协议外挂有本质区别）；但仍属逆向接口，如实标注不稳定。
- **红线（继承本技能铁律，不增不减）**：
  1. 只读枚举，不伪造成功；4xx/5xx 如实记录，不轰炸重试。
  2. 不绕过分享者设置的下载限制；本文件只覆盖「看清单」，不覆盖「取文件」。
  3. 签名常量属公开开源实现的默认值，不内置任何用户凭证；DEVICE_ID 本地随机生成。

## 2. 退化门纪律：浏览器停转 → API 直探

分享页是 NUXT SPA（`pan.xunlei.com`，前端 webpack 分包 xl_*.js）。沙箱内渲染
浏览器连续超时是已验证的高发故障——**同一工具连续 3 次雷同调用即触发退化门
停转**（项目既有立法）：停止 browser_visit 路线，改走 HTTP API 直探。

**不要从 webpack chunk 里重新逆签名算法**：Web 端签名模块（实战中编号 1640）
不在可抓取的 chunk 内，xl_captcha_svc.js 只给出调用形状 `captcha_sign=v.a(timestamp)`，
逆不全。直接去 alist `drivers/thunder` 读维护中的 Go 实现（见 §5），省掉整条死路。
（实证：2026-09-14 缄钥席在 chunk 层逆了约 20 步才转开源对照，转后 2 步即通。）

## 3. 已验证请求流（两步）

前置：本地生成 `DEVICE_ID`（32 位十六进制 GUID，如 `uuid4().hex`）。

**第 1 步：造 captcha_token**

```
POST https://xluser-ssl.xunlei.com/v1/shield/captcha/init
Headers: Content-Type: application/json, x-device-id: <DEVICE_ID>
Body(JSON): {
  "client_id": CLIENT_ID,
  "action": "get:/drive/v1/share",        # 按目标 API 的 method:path 填
  "device_id": DEVICE_ID,
  "meta": {"client_version": CLIENT_VERSION, "package_name": PACKAGE_NAME,
           "user_id": "0", "timestamp": <毫秒时间戳 str>, "captcha_sign": SIGN}
}
→ 200: {"captcha_token": "ck0....", "expires_in": 300}
```

**第 2 步：枚举分享清单**

```
GET https://api-pan.xunlei.com/drive/v1/share?share_id=<id>&pass_code=<pwd>&limit=100&page_token=
Headers: x-device-id, x-client-id: CLIENT_ID, x-client-version: CLIENT_VERSION,
         x-captcha-token: <第1步 token>, Accept: application/json
→ 200: {"share_status": "OK", "file_num": "18",
        "files": [{"kind": "drive#file", "name", "size", "id", ...}],
        "next_page_token": "", "user_info": {...}}
```

- token 有效期 300 秒，过期回第 1 步重造；`action` 与目标请求对应。
- 分页：`next_page_token` 非空则带入 `page_token` 续拉。
- 响应字段 `size` 为字节数 decimal 字符串——比对直接用。

## 4. 错误阶梯（实返登记）

| 缺失项 | 实返 | 处置 |
|---|---|---|
| device_id | 400 error_code=3，detail「device_id is empty」 | 补 `x-device-id`（GUID） |
| captcha_token | 400 error_code=9，detail「captcha_token is empty」 | 先走第 1 步取 token |
| 未签名 init | 400 error_code=9，detail「no client info found」 | meta 必须带 captcha_sign（§5） |
| 签名/常量失效 | （推定）captcha_invalid 持续 | 走 §7 漂移处置，不轰炸 |

## 5. 签名算法与常量（alist 对照）

上游：alist 仓库 `drivers/thunder/`（`common.go` 的 `GetCaptchaSign` +
`meta.go` 的 `algorithms` 默认值）。2026-09-13/14 实测可用值：

- `CLIENT_ID = "Xp6vsxz_7IYVw2BB"`（迅雷移动端驱动）
- `CLIENT_VERSION = "8.31.0.9726"`
- `PACKAGE_NAME = "com.xunlei.downloadprovider"`
- `ALGS` = `algorithms` 默认值的逗号分隔盐串（长串，以 alist 当前版本为准，
  **不要抄死在本文件外的脚本里就再也不核对**）。

算法（与 `GetCaptchaSign` 等价，纯标准库可算）：

```python
import hashlib, time
ts = str(int(time.time() * 1000))
s = CLIENT_ID + CLIENT_VERSION + PACKAGE_NAME + DEVICE_ID + ts
for a in ALGS:                       # 逗号分隔逐段链式
    s = hashlib.md5((s + a).encode()).hexdigest()
captcha_sign = "1." + s
```

注意：alist 另有 `thunder_browser`/`thunderx` 等驱动，常量互不相同
（如另一组 client_id `ZUBzD9J_XPXfn7f7` 带 client_secret）——**本次验证通过的
是 thunder（移动端）这一组**，混淆组别会卡在错误阶梯第 3 级。

## 6. 一致性比对模式

分享清单（name + size）与母本权威清单逐件比对，即得「已传/缺件」裁决：

1. 母本侧：对象存储列举接口实拉（如华为云 OBS ListObjects，列举免费）；
2. 分享侧：§3 第 2 步实拉；
3. 按 name 对齐、size 逐件精确比对（字节级，不用约数）；
4. 出报告：一致件数/缺件清单（name+size）/建议（补传 or 判不必补）。
   实证先例：18/21 件一致、缺 3 件大件 WAL，按「终态可重建」判**不必补传**
   ——比对的价值在裁决，不在凑齐。

## 7. 漂移处置

- 签名常量失效（init 持续 captcha_invalid）→ 回 alist `drivers/thunder` 拉最新
  `algorithms`/client 常量重试；仍败则如实报告「通道当前不可用」，给出人工
  手机端/App 端查看的替代路径，不绕过、不伪造。
- 端点结构变动 → 重新抓分享页 `xl_103.js`（getShare/getShareByCode 所在 chunk）
  与 `xl_manifest.js` 定位新 API host 与参数名，全程只读。
- 本文件事实以 data_cutoff 为准；每次实战后把新实返（错误码/字段变化）回填本节。
