# 一手核验：「宇宙级黏菌策略」——用黏菌模型重建宇宙网（MCPM）

核验日期：2026-09-09　|　范围：仅公开学术资料；未对外分发任何项目内容；无可实装项。
取到率总览：核心书志 3/3 取到；后续论文 3 条取到；方法参数大部分取到（SA/RA 之 RA 命名差异已澄清）；代码/数据可达性取到；评价影响部分取到（引用量级为快照值，一手批评未发现）。

---

## 1. 书志核验

| 项 | 状态 | 核验结果 | 一手来源 |
|---|---|---|---|
| ① Burchett et al. 2020 核心论文 | ✅ 取到 | Burchett, J. N.; Elek, O.; Tejos, N.; Prochaska, J. X.; Tripp, T. M.; Bordoloi, R.; Forbes, A. G. "Revealing the Dark Threads of the Cosmic Web", **The Astrophysical Journal Letters, Vol. 891, No. 2, L35**（2020-03-10 发表）。DOI: **10.3847/2041-8213/ab700c**；arXiv: **2003.04393** [astro-ph.GA]；Bibcode: 2020ApJ...891L..35B | NASA ADS 摘要页 https://ui.adsabs.harvard.edu/abs/2020ApJ...891L..35B/abstract ；DOI https://doi.org/10.3847/2041-8213/ab700c ；arXiv https://arxiv.org/abs/2003.04393 |
| ② MCPM 方法论文（Elek 一作，非 Hasan） | ✅ 取到（注意：一作是 **Oskar Elek**，任务描述中"Hasan, Burchett 等"不准确；Hasan 是后续应用论文一作） | Elek, O.; Burchett, J. N.; Prochaska, J. X.; Forbes, A. G. "Monte Carlo Physarum Machine: Characteristics of Pattern Formation in Continuous Stochastic Transport Networks", **Artificial Life, Vol. 28, No. 1, pp. 22–57**（2022-06）。DOI: **10.1162/artl_a_00351**；arXiv: **2204.01256**（2022-04-04 提交，目前引用约 27 次） | arXiv 摘要页 https://arxiv.org/abs/2204.01256 ；ALife 官方引用列表 https://www.alife.org/encyclopedia/software-platforms/mabe/ ；页码 22–57 经第三方论文参考文献核验 https://escholarship.org/content/qt1x6458cp/qt1x6458cp.pdf |
| ③a 后续：IllustrisTNG 应用 | ✅ 取到 | Hasan, F.; Burchett, J. N.; Elek, O.; Hellinger, D.; Primack, J. R.; Faber, S. M.; Koo, D. C.; Nagai, D.; Mandelker, N.; Woo, J. "Filaments of The Slime Mold Cosmic Web And How They Affect Galaxy Evolution", **ApJ 970(2):177**（2024）。arXiv: **2311.01443**。用 TNG100，MCPM 密度场替代 DTFE 输入 DisPerSE；MCPM 找到更多低显著度/弥散纤维、更好追踪暗物质分布；提出纤维线密度 Σ_fil(MCPM) 作为星系气体供给/淬灭更优预测量 | arXiv https://arxiv.org/abs/2311.01443 ；ApJ 书志经 https://arxiv.org/html/2608.04656v1 参考文献核验 |
| ③b 后续：SDSS 观测数据应用（Value-Added Catalog） | ✅ 取到 | Wilde, M. C.; Elek, O.; Burchett, J. N. 等，MCPM 拟合 SDSS Classic + eBOSS LRG 目录的宇宙网环境密度 VAC，**SDSS DR17 官方收录**。配套论文 arXiv: **2301.02719**（2023-01-06，astro-ph.CO）。对 ~325k NASA-Sloan Atlas 星系（0<z<0.1）与 LRG 四个红移切片（z≈0–0.51）分别拟合 | SDSS DR17 VAC 页 https://www.sdss.org/dr17/data_access/value-added-catalogs/?vac_id=cosmic-web-environmental-densities-from-mcpm-slimemold ；arXiv https://arxiv.org/pdf/2301.02719 |
| ③c 后续：3D/交互可视化方法（Polyphorm） | ✅ 取到 | Elek, O.; Burchett, J. N.; Prochaska, J. X.; Forbes, A. G. "Polyphorm: Structural Analysis of Cosmological Datasets via Interactive Physarum Polycephalum Visualization", **IEEE TVCG 27(2):806–816**（2021，VIS 2020）。DOI: 10.1109/TVCG.2020.3030407 | IEEE https://www.computer.org/csdl/journal/tg/2021/02/09240061/1oeZSWqO6Wc ；作者页 https://polytechnic.purdue.edu/visualization-research-group |
| 附加：Simha et al. 2020（FRB 视线方向宇宙网） | ✅ 取到 | Simha, Burchett, Prochaska et al. 2020, **ApJ 901:134**（"Disentangling the Cosmic Web towards FRB 190608"） | 参考文献核验 https://f004.backblazeb2.com/file/chinaxiv/english_pdfs/chinaxiv-202510.00044.pdf |

