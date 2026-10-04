# spec-compliance_check

## 目的
术语/格式/许可三查

## 输入/输出
文本/工件类别 → 检查结果

## 不变量
五层许可映射；GPL3 网络场景不适格

## 失败模式
未命中报人工核

## 关键函数
- check_terms
- check_format
- match_license
- license_layer
- gpl3_ineligible_note

## 验收断言
五层映射逐一命中
