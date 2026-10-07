# 统一投稿 body v1：独立数学与量词保全审查

日期2026-10-07。审查者ar1_proof。**结论：冻结body的数学整合可以接受；同一common-support模型、positive sharp H^{5/2}/zero Θ(H²)、SPD特化与SPD-only compact uniform的承重条件、构造和证明均保留。未发现压缩引入的承重反例或必须改变主定理的缺口。** 需补一处显式记号定义；另有已知host排版问题与引文措辞精度，不把它们伪装成数学失败或编译PASS。没有录用评分。

## 1. 精确绑定与实际审查覆盖

|文件|本次绑定SHA256|
|---|---|
|outputs/submission_body_consolidated_v1.tex|7ced33a8641dc8ccb0b216684f68d13f2f26334effa16ccf3dceaea98001a6d9|
|outputs/submission_consolidation_map_v1.md|060e9bc672b2718653c8cfdd3f596ce4a26d227d5cbd2346fd6842fd2f7a3fad|
|outputs/m2s_singular_memory_theorem_v1.md|8ff2de70274973e4a9e104b26a5bf4be14e0e742998f2c562f6023e6316ab431|
|outputs/m2s_recoverable_order_v1.md|5b04f87f23fbfe1d2bc1fb1fbb791e783a47e029c7cdf130e1c000dd22d0f4f1|
|outputs/compact_controller_uniform_bridge_v1.md|89762501f1272eb8b0ed5150985225655e62f0681d24c62c41729750dbcdf351|

新body实际完整读取，分三段无截断覆盖1–350、351–700、701–1164行；映射全文读取。对先前现场审过的revision4数学、冻结已接受common-G/Θ源和compact源逐条交叉核对；compact源本轮再完整读。实际读caption与13条verified bibliography，核新body条目一致性和正文限制。没有取得或重新审查那四个外部全文，没有重跑旧数学checks、PFA表、D2或science，没有修改作者body、map、根主稿或冻结来源。

旧revision4基线绑定70dc68db61599470cb6cd82ff6a2f83bcd30cdd4db89675e8074eab4e146f302由整合map及先前审查记录保留。本轮根正在修host布局，同一旧主稿路径现场已是e5d3c2d639e828795518101a78ea08cec56ea8bb1b44a01282186180fc75a371；**不将该新字节冒称70dc，也不声称本轮对不存在的旧字节快照做了逐字diff。** 新body的数学接受主要绑定上表冻结源、已审revision4内容和本轮逐式证明，而非依赖作者map自我背书。

## 2. Common-support实验与两分结果：保全

sf:plant/path/model保留fixed known stable A_K、full-column G、非零B∈rangeG、f=G†B、F>0；真实已知初始化、固定全读prefix、prefix fault0、post affine ramp、r/η严格正与ρ₀非负。两侧分别选择完整scalar paths，每侧rate r/2、free level；差分速率r作用于所有input相邻槽，包括missing。Calendar先选、nature后选path、最后独立noise，不是数据适应或每块独立nuisance。

Holding g=±1、读完整state；missing known |g|≤1，双向exact-k可以在预定起点与holds重复串接，任意更长gap仍属于converse，无terminal task。诊断器与controller的内部state/command权限区别保留；没有额外传感、reset或硬actuator/state/tracking预算。

sf:information保持KL半平方约定。O_H=FΣa²/2是healthy-subtracted complete-record oracle，不能与仍inf_z的full composite information混同。用sup，无需finite-H attaining optimizer。sf:two-regime保留positive系数√2/5√(Fβ_k r)η^{3/2}、fixed-ξ上界及ξ*=2β_kη/(Fr)；zero只是order sharp Θ(H²)，没有quadratic sharp常数。

## 3. 附录A：合法支持、恢复容量与统一几何工具

所有实际均值L_Rϑ在同一noise image，SVD只在共同支持上产生白化；predictor是可逆triangular左变换，保rowspace而不是对伪逆作错误congruence。T_m的row维数是rank W_m、U_m明确orthonormal，P是真orthoproject；跨history covariance和初始化均保留。

