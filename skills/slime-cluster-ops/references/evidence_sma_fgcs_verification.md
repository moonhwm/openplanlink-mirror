# SMA（黏菌算法）FGCS 原始文献一手核验
核验日期：2026-09-09 ｜ 范围：书志 / 公式逐字 / 文献层风险 / 三要素对账
图例：【取到】=有一手来源；【部分】=有一手来源但被反爬挡下一项；【未取到】=无一手来源

---

## 1. 书志核验 【取到】

| 字段 | 值 | 一手来源 |
|---|---|---|
| 标题 | Slime mould algorithm: A new method for stochastic optimization | CrossRef API |
| 作者 | Shimin Li, Huiling Chen（通讯）, Mingjing Wang, Ali Asghar Heidari, Seyedali Mirjalili | 作者自存 pre-proof PDF 首页 |
| 期刊 | Future Generation Computer Systems (FGCS), Elsevier | CrossRef + PDF |
| 卷/页 | **Vol. 111, pp. 300–323**（2020 年 10 月） | CrossRef API（volume=111, page=300-323, published-print 2020-10）|
| DOI | **10.1016/j.future.2020.03.055** | CrossRef API |
| PII | S0167-739X(19)32094-1 | pre-proof PDF 封面 |
| Received | **2019-08-06** | pre-proof PDF 封面（"Received date: 6 August 2019"）|
| Revised | **2020-02-16** | 同上 |
| Accepted | **2020-03-29** | 同上（"Accepted date: 29 March 2020"）|
| Online | 2020-04-03（CrossRef created 2020-04-03T20:32Z；官方 README 亦记 2020/4/3） | CrossRef + GitHub README |

来源 URL：
- CrossRef: https://api.crossref.org/works/10.1016/j.future.2020.03.055
- 作者自存 Elsevier pre-proof PDF: https://aliasgharheidari.com/SlimeMouldAlgorithmANewMethodforStochasticOptimization-fgcs.pdf
- 官方代码仓: https://github.com/aliasghar68/Slime-Mould-Algorithm-A-New-Method-for-Stochastic-Optimization-
- MATLAB Central（作者发布，v1.0.7）: https://www.mathworks.com/matlabcentral/fileexchange/76619

预期值（vol 111, pp.300-323, DOI 10.1016/j.future.2020.03.055）**全部核实无误**。
注：ScienceDirect 正式页面（https://www.sciencedirect.com/science/article/pii/S0167739X19320941）被人机验证拦截，卷期页码以 CrossRef 注册数据 + 作者自存 Elsevier proof 双一手来源交叉确认。

## 2. 原公式逐字对照 【取到】

以下来自 pre-proof PDF §2.3（与作者官方 SMA.m v1.0 逐行一致，行号为 SMA.m 实际行号）：

