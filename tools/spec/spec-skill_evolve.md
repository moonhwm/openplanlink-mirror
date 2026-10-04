# spec-skill_evolve

## 目的
SkillOpt 自进化技能

## 输入/输出
rollouts → 技能文档编辑

## 不变量
有界编辑(预算4)；gate 通过才落盘

## 失败模式
reflect 无编辑/JSON 坏不崩

## 关键函数
- evolve
- reflect
- apply_edits
- gate

## 验收断言
accepted 时 best_skill.md 更新
