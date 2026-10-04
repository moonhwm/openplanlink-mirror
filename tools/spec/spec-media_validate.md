# spec-media_validate

## 目的
AV1/H265 编码校验

## 输入/输出
路径 → 分类/校验

## 不变量
AV1/H265 规则；与缓存解耦

## 失败模式
编码不合规报错

## 关键函数
- classify
- validate
- assertion

## 验收断言
AV1/H265 规则命中
