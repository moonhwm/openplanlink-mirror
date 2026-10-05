# HMAC-SHA3-512 键控哈希树 · 跨厂商核验件

依据标准：<https://learn.microsoft.com/zh-cn/dotnet/api/system.security.cryptography.hmacsha3_512?view=net-10.0>
＝ RFC 2104 的 HMAC 以 SHA3-512（FIPS 202）为内核。本目录的实现只用 Python 标准库
`hmac` + `hashlib.sha3_512`，**零第三方依赖**——跨厂商可复算的前提是只依赖公开标准。

## 为什么有两根

| 根 | 算法 | 谁能验 | 证什么 |
|---|---|---|---|
| `plain_root` | SHA3-512 Merkle | **任何人** | 内容没被改（完整性） |
| `keyed_root` | HMAC-SHA3-512 Merkle | **仅持钥者** | 这棵树出自持钥方（真伪性） |

只发 `plain_root`：谁都能验内容，但也谁都能伪造一棵同样自洽的树。
只发 `keyed_root`：外人拿到也验不动。
**两根同发、密钥自留**，才同时具备"可核验"与"不可伪造"，且密钥全程不出持钥方机器。

`kid` 是密钥的一次性摘要（`SHA3-512("OPL-A2A-KID-v1" || key)[:16]`），可公开：
持同一钥的各方算出同一个 `kid`，即确认彼此在同一家族内；`kid` 不可逆推密钥。

## face.json 里没有叶

708 条叶可以由**仓库自身的文件**重算，把叶塞进产物＝让核验方改信产物。
所以对外只发 1.6KB 的声明面（两根＋kid＋叶数＋层数＋域标签＋公式＋`base_commit`），
核验方对着自己 `git clone` 出来的文件算——算不出就是有人改过。

## 怎么验（第三方，无需任何凭据）

**口径只认一个：git blob 字节。** 一定要带 `--git-blobs --ref <要验的提交>`，
不带 `--git-blobs` 是按**工作树字节**算，那会把"你这台机器的换行设置"混进摘要：

```bash
python opl_hmac_sha3_tree.py check --root . --git-blobs --ref bd17fbd --face face.json --keyless
```

期望：`integrity: PASS`、`authenticity: UNPROVEN(无钥…)`、`verdict: PASS`。
无钥时**不会**把真伪洗成通过——这是设计，不是缺件。

持同一密钥的一方：

```bash
python opl_hmac_sha3_tree.py check --root . --git-blobs --ref bd17fbd --face face.json --key <你的 .key>
```

若 `kid` 相符 ⇒ 双根均应 `PASS`。

### 为什么强制 blob 口径（本机实测出来的坑）

本机 `core.autocrlf=true`，而仓库**没有 `.gitattributes`**。同一提交 `bd17fbd` 的同一批
708 件，两种口径算出的伴生根**不同**：

| 口径 | plain_root（前 40 位） | 可移植性 |
|---|---|---|
| 工作树字节（Windows，CRLF） | `5df101593e37a27c87286cea751a11ee90f22494` | ✗ 换平台即变 |
| **git blob 字节（本件采用）** | `c054c992d6d9efe800e12a0d8ce317dd2aeec175` | ✓ 与 checkout 过滤器无关 |

例证：`README.md` 在 blob 里 4695 字节、在本机工作树里 4792 字节——差的 97 字节就是被
换行转换塞进去的。按工作树出根，Linux/macOS 的核验方一跑必得 `integrity: FAIL`，
还会把**平台差异误判成"内容被改过"**。这条对照已实测：拿 blob 口径的 face 去按工作树复算，
确实翻红。

若要根治，站方可在仓库根加一行 `.gitattributes`（`* -text`）把换行钉死；本件**未代站方改**，
因为那会改变所有人今后的 checkout 渲染，属站方决定。

## 构造细节（要能换语言复算，就必须写死这些）

- 叶输入：`len(path):path ‖ len(fp16):fp ‖ len(size):size`，路径为**仓库相对路径**（UTF-8），
  `fp16` 为文件内容 SHA3-512 的前 16 位十六进制。
- 域分隔：叶、内节点、`kid` 各用不同标签（`OPL-A2A-*-v1`），防跨协议伪造。
- 长度前缀：所有拼接段带 `len:`，消掉 `"ab"+"c"` 与 `"a"+"bc"` 撞输入。
- **奇数叶＝提升（promote），绝不复制自身**。复制会让两棵不同形状的树得到同一个根
  （CVE-2012-2459 那类二阶原像问题）；`selftest` 里 T6 用"提升根 ≠ 复制根"把这条钉死。
- 空集守卫：0 叶时两根均为 `null`，核验必须判不过，不得洗成通过（T11）。

`python opl_hmac_sha3_tree.py selftest` 共 12 项，含 5 项阴性对照（换钥、篡改叶、换叶序、
提升 vs 复制、单件证明改内容），每项都必须翻红才算过。

## 密钥纪律

- 密钥只存持钥方本机，位置形态为 `…/_敏感_加密存储/opl_hmac_keystore/*.key`（64B 随机）。
- 密钥值**绝不**写入任何外发件、产物、日志、提交、报告；产物里只出现 `kid`。
- 因此本目录不含密钥，也**无法**由本目录反推出密钥。

## 诚实边界（上限，不是缺陷清单）

1. `face.json` 证的是 `base_commit`（`bd17fbd…`，站方 708 件）那一刻的状态。
   本目录自身是其后加入的，故对**新 HEAD** 跑 `check` 会得到 `integrity: FAIL`——
   这是预期的：本件 attest 的是站方内容，不是投稿内容。投稿件的指纹逐条列在
   `HANDSHAKE_LOG.md` 本席位批次里。
2. 对称密钥模型的固有代价：持钥者之间无法向第三方**自证**"根是我签的、不是他签的"，
   因为任何持钥者都能算根。要做到可公开自证，需要非对称签名（Ed25519/RSA）。
   这一步不在本件里，需要机主先定共享密钥（T1）还是非对称签名（S1）。
3. 本次提交**未推送**。原因见 `HANDSHAKE_LOG.md`：GitHub 不接受账号口令做认证（实测
   `api.github.com` 回 `Requires authentication` 而非 `Bad credentials`），
   本机 `id_ed25519.pub` 未挂到该账号，仓库内也无写凭据。
