# CONTRIBUTING · 贡献指引

本仓库是 **OpenPlanLink 公网镜像**，遵循「上游源站优先」原则。

## 铁律

1. **不要直接改本仓库的站点文件**（index.html / assets / atlas / data …）——它们由看守链
   从上游 `dist-handshake` 自动同步，直接修改会在下一次同步被覆盖。
2. 想改站点？去上游（Qoder 工程 `2026-09-25/882fec9c`）改构建源，镜像链数秒内跟进。
3. 例外：README.md / LICENSE / 本文件 / `.well-known/` 之外的运维文档可直改（不随同步）。

## 可以直改的

- 文档（README / CONTRIBUTING / docs/）
- 完整性验证工具脚本（tools/，新增文件，不碰同步文件）
- Issues / Discussions：镜像异常、验证失败、安全问题

## 验证镜像完整性

见 [README「完整性验证」](README.md#完整性验证)。当前 Git 索引证明以 `attest-hmac-sha3-512.json` 为准；任何结构、文件集合、Merkle 根或 HMAC 复算不匹配均应 fail closed。请立即开 Issue 并附脱敏后的验证输出，禁止附带密钥或其他凭据。

## 安全上报

不要公开贴凭据。发现密钥泄露/篡改迹象：开 Issue 标题加 `[SECURITY]`，
或经 A2A 总线联系席位 `desktop-gengfu`。
