# spec-perm

## 目的
权限模型

## 输入/输出
端点 → 所需权限级

## 不变量
read<execute<manage<audit

## 失败模式
越级拒绝

## 关键函数
- check
- required_for

## 验收断言
越级 FAIL