---

## 2. 方法参数一手提取（MCPM）

来源：arXiv:2204.01256 全文（Elek et al. 2022, Artificial Life 28(1):22–57）§4、§5；arXiv:2301.02719（Wilde et al. 2023）§3.2；PolyPhy 官方 GitHub README。

### 2.1 模型结构（逐字要点，arXiv:2204.01256 §4）

- 混合模型：离散分量=particle-like agents（位置+运动方向）；连续分量=3D 标量点阵（deposit 场=chemo-attractant）。两步交替：**propagation**（agent 并行随机游走）与 **relaxation**（deposit 场小各向同性核扩散+每格乘以 <1 的衰减；trace 场只衰减不扩散）。
- 数据点本身是不动的特殊 agent，按权重（质量）发射 deposit："deposit[agents[i].pos] += agents[i].weight * params.data_deposit"。
- agent 更新伪代码（§4）：传感方向 dir_s1 ~ P_dir(sense_angle)；传感距离 dist_s ~ P_dist(sense_distance)；比较 d0=deposit[pos+dist_s·dir_s0] 与 d1，以 P_mut(d0,d1,sampling_exponent) 概率转向（rotate_towards by move_angle），移动 dist_m ~ P_dist(move_distance)；`deposit[pos]+=agent_deposit; trace[pos]+=dist_m/move_distance`。
- 三个可调概率分布：**P_dir**（方向，单位球上相对当前方向）、**P_dist**（距离，正实数）、**P_mut**（二元"突变"决策）。
- 平衡判据：注入 deposit/trace = 衰减移除；实验参数下通常"数百次迭代"达到（§4 原文 "hundreds of iterations"）。

### 2.2 与经典 2D Jones/Max-PM 模型差异（§1、§5 逐条）

1. 全部决策随机化（probabilistic），先验可编码进 PDF；
2. 2D→3D：用二元传感决策（1+1 采样）替代 Jones 2015 3D 扩展的密集方向采样（Max-PM 2D 用 1+2 方向，其 3D 扩展至少需 1+8 方向，§5 原文）；
3. 新增 **trace** 场（agent 平衡密度记录，不参与导航），低 agent 密度下更稳健；
4. 效果对比（§5.1，Figure 7）：Max-PM 漏掉 32% 数据点，MCPM 仅漏 0.072%（同一数据）。

### 2.3 核心参数表

| 参数（论文/PolyPhy 名） | 含义 | Burchett2020/Wilde2023 宇宙网拟合值 | 来源 |
|---|---|---|---|
| Sensing angle (SA, sense_angle) | 传感锥角（PolyPhy 用弧度） | **20°**（Bolshoi-Planck 标定沿用）；PolyPhy 3D 示例 0.798 rad | 2301.02719 §3.2；GitHub README 截图 |
| Sensing distance (SO, sense_distance) | 传感距离（结构尺度主参数） | **2.37 Mpc**（BP 模拟标定）；SDSS 用 **5.2**；LRG 切片更高（随红移近 2 倍增长） | 2301.02719 §3.2, Fig.6 |
| Moving angle (≈RA/turn) | 转向角 | **10°** | 2301.02719 §3.2 |
| Moving distance / step size | 每步移动距离 | **0.1 Mpc** | 2301.02719 §3.2 |
| Sampling exponent (P_mut 锐度) | 结构锐度/"温度" | **2.5 @z=0，2.2 @z=0.5**（BP 标定）；观测数据 **3.5**（SDSS 与 LRG） | 2301.02719 §3.2, Fig.5 |
| Persistence / deposit attn | 沉积场保留率（1−衰减） | 0.0 → **0.92**（Wilde 改用更细 halo 粒度后）；PolyPhy 3D 示例 0.850 | 2301.02719 §3.2；GitHub |
| Trace attn | trace 场保留率 | PolyPhy 3D 示例 **0.999** | GitHub README |
| Data deposit / Agent deposit | 数据/agent 每步发射量 | PolyPhy 3D 示例 3.838 / 0.000 | GitHub README |
| Agent 数 | 群体规模 | TNG100 应用用 **5×10⁶ agents**（512³ 网格 ≈0.25 Mpc 体素，≤30 voxels/agent）；论文示图示 50 vs 1M agents | 2311.01443 §II.3.1；2204.01256 Fig.5 |
| 距离分布/方向分布 | 采样核 | **Maxwell–Boltzmann**（距离）、**Cone**（方向）、Stochastic mutation | GitHub README 选项 |
| 网格分辨率 | 体素化 | 512³（~100 Mpc 体积通用）；768³/1024³ 只降 MC 噪声不显著改密度场 | 2311.01443 §II.3.1 |

