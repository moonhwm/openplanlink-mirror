# spec-cas_store

## 目的
CAS+gzip 内容寻址存储

## 输入/输出
bytes → 键(内容哈希)

## 不变量
同内容同键；CAS 冲突拒绝

## 失败模式
损坏/缺失报错

## 关键函数
- CasStore
- put
- get
- exists
- stats

## 验收断言
同内容幂等同键
