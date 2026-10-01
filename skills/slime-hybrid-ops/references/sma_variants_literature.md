# SMA 变体文献谱系（r106 E1 深挖，2026-09-10）

基线：Li S. et al. "Slime mould algorithm: A new method for stochastic optimization", FGCS 111 (2020) 300–323, DOI 10.1016/j.future.2020.03.055。开源参考：mealpy `SMA.OriginalSMA`（p_t=0.03）。
核验纪律：conf=高=DOI/卷期可核；conf=中=部分字段未核。全部条目来自当轮检索，未逐条打开 DOI 的已标注。

## 1. 混沌映射
- Altay O. Chaotic slime mould optimization algorithm…, Artificial Intelligence Review 55(5) (2022) 3979–4040. DOI 10.1007/s10462-021-10100-5 [conf 高]
- Singh T. Chaotic SMA for economic load dispatch, Applied Intelligence 52 (2022) 15325–15344. DOI 10.1007/s10489-022-03179-y [高]
- Abid M.S. et al. Chaotic SMA for load-shedding, Ain Shams Eng. J. 13(4) (2022) 101659. DOI 10.1016/j.asej.2021.101659 [高]
- Chen H., Li X. et al. CHDESMA（混沌+DE 混合）, IEEE Access 10 (2022) 66811–66830 [中：DOI 未核]
- Zhang Y. et al. BDSSMA（Bernoulli 混沌+Brownian/Levy+镜面反射+蒲公英）, Biomimetics 8(6) (2023) 482. DOI 10.3390/biomimetics8060482 [高]；明确批评原生 z=0.03 多样性不足

## 2. Levy 飞行
- Zheng L. et al. LRSMA 路径规划, Drones 7(4) (2023) 257 [高]
- Kundu T., Garg H. et al. LSMA-TLBO, Advances in Engineering Software [中：卷期未核]
- Qi A., Zhao D. et al. SDSMA 方向交叉+自适应 Levy, J. Computational Design and Engineering [中]
- EISMA（均值+Levy+精英交换+双差分）, Ain Shams Eng. J. (2024), pii S1110866524000057 [高]
- Levy 重构 vb 参数化, Energies（卷期 2026 预排，数值需再核）[中]

## 3. 对立/准对立学习
- Naik M.K. et al. AOSMA 自适应对立, Soft Computing 25(22) (2021) 14297–14313. DOI 10.1007/s00500-021-06140-2 [高]
- Sharma A.K. et al. OSMA, ESWA 214 (2023) 119002 [高：文章号双源确认，DOI 拼写未直接验证]
- Patra D.K. et al. QOBL-SMA 乳腺 MRI, Multimedia Tools and Applications 82 (2023) 30599–30641. DOI 10.1007/s11042-023-14329-w [高]
- Houssein E.H. et al. OOBL-SMA 正交对立 MPPT, Neural Computing and Applications 34 (2022) 3671–3695 [高]
- Rizk-Allah R.M. et al. CO-SMA 混沌+对立, ISA Transactions 121 (2022) 191–205. DOI 10.1016/j.isatra.2021.04.011 [高]

## 4. 混合算法
- Houssein E.H. et al. SMA-AGDE（SMA×自适应引导DE）, ESWA 174 (2021) 114689. DOI 10.1016/j.eswa.2021.114689 [高，被引~178]
- Gao Z.-M. et al. GWO-SMA, J. Phys.: Conf. Ser. 1617(1) (2020) 012034. DOI 10.1088/1742-6596/1617/1/012034 [高]
- Gao Z.-M. et al. HPSO-SMA, IEEE AUTEEE 2020: 304–308 [高]
- Samantaray S., Sahoo P. ANFIS-PSOSMA 洪水预测, Environ. Sci. Pollut. Res. 30 (2023) 83845–83872 [高]
- Ali & Syed Nasir. SMA-PSO 双重优化, ASEAN Eng. J. (2025). DOI 10.11113/aej.v15.23372；IEEE 33 节点损耗降 49.64% [中：单一来源]
- GASMA 轨迹分割（GA 全局+SMA 局部+适应度偏差自适应切换）, Information Processing in Agriculture (2024) [高]
- GSMA 微电网经济调度, Prot. Control Mod. Power Syst. (2025). DOI 10.1186/s43067-025-00252-7 [高]
- Leela Kumari & Kamboj. SMA×SA, Complex & Intelligent Systems (2022). DOI 10.1007/s40747-022-00852-0 [高]
- Abdel-Basset M. et al. HSMA_WOA 胸片分割, Applied Soft Computing 95 (2020) 106642. DOI 10.1016/j.asoc.2020.106642 [高]
- SMWOA 机械臂轨迹, Algorithms 15(10) (2022) 363 [高]
- Yin S., Luo Q. et al. EOSMA 7-DOF 逆运动学, Scientific Reports 12 (2022) 9421. DOI 10.1038/s41598-022-13516-3 [高]
- Ewees et al. SMA×GBO, ESWA 213 (2023) 118872 [高]