**Eq (2.1) 位置更新（"Approach food"）：**
X(t+1) = { Xb(t) + vb·(W·XA(t) − XB(t)),  r < p
         { vc·X(t),                        r ≥ p
官方实现：SMA.m L106-110（`if r<p: X(i,j)=bestPositions(j)+vb(j)*(weight(i,j)*X(A,j)-X(B,j)); else X(i,j)=vc(j)*X(i,j)`）

**Eq (2.2)：p = tanh|S(i) − DF|**，S(i) 为 X 的 fitness，DF 为历代最优 fitness。
SMA.m L99：`p = tanh(abs(AllFitness(i)-Destination_fitness))`

**Eq (2.3)/(2.4)：vb ∈ [−a, a]，a = arctanh(−(t/max_t) + 1)**
SMA.m L92：`a = atanh(-(it/Max_iter)+1)`；L100：`vb = unifrnd(-a,a,1,dim)`

**vc：从 1 线性递减到 0**（文中文字："vc decreases linearly from one to zero"）
SMA.m L93：`b = 1-it/Max_iter`；L101：`vc = unifrnd(-b,b,1,dim)`

**Eq (2.5) 权重 W（双分支！）：**
W(SmellIndex(i)) = { 1 + r·log((bF−S(i))/(bF−wF) + 1),  condition（S(i) 排名前半）
                   { 1 − r·log((bF−S(i))/(bF−wF) + 1),  others（排名后半）
**Eq (2.6)：** SmellIndex = sort(S)
符号表（原文）：condition=S(i) 排名前一半；r∈[0,1] 随机；bF=当前迭代最优 fitness；wF=当前迭代最差 fitness；SmellIndex=fitness 升序排序序列（最小化问题）。
SMA.m L76-84：`if i<=(N/2): weight=1+rand()*log10((bestFitness-SmellOrder(i))/S+1); else: 1-rand()*log10(...)`，其中 S=bestFitness−worstFitness+eps（L73）。

**Eq (2.7) 三分支总更新（含 z 分支）：**
X* = { rand·(UB−LB)+LB,            rand < z
     { Xb(t)+vb·(W·XA(t)−XB(t)),   r < p
     { vc·X(t),                    r ≥ p
SMA.m L96-112；L55：`z=0.03`。

**z 取值依据（原文 §3.4 参数敏感性）：** "z 范围 [0,0.1]，间隔 0.01 共 11 值……z 取 0.03 时结果最优，因该概率维持了 exploration 与 exploitation 的平衡"。

**⚠ 论文-代码不一致点（一手证据）：** 论文 Eq (2.5) 印刷为 "log"（未标底数），官方 MATLAB 代码与第三方复现（MEALPY OriginalSMA）均用 **log10**。引用公式时须注明此歧义。

## 3. 文献层风险（勘误/撤稿/批评）【取到】

- **勘误/撤稿/关切声明：未检出。** CrossRef relation 字段为空（无 update-to/updated-by）；web 检索 "Slime mould algorithm" + retraction/erratum/corrigendum 无任何命中。ScienceDirect 页面 status 因反爬未能直读（部分未取到项，建议人工浏览器复核一次）。
- **批评文献（隐喻式元启发式家族）：**
  1. **Camacho-Villalón, Dorigo, Stützle (2022)** "Metaphor-based metaheuristics, a call for action: the elephant in the room", *Swarm Intelligence* 16(1):1-6——系统论证隐喻式"新"算法三宗罪：无用隐喻、缺乏新颖性（常为旧机制改名）、实验验证 biased；SMA 属其批评的算法家族。https://hal.science/hal-03460953v1/document
  2. **Rajwar, Deep, Das et al. (2025)** "Rethinking Metaheuristics: Unveiling the Myth of 'Novelty' in Metaheuristic Algorithms", *Mathematics* 13(13):2158——其 Table 2（ref[62]）将 **SMA 明确列入缺陷算法清单，标注"无效隐喻 ✓ + 结构性偏置 ✓"**。https://www.mdpi.com/2227-7390/13/13/2158
  3. **Sörensen (2015)** "Metaheuristics—the metaphor exposed", *Int. Trans. in Operational Research* 22(1):3-18——该领域方法论批评的奠基文献：隐喻不贡献科学内容，仅换术语。（被上述所有批评文献引为源头）
  补充：Camacho-Villalón, Stützle, Dorigo (2023) "Designing New Metaheuristics: Manual Versus Automatic..."（Swarm and Evolutionary Computation）——指出"新隐喻无用且造成文献混乱"。

## 4. 三要素对账（r74 引用 vs 原文/官方代码）

| 要素 | r74 口径 | 原文/官方代码口径 | 判定 |
|---|---|---|---|
| ① p = tanh\|fitness(i)−best\| | 深挖/放过决策概率 | Eq(2.2)：p=tanh\|S(i)−DF\|，DF=历代最优；用于 Eq(2.1) r<p 选分支 | **逐字吻合**（conf: 高）|
| ② z = 0.03 | 随机跳跃概率 | SMA.m L55 `z=0.03`；Eq(2.7) rand<z 时重新随机初始化位置；原文 §3.4 敏感性实验选定 | **逐字吻合**（conf: 高）|
| ③ W = 1+r·log((bF−fitness)/(bF−wF)+1) | （曾被当作）质量排序权重 | Eq(2.5) **双分支**：前半群体 1+r·log(...)，后半 1−r·log(...)；W 在 Eq(2.1) 中作为位置更新项 (W·XA−XB) 的**乘性步长权重**；代码用 log10 | **公式本身与原文前半分支逐字吻合，但 r74 只取了正分支**；且"W=质量排序权重"的语义与原文不符 |

**r74「W 语义误读」结论核验：成立（conf: 高）。**
原文证据：(a) Eq(2.1) 中 W 直接乘在探索差分项上（`vb*(weight*XA−XB)`，SMA.m L107），是**位置更新的探索步长权重**；(b) 原文 §2.3.3："W mathematically simulates the oscillation frequency... near one at different food concentrations"，即围绕 1 振荡的步长调节因子，非对个体质量排序打分的"质量权重"。排序（Eq2.6 sort）只决定 ± 分支归属，W 本身不用于选择/排序操作。

## 5. top3_likely_wrong（最可能出错处）

1. **W 公式的 log 底数**：论文印刷 "log"，官方代码实为 **log10**。凡复现/引用须按 log10，否则数值偏差大。（conf: 高，代码+第三方复现双重证据）
2. **W 漏掉负分支**：r74 及多数二手转述只写 1+r·log(...)，遗漏后半群体 1−r·log(...)（Eq2.5 others 分支）。只实现单分支等于改了算法。（conf: 高）
3. **Eq(2.1) 括号层级**：官方代码为 `vb*(W*XA − XB)`（W 只乘 XA），部分二手文献写成 `vb*W*(XA − XB)`（W 乘整个差分项），两者数学上不等价。引用时须以官方代码/原文排版 `vb·(W·XA − XB)` 为准。（conf: 中-高；原文 PDF 排版为 vb·⌊W·XA − XB⌋，与代码一致）

## 附：取到率
- 书志：取到（CrossRef + 作者自存 Elsevier proof；ScienceDirect 页面被反爬，status 直读未取到）
- 公式逐字：取到（pre-proof PDF 全文 + 官方 SMA.m 逐行）
- 勘误/撤稿：取到（阴性结果，CrossRef relation 为空 + 检索零命中；Retraction Watch 数据库未直接检索，标注为残余缺口）
- 批评文献：取到（3+1 篇）
- 三要素对账：完成
