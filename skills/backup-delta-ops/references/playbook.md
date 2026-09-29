# playbook：增量对齐逐步 SOP（含 2026-09-11 出生案）

## 目录
1. 标准六步（命令模板）
2. 出生案全程（20260904→20260911 对齐）
3. 坑位清单

## 1. 标准六步

```bash
S=scripts   # 本技能 scripts 目录

# ① 盘点（截止线=备份基线日；排除表按项目私件表）
python3 $S/delta_inventory.py <注册处/文书根> --since YYYY-MM-DD \
    --exclude desensitize_rules_private.json --json inv.json

# ② 组 spec（域要全：registry/ledgers/canon/research…每域有件或声明无增量）
#    spec.json = {"copy_layers":[{"layer":"...", "files":[...]}],
#                 "skill_zips":["a.skill","b.skill"]}

# ③ 组装（技能双形态+扁平归一化+MANIFEST）
python3 $S/pack_delta.py spec.json <pkg_dir>

# ④ 验证（四闸）
cd <pkg_dir> && zip -q -r ../pkg.zip . && cd ..
python3 $S/verify_delta.py <pkg_dir> --zip pkg.zip

# ⑤ 文书：00_致接收侧说明书.md + SKILL_计数修订稿（随包）

# ⑥ 交付入账：zip→交付位；说明书副本→社区入口位；台账→锚→验→chown
```

说明书四段式（缺一即返工）：这是什么（分格表）/ 本体怎么读（答「不会读」）/ 合并几步（编号步骤、动作到文件夹级）/ 必须知道的几件事（排除名单、名实错位、版本换装、红线自查结论）。

## 2. 出生案全程（2026-09-11）

- 基线：k3-omnibus-archive 止 20260903（1176 件/15MB，挂载于 autonomous-advance-ops 目录名之下=名实错位在案）。
- 增量：registry 231 件（44.7MB，私件 1 故意排除）+ 三账副本 4 + canon 卡 4 + 技能 19 件（17 新+2 棘轮 KEEP 换装）+ 研究产物全量。
- 事故与自纠：初排 overlay 遇三件扁平 zip（munger-mind-ops/persona-iteration-loop-ops/tripo-avatar-ops）串件互盖→清位重排、逐件独立包壳→抽查结构正。此事故即 S1 闸由来。
- 收口：全包 734 件/83MB，MANIFEST 733 行；zip 10.6MB（md5 b37cd028cf0d7b0afcdd5c5382aa1096）unzip -t 无损；说明书投 quarantine/incoming；锚 A-20260911-057。

## 3. 坑位清单

| 坑 | 症状 | 解法 |
|---|---|---|
| 扁平 zip | overlay 根多出散件 SKILL.md/README、技能互盖 | pack 归一化 + S1 回检 |
| /tmp 焚毁 | 相邻工具调用间中间件消失 | 一律 /mnt/agents/temp |
| dash 无 brace 扩展 | mkdir 出字面 `{a,b}` 目录 | 逐条 mkdir 或 python |
| 只读挂载 | /app/.user/skills 写失败 | 只出修订稿，机主侧替换 |
| 权限位即分类 | 600 件混入包 | 逐件过脑，私件入排除表+说明书声明 |
| 凭证嗅探误伤 | Lark 资源 ID(file_token 等)误报 | S3 已内建占位词与资源 ID 白名单；真硬密钥才 FAIL |
| 计数滞后 | 备份自述件数过时 | 每次对齐出计数修订稿（体积诚实） |
