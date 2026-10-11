# 审议口径

“幂等”对应 idempotency，指同一事件重复处理不重复产生约定的业务副作用。若文档使用“等幂”，核对术语表是否明确该对应关系；输出相似不能代替事件身份或业务副作用证据。

HMAC 属于共享密钥的消息认证码，核对文档是否误写成公开验签或不可否认性的数字签名。MAC 地址是设备属性，核对是否被直接当作 MFA 的第二因素。本地 pre-commit 可以被 --no-verify 绕过，服务端阻断须有服务端控制证据。参考 [Git 官方 hooks 文档](https://git-scm.com/docs/githooks)。

许可标识只证明提到了某种许可。核对文件或组件的权利主体、适用版本、授权声明、依赖边界以及源码交付义务，分别记录条款出处和待复核事项；标识出现不证明授权生效或组合兼容。

- [AGPL-3.0-only](https://spdx.org/licenses/AGPL-3.0-only.html)：网络交互条款按适用版本与实际交互范围分析，避免把任意 API 客户端或全部关联后端一概纳入。
- [GPL-3.0-only](https://spdx.org/licenses/GPL-3.0-only.html)、[CC-BY-SA-4.0](https://spdx.org/licenses/CC-BY-SA-4.0.html)、[ODbL-1.0](https://spdx.org/licenses/ODbL-1.0.html)：分别核对软件、内容与数据库的实际适用对象。
- [SSPL-1.0 条款](https://www.mongodb.com/legal/licensing/server-side-public-license) 与 AGPL 分开核对；[OSI 对 SSPL 的说明](https://opensource.org/blog/the-sspl-is-not-an-open-source-license) 明确其不属于 OSI 认可的开源许可。同一组件叠加条款与不同组件分别许可须有不同的权利与范围证据。

结构化 OTL 候选需有 data.title 和 data.mainBody，文本节点为 type: text 且 content 为字符串；无法读取的节点、空正文或只有标题保留待核状态。DOCX 的容器、修订、评论和附件计数可作为预检证据，媒体与嵌入对象的内容须另行检验。WPS 原生导入接受、云权限和完整修订历史须从实际产品或接口取得证据。

面向机关或学术技术行文的表达风格，不授予机关身份、职务或签发权。核对角色是否属于明确引文或案例，正式主体字段保持一致。