## 5. 自适应权重/参数
- Lin H. et al. ASMA 光伏辨识（三角+双最优变异+二项交叉）, Energy Sci. Eng. 10(7) (2022) 2035–2064 [高]
- Deng L., Liu S. AGSMA 自适应分组, ESWA 222 (2023) 119877. DOI 10.1016/j.eswa.2023.119877 [高]
- Alfadhli J. et al. FP-SMA 波动种群, Neural Computing and Applications (2022). DOI 10.1007/s00521-022-07034-6 [高]
- 非线性 a 曲线 sigmoid 替代 arctanh（降水预测用）；黄鹤等 GSMA（Logistic 混沌+自适应惯性+Cauchy）UAV 三维路径, 上海交大学报 57(10) (2023) 1282–1291. DOI 10.16183/j.cnki.jsjtu.2022.191 [高]
- Yin S., Luo Q. et al. DTSMA 优势种群+t 分布变异, Math. Biosci. Eng. 19(3) (2022) 2240–2285 [高]

## 6. 量子/二进制/离散
- Yu C., Heidari A.A., Xue X. et al. WQSMA 量子旋转门, ESWA 181 (2021) 115082. DOI 10.1016/j.eswa.2021.115082 [高；CEC2014 双 14 算法排名第一]
- Zhang Y. et al. 动态量子旋转门+对立, Algorithms 15(9) (2022) 317 [高]
- Abdel-Basset M. et al. BSMA 攻击-觅食特征选择, Comput. Ind. Eng. 153 (2021) 107078. DOI 10.1016/j.cie.2020.107078 [高；28 UCI]
- Abdollahzadeh B. et al. 二进制 SMA 0-1 背包, Eng. with Computers (2022). DOI 10.1007/s00366-021-01470-z [高]
- Hu J. et al. BDFSMA, Knowledge-Based Systems 237 (2022) 107761. DOI 10.1016/j.knosys.2021.107761 [高]

## 7. 多目标
- Premkumar M. et al. MOSMA 精英非支配, IEEE Access 9 (2021) 3229–3248. DOI 10.1109/ACCESS.2020.3047936 [高；开源 github.com/mpremme/Multiobjective_SMA]
- Houssein E.H. et al. 外部存档 MOSMA, ESWA 187 (2022) 115870. DOI 10.1016/j.eswa.2021.115870 [高]
- Cai X., He Z. 参考点+逻辑混沌 MOSMA, IEEE Access 11 (2023) 72088–72100 [高]
- MOSMA 供水管网（EPANET）, Water Resources Management. DOI 10.1007/s11269-025-04462-6 [高]

## 8. 应用证据
BDSSMA-ELM 负荷预测（Biomimetics 2023）；SMA-ANN 软土桩基沉降（6 模型最优）；SMA-SVM COVID 严重度（IEEE Access 9:121996–122015）；SMA-KNN 医学分类（DOI 10.1109/ACCESS.2021.3105485）；MOSMA-SVR 铣削振动（Applied Soft Computing）。

## 9. Physarum 路由/网络实证+开源
- Tero/Kobayashi/Nakagaki 管径-流量正反馈, J. Theor. Biol. 244(4) (2007) 553–564. DOI 10.1016/j.jtbi.2006.07.015 [高]；前身 Physica A 363 (2006) 115–119
- 东京铁路实证, Science 327(5964) (2010) 439–442. DOI 10.1126/science.1177894 [高]
- 迷宫最短路 Nature 407 (2000) 470；收敛证明 Becchetti et al. ICALP 2013. DOI 10.1007/978-3-642-39212-2_42 [高]
- IPPA 改进最短路, Scientific World J. 2014: 487069. DOI 10.1155/2014/487069 [高；15 网 100% 最优]
- 动态图 SPT, Information Sciences 405 (2017) 123–140. DOI 10.1016/j.ins.2017.04.021 [高]
- 路由协议族 P-iRP（IEEE VTC 2013）/PRA-APC（70% 表述 conf 中）
- 开源：robert-30/physarum-maze（Py）/ fogleman/physarum（Go,~918★）/ samjsnn/Physarum-Transport-Network（Web）/ MOSMA 官方 / mealpy
- 综述：Sun Y. Physarum-inspired Network Optimization: A Review, arXiv:1712.02910

## 10. 综述三篇（2025–2026 专门综述未发现，如实登记）
1. Chen H. et al. IJSS 54(1) (2023) 204–235. DOI 10.1080/00207721.2022.2153635 [WoS 98 篇]
2. Gharehchopogh F.S. et al. Arch. Comput. Methods Eng. 30(4) (2023) 2683–2723. DOI 10.1007/s11831-023-09883-3
3. Wei Y. et al. Biomimetics 9(1) (2024) 31. DOI 10.3390/biomimetics9010031 [130 篇；modified/hybridized/multi-objective(17%)/discrete(8%) 分类]

## top3_likely_wrong
1. CHDESMA IEEE Access DOI 未验证（卷期页码已核）
2. PRA-APC「70% 改善」语义含糊、venue 未确认
3. OSMA DOI 拼写（10.1016/j.eswa.2022.119002）未直接打开验证
