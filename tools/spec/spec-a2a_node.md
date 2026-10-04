# spec-a2a_node

## 目的
A2A 本地节点(127.0.0.1:4173)

## 输入/输出
请求(POST / 消息信封) → 响应(JSON-RPC 结果/入箱/死信)

## 不变量
HMAC-SHA3-512 验签失败必 401；nonce 不重放；未知席位入 DLQ 不丢弃；限频 90/min

## 失败模式
MFA_FAIL/UNKNOWN_SEAT 记录审计；信箱/DLQ 原子落盘

## 关键函数
- do_GET
- do_POST
- _send_panel
- _rpc_result
- _nonce_count

## 验收断言
POST /model 返回异质模型真答；POST / 验签通过入箱
