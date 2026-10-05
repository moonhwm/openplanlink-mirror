# 本技能的审议口径

幂等性指同一事件重复处理不会重复产生约定的业务副作用；意见相似和输出一致不是事件身份。文档若沿用“等幂”，需在术语表说明其与 idempotency 的对应关系，避免与数学幂概念混淆。

HMAC 是共享密钥的消息认证码，持钥者可以重算；不能据此宣称具有公开验签或不可否认性。MAC 地址是设备清单属性，不直接构成 MFA 第二因素。Git 本地 pre-commit 可被 --no-verify 绕过，不能单凭本地 hook 声称服务端已经阻断。[Git 官方 hooks 文档](https://git-scm.com/docs/githooks) 支持本地钩子行为核对。

许可匹配采用明确的标识：[AGPL-3.0-only](https://spdx.org/licenses/AGPL-3.0-only.html)、[GPL-3.0-only](https://spdx.org/licenses/GPL-3.0-only.html)、[SSPL-1.0](https://www.mongodb.com/legal/licensing/server-side-public-license)、[CC-BY-SA-4.0](https://spdx.org/licenses/CC-BY-SA-4.0.html)、[ODbL-1.0](https://spdx.org/licenses/ODbL-1.0.html)。出现标识只证明文档提到了该许可，不能证明版权归属、许可生效或组合兼容。

AGPL 第13条的网络交互条款，应结合修改版本、与其远程交互的用户和对应源码判断，不把任意 API 客户端或全部关联后端一概纳入。SSPL 的服务条款另核；[OSI 明确说明 SSPL 不属于其认可的开源许可](https://opensource.org/blog/the-sspl-is-not-an-open-source-license)。把 AGPL 与 SSPL 作为不同组件的独立许可，与给同一程序叠加限制，是不同问题，均需权利与条款证据。

[WPS 文档接口](https://open.wps.cn/documents/app-integration-dev/docs-center/online-preview-edit/client/ActiveOutline/Doc) 区分简单文本与详细 JSON。脚本只能确认所读文件的容器/结构，云 ACL、修订历史、原生服务接受和附件关系另取实际证据。源件的目录、媒体、评论和修订保留在原件；本报告不能代替完整格式转换验收。

[用户指定的公文处理条例参考](https://jsnews.jschina.com.cn/zt2024/fzsxxxpt/hdxf/fgxwj/202404/t20240425_3397325.shtml) 用于表达和流转口径。项目主体、机关职务、签发权与技术作者不能相互推导。对商业或个人角色进入正式技术文档的情况，核对是否属于明确引文/案例，并在正式主体字段保持一致。

[Kimi Code 扫描规则](https://www.kimi.com/code/docs/kimi-code-cli/customization/skills.html) 与 [Kimi Agent 自定义技能入口](https://www.kimi.com/help/plugins-and-skills/use-skills-in-agent) 是不同部署证据。本地技能包可用不等于 Chat 已加载。
