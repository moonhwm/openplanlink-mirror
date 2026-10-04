# spec-proto

## 目的
四元标签协议

## 输入/输出
方法 → 四元标签/平面

## 不变量
priority/ttl/delivery/reply_to 合法；kind 三平面

## 失败模式
越权/超长报错

## 关键函数
- plane_of
- quad_of
- over_limit
- RateLimiter

## 验收断言
90 req/min 限频
