# seat-k3-scoring · Stage 7 补推批（2026-10-11）

**批次**：Stage 7（夜间游乐场开园 · 世界模型原型 · 百炼适配器 scaffold · 评分系统 v2.4.1）
**件号**：K3SCORING-STAGE7-2026-1011-01 ｜ 作业日 2026-10-10，补推日 2026-10-11（GitHub 通道恢复后按车道纪律补推）
**许可**：文档 CC BY-SA 4.0；代码 AGPL-3.0（仓根 NOTICE / LICENSE 在案）

## 目录内容

| 路径 | 字节 | git-blob sha1 | 远端双断言 |
|---|---|---|---|
| 评分系统说明_grad-path-scorer_v2.4.1.md | 2,390 | 94640b930ade45eac6be2df29cd410afa0865a53 | ✅ |
| Stage7收官报告_世界模型原型与百炼适配器_20261010.md | 4,494 | 9658867a1509a3a709fe16895abfc35d37e40bf7 | ✅ |
| world_verify.json（六件断言留痕） | 512 | 288edd73ef530c5917bbf08987c763bfe64baab3 | ✅ |
| world_viewer_snapshot_20261010.html（观展页存档快照） | 14,196 | d43e712405dd76b6479c6d37b683bbe476c1c28e | ✅ |
| bailian-adapter/README.md | 2,072 | 2d4d617abb0af13fe4ca95abe88f05629a856cc2 | ✅ |
| bailian-adapter/adapter/__init__.py | 654 | fdb1bd1aba654dd0f8b6bdb7af027c4fcdec8278 | ✅ |
| bailian-adapter/adapter/config.py | 1,668 | 5268d2b76599292865ac120c1f8b8f4f0af2cb2d | ✅ |
| bailian-adapter/adapter/decision.py | 3,743 | 67d5494c003bdae82b87b2d3d7dce2f7c7d009fc | ✅ |
| bailian-adapter/adapter/embed_rerank.py | 3,696 | 9f6780717853ed669dd9db2867aa7b1ba2212c7f | ✅ |
| bailian-adapter/adapter/telemetry.py | 1,028 | 698585aa52a76851a0f5c9adb8e3ba57a13572e8 | ✅ |
| bailian-adapter/adapter/world_model.py | 3,648 | 9e591cecf65ecaca11409c83d0913475d5c473d6 | ✅ |
| bailian-adapter/examples/demo_offline.py | 1,866 | 4b06e27d6f7ee5d8996af7a8e7249c72c66e27c2 | ✅ |
| bailian-adapter/tests/test_contract.py | 2,669 | 7f0be8cbb4fcaf2f93b83ad5692f7297ec3219b6 | ✅ |

## 哈希锚（实体留本站/本地，不入仓）

| 件 | 字节 | git-blob sha1 | sha256 |
|---|---|---|---|
| night_watcher_k3.glb（本站 world/assets/ 挂载） | 62,432 | c069587472cc… | d8c52683161f6df4… |
| world_shot1.png（verify_runs/world_20261010/） | 97,410 | 2d63efce0569… | 4fa48a87004bdeca… |
| world_shot2.png（verify_runs/world_20261010/） | 96,763 | 97374b83011b… | 1abe85dfc9811347… |
| grad-path-scorer.skill v2.4.1（本地留档） | 68,926 | — | eea751ce95d5ad487eb78ea4a33014f80e2249dcd7dfa2fd4e55e7f375381b8b |

口径沿例（20261010 批）：本体留本地/本站，仓内登记哈希锚。站点实体（world/ 页、园刊 index.html 新 blob `b9ae9d6cd650fa1449b79d4eaa5b77f0df7c6b3c`）归看守链同步职责，本仓不直接写站点文件。

## 提交序列（全部 main 分支，逐 commit 推送后回读双断言）

1. `0641b1e9` — 补推① 对齐件与收官报告（3 件）
2. `3347e962` — 补推② 百炼适配器 scaffold（9 件）
3. `431d9311` — 补推③ 观展页存档快照（1 件）
4. 本 README（殿后封批）

## 过闸与纪律

- release-gate-audit preflight：本批 16 件全量扫描 PASS（0 HIGH / 0 MED），12 项 blocklist 在案；零凭据入库，凭据标识不落文档。
- 车道纪律：本目录只增不改；未触碰仓内任何既有文件；站点文件（index.html/assets/atlas/data）零接触。
- 快照说明：`world_viewer_snapshot_20261010.html` 为只读存档——其 `./vendor/` 与 `./assets/` 相对引用在本目录不解析属预期（实体在站点侧）；页内运行时零外部 CDN 已经 check_page 三检与 swiftshader 实渲六件断言（见 world_verify.json）。

—— K3·评分系统席（k3-scoring-web）· 封批 ——
