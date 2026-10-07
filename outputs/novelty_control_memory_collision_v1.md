# Controlled-memory 新主张与最近邻：定向碰撞复核 v1

日期：2026-10-07。范围：将已核原始文献与当前 M2/M2S 主张重新对齐，不重复数学证明审查或稿件基础集成，不修改旧 M0 矩阵/根台账。不声称穷尽历史新颖性。

**结论：本轮实际取得并定向读过的最近邻全文中，未见直接给出当前 M2 合同的任意确定性日历逆界及匹配 H^{5/2} 亏损系数。可保留的候选贡献是这条 sharp calendar law 及其同合同的控制依赖解释。不能把“反馈改善诊断”“优化切换”“完整历史 uncertainty”“共同 Gaussian 最近对”“Markov 压缩/projection”“记忆保存 score”概括为首次。两篇直接研究 feedback/active diagnosis 的 Esna Ashari 2012 全文尚未取得，故新控制叙述仍有明确文献缺口。**

## 1. 此次版本与已有证据

| 当前来源 | SHA256 |
|---|---|
| m2_problem_contract_v1.md | 794c245d0fdb672021cb36566382d68834b2abe20331dde0bc01a0bc71671eae |
| m2_controlled_memory_theorem_v1.md | 38d2aecf2d00a6a781f0a99f6448d93a4d2fcccd1e895526ca3c5fed2c3455b1 |
| m2s_problem_contract_v1.md | 80a5a5d643432f54f1a2d9f3dc7a9e374528358c18e10beb6b0e1ac1d5b9e7d5 |
| m2s_singular_memory_theorem_v1.md | 8ff2de70274973e4a9e104b26a5bf4be14e0e742998f2c562f6023e6316ab431 |
| m2s_recoverable_order_v1.md | 5b04f87f23fbfe1d2bc1fb1fbb791e783a47e029c7cdf130e1c000dd22d0f4f1 |
| certo_fdi_control_memory_draft_v1.tex | 0f24a30953681a51f392f65dc5ef88aa7eb64c6ff04c10c38ee9ba8b441168ff |
| control_design_prior_art_extension_v1.md | 0f0d87e1f5d655e3b7bf1d374dfd3f0cad103037210d1f9737773fab8b70006f |

旧 outputs/novelty_matrix.csv 和 novelty_audit_v1.md 绑定的是 M0，不能改名后当作 M2 完整新颖性覆盖。此次依据同一份已缓存原始全文，针对新合同重新判断。11 篇全文的 URL、版本、PDF 页码和哈希仍以 work/literature_20261007/download_manifest.json 和旧报告为准；本次没有替换这些缓存。另实际读取根新增 control_design_prior_art_extension_v1.md，并直接核 KimECC2013 模型/反馈均值与 covariance 公式、Remark3，以及 RaimondoAutomatica2016 Theorem1、Lemma3、Theorems4–5、Algorithm1 和相应证明段。两份新 PDF 哈希现场复验，与 work/literature_control_extension/receipt.json 一致。另对反馈两篇与两篇趋势设计作了有限重检，缺口没有被假装填上。

M2 的关键联合条件：同 plant、同 B/Q；已知 fixed finite-order Schur feedback；全状态保留读数；一条两侧自由初值的 scalar Lipschitz 全史健康路径；known linearly growing fault；deterministic known H calendar；移动内物理动态持续但诊断缺测；两方向 exact-k profiles 可重复；排除 control/fast-state 信息旁路。仅“有 feedback”或“有 switching cost”不能区分该合同。

## 2. Claim-to-nearest-result 矩阵

