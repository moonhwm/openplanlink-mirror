# spec-supply_chain

## 目的
第三方组件三查门

## 输入/输出
manifest → 可引入/不得引入

## 不变量
NOTICE/密钥扫描/SBOM 三项先行缺一不得引入

## 失败模式
密钥只报位置不打印值

## 关键函数
- notice_check
- secret_scan
- sbom_register
- gate

## 验收断言
缺 NOTICE → 不得引入