Gamma界先用Cayley–Hamilton稳定reached subspace，再在相同kernel/range上比较W_m†与W_d†；没有错误地以W₁†作所有span的ambient bound。Strict stability给S_B finite。β=||(I−P)d_m||²、nested deletion monotonic及tail保持。恢复条件Gᵀ(A_Kᵀ)^q y=f，q=0,…,k是constant force score条件，不是P=I；k<ν_R≤d−p+1容量与SPD eigenvalue1矛盾均完整保留。3D rank3/latent dimension4、slope residual1/2例继续明确非全input恢复。

Affine非reflection的L₁=−MᵀW†N、L₂≥0保留；|L₁|≤mC_K/2及全日历cross费用E_H=O(H²)没有被压成零。Complete-input support精确为rΣ|partial masses|，非零scalar总质量则∞。Range(P)统计量真实作用于predictor，latent pullback=P_mv_m=v_m、variance||v_m||²；Fenchel分解仍带所有½因子。

## 4. 附录B：positive converse/attainment

**Converse通过。** Terminal fill先做experiment dominance。Signed tents是一个全史合法z，由±z/2实现两侧path，在所有missing及gap-right input取0；左prior state不重复纳入gap input。新稿显式i=0,…,n−1，tent面积/height界与原证明一致。原T确为同一actual gap norm loss：一个bound按complete internal gaps计M−1，另一个按dead slots分配；先对全局T作一次convex split，cross error仅付一次，cross-macro missing节点只分一次。M=0,d=L分支单独处理，不除0。Absorption threshold、宏H^{3/4}、uniform calendar remainder、Riemann系数与先取最优亏损/H-limit再epsilon/delta→0均保留。

**Upper通过。** H−1 packing、maximal block数、均匀padding和1–4真实tail reads保证n_l=ξl+O(1)、A_l=ηξl²+O(l)。s_l、L_l、c_l=n_l+k+1/2及真实gap centers的1/2±(n_l+k)/2保持精确。Join使用两侧实际读过的states，下一真实span singleton；没有假独立输出初始化。

局部levels只生成dual，非声称全史primal可拼。四重held-level计数是原baseline公式的合法展开：Σg zloc=r n(n+2k)/2；其zero-mass support包括missing-slot plateau。所有singletons用I_p，gap的right retained点从2n单例中扣去；D≥F(2n−2)≥Fn，N bound C_kFA、repair N²/D及scalar总mass0正确。只有一条scalar健康路径，所以只修一个weighted scalar constraint，未偷偷改为vector uncertainty。

Support correction、aux error与energy均O(H²)，真实range-statistic可观察。Affine pair保留半slot center和nonzero cross；两项幂和给2D≤2βΣA²+FrΣAn²+O(H²)，fixed-ξ公式与最优ξ及√2/5常数一致。没有用未读input数据作额外观测。

## 5. 附录C：zero Θ(H²)完整两边

**Upper通过。** 真实离线calendar按full-input M_t=Σg threshold切换，含任意known missing profile；不是只配held counts。S_t=M_t−n₀及其bound显式保留，Abel给全部weighted ramp partial sums O(t)、global N=O(H)。每held run≥2，right gap点不算singleton，S=N_h−N_m≥H/(k+2)。β0只消constant loss，affine slope仍可丢，但fixed-gap总E=O(H)。Global repair D≥FH/(k+2)、α=O(1)、误差E+α²D=O(H)、partial weights与free-level support O(H²)均完整，且v∈rangeP。

**Lower通过。** L_z有限、b_+>0来自monotonic/tail。晚期positive span给center A≥ηepsilonH/2，即使long gap也成立，得到calendar-uniform oracle H²下界。否则late spans均≤L_z，覆盖late clock计数正确。单条legal z=(r/2)g使healthy white shift=(r/2)f g²；right retained g²=1确保每late span至少一份constant cross。未假P entries正性。Early negative cross和||P healthy||²单独控制，不隐去；epsilon=(4L_z+2)^−1使bracket=epsilon/(4L_z)>0，半平方展开最后系数rFηepsilon/(8L_z)。常数不依calendar，且r/η>0与held g=±1仍在合同内。

## 6. 附录D/E与common-SPD uniform：未越界

Uniform theorem明确共同fixed Q≻0、B/plant/path/prefix/readout、nonempty compact gain set与每点Schur、k(K)有限positive integer范围、两方向重复exact profiles。没有把fixed-G singular结果推广为rank-changing gain-family uniform。

