# spec-compensate

## 目的
Saga 回滚补偿

## 输入/输出
步骤事务 → 回滚

## 不变量
失败步骤逆序补偿；MFA_FAIL/GIT_HOOK_FAIL 触发

## 失败模式
补偿缺失报错

## 关键函数
- Tx
- step
- rollback
- commit

## 验收断言
失败全量回滚
