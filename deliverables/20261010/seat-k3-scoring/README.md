# seat-k3-scoring · 园刊第叁版（全园在册巡览）

**交付物**：《园刊第叁版》单文件静态站点（`园刊第叁版_全园在册_20261010.html`，140,511 B）。
数据口径：评分系统 panel v4 / Lane D v4，cutoff 2026-09-09，在册 10,893 行、64 单元。页内敏感标识一律只示 SHA-256 哈希，无明文凭据、无未掩码个人信息。

## 为何是分片

原文件超出推送通道可靠上限，按 `github-mirror-sync-ops` §5 分片发布：
`parts/p0.part … p341.part`（342 片，字符边界切分、UTF-8 安全）+ 指针 `园刊第叁版_全园在册_20261010.html.PARTS.md`（34,980 B，逐片 sha/size 清单）。

## 哈希锚（复算口径）

- 整件 git-blob sha1：`c367879da5755b6f51afd5304f2ec465e649f470`
- 整件 sha256：`1670cce4c268c6ff7693aac1a5f0fdb1ee874b1a5771622c66261b76b2516588`
- 复算：`sha1(b"blob 140511\0" + data)` 等于上一行即逐字节无损。

## 还原（三步）

```sh
# 1. 取件：克隆本仓后进入本目录
# 2. 拼接（PARTS.md 清单顺序即 p0→p341）
for i in $(seq 0 341); do cat "parts/p$i.part"; done > restored.html
# 3. 核验
python3 - <<'EOF'
import hashlib
d = open('restored.html','rb').read()
assert len(d) == 140511
assert hashlib.sha1(b"blob %d\0" % len(d) + d).hexdigest() == "c367879da5755b6f51afd5304f2ec465e649f470"
print("OK 140511B c367879d")
EOF
```

## 核验状态（2026-10-10 收官）

- 342/342 分片推送后逐件 blob-sha + size 双等断言通过；
- 端到端还原验证通过：远端拉取全部 342 片拼接 == 本地源（140,511 B / c367879d…）；
- PARTS 指针远端 blob `d3f68ad480bf0565919be8f86361b59b2100f2da`（34,980 B）回读断言一致。

## 席位纪律

本目录只增不改；零凭据入库；不改动仓内任何既有文件。许可姿态：开源筹备中，许可证文件待主权人指定后落于仓根——在明确许可文件到位前，内容仅供查看，保留所有权利。