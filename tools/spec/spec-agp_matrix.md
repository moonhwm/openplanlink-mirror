# spec-agp_matrix

## 目的
AGP×Gradle×MFA×AV1/H265 兼容矩阵

## 输入/输出
版本元组 → 兼容断言

## 不变量
缓存命中仍强制认证复查

## 失败模式
版本漂移报回退风险

## 关键函数
- assert_matrix
- cache_decouple_check

## 验收断言
漂移组合 FAIL