注：经典 Jones 记号 SA/RA（sensor/rotation angle）与 SO（sensor offset）在 MCPM 中被重参数化为 sense_angle/sense_distance + move_angle/move_distance + P_mut；「RA」在 MCPM 中无独立对应名，最近似为 move_angle（10°）。此项为术语映射，属推断，非原文。

### 2.4 收敛/实现

- 单 GPU 实时，1–2 分钟收敛（作者 IRIS-HEP 2021 报告 https://indico.cern.ch/event/1098638/attachments/2349152/4019391/PolyPhy%20@%20IRIS-HEP%202021.pdf ）。
- Wilde 2023 相比 Burchett 2020 的改动：f_T/f_o 线性累积取代指数滑窗平均；新增 orientation field f_o: R³→R³。

---

## 3. 数据与代码可达性

| 资源 | 状态 | 链接 |
|---|---|---|
| PolyPhy（官方 MCPM Python/Taichi 实现，2D+3D 管线，UCSC OSPO 孵化） | ✅ 公开 | https://github.com/PolyPhyHub/PolyPhy （org: https://github.com/PolyPhyHub ；官网 polyphy.io）。CLI 示例：`python polyphy.py 3d_discrete -f data/csv/sample_3D_linW.csv -t 200`；附 2D/3D 样本 CSV |
| Polyphorm（原始 C++ 原型+体渲染） | ✅ 公开 | https://github.com/CreativeCodingLab/Polyphorm |
| pyslime（Hasan 组读取 MCPM 输出+DisPerSE 衔接） | ✅ 公开 | https://github.com/jnburchett/pyslime （2311.01443 脚注 3） |
| SDSS DR17 MCPM 宇宙网环境密度 VAC（SDSS Classic + eBOSS LRG，可直接下载） | ✅ 公开 | https://www.sdss.org/dr17/data_access/value-added-catalogs/?vac_id=cosmic-web-environmental-densities-from-mcpm-slimemold |
| Burchett 2020 用 SDSS 37,000 星系目录 | ⚠️ 部分：论文用 SDSS DR7 等公开巡天数据（37,000 星系子样 + 350 条 HST/COS 类星体视线），重建目录本身未见单独公开下载（以 SDSS CasJobs/NSA 可复现）；**确切现成目录文件：未取到** | ESA/Hubble heic2003 https://sci.esa.int/web/hubble/-/astronomers-use-slime-mould-to-map-the-universe-s-largest-structures ；UCSC 新闻 https://news.ucsc.edu/2020/03/cosmic-web/ |
| 小规模公开星系目录样本获取路径 | ✅ | NASA-Sloan Atlas（~325k，0<z<0.1，Wilde 2023 使用）http://nsatlas.org ；SDSS DR17 Science Archive Server/CasJobs https://skyserver.sdss.org/ ；PolyPhy 仓库自带 sample_3D CSV 可即刻上手 |
| 模拟数据 | ✅ 公开渠道 | Bolshoi-Planck halo 目录（CosmoSim https://www.cosmosim.org/ ）；IllustrisTNG TNG100 公共数据 https://www.tng-project.org/data/ |

---

## 4. 评价与后续影响

- **引用量级（快照，非实时）**：Burchett et al. 2020 ≈43 次（papersflow.ai 主题页， https://papersflow.ai/research/topics/slime-mold-and-myxomycetes-research/slime-mold-maze-solving-behavior ）；MCPM 方法论文 ≈27 次（arXiv 摘要页）；Polyphorm ≈29 次（IEEE Xplore 页）。NASA ADS 实时数未取到。
- **独立后续使用（一手）**：Hasan et al. 2024 (ApJ 970:177) 与 Hasan et al. 2023 (ApJ 950:114) 用 MCPM 目录做纤维—星系淬灭；Hasan et al. 2025 (arXiv:2509.23549) 扩展到形态演化与 Roman 望远镜预测；Simha et al. 2020 (ApJ 901:134) 用于 FRB 190608 视线；SDSS 官方收录为 DR17 VAC（获巡天级采纳）。第三方应用：MIGHTEE-H I 工作（arXiv:2608.04656）引用其纤维环境方法。
- **独立批评/复现**：未发现独立复现或方法学批评论文（检索 "MCPM criticism/reproduction" 无命中）——**取到的是"无"这一负面结果**。方法学局限由作者自述：拟合为半监督、需人工在 Polyphorm 中交互判连通性，"developing a fully automated fitting procedure remains a future work"（2301.02719 §3.2）；低密度区恢复曾失败（Burchett 2020 Fig.10，Wilde 2023 §3.2 提及 sampling exponent 2.5 改善）。
- **传播影响**：NASA/ESA 联合新闻稿 heic2003（2020-03-10）、UCSC News、Science News、Space.com 等主流科普覆盖。

