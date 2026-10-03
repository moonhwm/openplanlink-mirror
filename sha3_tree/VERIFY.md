# 跨厂商核验指引 · SHA3-512 / HMAC-SHA3-512 哈希树

适用：`TREE-K3-2026-1003-01`（证据树）、`TREE-K3-2026-1003-02`（节点注册树）及同规则后续树。

## 算法等价声明

本树内部节点使用 **HMAC-SHA3-512**，即 RFC 2104 HMAC 作用于 FIPS 202 SHA3-512。
以下实现逐一等价，任选其一即可复算：

- .NET 10：`System.Security.Cryptography.HMACSHA3_512`
- Python 3.6+：`hmac.new(key, msg, hashlib.sha3_512)`（标准库，零依赖）
- OpenSSL 3.x：`openssl dgst -sha3-512 -mac HMAC -macopt key:...`
- Node.js：`crypto.createHmac('sha3-512', key)`

叶子为**无钥** SHA3-512：任何厂商不需要密钥即可复算叶哈希并比对清单。
内部节点与根需要密钥复算；密钥由持钥方自留（永不上传），对外仅公布
`key_fingerprint_sha3_512 = sha3_512(key)` 用于锁定持钥人身份。

## Python（推荐，随库 verify_tree.py）

```bash
# 无钥模式（任何厂商）：结构 + 叶子复算
python verify_tree.py TREE-K3-2026-1003-02_manifest.json \
  --records TREE-K3-2026-1003-02_leaf_records.json

# 持钥模式（密钥自留方）：追加内部节点/根/密钥指纹/包含证明
python verify_tree.py TREE-K3-2026-1003-02_manifest.json \
  --records TREE-K3-2026-1003-02_leaf_records.json \
  --key tree02_key.bin --proof seat:tencent-tokenhub
```

退出码 0 = PASS，1 = FAIL。

## .NET / C#

```csharp
using System.Security.Cryptography;
byte[] Node(byte[] key, string leftHex, string rightHex)
{
    var L = Convert.FromHexString(leftHex);
    var R = Convert.FromHexString(rightHex);
    using var h = new HMACSHA3_512(key);          // .NET 10 标准类
    h.TransformBlock(L, 0, L.Length, null, 0);
    h.TransformFinalBlock(R, 0, R.Length);
    return h.Hash;
}
byte[] Leaf(byte[] canonical) => SHA3_512.HashData(canonical);
```

## OpenSSL

```bash
# 叶子
openssl dgst -sha3-512 asset.bin
# 内部节点（key 为 hex）
cat <(xxd -r -p <<<"$L") <(xxd -r -p <<<"$R") | \
  openssl dgst -sha3-512 -mac HMAC -macopt hexkey:$KEY_HEX
```

## A2A 握手（挑战-应答）

验明「对方是否持钥方」而不传输密钥：

1. 挑战方发 32B 随机 nonce（hex）
2. 持钥方回 `HMAC-SHA3-512(key, "a2a-challenge:" || nonce_bytes)`
3. 挑战方（同钥或预共享副本）比对；不同厂商间可用一次性会话密钥替代根密钥做隔离

## 叶子规范 JSON

`canonical_json = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",",":"))`
后取 UTF-8 字节。`leaf_records.json` 以 base64 携带逐叶规范字节，解码即得原文。

## 已知边界（top3_likely_wrong 摘要）

- TREE-02 中 Doubao 席为 pending_user_login：叶已锚、席未激活；激活后重建新树，旧树留档不覆盖
- 密钥单份存放于持钥机；丢钥不影响叶子无钥核验，仅内部节点不可复算
- registered_at 为台账自报时间；可信时序以树链 + 仓库 commit 双重锚定为准
