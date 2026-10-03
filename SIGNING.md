# 提交签名登记（Git 钩子双重校验）

依《认证流程专章》第四章：入库提交须携带提交签名（commit signature），钩子校验签名者身份与绑定完整性。

- 签名算法：SSH Ed25519
- 签名公钥（供校验方）：
  ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIPI3Az+d4lQgVLHchnI65ibQSXV5P3Thqf8hBxq275e cairn-dsh commit signing
- 本地配置：commit.gpgsign=true、gpg.format=ssh、user.signingkey=<私钥路径>
