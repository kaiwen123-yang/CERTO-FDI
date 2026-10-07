# CERTO-FDI 定理级定向文献对照 v1

日期：2026-10-07。依据：`RESEARCH_PLAN.md`、`references/audit_20261007/TAC_THEORY_ROADMAP.md`、`references/audit_20261007/research_review.md`。此报告只维护文献证据，不更新根主张台账。

## 判断及阅读范围

**所核查的九篇主文献没有提供当前候选锐亏损定理的直接代入结果；最近对 Gaussian 凸集风险接口则明确属于已有方法。** 可继续检验的新命题应是同一合同内的任意确定性日历逆界、可达构造和有色缺测边界首项，而不是“首次考虑反馈、记忆、切换代价、全史 nuisance、凸集检验或最优切换结构”。本轮为定向核查，不能证明穷尽新颖性；Esna Ashari 两篇及趋势设计两篇近邻的完整定理尚未取得。

十一篇原始全文已从作者机构或 arXiv 下载，PDF、提取文本、URL、页数和 SHA256 保存于 `work/literature_20261007/`；原始 PDF 哈希在 `download_manifest.json`。下文页号均为 **PDF 页号，从 1 开始**；有出版社页码时另列。Classens 的 PDF 首页是机构封面，因此论文首页是 PDF 第 2 页。核查覆盖问题定义、所列结果、承重证明段；不声称逐行重证全部十一篇论文。TAC2013 的公式文字提取丢失，已用 PDF 图像复核第 3、4、6 页；Classens 第 5 页的 tight-envelope 定义和证明已图像复核。

技能流程：nature-academic-search 的 multi-source-search 定向来源核验；其 academic-search MCP 在本会话未挂载，直接使用 primary web/author/arXiv 入口；检索前 preflight 通过 CrossRef、arXiv、PubMed 可达性检查。PDF 公式用提取与渲染交叉核对。

## 当前需要对齐的合同

本报告绑定已冻结的 `outputs/problem_contract_v1.md`（2026-10-07，SHA256 `99519b20be43dd2cd6a3690c86217bf574b5ef72c46e189f7622c108c2b0b7ef`）。M0 的原始均值为 `Y_i=s_i b^h(j_i)+1_(h=1)a_(j_i)+epsilon_(j_i)`；共同已知平稳 AR(1) covariance；固定健康前缀但健康初值不固定；已知 post-onset 线性增长；健康两侧各 B/2、r/2，差分为 B、r；H 已知，日历确定，切换至少 k 个真实缺测槽，无噪声 reset。信息集仅含指定标量保留读数，排除额外传感、控制命令、第三任务和移动读数。O 使用同一前缀及全部 post-onset 槽并知道健康解释。M1 的控制实现属于后续桥梁，不能作为当前 M0 已证性质。下列判断随合同改变而须重审；矩阵每行带同一合同路径、版本与哈希。

## 主文献的定理合同

### L01 — Nitinawarat、Atia、Veeravalli，TAC 2013

