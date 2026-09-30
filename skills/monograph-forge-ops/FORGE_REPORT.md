# FORGE_REPORT — monograph-forge-ops v1.0.0（首锻）

## 主链纪事

- **立项**：2026-09-27，机主质问「金融技能还没创建完吗」——查证：monograph-delivery-ops 四次引用的姊妹件 monograph-forge-ops 从未开锻（安装位无目录、注册处无立项、索引无记录）。首锻模式（N-C-D 主链）。
- **素材重建事故**：delivery 件 references 指向的 `/mnt/agents/temp/assault_20260914/` 三件深读文档与上游仓**已随 temp 灭失**——教训铸卡候选：references 永不指向 /mnt/agents/temp。经 GitHub API 重建 alchaincyf/huashu-report（MIT，master）写作侧 12 件，落 `upstream/`（锻造工作区持久层）。
- **N 节点**：提炼卡三件套齐（方法论一句话/黑名单 6/诚实边界 3），见 PLAN.md。准出过。
- **C 节点**：SKILL.md（七步主流程/二门🔴/黑名单 10/失败模式 8）+ scripts/draft_lint.py + references/dryrun-suite.md。C 准出机检 9/9 全绿（frontmatter 411 字≤1024）。
- **实测**：draft_lint.py --smoke PASS——好稿 0 FAIL；坏稿 R1（缺字段/verified 非 bool/basis 过短）/R2（%无N）/R3（自指 2.2‰>2‰）/R4（日志句式）/R5（附录 89%>10%）全命中；exit 0/1 正确。

## D 节点：三视角 triage（宿主无 spawn 子代理能力，声明非独立，仅 triage 不进投票）

- **结构**：七步依赖清楚，交棒门与 delivery 接口明。短板：§七失败模式多为两段式（若→则），第三段「否则」不全。
- **实证**：smoke 确定性套件全过。短板：负断言来自自建反例，非判官 bug 清单（首锻无清单，待 D 后补入）。
- **对抗用户**：高频路径（写专著/续写/口径停点）触发覆盖；误伤面小（金融专著限定+免责锚与通用写作件正交）。短板：与 research-writer/equity-researcher 的边界靠「金融分析专著+长篇+免责锚」三限定，撞面登记待 collide 实测。

## 残余与候窗项（出链登记）

1. **判官独立盲评未做**——宿主降级声明在案；外池三判官（结构/实证/对抗用户）paired 评审列为候窗项（外池燃烧需机主呈批额度）。
2. **撞面实测未做**——fusion-cast-ops collide 闸待安装位可写后跑（descs.jsonl 注册表在安装位）。
3. **安装候窗**：/app/.user/skills 只读，.skill 包落 /mnt/agents/output/ 排队，同六卡补丁包候同一窗口。
4. §七失败模式「否则」段补齐（次版本补丁位）。
5. smoke 负断言待判官 bug 清单补入。

## 已知边界

- 本件不产数据、不构成投资建议（免责锚）；实时行情归数据插件席；交付验收归 delivery-ops。
- 上游仓方自报统计（41 份解剖等）按待验证假设引用，不背书。
