# spec-quota_wall

## 目的
额度墙

## 输入/输出
错误码 → 墙策略

## 不变量
墙码零重试

## 失败模式
墙外重试

## 关键函数
- is_wall
- policy
- WallLedger

## 验收断言
1308/1310/1005 零重试
