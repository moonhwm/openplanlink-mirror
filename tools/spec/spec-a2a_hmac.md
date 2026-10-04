# spec-a2a_hmac

## 目的
HMAC-SHA3-512 包络

## 输入/输出
无 → 包络(tag/timestamp/nonce)；验签 → (ok,reason)

## 不变量
tag 错配拒绝；时间窗固定 300s；nonce 经 ReplayCache 幂等

## 失败模式
格式非法返回原因不抛异常

## 关键函数
- build_envelope
- verify_envelope
- ReplayCache
- compute_tag

## 验收断言
test_a2a_hmac 33 测 PASS