| 当前主张 | 最近的实际核查原始结果 | 直接覆盖判断 | 可保留的表达/限制 |
|---|---|---|---|
| D_H^*=(√2/5)√(Fβ_K(k)r)η^{3/2}H^{5/2}+o(H^{5/2})，任意 legal calendars 的 converse 与 exact-k attaining family | Nitinawarat–Atia–Veeravalli TAC2013 §III Proposition 1 / Theorems 1–2；Markov cost 1310.1844 §4–5；switching 1505.02358 Theorem 6 / 2108.03082 Theorem 1 | 已核定理不直接覆盖：这些是 known stationary simple distributions 的误差指数/序贯 first-order cost，非两条全史健康路径、增长 fault、删 retained states 的二阶亏损 | 在冻结 M2 范围说 sharp fixed-controller calendar law；不能说首次 controlled/Markov sensing 或首次 switching-aware optimal design |
| Oracle 完整记录对 known K 中性，删记录后的 β 随真实 A_K 改变；equal poles 可有不同罚 | KimECC2013 §V-C (20)–(25) 已同时设计 Gaussian 预测均值/covariance 的反馈；RaimondoAutomatica2016 Theorems4–5 给 online closed-loop input 的有限时域 guarantee；Scott2014 全历史集合；ClassensCDC2024 fixed-K filter；Esna Ashari2012（全文缺口） | 已核结果未给本 β/calendar-law，但一般 feedback/closed-loop statistical diagnosis 已直接存在；Esna 两篇未完成 theorem comparison，不能判“不覆盖” | 将 full-record invariance 作为共同可逆变换事实；equal-pole 示例是同 B/Q/protocol 的具体 law 应用；不能把“共同传播均值与噪声”或“闭环统计主动诊断”写成首创 |
| 真 retained conditional Gaussian input projection、free-level weighted repair | GJN1311.6765 §2.1–2.3.1；标准 common-covariance Gaussian/linear projection 工具；Scott2014 §3.2 对 full-history sets | 最近对/白化/projector 本身是工具。此前结果不能自动给 arbitrary calendar support 和 repair O(H²) 的本次定理 | 方法介绍明确归功于 Gaussian 凸检验；贡献落在完整健康路径、真实删除实验和全日历上下界，而不是把 Moore–Penrose 或白化包装成 detector 新方法 |
| terminal-balanced symmetric calendar、hold 随时间线性增长、drift/switching tradeoff | Schieder–Kramer2001 §4.1 (15)–(17)；Ossenkopf2008 §5 (23)–(27)；Bojinov–Simchi-Levi–Zhao2009.00148v4 Theorem 2 | 对称补漂移、真实 dead time 和最优 phase length 都有原始前史；switchback 已有 minimax randomized design 结构。其随机 spectrum/HT-MSE 与当前确定性 rate-adversary Gaussian-information 合同不同 | 不声称首次 AB/ABBA、首次停测最优、首次 minimax switch structure；新点须是当前 law 的精确系数、calendar-uniform converse 及构造 |
| 齐次 settling qualification 对 scalar c 的 finite plateau candidates / continuum candidate | 此次不是新的反馈检测通用最优控制理论；同 law 加 ceil threshold 的数学推论 | 有限族 .9 最好与闭区间 [.8,.95] 的 κ 最小 .81 是不同命题；当前最近邻检索不证明 controller-design 历史优先权 | 称 restricted joint-design implication；从 pointwise fixed-K 到实际 continuous joint asymptotic 需另审 uniform bridge。c^s E≤ε 不等于 forced/noisy return，gain budget 不等于 actuator budget |
| M2S β=0 iff constant ray 在 rowspace；k≤d−p；zero normalized penalty；新补充给 Θ(H²) | 共支持 Gaussian score/projection 与 finite reachability 基础；本轮旧近邻未直接给这个 gap/calendar 联合结论 | rowspace equivalence 本身是标准信息几何；容量 bound、positive sharp H^{5/2} 与 zero Θ(H²) 二分在当前合同推导。没有完成广泛 singular-information/control-memory 优先检索，不能据有限近邻独占 rank-transition 思想 | 强调保存一个 constant-shift score，不能改写为恢复全部 inputs；fixed-rank/known common support；原v1仍仅o(H^{5/2})，Θ(H²)来自另一个已独审补充，且无H² sharp coefficient。当前 frozen稿没有纳入该扩展 |
| bounded fixed task-even E 保留 leading law | 共同 covariance 上 convex Minkowski envelope 与 projection contraction | 属于当前主定理的 perturbation 推论；本轮不支持独立“大范围参数鲁棒定理”的创新称谓 | 只写 additive bounded envelope，不扩大到 multiplicative plant/covariance/rank/unknown nuisance 参数 |

## 3. 可复核 primary 来源与承重位置