Compact Schur→uniform resolvent/power tail；W_m,K≽Q→common cross bound；finite k+strict positive continuous β→common βlo/b；ξ_K处于positive compact区间、padding和inactive cutoff统一、O(H²)各项统一的证明都保留。尤其新稿补出base duration和quadratic active cutoff，正确强化既有证明表达。取inf只在统一误差之后，未假k/profiles连续、C minimum或finite-H optimizer。Scalar settling例的shorter-s equality、plateau candidate、near-unit limit、unique0.81与near-optimal controller convergence保持；只homogeneous qualification，无forced/noisy return保证。

Bounded-even仍以实际Minkowski difference envelope、contains zero、fixed E、unchanged projection/covariance为条件。Contraction给O(H²)亏损差，所以positive首项不变、zero order不变，没有quadratic coefficient不变的多余断言。E与kappa/settling误差盒的不同局部含义按上下文可辨。

## 7. 两处小型补清和host布局提醒

1. **新增记号遗漏，不改变唯一可理解的模型。** sf:predictor第122行及A第533行使用a_j^h，但sf:plant直接写indicator，未显式定义简写。旧revision4有a_j^h=1_{h=1}a_j。建议root集成时在hypotheses介绍后补这一等式，或在predictor里继续使用indicator。该符号无法合理解释成新自由故障path，主plant已经固定ramp；这是编辑补清，不是主定理缺口。
2. **引文措辞更精确。** 第52行multipleplays称switching penalty“of the same order as delay cost”；当前verified support locator实际写s=O(c)。为避免把O误读为Θ，可改成“switching cost s=O(c) as delay cost c tends to zero”。这是已有文献措辞精度，本审查不重新获取该全文或升级bibliography核验。
3. **编译不能由静态推出。** 附录C第859–860行proof environment立即接paragraph heading，仍有root刚在旧host CLI暴露的amsthm/layout风险。数学接受不等于该冻结fragment的编译接受；root可在新集成host版本处理heading布局，并绑定真实compiler receipt。摘要Theta等词的math/text格式也由root按既有计划处理。本轮不编译或改body。

不要求改冻结7ced源来接受其数学等价性。若在host补清上述文字/布局，需新的host字节绑定，而不是改写本报告接受范围。

## 8. 图、13 cite与独立nonlinear边界

实际caption与既有caption源语义一致：kappa/beta单位、same homogeneous E=1/epsilon.81、shorter tie、空/实端点、exact continuum0.81与三点best0.9不同、无random CI、非forced/nonlinear/actuator资格均保留。Figure fallback不影响数学证明；本轮不重新渲染或给新视觉/字体验收。

13 bibentries与submission_bibliography_verified_v1.tex去comment/空白后逐key内容完全一致，均被引用，无missing citekey。正文明确未完成两篇2012 feedback及Cheng–Steinberg1991、Coster–Cheng1988四个fulltext theorem comparison；identity/metadata不等于noncoverage，未写历史优先性穷尽结论。Standard Gaussian detector不是声称本研究的新工具；free-level polyhedral attainment在稿内独立证明，未冒充compact-source theorem原文。

Nonlinear H120 comparator被明确划为独立有限实例，非exact fixed-covariance M2模型；unconditional parameter/path-specific Gaussian comparator、same-noise good event的inclusion+union而非conditioning、两侧误差/均值/事件、positive gap才代Vplus、nonpositive sufficient power0非actualpower0、ramp≤.045而非wide.75、400-row未全完/非all-family最短/sequential optimum均保留。本轮不重新算其数值或PFA。

## 9. 静态连接与最终判定边界

现场只读静态核验：48 labels唯一且全sf:，ref/eqref无悬空，13 bibkeys均用到，bib内容与verified fragment一致；TAB=0、孤立CR=0、其他低控制字节=0。它们是转录/连接证据，不是compiler、PDF或页数PASS。

因此可把7ced body作为**已独立核过数学/量词等价性的整合源**；仍保留上述显式记号补清、四篇全文比较缺口、实际编译/布局、证书可访问发布包与投稿格式等边界。未运行旧checks、science或新研究，不关闭长期goal。

