# spec-event_driven

## 目的
事件驱动共振场

## 输入/输出
事件(type/source/payload/幂等键) → 处理结果

## 不变量
同幂等键只消费一次；handler 抛错不静默

## 失败模式
未知事件类型拒绝；无 handler 报错

## 关键函数
- emit
- on
- _audit

## 验收断言
重复事件 dup=True；留痕落盘
