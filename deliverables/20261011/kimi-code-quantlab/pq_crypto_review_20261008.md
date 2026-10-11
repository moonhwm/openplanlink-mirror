# 后量子栈独立技术审议报告
## ——对机主 2026-10-08 全局声明 v2 §3 加密体系段的判官级逐项重算

| 项目 | 内容 |
|---|---|
| 审议日期 | 2026-10-08 |
| 审议性质 | 独立重算，不盲信声明文本；逐项定级 |
| 定级标尺 | 【后量子安全】/【经典安全但量子时代可用】/【非后量子】/【存疑】 |
| 证据纪律 | 实质性断言均附来源；未能打开正文的链接标注「指针级」或「检索摘要级」 |

---

## 一、结论速览（逐项定级总表）

| # | 待审断言 | 定级 | 一句话裁决 |
|---|---|---|---|
| a | HMAC-SHA3-512 树 | **经典安全但量子时代可用** | 对称 MAC，Grover 下密钥搜索折半，512 位密钥仍有约 256 位强度；但「树」语义必须勘明（Merkle 树 or 密钥派生树），且 MAC 不是签名、不提供不可否认性 |
| b | AES-256-GCM | **经典安全但量子时代可用** ✔ | Grover 折半后约 128 位安全强度，业界共识为 PQ 时代可保留的对称主力 |
| c | IBC / SM9 | **非后量子** | 双线性对（pairing）体系，安全性基于配对群离散对数，Shor 算法可破；只能作经典期兼容层 |
| d | 「SM10」 | **存疑（官方标准序列中不存在）** | 截至 2026-10-08，国家密码管理局/商用密码标准研究院官方序列为 SM1/2/3/4/7/9+ZUC；国密后量子算法（NGCC）尚在评审中，第一轮评估预计 2027 年 6 月才完成，无任何「SM10」标准生效。声明引用存疑标准 |
| e | ZUC（祖冲之） | **经典安全但量子时代可用（附条件）** | 对称流密码；ZUC-256（5G 版）折半后约 128 位可用，ZUC-128 折半后仅约 64 位不达标，须限用 256 位版 |
| f | QRNG / HSM / ABE | **角色定位件，非 PQ 算法本身** | QRNG=熵源、HSM=密钥托管设施（算法无关）、主流 ABE=配对基（非后量子，格基 ABE 尚在学术研究阶段） |
| g | 「量子抗性前提下签名验证毫秒级」 | **条件成立，但断言必须限定平台与算法** | 服务器/桌面级 CPU 上 ML-DSA 验签为亚毫秒（约 0.12–0.2 ms）；嵌入式/智能卡上为数十至数百毫秒。且须指明真 PQ 签名（ML-DSA 等）——SM9 验签虽也是毫秒级但不抗量子 |

**总体裁决**：声明 v2 §3 的对称侧（AES-256-GCM、SHA3/HMAC、ZUC-256、QRNG 熵源、HSM 托管）在 PQ 时代大体可保留；公钥侧混入了一个非后量子体系（SM9/IBC）和一个不存在的标准（SM10），构成实质性失实风险，必须修正。

---

## 二、逐项审议

### a) HMAC-SHA3-512「树」

