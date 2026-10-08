# spec-hetero_models

## 目的
异质模型接入。ID OPL-HETERO-SPEC-20261009-01；署名 codex-review-20261005。
302 固定使用用户指定 https://api.302ai.cn/v1；型号由调用方逐项核验。

## 输入/输出
prompt → 模型真答

## 不变量
key 本地 env 不入库
端点与凭据名称绑定；带凭据请求拒绝重定向。
302 国内模型、未知家族及未在 verified_foreign_models 中的型号，在读取凭据或发送请求前拒绝。
直接运行模块只报存在性，不自动调用模型；catalog 读取不证明推理或费用为零。
chat 的调用方须取得资源/费用审批，不能由 key 存在授予预算。

## 失败模式
无 key/网络报错

## 关键函数
- _load_keys
- chat
- status
- catalog
- _route

## 验收断言
端点绑定、302 禁用国内型号、未核验外部型号拒绝、错误体遮蔽、输出限制与返回结构分别测试。
实际目录GET、有限推理、价格/账单与真实节点签收分别凭独立回执确认，不以 mock 证明真实连通。