来源：[作者全文](https://vvv.ece.illinois.edu/papers/journal/niti-atia-veer-tac-2013.pdf)，DOI 10.1109/TAC.2013.2261188。位置：§II–III，PDF pp.2–5 / 出版 pp.2452–2455；Proposition 1、Theorems 1–2；§IV 的 Theorems 3–4，PDF pp.5–6；Appendix A/B，PDF pp.8–13。

有限 controls，已知有限简单假设；条件于当前 control 与假设，观测对全部过去独立，分布不随时间变，且每一对 log-likelihood ratio 有有限二阶矩。固定 N 时允许开环和随机因果策略。**二元结论是 Proposition 1**：最佳最大误差指数为最大 control-Chernoff 信息，纯 stationary 开环达到；多元 Theorem 1 给开环指数，Theorem 2 给因果界。序贯结论的风险为 `R_i=Σ_{j≠i}prior_j P_j(decide i)`，不是本项目固定 H 的两侧功效合同。此文没有整史漂移对手、增长信号或真实 dead slots，因而不能将二元开环最优性直接迁到本项目。[原始结果](https://vvv.ece.illinois.edu/papers/journal/niti-atia-veer-tac-2013.pdf)

### L02 — Nitinawarat、Veeravalli，arXiv:1310.1844v2

来源：[全文 v2](https://arxiv.org/pdf/1310.1844v2)。位置：§3，PDF pp.6–7，(3.1)–(3.2)；Theorems 4.1–4.2，pp.8–10；§5 Theorem 5.1，p.11；证明 Appendix pp.14–22，特别 Lemma 6.2 与占用测度论证。

有限且**完全观测**的 Markov observation，固定已知转移 `p_i^u(y|y_prev)>0`，固定 y0；策略可依赖全部记录。每步 action cost `c(u)>0`，证明使用正的最小 cost；可识别情形还需最优 KL/cost 率 `d_i*>0`。Theorem 5.1 给风险趋零时最小预期累计 cost 的首项 `−log R_i/d_i*`，其中 `R_i=max_{j≠i}P_j(decide i)`；ML 自调策略加稀疏探索达到。其 oracle 知道真实 hypothesis，区别于本项目知道健康解释的 oracle。隐藏 Gaussian 状态、时变健康路径、观测删除及 H^(5/2) 二阶差均不在该结果内；增强状态须另证平稳性/可观察性/正转移条件。[原始结果](https://arxiv.org/pdf/1310.1844v2)

### L03 — Vaidhiyan、Sundaresan，Active Search with a Cost for Switching Actions

来源：[arXiv:1505.02358v1 全文](https://arxiv.org/pdf/1505.02358v1)，2015 ITA。位置：§II-A，PDF pp.2–3，Assumptions (I),(IIa),(IIb)；§II-B，p.4，Theorem 4、Proposition 5、Theorem 6；Appendix pp.5–8。

有限简单假设、有限 actions；已知 `q_i^a` 且条件无记忆；LLR 二阶矩有限，(IIb) 要求每个最优 mixed action 对每一假设对都有正概率选到可区分 action。cost 是 `τ+Σg(A_l,A_{l+1})`，g 非负、有界、同 action 为零；切换仍有一个普通观测。Theorem 6 在误差向量各项同阶趋零，**先风险趋零，再 sluggish 参数趋零**时给 `E_i C/log L→1/D_i`。固定 sluggish 参数只有 Proposition 5 的额外收费上界，不能改成固定参数严格最优。漂移在移动时继续演化、增长信号和固定终点信息亏损均未覆盖。[原始结果](https://arxiv.org/pdf/1505.02358v1)

### L04 — Lambez、Cohen，Anomaly Search with Multiple Plays under Delay and Switching Costs

来源：[arXiv:2108.03082v1 全文](https://arxiv.org/pdf/2108.03082v1)；arXiv 列出相关出版社 DOI 10.1109/TSP.2021.3136810，本轮以 arXiv 版本定理为准。位置：§II，PDF pp.4–5；§III-C Theorem 1，p.12；Appendix Lemmas 1–7，pp.17–27。

M 个过程，已知 L 个异常，最多 K 个同时观测（多异常设计要求 K≥L，§III-B pp.10–11），采样 iid 且正常/异常分布 f/g 已知；策略从 LLR 自适应选择过程，Bayes prior 已知。风险 `P_error+cEτ+sEτ_switch`，`s=O(c)`。Theorem 1 给 CCS 的有限误差 O(c)、预期切换 O(1)，以及 c→0 时 Bayes risk 首项 `−c log c/I*`。原文的 idle time 用于避免同一过程被多台机器同时观测，不等于切换后固定失去 k 个真实槽。没有健康对手和闭环记忆；“闭环 sensing”是在线选择过程，不能作为物理反馈控制设计定理。f/g 的可识别性与 KL 率须非退化。[原始结果](https://arxiv.org/pdf/2108.03082v1)

### L05 — Classens 等，Optimal Fault Detection for Closed-Loop Linear Uncertain Systems

来源：[TU Eindhoven 全文](https://pure.tue.nl/ws/files/361857968/Optimal_Fault_Detection_for_Closed-Loop_Linear_Uncertain_Systems.pdf)，CDC 2024，DOI 10.1109/CDC56724.2024.10886525。位置：§III，PDF pp.3–4 / 出版 pp.1327–1328；§IV Theorem 1 与完整证明，PDF p.5 / 出版 p.1329；Remarks 8–9，PDF p.6。

连续时间不确定 LTI 系统，robustly stabilizing K 已给定；检测器可读取 u、y，设计稳定 residual post-filter R。健康扰动用诱导范数，模型参数/动态不确定性为 Δ；目标是所有频率的故障奇异值增益与 H∞ 扰动抑制。Theorem 1 在稳定可检测、满行秩直接传递、无虚轴零点及 tight-envelope (A4) 下给 co-inner/outer 逆后滤波器。无主动日历、Gaussian PFA/power、健康限速类或终点亏损；不能作为本项目统计最优证据。[原始结果](https://pure.tue.nl/ws/files/361857968/Optimal_Fault_Detection_for_Closed-Loop_Linear_Uncertain_Systems.pdf)

**引用前的独立核查点：** Definition 5 的 tight-envelope 是对 Δ 取最坏值的方向增益等式，而证明 (17) 写成每个 Δ 都有 `||R Gtilde_d(Δ)||∞=||R Gbar_d||∞`。标量 `Gtilde_d(Δ)=Δ∈[1,2]`、`Gbar_d=2` 满足最坏 envelope 紧，但 Δ=1 的两个范数不同。因此该步的逐 Δ 表述需要更强假设或将分母改成 robust supremum；本轮标记 **PENDING**，不照搬其逐 Δ 最优结论，也不据此宣称论文整体错误。

### L06 — Scott、Findeisen、Braatz、Raimondo，Automatica 2014

来源：[MIT 作者全文](https://web.mit.edu/braatzgroup/input_design_for_guaranteed_fault_diagnosis_using_zonotopes.pdf)，50:1580–1589。位置：§2，PDF p.2；§3.2、§4 Theorem 3 与证明，p.3 / 出版 p.1582；§5，pp.4–5，(18)–(29)；§7，p.6。

已知有限线性模型与允许 fault scenarios；固定 N；初始状态、逐时刻扰动、测量误差为紧 zonotopes。开环输入在输入/状态约束下使不同 scenarios 的**完整输出历史集合**不相交；Theorem 3 将其等价为 pairwise zonotope 排除条件，§5 给 MIQP 输入优化。零错误保证来自点态有界误差，不能代替无界 Gaussian 风险。全史耦合已由 (14) 明确保留；“不能逐块重置 nuisance”本身不是新意。有限盒限速健康可通过增广状态/增量扰动与状态约束建模，但当前无界初值、统计风险和全日历锐渐近还需新的证明。[原始结果](https://web.mit.edu/braatzgroup/input_design_for_guaranteed_fault_diagnosis_using_zonotopes.pdf)

## 已有 Gaussian 凸集接口：必须作为工具引用

L07：[Goldenshluger–Juditsky–Nemirovski，arXiv:1311.6765v7](https://arxiv.org/pdf/1311.6765v7)，§2.1–2.2 pp.3–4，Theorem 2.1；§2.3.1 pp.5–7，尤其 p.6。L08：[Juditsky–Nemirovski，arXiv:1604.02576](https://arxiv.org/pdf/1604.02576)，§3.2.3 pp.12–13，Propositions 3.3–3.4 及完整短证明。

已知共同非奇异 covariance Σ，非空凸均值集合且最近对达到时，白化最近距离 d 给中点 affine test 的 minimax 最大错误 `Φ(−d/2)`；最坏点达到此值，因此可用最近简单对的 Neyman–Pearson 界给反向界。按 null 阈值 `z_(1−α)` 偏置，可得到统一 power `Φ(d−z_(1−α))`，目标 power≥1−β 等价于 `d≥z_(1−α)+z_(1−β)`。这最后一步是共同 covariance 情形的直接正态分位数推论，不是文献对任意非 Gaussian/adaptive 实验的承诺。[最近对接口](https://arxiv.org/pdf/1311.6765v7)，[正态尾界](https://arxiv.org/pdf/1604.02576)

适用边界：这些章节的现成存在性条件含至少一侧 compact；本项目无界幅值类不能只说“闭凸”就调用。有限 H 的差分若为闭多面体，可用投影及去除公共无界方向另证最近对存在；两侧均值集合分别最近对的提升也须检查。若 covariance 随健康/假设变、读出非线性、方向从同批数据选出或日历依数据自适应，单一共同 Gaussian 最近对公式不能直接使用。没有逐条核查整篇 L07/L08 的其他构造。

## 统计实验设计与 Allan 漂移碰撞核查

### L11 — Bojinov、Simchi-Levi、Zhao，switchback 最优设计

来源：[arXiv:2009.00148v4 全文](https://arxiv.org/pdf/2009.00148v4)，2025-09-17 版本（作者说明修订 definition 的文字笔误；本轮不将它与旧版定理编号混用）。位置：§2 Assumptions 1–2，PDF pp.6–7；regular designs，p.8；HT estimator 与 squared-error risk (4)–(6)，pp.10–11；Assumption 3、Lemma 1、Theorem 1，p.12；**Theorem 2**，p.13；EC.3.6.1 证明，pp.56–57。

单元的潜在结果非预见、known m-carryover，并逐时刻/assignment path 有界；regular designs 在预定点独立抛硬币确定后续 treatment。对固定 HT estimator 的最坏随机化 MSE，Theorems 1–2 给公平硬币和显式 subset-selection 目标；T=nm、n≥4 时有最优规律间隔，首尾 epoch 为 2m，中间为 m。对手可随时变，并非仅固定低阶趋势，但没有相邻 Lipschitz 限制；randomization points 也不保证实际 treatment 发生切换。carryover 后非全 0/全 1 的结果影响 estimand 可用性，区别于设备真实缺测。它直接否定“首次 minimax 切换结构”叙述，但不能代入 M0 的确定性诊断信息/增长故障二阶 oracle 亏损。[原始结果](https://arxiv.org/pdf/2009.00148v4)

### L12 — Schieder、Kramer，Allan variance 与真实 dead time

来源：[arXiv:astro-ph/0105071v1 全文](https://arxiv.org/pdf/astro-ph/0105071)，2001。该 preprint 标题为 Optimization of radio astronomical observations using Allan variance measurements；后续出版社题名用 heterodyne observations，本轮按已下载版本定位。位置：§3，PDF pp.3–5，(5)–(13)；§4.1，pp.5–7，(15)–(17)；§4.2 mapping，pp.7–10。

辐射计白噪声加具有有限物理 cutoff 的随机功率谱漂移；Allan variance 为 `a/T+bT^β`，重点处理 β=1、2（谱指数 α=2、3）。source/reference 等长积分之间有真实移动 dead time，cycle=`2T+T_d`；(16) 给固定总观测时间的累计方差，并优化 T；(17) 与理想无 overhead 的 radiometric 基准比较效率。对称 On–Off/Off–On 减少移动的结构确为前史，不能当新发现。其 signal 与 variance/covariance 合同不含两侧 Lipschitz 全称健康路径、线性增长故障或全部确定性日历的 H^(5/2) Gaussian 信息亏损。[原始结果](https://arxiv.org/pdf/astro-ph/0105071)

### L13 — Ossenkopf，任意谱指数的对称观测优化

来源：[arXiv:0712.4335 全文](https://arxiv.org/pdf/0712.4335)，§4.2 pp.7–8，(14)–(18) 的 Allan 时间定义；**§5 pp.10–11，(23)–(27)**；p.11 末另讨论 second-order observing loops。

将漂移功率谱推广到 0<α<3（α=1 需另一对数表达），明确 reference–source–source–reference、相同积分时长及真实 dead time；(26) 给固定 total time 的总随机方差，(27) 规定最优 phase length 根。不是只讨论无缺测 AB 经验交替，也不是只给 qualitative guideline。有限截止尺度和谱模型决定可用范围。物理 dead time、对称消线性漂移及最优 hold 的一般思想已有直接前史；但这些结果不对最坏 Lipschitz 路径取 inf，不以 growing fault 诊断风险或 full-record oracle 信息为目标，未直接给当前二阶亏损定理。[原始结果](https://arxiv.org/pdf/0712.4335)

### L14/L15 — 趋势鲁棒/最小换级成本：尚待全文

[Cheng–Steinberg，Trend robust two-level factorial designs](https://academic.oup.com/biomet/article-abstract/78/2/325/232157)，Biometrika 78:325–336，1991，DOI 10.1093/biomet/78.2.325：出版社摘要明确列出 AR(1) error 与 time-series trend 模型，故不能概括为“仅多项式趋势”。出版社页面显示 purchase/PDF，本轮没有取得原始全文；作者主页没有该旧稿下载入口。**结果覆盖 UNREVIEWED**，不能据摘要判断不存在当前条件。

[Coster–Cheng，Minimum Cost Trend-Free Run Orders of Fractional Factorial Designs](https://projecteuclid.org/journals/annals-of-statistics/volume-16/issue-3/Minimum-Cost-Trend-Free-Run-Orders-of-Fractional-Factorial-Designs/10.1214/aos/1176350955.full)，Annals of Statistics 16:1188–1205，1988，DOI 10.1214/aos/1176350955：Berkeley 作者出版目录及 Purdue technical-report 目录确认；Euclid 页面返回 security check，Purdue 当前目录只提示联系获取旧全文。本轮未取得全文，**结果覆盖 UNREVIEWED**；没有对外联系。

一个有限反例只说明模型区别：趋势 contrast `w=(1,−1,−1,1)` 消去常数与线性趋势，而节点健康路径 `h=r(0,1,0,0)` 在单位间隔满足 Lipschitz r，却有 `w·h=−r`。它不能否定 Cheng–Steinberg 的未审时间序列定理，不能代替当前模型的协方差/任务符号对齐；它说明 polynomial annihilation 单独不能充当全 Lipschitz 统一风险保证。

## 信息旁路与创新收缩判断

|合同检查|若可用时怎样破坏当前叙述|当前必须落实的动作|
|---|---|---|
|健康不敏感任务/姿态|允许长期使用 `a(q)=0` 而故障增益非零时，无需任务切换即可读到故障；漂移亏损不能限制该实验|将实际可行姿态/任务集合纳入合同，或以工作任务限制解释排除；仅两姿态证明不能称一般机器人极限|
|其他关节或观测通道|例：`y1=f+h+e1,y2=h+e2`，差分消去 h；两个独立等方差噪声时信息为 `Σ f(t)^2/(4σ²)=Θ(H³)`，不支付切换停测|对完整可用传感/命令/状态观测做健康子空间与故障方向检查；不能只审目标关节|
|u、控制器状态及快采样历史|Classens 使用 u/y 双通道。若 u 是所记录 y 的共同已知确定函数，不增加信息；若 u 保留未记录快采样/隐含状态，则可能比低频残差有更多信息|明确检测器的 sigma-field、已知 reference、内部状态及采样精度；逐个说明可用/排除理由|
|移动中观测|协议停测或证书暂缺仅限制协议，不能推出物理系统无法观测|把 dead slots 写成信息合同；若观测实际可得，另评估能否形成无漂移方向|
|共同可逆滤波/反馈变换|同一、已知、参数无关的双射保留全部复合实验风险；只改 covariance 却不改故障/健康像会造假收益|由根代理证明完整实验的风险不变性，并把真实收益归到可用观测、未知依赖或控制约束|
|oracle 含义|L02 的 oracle 知道真实 hypothesis；当前 oracle 若知道健康路径或看见全部槽，信息集不同|O 与 G 采用同一物理时间/预算，并分开写清健康知识、假设知识与缺测知识|

切换收费与真实时间不是名称差别：现有 stationary 简单分布的 g 可以计入预期 cost，却不会自动让故障 `f(t)` 在跳过 k 槽期间继续增长，也不会让全史健康路径随真实时间漂移。对有色过程，删除观测还改变保留记录的边缘转移/协方差；这是本项目必须显式求出的实验，而非把缺测值置零后沿用完整白化。

**可以采用的限定创新表述：** 对一个冻结的、无旁路的稳定 Gaussian 通道与确定性已知终点日历类，研究全史健康漂移和真实停测的联合 minimax 信息亏损，并尝试证明任意日历逆界及匹配构造。称首项 sharp 必须在同一合同、参数范围与极限区间匹配常数并证明余项一致可忽略。仅有单间隙 Schur/Markov 恒等式、替换 σ 为有效方差、有限枚举最优或一般 ISS/LMI 应用均不构成该主贡献。

## 尚未完成的最近邻核查

1. [Esna Ashari 等，Effects of feedback on active fault detection](https://www.sciencedirect.com/science/article/pii/S0005109812000714)，DOI 10.1016/j.automatica.2012.02.020：出版社引言、结论和节选可读；完整定理/证明未取得。HAL 的尝试受到 Anubis 拒绝。只保留其存在和问题方向，不以节选替代定理审查。
2. [Esna Ashari 等，Active Robust Fault Detection in Closed-Loop Systems: Quadratic Optimization Approach](https://doi.org/10.1109/TAC.2012.2188430)：作者出版目录确认出处 TAC 57:2532–2544；IEEE 全文入口返回 418，DOI 入口工具无法取得。完整模型、定理和证明 **NOT_OBTAINED**。这是本轮剩余的相关文献缺口，不代表整个研究已阻塞。
3. Cheng–Steinberg 与 Coster–Cheng 两篇全文仍未取得，详见 L14/L15。不能将这些缺口标成“不覆盖”，也不能把全部趋势设计归为多项式类。
4. 自适应 composite testing、故障未知起点/增长检测与 minimax drifting nuisance 的更广定向检索尚未完成。本轮仅允许“在所核定理中未见直接覆盖”，不能写“首次”或“全面证明新颖”。

## 可复核文件与下一步

- `outputs/novelty_matrix.csv`：15 条记录，11 条全文定向核查、4 条缺口；每行含来源、页/节/定理、假设、信息结构、nuisance、策略、风险/时域、现有结论、迁移边界、旁路及 M0 合同哈希。
- `work/literature_20261007/download_manifest.json`：11 个 PDF 的 URL、版本对应文件、SHA256；矩阵的 pdf_sha256 与此文件相连。
- `work/literature_download.py` 与 `work/literature_read_pages.py`：下载/页级提取脚本；已有 cached PDF 为本轮冻结证据，重下载可能随默认 arXiv 版本更新，应比较哈希。

下一步按依赖推进：维护已冻结 M0 的单通道信息合同与 oracle，另审 M1 机械旁路；把最近对统计接口标为经典工具并单独证明无界类距离达到条件；以任意日历的有色漂移逆界和达到性为主理论目标，同时补完四项全文缺口。
