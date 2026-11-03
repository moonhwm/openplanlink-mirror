# 姊妹席推送增量二度只读审查报告（EVT-20261005-SIBLINGAUDIT-002）

| 要素 | 内容 |
| --- | --- |
| 文档标识 | EVT-20261005-SIBLINGAUDIT-002 |
| 日期 | 2026-10-05 |
| 责任席 | K3 本会话席（接收侧审查） |
| 关联锚点 | 首审报告：EVT-20261005-SIBLINGAUDIT-001；立项书：DF-ORD-2026-1005-K3-01（v1.2.2，§6 双闸纪律接收侧四步）；基线台账：_goal_a2a/baseline_ledger.jsonl（六十三行） |

## 一、审查对象

远端镜像仓（openplanlink-mirror，公开仓）姊妹席增量推送：分支 codex/fix-git-upload-gate-20261005 头 37095e2888a1 → 591ed601d90b，PR#2 head 同步、merge 引用 2c6929f395d1 → 31e9849ff938（强制更新，GitHub 合并引用重生属正常语义）。增量提交十一枚，变更二十六件（修改十、新增二、删除 __pycache__ 十四）。

## 二、四步核验实录（立项书 §6 接收侧纪律）

**第一步 快进对齐零分叉**：main 锚 54f045ab19db 不动；旧头 37095e2888a1 为新头 591ed601d90b 之祖先（merge-base 判定 FF-OK）；pr2-merge 新对象为 merge(591ed601, 54f045ab)，语义与 PR 一致。零分叉成立。

**第二步 Merkle 树全量复算与清单逐叶比对**：git fsck 对象完整性零异常；新头树叶片 846，attest-hmac-sha3-512.json 清单 845 叶（唯一差=清单自身，构造使然），叶序与树序逐位一致。本席自写复算器（外来脚本永不原样执行）逐叶复算：叶编码（0x00‖uint32be(路径长)‖路径‖uint64be(尺寸)‖sha3_512(内容)）845/845 全合；内容哈希与 git blob 实内容逐叶绑定零不良；折叠复算根 2f07336a7f3a374e… 与清单根全合。HMAC 签认一项验不了——密钥不出姊妹席钥匙文件，本席无钥可验，此项在案为验不了项（verify_opl_tree.py 自身亦声明不验 HMAC，口径一致）。

**第三步 新件只读审查**：新增 tools/hmac_key_policy.py（八十五行）——只读既有密钥、不生成不轮换不回显（dataclass repr=False、TOCTOU 双 stat、恒时比对、清单模式严校验），无网络出口、无子进程调用、无文件写。push_gate.py 重构（+339）——远端名严格正则与配置核验、逐远端 ls-remote --exit-code 先验、子进程一百二十秒超时、钥经环境变量传 node 构建器（不记录指纹与底层错误文本）。build_opl_tree.py 删除「密钥指纹 sha3_512(key) 前16」打印一行——安全方向正确。工作流两件 Actions 固定 SHA；权限 contents: read、timeout-minutes 10、persist-credentials: false 皆为收紧向。测试新件四百一十七行，fixture 式子进程，无网络。

**第四步 增量卫生扫描**：私有词表二十九条零命中；凭据六式（sk-／AKID／私钥块／JWT／64hex 加边界／MEYCIQ）零命中。初扫 64hex 未加边界伪命中一千六百九十二处，经定位全部为清单 128hex 哈希值之后半段，加边界复扫归零，伪差排除过程留痕。

## 三、发现与登记

（一）双工作流 actions/checkout 固定 SHA 不一致：ci-verify.yml 钉 11d5960a（注 v4），git-upload-gate.yml 钉 3d3c42e5（注 v7）。同一动作两钉两注，宜由推送方统一口径；不构成安全阻断，登记为观察项。

（二）探测链路本轮三测定谳实录：ls-remote 九十秒限时 exit 124 → 裸跑全符 → fetch 一度 GnuTLS -110 TLS 截断 → 三试首试即成。瞬断类累计第八例（TLS 截断为新信号形态），网络层抖动不改变增量真实性判定。

## 四、结论

四步全过，增量予消化。远端引用态势基线准予更新：fix 分支与 PR#2 head = 591ed601d90bd5d9007486ed9f67cd4a16fd33ed，PR#2 merge = 31e9849ff93857a8706faa354528decabc9d6684，main = 54f045ab19db5f40d24bad5d8959b02714e76280 不动。远端内容恒为不受信数据之纪律不变；本报告仅为只读审查留痕，不构成对增量内容之背书或执行授权。