---

## 5. 我方玩具复现可行性评估（numpy 级 3D MCPM 小盒）

**结论：可行。** 目标=「合成点云上纤维涌现」定性演示，非天文精度。

最小参数集（按 §2 一手参数降尺度映射）：

| 参数 | 建议值（玩具） | 依据 |
|---|---|---|
| 网格 | 64³（周期边界 wrap around，PolyPhy 选项之一） | 内存 ~1 MB/场×2 场 |
| agents | 3,000–50,000（论文示 1M 出细结构；玩具 ≥数千即可见纤维） | 2204.01256 Fig.5 |
| 输入点云 | 30–100 个加权点：2–3 个富团+链状稀疏点（模拟节点-纤维几何） | 结构插值器原理 §4 |
| sense_angle | 20°≈0.35 rad（锥内均匀采样） | 2301.02719 |
| sense_distance | 3–6 体素（≈点间平均间距的 0.5–1 倍，按点数密度调） | 参数缩放原则 2301.02719 Fig.6 |
| move_angle | 10° | 2301.02719 |
| move_distance | 0.5–1 体素 | 2301.02719 (0.1 Mpc ≈ 0.4 体素@0.25Mpc 网格) |
| sampling_exponent (P_mut) | 2.5 | 2301.02719 (z=0 标定) |
| P_mut 形式 | p = d1^γ/(d0^γ+d1^γ)（γ=sampling exponent；偏向高 deposit 方向） | §4.1 定性描述，具体函数形式论文未在已取到段落给出——**此形式为常规实现，标注为推断** |
| data_deposit / agent_deposit | 数据≫agent（如 3.8 / 0.0，PolyPhy 3D 示例同比例） | GitHub README |
| deposit attn | 0.85–0.92 | 2301.02719 / GitHub |
| trace attn | 0.99–0.999 | GitHub |
| 迭代数 | 数百（论文原话）→ 玩具 300–1000 步 | 2204.01256 §4 |

资源估算：每步每 agent 常数次纹理采样与 RNG ⇒ numpy 向量化下 5×10⁴ agents × 500 步 ≈ 2.5×10⁷ 次更新，纯 numpy CPU 约数十秒至数分钟；扩散用 3×3×3 核 scipy.ndimage/滑窗卷积，64³ 可忽略。瓶颈在 agent 循环，Numba/GPU 非必需。判据：trace 场出现连接相邻点团的连续细丝、且 fitness E（Wilde 2023 §3.2 公式 E=⟨f_T(d_pos)/d_mass⟩）随迭代上升并稳定。

---

## 6. top3_likely_wrong（最可能出错处）

1. **任务描述称 MCPM 方法论文为「Hasan, Burchett 等」——错误**：方法论文一作是 Oskar Elek（Artificial Life 2022；Polyphorm 2021）；Hasan 是 2023–2024 TNG 应用论文一作。引用时若写 Hasan et al. 2022 MCPM 方法即为书志错误。
2. **经典 SA/RA/SO 记号与 MCPM 参数不一一对应**：MCPM 重参数化为 sense_angle/sense_distance/move_angle/move_distance/sampling_exponent，且用弧度（PolyPhy）；若按 Jones 2D 模型默认值（如 SA=45°）直接搬用会偏离论文标定值（20°/10°，传感距离随数据密度从 2.37 Mpc 到 >5 Mpc 大幅变化）。
3. **引用量与「无批评」结论是快照+检索负面结果**：引用数为各站点不同时点值（可能滞后），"未发现独立复现/批评"不等于不存在；NASA ADS 实时引用数未取到，若报告需精确值应查 ADS。

### 未取到清单
- Burchett 2020 论文内部原始超参数表（arXiv:2003.04393 全文表）——以 Wilde 2023 转述标定值替代。
- Elek 2022 论文 §6/§7 的逐字参数表（PDF 抓取只返回前半部分）——参数名/机制已取到，数值以 PolyPhy 官方默认值+2301.02719 替代。
- NASA ADS 实时引用数；Jones 2010 原文参数默认值。
- P_mut 的精确函数形式（论文已取到段落仅定性描述）。