- [Nitinawarat–Atia–Veeravalli TAC2013 作者全文](https://vvv.ece.illinois.edu/papers/journal/niti-atia-veer-tac-2013.pdf)：§II–III、PDF pp.2–5、binary Proposition 1、Theorems 1–2；其 hypotheses 是有限 known simple distributions，当前 control 条件下 memoryless。
- [Nitinawarat–Veeravalli 1310.1844v2](https://arxiv.org/pdf/1310.1844v2)：§3、(3.1)–(3.2)、PDF pp.6–7；Theorems 4.1–4.2 pp.8–10、5.1 p.11。Finite fully observed Markov chain、正转移及 positive observation costs 是实质条件；不能通过名称“Markov”把本 hidden white-input/retained-state 实验直接代入。
- [Vaidhiyan–Sundaresan 1505.02358v1](https://arxiv.org/pdf/1505.02358v1)：§II-A/II-B，Theorem 6、Proposition 5，PDF pp.2–4。误差趋零与 sluggish 参数的有序极限；switch 是 monetary/additive cost，仍有普通观测。
- [Lambez–Cohen 2108.03082v1](https://arxiv.org/pdf/2108.03082v1)：§II、§III-C Theorem 1，PDF pp.4–5、12；known iid f/g、s=O(c) 的 Bayes leading risk，非真实 fixed-k physical blackouts。
- [Scott et al.2014 作者全文](https://web.mit.edu/braatzgroup/input_design_for_guaranteed_fault_diagnosis_using_zonotopes.pdf)：§2、§3.2、Theorem 3、§5，PDF pp.2–5。Compact uncertainty/initial sets、bounded disturbance/measurement error、constrained auxiliary input 设计与全历史 output-set separation；不能称其忘记历史 coupling。
- [Classens et al.CDC2024 机构全文](https://pure.tue.nl/ws/files/361857968/Optimal_Fault_Detection_for_Closed-Loop_Linear_Uncertain_Systems.pdf)：§III–IV Theorem 1，PDF pp.3–5；filter 使用 u/y，fixed K；H∞ robustness 与频率增益目标。旧报告已标记 tight-envelope 到逐 Δ equality 的待核步骤，本次不借该步作为证明。
- [Kim–Raimondo–Braatz ECC2013 会议全文](https://skoge.folk.ntnu.no/prost/proceedings/ecc-2013/data/papers/1214.pdf)：PDF pp.1–5 / 出版 pp.1940–1944，§III (4)–(5) 是有限 known stochastic fault models；§IV (9)–(16) 是 Gaussian KL/geometry 和 monitoring-window Bayesian likelihood；§V-C (20)–(25) 明示同一 affine feedback u_t=K_tx_t+ν_t 在每个 fault model 下同时改变 mean/covariance，带 input/state moment constraints。**Remark3 限制必须保留：Algorithm1 不能直接对 (K_t,ν_t) 做完整联合全局优化，K_t 单独设计，input 的非凸程序取得 local solutions。** 这仍足以确认 Gaussian feedback-design 前史，却不能宣称它已有本 sharp calendar theorem。其不同 fault dynamics、finite lookahead/monitoring window、已知随机 current-state law 与本 additive-template/common-plant/full-health-path 模型不同。PDF SHA26786822156dc8350928d7798bd5e98afe8c126007791278df07215b36c8df3e。
- [Raimondo–Marseglia–Braatz–Scott Automatica2016 作者全文](https://web.mit.edu/braatzgroup/Raimondo_Automatica_2016.pdf)：§2.2 (10)–(13)、PDF p.3 / 出版 p.109 的完整 reachable output histories；Theorem1 (19)–(20)、p.4 / p.110 的 separation；Lemma3、Theorem4 (24)、Algorithm1、Theorem5、p.5 / p.111，以及附录 pp.9–10 / pp.115–116。**Conservative observer 只给 sufficient implication，exact observer 才有 converse；Algorithm1 通过保留旧 shifted sequence 维持 ≤原 separation horizon 的 diagnosis guarantee。** 因而不能把已有方法概括为 open-loop 或逐块忘记 past measurements。其 bounded convex uncertainty、在线根据 observations 选输入、模型间 set exclusion 不等于当前 deterministic calendar 的 Gaussian minimax power/亏损。PDF SHAcf26542d1749811684b7a77123883aa399b59c31d9f7a4f2ea199a6528a8df84。
- [GJN1311.6765v7](https://arxiv.org/pdf/1311.6765v7)：§2.1–2.3.1、Theorem 2.1、PDF pp.3–7；[JN1604.02576](https://arxiv.org/pdf/1604.02576)：§3.2.3、Propositions 3.3–3.4、pp.12–13。最近对 Gaussian 检验是已有接口；当前无界健康类的 polyhedral attainment 另由合同证明。
- [Bojinov–Simchi-Levi–Zhao switchback v4](https://arxiv.org/pdf/2009.00148v4)：Assumptions 1–3、PDF pp.6–7、12，Theorem 2 p.13，证明 pp.56–57；bounded potential outcomes、known m-carryover、randomized treatment 和 HT worst-case MSE。不是只考虑静态趋势，也不是其所有 randomization points 都发生切换。
- [Schieder–Kramer2001](https://arxiv.org/pdf/astro-ph/0105071)：§4.1、PDF pp.5–7、(15)–(17)；[Ossenkopf0712.4335](https://arxiv.org/pdf/0712.4335)：§5、pp.10–11、(23)–(27)。真实移动 dead time 已在原目标中，且与理想 baseline 比效率；区别是 stochastic power-spectrum drift 与当前全称 Lipschitz adversary。

## 4. 直接控制近邻的缺口不能藏在泛称 audit 后

当前 frozen draft 的 Relation to established results（源第 73–106 行）只具名讨论 controlled sensing、Markov、Scott、convex Gaussian 和 Allan。根已准备将上述 Kim2013/Raimondo2016 加入下一稿，但此版冻结字节尚未更新。对一篇题名/摘要突出 closed-loop memory 的稿件，还应具名列 Esna Ashari–Nikoukhah–Campbell 的两篇直接 feedback/active diagnosis 工作，并清楚说明暂缺 theorem-level comparison；只在段尾笼统说 unresolved comparisons 不足以让读者定位这一最相关缺口。新取得两篇 primary 全文不会关闭旧四项缺口。

1. [Effects of feedback on active fault detection](https://www.sciencedirect.com/science/article/pii/S0005109812000714)，Automatica48:866–872，2012，DOI10.1016/j.automatica.2012.02.020。出版社 introduction、section snippets 和 conclusion 本次重检可读，明确研究 feedback 对辅助输入诊断的作用及成本定义；**完整定理/证明仍未取得**。不能把 snippets 的 cost 比较结论当作已审全称定理，也不能据其未出现 blackout 字词判定无覆盖。
2. [Active Robust Fault Detection in Closed-Loop Systems: Quadratic Optimization Approach](https://doi.org/10.1109/TAC.2012.2188430)，TAC57:2532–2544，2012。IEEE CSS 原始 publication digest 可确认题名/作者及全文入口，但本次入口仍未取得 article full text。**theorem coverage NOT_OBTAINED**，不从 abstract/二手引用补全其模型与结论。
3. [Cheng–Steinberg1991](https://academic.oup.com/biomet/article-abstract/78/2/325/232157)，Biometrika78:325–336，DOI10.1093/biomet/78.2.325，全文仍未取得。摘要明确包括 AR(1) 和 time-series trend，不能说仅 polynomial trend。
4. [Coster–Cheng1988](https://projecteuclid.org/journals/annals-of-statistics/volume-16/issue-3/Minimum-Cost-Trend-Free-Run-Orders-of-Fractional-Factorial-Designs/10.1214/aos/1176350955.full)，AoS16:1188–1205，全文仍未取得。Minimum change cost + trend-free run order 的优先权风险仍是实际缺口。

已取得全文的 switchback 应在 related work 中占一条明确比较，避免读者将 deterministic robust calendar 视为绕开统计实验设计的优先权叙述。需要区别随机化 worst-case MSE 与 deterministic Gaussian-distance information，而不是仅以“我们的任务是机器人”区分。

## 5. 控制记忆与旁路风险的实际解释

M2 的收益不是共同 feedback 的可逆全记录滤波收益，而是先按不同真实 A_K 演化、再删 states，得到不同 retained input rowspace。这个操作顺序及完整已知 plant 是主张的实质。若 commands 揭示 hidden x、fast states 被 log、额外传感器提供健康不敏感方向、缺测只是当前算法没有使用，而不是信息合同排除，这些都改变实验，当前 D_H^* 不能继续作为通用物理极限。

M2S 的 singular case 更依赖精确无 measurement noise 的 state relations。ε=0 时可由小非零 copy gain 保存 score，ε>0 时罚通常恢复为正；这不是用控制器免费改变 physical Q，而是一次次固定 common Q 下的比较。未知 rank 或微小额外 measurement noise 不能直接继承 noiseless deterministic channel。

现稿可以使用的限定文字为：

> For a known fixed stable linear plant with the declared retained-state information and a scalar full-history rate-limited healthy input, we characterize the sharp leading deficit over all deterministic task calendars and provide a matching construction. Existing convex Gaussian tests and input projection provide the fixed-calendar interface. The selected comparisons do not establish exhaustive historical priority; theorem-level comparisons with the two feedback-active-diagnosis papers remain incomplete.

此处文字只是可复核范围建议，不修改稿件。M2S 的 Θ(H²) 补充本次随后完成独审（见 m2s_recoverable_order_review_v1.md）：数学上 fixed-scope 接受，但历史优先权覆盖没有因此扩大，现 frozen manuscript 也没有自动升级。Continuous joint-controller uniform bridge 由另一代理审查，其结果不预设在本报告中。

最终状态：**有限范围未见已核定理直接覆盖 M2 sharp law；新增两篇 primary 控制设计全文进一步确认 Gaussian feedback optimization 与 online history-aware closed-loop diagnosis 已有前史；Esna2012 两篇与趋势设计两篇全文缺口保持开放。无“首次”、无穷尽优先权结论。**
