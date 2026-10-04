# spec-totp

## 目的
TOTP RFC6238

## 输入/输出
密钥+时间 → 码/校验

## 不变量
30s 步长；6 位

## 失败模式
窗口外拒绝

## 关键函数
- _hotp
- totp
- verify
- gen_secret

## 验收断言
标准向量通过