- **算法本体**：HMAC 是基于杂凑的消息鉴别码（MAC），属对称体系。量子威胁仅为 Grover 通用搜索的平方根加速：512 位密钥经 Grover 折半仍余约 256 位安全强度，远超 128 位门槛。GMAC/HMAC 类结构在公开安全评估表中被列为「量子影响有限」一档（[ewadirect 安全评估表，检索摘要级](https://www.ewadirect.com/proceedings/ace/volumes/vol/110/517.pdf)：AES-256 后量子 128 位、GMAC 128 位「no impact」；[Renesas 白皮书，检索摘要级](https://www.renesas.com/us/en/document/whp/latest-trends-post-quantum-cryptography)：Grover 使穷举从 2^N 降为 2^(N/2)）。
- **「树」语义勘明（声明文本未澄清，存在两种读法）**：
  1. **Merkle 树 / 哈希树**读法：以 SHA3-512 为叶/节点杂凑的完整性树。抗碰撞在 BHT 量子攻击下约为 2^(n/3)≈2^170（512 位输出），仍充裕；此读法成立。
  2. **HMAC 密钥派生树**读法（HKDF 链/棘轮式派生）：逐层 HMAC 派生子密钥，安全性归于底层 HMAC 的 PRF 性，量子影响同样只是密钥搜索折半；此读法亦成立。
  - 两种读法在 PQ 时代均可用，**但二者工程语义完全不同（完整性存证 vs 密钥层级管理），声明必须写明所指**。
- **纪律提示**：MAC 依赖共享密钥，**不提供不可否认性，不能替代数字签名**。若 §3 把「HMAC 树」用于需要抗抵赖的场景，属功能误配。

### b) AES-256-GCM

- 分组密码对称体系。Grover 折半后约 128 位安全强度（[PQShield，检索摘要级](https://pqshield.com/explainer-articles/aes-quantum-resistant/)：「AES-256 offers approximately 128 bits of quantum security」；[postquantum.com，检索摘要级](https://postquantum.com/post-quantum/grovers-algorithm/)；[Renesas 白皮书，检索摘要级](https://www.renesas.com/us/en/document/whp/latest-trends-post-quantum-cryptography)）。GCM 为 AEAD 模式，认证部分（GHASH/GMAC）不受 Grover 实质影响（同上文 ewadirect 表）。
- **裁决**：PQ 时代可保留，无需替换。此项断言成立 ✔。

### c) IBC / SM9

- IBC（标识密码）的工程主流实现基于**双线性对**。SM9 即中国国家标准的配对基标识密码体系：GM/T 0044-2016，含标识签名（IBS）、标识密钥协商（IB-KA）、标识加密（IBE），技术规范见其英文版（[Cheng, "The SM9 Cryptographic Schemes", ePrint 2017/117，指针级](https://eprint.iacr.org/2017/117.pdf)：「a set of identity-based cryptographic schemes **from pairings**」）。
- 配对体系的安全性归于椭圆曲线群/扩域乘法群上的离散对数困难性，**Shor 算法可在容错量子计算机上多项式时间破解**。多方佐证：[Crypto.SE「Is pairing-based crypto post-quantum secure?」，指针级](https://crypto.stackexchange.com/questions/106181/is-pairing-based-crypto-post-quantum-secure)；[乾珩量子 FAQ，检索摘要级](https://qhquantumdoc.com/pqc/faq.html)：「SM2 and SM9 are classical public-key algorithms broken by Shor exactly like RSA/ECC」。
- **裁决**：**非后量子**。在声明中只能作为经典期兼容层（legacy compatibility layer）存在，不得计入「后量子栈」的安全凭据。

### d) 「SM10」——官方标准序列核查（本报告核心核查项）

**核查结论：截至 2026-10-08，国家密码管理体系中不存在名为「SM10」的已发布密码算法标准。**

证据链：

1. **官方/准官方序列一致为 SM1、SM2、SM3、SM4、SM7、SM9 + ZUC（祖冲之）**：
   - [云南省林业和草原局《商用密码算法简介》(2023-10-23)](https://lcj.yn.gov.cn/special/2023/1023/5399.html)：「国家商用密码管理办公室制定了一系列密码标准，包括 SM1（SCB2）、SM2、SM3、SMS4、SM7、SM9、祖冲之密码算法等等」；
   - [《电力科学与技术学报》SM9 门限签名论文，检索摘要级](https://dlkjxb.csust.edu.cn/dlgcjs/article/pdf/20220421?st=article_issue)：「国家密码管理局制定了一系列密码算法标准，包括 SM1、SM2、SM3、SM4、SM7 和 SM9 等」；
   - [百度百科「国产商用密码」，检索摘要级](https://baike.baidu.com/item/%E5%9B%BD%E4%BA%A7%E5%95%86%E7%94%A8%E5%AF%86%E7%A0%81/68743756)：「覆盖 SM1、SM2、SM3、SM4、SM7、SM9、祖冲之密码算法等」。

2. **国密后量子算法（NGCC）尚在评审流程中，未产生任何新标准命名**：
   - 2025-02-05，商用密码标准研究院（ICCS）启动「新一代商用密码算法全球征集活动（NGCC）」，征集公钥、杂凑、分组三类算法（[中国密码学会转发公告](https://www.cacrnet.org.cn/site/content/1572.html)；[新浪财经，检索摘要级](https://finance.sina.com.cn/tech/roll/2025-02-07/doc-ineirsee0096313.shtml)；[ICCS 于 IETF 125 SAAG 的官方介绍幻灯片（2026-03），已读正文](https://datatracker.ietf.org/meeting/125/materials/slides-125-saag-introduction-to-the-next-generation-commercial-cryptographic-algorithms-program-01.pdf)）；
   - 提案提交 2026-06-30 截止（[腾讯新闻转载 ICCS 通知，检索摘要级](https://view.inews.qq.com/a/20251009A06ZNO00)；[ICCS 官网通知 niccs.org.cn，检索摘要级](https://www.niccs.org.cn/symmbzyjy/tzgg/pc/content/1976155884915003392/content_1976155884915003392.html)）；
   - **2026-09-20，ICCS 公布第一轮候选名单：84 个公钥算法（34 签名 + 41 密钥封装 + 9 密钥交换）+ 35 个杂凑算法进入第一轮评估，预计 2027 年 6 月完成**（[苏州信息安全法学所转载 ICCS 官方通知全文，已读正文](https://zone.ci/secarticles/wx/577782.html)）。名单中全部以方案本名（Aigis-Sig+、LoongKEM 等）称呼，**无任何「SM10」字样**。

3. **「SM10」说法仅见于自媒体，且与官方时间线矛盾**：
   - [知乎专栏（2025-07-30），检索摘要级](https://zhuanlan.zhihu.com/p/1934030571845181906)：称「抗量子计算攻击的 SM10 算法预计 2026 年完成标准化」——无 GM/T 标准编号、无官方文号，且「2026 年完成标准化」已被官方流程证伪（第一轮评估 2027 年 6 月才结束）；
   - [CSDN 博客「国密算法完整列表」（2026-04-08），已读正文](https://blog.csdn.net/zmj320324/article/details/159958407)：列「SM10：后量子密码算法」于「其他国密算法」下，同段还列出官方序列中同样不存在的「SM5/SM6/SM8」，均无标准编号，可信度低。

- **裁决**：**存疑**。声明 v2 §3 若把「SM10」当作已存在的国家密码管理局后量子标准引用，判定为**引用存疑/失实标准**；若原意为「未来的国密后量子算法」，正确表述应为「NGCC 第一轮候选在评，预计 2027 年 6 月后见分晓」。

### e) ZUC（祖冲之）

- 对称流密码。ZUC-128 为 3GPP 128-EEA3/EIA3（4G）国际标准与国密行业标准；**ZUC-256 为 2018 年设计的 5G 升级版的 256 位密钥版**，目标提供 256 位经典安全（折半后约 128 位量子安全），与 AES-256、SNOW-V 同列 3GPP SAGE 5G 评估对象（[arXiv 2111.05117，检索摘要级](https://arxiv.org/pdf/2111.05117)；[IEEE 硬件实现论文，检索摘要级](https://ieeexplore.ieee.org/document/9271719/)；[中科院软件所 ZUC-256 规范 PDF，指针级](http://www.is.cas.cn/ztzl/zouchongzhi/202607/W020180416526664982687.pdf)；[ePrint 2021/1439 补遗，检索摘要级](https://eprint.iacr.org/2021/1439)）。
- **裁决**：经典安全但量子时代可用，**附条件：须限用 ZUC-256**；ZUC-128 折半后仅约 64 位，不满足 PQ 时代长期安全门槛。声明若未区分版本，须补注。

### f) QRNG / HSM / ABE 角色定位

| 组件 | 真实角色 | PQ 属性 | 来源 |
|---|---|---|---|
| QRNG（量子随机数发生器） | **熵源**：从量子物理过程提取真随机性，喂给密钥生成；不是加密算法，也不自身提供量子抗性 | 信任根增强件，PQ 时代可用且推荐 | [Palo Alto Networks Cyberpedia，检索摘要级](https://www.paloaltonetworks.com/cyberpedia/what-is-a-quantum-random-number-generator-qrng)（「QRNGs feed entropy directly into key generation systems」）；[Fraunhofer IPMS，检索摘要级](https://www.ipms.fraunhofer.de/en/applications/Quantum-Technologies/Quantum-Communication/Quantum-Random-Number-Generation.html) |
| HSM（硬件安全模块） | **密钥托管/安全运算设施**（FIPS 140-3 认证体系），算法无关 | 其 PQ 性取决于固件是否支持 ML-KEM/ML-DSA——例如 AWS KMS 已支持 ML-DSA 而 AWS CloudHSM 尚不支持（见下节已读正文来源）；HSM 本身不构成「后量子」证据 | [crypto4a「What is an HSM」，检索摘要级](https://crypto4a.com/resources/newsroom/2026-02-09-what-is-a-hardware-security-module) |
| ABE（属性基加密） | **细粒度授权加密**（密文/密钥策略） | **主流 ABE 基于双线性对（DBDH 假设）→ Shor 可破，非后量子**；格基 PQ-ABE 仅有学术文献，未标准化 | [Fu 等格基 ABE 综述（ScienceDirect 2022），检索摘要级](https://www.sciencedirect.com/science/article/abs/pii/S1574013721000770)：「classical ABE schemes based on bilinear pairing are vulnerable to quantum cryptanalysis」；[Hasib 等格基 ABE 系统综述（Springer 2026），检索摘要级](https://link.springer.com/article/10.1007/s10791-026-09965-3) |

- **裁决**：三者都是**角色定位件而非 PQ 算法**。声明 §3 若把它们与 PQ 算法并列陈述，须在文本中明确标注「熵源/托管/授权」角色，避免读者误读为量子抗性来源。其中 ABE 若为经典配对基实现，本身是非后量子组件。

### g) 「量子抗性前提下签名验证毫秒级」实证基线

公开 benchmark 重算（按平台分层）：

| 平台 | 算法 | 验签耗时 | 来源等级 |
|---|---|---|---|
| 服务器/桌面级 CPU | ML-DSA-65 | **约 0.12 ms（亚毫秒），签名约 0.5 ms** | [shattered.io 基准汇总（2026-08），已读正文](https://shattered.io/ml-dsa-vs-slh-dsa-2026/)：「ML-DSA verification stays under 0.2 ms」 |
| 服务器级 | ML-DSA-44 | 验签中位 159.38 µs（约 0.16 ms），签名中位 379.83 µs | [DergiPark 性能评估，检索摘要级](https://dergipark.org.tr/en/download/article-file/5652694) |
| 服务器级 | ML-DSA-65 | 验签约 200 µs | [JETNR 论文，检索摘要级](https://rjpn.org/jetnr/papers/JETNR2604377.pdf)：「ML-DSA-65 signature verification completes in approximately 200 microseconds」 |
| 服务器级 | SLH-DSA-SHA2-128s / 128f | 验签约 0.8 ms / 亚毫秒至低毫秒；签名数毫秒至约 8 ms | 同 shattered.io（已读正文） |
| 嵌入式 RP2040（Cortex-M0+，133 MHz） | ML-DSA-65 | **约 256.6 ms（keygen+sign+verify 组合均值口径）** | [arXiv 2603.19340，检索摘要级](https://arxiv.org/html/2603.19340v3) |
| 智能卡（无硬件加速） | ML-DSA-65 | 估计 50–300 ms | [QNSQY EMV 分析，检索摘要级](https://quantumsequrity.com/blog/emv-chip-cards-pqc) |

- **裁决**：断言在**服务器/桌面级 CPU + 真 PQ 签名（ML-DSA/FN-DSA/SLH-DSA）**前提下成立，且实际为**亚毫秒**（0.1–0.8 ms），「毫秒级」表述偏保守、方向正确；在**嵌入式/智能卡**上不成立（数十至数百毫秒）。
- **纪律提示**：断言必须指明算法与平台。SM9 的配对验签同样是毫秒量级但不抗量子——**不得拿 SM9 的性能数据为「量子抗性毫秒级」背书**。另注意 SLH-DSA 签名耗时显著高于验签（数毫秒），若声明承诺的是「签名+验签均毫秒级」，SLH-DSA 路线不满足，须用 ML-DSA。

---

## 三、NIST PQC 标准现状（佐证，截至 2026-10-08）

- **2024-08-13，NIST 发布首批三项后量子标准**：FIPS 203（ML-KEM，密钥封装，源自 CRYSTALS-Kyber）、FIPS 204（ML-DSA，通用签名，源自 CRYSTALS-Dilithium）、FIPS 205（SLH-DSA，无状态哈希签名，源自 SPHINCS+）（[Encryption Consulting 解读，检索摘要级](https://www.encryptionconsulting.com/nist-pqc-standards-fips-203-204-205/)；[shattered.io，已读正文](https://shattered.io/ml-dsa-vs-slh-dsa-2026/)；[PQC Audit Index，检索摘要级](https://pqaudit.org/)）。
- **2025-03-11，NIST 选定 HQC 为 ML-KEM 的备份 KEM**（基于纠错码，数学假设独立于格）（[Quantum Zeitgeist，检索摘要级](https://quantumzeitgeist.com/post-quantum-security/)；[IntelliXBOM，检索摘要级](https://intellixbom.com/resources/qbom/nist-pqc-standards/)）。
- **FIPS 206（FN-DSA，源自 Falcon）仍为草案**，预计 2026 年底至 2027 年初定稿（[pqcreadiness.ai，检索摘要级](https://pqcreadiness.ai/)；[QubitChain 对比文，检索摘要级](https://qubitchain.io/blog/ml-dsa-dilithium-vs-fn-dsa-falcon-nist-signature-blockchain)）。
- 迁移时间表：NIST IR 8547（草案）提出 2030 年前后弃用、2035 年禁用经典公钥算法的过渡框架（[Sec Solutions Hub，检索摘要级](https://www.secsolutionshub.com/post-quantum-cryptography-roadmap-apac-banks/)提及 IR 8547 为草案过渡指引；具体年份以 NIST 原文为准，本报告未读 IR 8547 原文，标注指针级）。
- 产业落地：AWS KMS 已支持 ML-DSA 全参数集（CloudHSM 尚未）；Google Cloud KMS 公共预览 ML-DSA-65 与 SLH-DSA-SHA2-128s；Cloudflare 边缘至源站接受 ML-DSA 证书；OpenSSL 3.5.0（2025-04）起原生支持 ML-DSA/SLH-DSA（[shattered.io，已读正文](https://shattered.io/ml-dsa-vs-slh-dsa-2026/)）。

## 四、修正建议（对声明 v2 §3）

1. **真 PQ 路线重写**：公钥层应为 **ML-KEM（FIPS 203，密钥封装）+ ML-DSA（FIPS 204，签名）**，过渡期采用混合模式（经典 X25519/ECDH + ML-KEM-768 复合密钥交换；经典签名与 ML-DSA 双签）。SLH-DSA 作长寿命签名（档案、固件、数十年有效期文书）的保守备份；跟踪 FN-DSA（FIPS 206）与 HQC 定稿。
2. **SM9/IBC 降级**：明确标注为「经典期兼容层」，不得计入后量子安全凭据；凡以 SM9 验签性能支撑「量子抗性毫秒级」的表述一律删除。
3. **「SM10」删除或改写**：删除该引用；如需保留国密 PQ 前瞻表述，改为「NGCC 第一轮候选（84 公钥 + 35 杂凑）在评，预计 2027 年 6 月完成第一轮评估，标准化命名未定」。
4. **对称侧保留并补注**：AES-256-GCM ✔；HMAC-SHA3-512 须写明「树」指 Merkle 树还是密钥派生树，并注明 MAC 不可替代签名；ZUC 限用 256 位版。
5. **角色件归位**：QRNG 标为熵源（信任根增强，非量子抗性来源）；HSM 标为托管设施（PQ 性以固件支持清单为准，采购时核验 ML-KEM/ML-DSA 支持）；ABE 若为配对基实现则标注非后量子，PQ 需求应改以格基 ABE（研究阶段）或「ML-KEM 封装 + 对称授权层」混合替代。
6. **性能断言平台化**：改写为「服务器级 CPU 上 ML-DSA 验签约 0.1–0.2 ms（亚毫秒）、签名约 0.5 ms；嵌入式/智能卡数十至数百毫秒，须硬件加速」。

---

## 五、来源清单

**已读正文（FetchURL 全文/主体读取）：**
1. 商用密码标准研究院（ICCS），《Introduction to NGCC》IETF 125 SAAG 官方幻灯片（2026-03）：https://datatracker.ietf.org/meeting/125/materials/slides-125-saag-introduction-to-the-next-generation-commercial-cryptographic-algorithms-program-01.pdf
2. 苏州信息安全法学所转载 ICCS《新一代商用密码算法全球征集活动第一轮候选算法名单》（含 84 公钥 + 35 杂凑全名单，ICCS 2026-09-20 原文链接见文内）：https://zone.ci/secarticles/wx/577782.html
3. CSDN 博客《国密算法完整列表》（2026-04-08，「SM10」自媒体出处，低可信度证物）：https://blog.csdn.net/zmj320324/article/details/159958407
4. shattered.io《ML-DSA Beats SLH-DSA》（2026-08-22，基准与落地现状）：https://shattered.io/ml-dsa-vs-slh-dsa-2026/
5. 云南省林业和草原局《商用密码算法简介》（官方序列 SM1/2/3/4/7/9+ZUC）：https://lcj.yn.gov.cn/special/2023/1023/5399.html
6. 中国密码学会转发《关于开展新一代商用密码算法征集活动的公告》：https://www.cacrnet.org.cn/site/content/1572.html

**检索摘要级（WebSearch 返回片段，未读全文）：**
7. Cheng, "The SM9 Cryptographic Schemes", ePrint 2017/117：https://eprint.iacr.org/2017/117.pdf
8. Crypto.SE, "Is pairing-based crypto post-quantum secure?"：https://crypto.stackexchange.com/questions/106181/is-pairing-based-crypto-post-quantum-secure
9. 乾珩量子 PQC FAQ（SM2/SM9 被 Shor 破）：https://qhquantumdoc.com/pqc/faq.html
10. PQShield《AES Quantum Resistant》：https://pqshield.com/explainer-articles/aes-quantum-resistant/
11. Renesas《Latest Trends in PQC》白皮书：https://www.renesas.com/us/en/document/whp/latest-trends-post-quantum-cryptography
12. ewadirect 安全评估表（AES-256 后量子 128 位、GMAC 无影响）：https://www.ewadirect.com/proceedings/ace/volumes/vol/110/517.pdf
13. 知乎专栏（2025-07-30，「SM10 预计 2026 标准化」自媒体出处）：https://zhuanlan.zhihu.com/p/1934030571845181906
14. 百度百科「国产商用密码」：https://baike.baidu.com/item/%E5%9B%BD%E4%BA%A7%E5%95%86%E7%94%A8%E5%AF%86%E7%A0%81/68743756
15. 《电力科学与技术学报》SM9 门限签名论文（SM 序列）：https://dlkjxb.csust.edu.cn/dlgcjs/article/pdf/20220421?st=article_issue
16. 新浪财经《我国征集新一代商用密码算法》（2025-02-07）：https://finance.sina.com.cn/tech/roll/2025-02-07/doc-ineirsee0096313.shtml
17. 腾讯新闻转载 ICCS《关于征集新一代公钥密码算法提案的通知》：https://view.inews.qq.com/a/20251009A06ZNO00
18. arXiv 2111.05117（ZUC 家族 AEAD）：https://arxiv.org/pdf/2111.05117
19. IEEE《A Hardware Implementation of ZUC-256》：https://ieeexplore.ieee.org/document/9271719/
20. ePrint 2021/1439（ZUC-256 补遗）：https://eprint.iacr.org/2021/1439
21. DergiPark ML-DSA 性能评估（验签中位 159.38 µs）：https://dergipark.org.tr/en/download/article-file/5652694
22. JETNR 论文（ML-DSA-65 验签约 200 µs）：https://rjpn.org/jetnr/papers/JETNR2604377.pdf
23. arXiv 2603.19340（RP2040 上 ML-DSA-65 约 256.6 ms）：https://arxiv.org/html/2603.19340v3
24. QNSQY《EMV Chip Cards and PQC》（智能卡 50–300 ms 估计）：https://quantumsequrity.com/blog/emv-chip-cards-pqc
25. Encryption Consulting《NIST PQC Standards Explained》：https://www.encryptionconsulting.com/nist-pqc-standards-fips-203-204-205/
26. Quantum Zeitgeist（HQC 2025-03-11 选定）：https://quantumzeitgeist.com/post-quantum-security/
27. IntelliXBOM（FIPS 206/HQC 状态）：https://intellixbom.com/resources/qbom/nist-pqc-standards/
28. pqcreadiness.ai（FN-DSA 未定稿）：https://pqcreadiness.ai/
29. PQC Audit Index（标准清单与日期）：https://pqaudit.org/
30. Fu 等，格基 ABE 综述（ScienceDirect 2022）：https://www.sciencedirect.com/science/article/abs/pii/S1574013721000770
31. Hasib 等，格基 ABE 系统综述（Springer 2026）：https://link.springer.com/article/10.1007/s10791-026-09965-3
32. Palo Alto Networks Cyberpedia（QRNG 定义）：https://www.paloaltonetworks.com/cyberpedia/what-is-a-quantum-random-number-generator-qrng
33. Fraunhofer IPMS（QRNG 为密钥生成供熵）：https://www.ipms.fraunhofer.de/en/applications/Quantum-Technologies/Quantum-Communication/Quantum-Random-Number-Generation.html
34. crypto4a《What is an HSM》：https://crypto4a.com/resources/newsroom/2026-02-09-what-is-a-hardware-security-module

**指针级，未读正文：**
35. Ledger 博客（嵌入式 PQC 基准表，FetchURL 抓取失败）：https://www.ledger.com/blog-quantum-computing-threat-to-blockchain
36. 中科院软件所《The ZUC-256 Stream Cipher》规范 PDF：http://www.is.cas.cn/ztzl/zouchongzhi/202607/W020180416526664982687.pdf
37. NIST IR 8547 草案原文（迁移时间表以原文为准）：未检索到直链，经来源 25/二手转述

## 六、局限声明

1. 本报告基准数据（第二节 g 表）多为厂商/论文在特定硬件上的实测或估计，跨平台不可直接互比；「毫秒级」断言的平台分层结论以方向性为准，精确数值随实现与硬件浮动。
2. 「SM10 不存在」的判定基于公开可查的官方/准官方序列与 NGCC 官方流程文件；国家密码管理局可能存在不公开算法（如 SM1/SM7 之例），本报告无法核查未公开标准，但「不公开」不等于可作为公开声明的引用依据——声明引用不可验证标准本身即构成纪律问题。
3. Grover 折半为理论通用界；并行化与 Grover 实际开销的争论（如 Bernstein 分析）未展开，本报告采用业界通行的保守口径（折半）。
4. 知乎专栏页面（来源 13）正文未读取（403），其「SM10 预计 2026 标准化」表述取自检索摘要，作为自媒体说法的证物使用，不作为事实依据。
5. NIST IR 8547 的 2030/2035 时间节点为二手转述，未读 NIST 原文，标注指针级。
6. 本报告未对声明 v2 全文做独立取证，审议范围限于委托方转述的 §3 加密体系段断言清单。
