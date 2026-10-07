# M2S β=0 的 Θ(H²) 补充：独立审查 v1

日期：2026-10-07。审查者：novelty_theorems。范围：新冻结阶数证明的逐式审查及新增小检查；不重跑 M1/M2/M2S 历史大表，不改源证明/合同/根台账。

**结论：冻结 fixed-scope 下定理 R 可以接受。β_k=0 时存在仅依固定合同的 0<c<C<∞、H₀，使所有整数 H≥H₀ 有 cH²≤D_H^*≤CH²。** 上界真正平衡全输入累计 g，包括任意已知 missing profile；下界覆盖全部允许日历。没有发现需要修复才能成立的承重缺口。这是阶数结论，没有 sharp H² 系数，也没有 controller-family 一致性或真实机器人最优控制结论。

## 1. 冻结绑定与实际读取

| 文件 | SHA256 |
|---|---|
| m2s_problem_contract_v1.md | 80a5a5d643432f54f1a2d9f3dc7a9e374528358c18e10beb6b0e1ac1d5b9e7d5 |
| m2s_singular_memory_theorem_v1.md | 8ff2de70274973e4a9e104b26a5bf4be14e0e742998f2c562f6023e6316ab431 |
| m2s_recoverable_order_v1.md | 5b04f87f23fbfe1d2bc1fb1fbb791e783a47e029c7cdf130e1c000dd22d0f4f1 |
| m2s_recoverable_order_checks_v1.py | 09a375c98f27e4c2c4afe33d41e5420f5647ded852ddb9708177d8bd9e3302c3 |
| m2s_recoverable_order_checks_v1.json | 11e34d29ff2186617fc2cb13622aab0ed30ab850a9e10191dc93fb490a11382b |
| memory_asymmetric_repair_supplement_v1.md | e297d281991a41273318a4775f8f32ac51ce5d7ccfb3a1a9b601a1b7b1d8d071 |
| memory_asymmetric_repair_checks_v1.py | 0411fba7daac9948bb6d3a1a3687f657f0bb9e21f8779cf04ced9852dcb96db1 |
| memory_asymmetric_repair_checks_v1.json | ba6e9936cccf6c32685298af971904217a6d1e88615d1ada47078c5bc3496576 |

各哈希现场复验。阶数 .md 全文、相关 .py/.json、非零修复补充全文均实际读取。M2S v1 的共同 Gaussian 支持、真正的 rowspace P、固定 reached-subspace Γ、恢复容量等已经在 m2s_independent_review_v1.md 独审；本次只在该接受范围内继承，不靠伪逆 congruence 或 rankless whitening。

实际运行两个**新增** standalone Fraction 脚本，各 exit=0、status PASS，stdout 解析后的 JSON 与保存副本完全一致。此运行只含六个 bounded-cumulative calendars、十九个 ε 代数恒等式和六个非零局部 repair cases；没有调用旧大表。配套 TeX 未在本审查重编译，平台 compiler failure 的 UNVERIFIED 状态不改变。

## 2. 量词和有限零罚长度

定理固定 A_K、G、B、k、r、η、ρ₀、n₀；G full column、B∈rangeG 非零；strict Schur；known initialization/prefix；一条 full-input scalar 健康差分 z 的 rate≤r，两侧各 rate≤r/2；r>0、η>0。Held g=±1、missing |g|≤1 known，nature 在 deterministic calendar 之后、noise 之前选完整健康路径。

第 27–49 行的 L_z 和 b_+ 合法：β₀=0，β_ℓ 非减且 β_ℓ/ℓ→F>0，故零集合是有限连续初段，L_z=max{m:β_{m−1}=0}。β_k=0 保证 L_z≥k+1≥2；v1 的容量界给 L_z≤ν_R≤d−p+1。m>L_z 的 β/m 都正，有限前缀有正最小值、尾部趋 F，故 b_+>0。不能把这里的 b_+ 与 v1 在 β_k>0 时的 b_K 混用；新证明没有这样做。

上界需要在任意预定起点双向可重复、可串接 exact-k profiles。第 9 行明确允许 profile 随已知起点变化，但仅使用 length k 和 |g|≤1。因为没有观测数据参与阈值决策，日历可以在实验前完全计算。若 moves 不能任意如此串接，仅下界自动继承；不能把该可实现性条件省掉。

## 3. Upper：全输入平衡而不是只平衡 held counts

第 53–59 行选 L>n₀+k+2，累计 M_t 含 prefix 和所有 missing g。Holding 的每槽增量为 ±1，所以阈值 overshoot<1；一次 move 对 M 的改变至多 k。反向 hold 开始时旧符号的累计量在 [L−k,L+k+1)，之后到相反阈值的长度在 [2L−k,2L+k+2] 内。首 hold 长于 L−n₀>2；仅在至少 k+2 个剩余槽时开启 move，故 truncated 最后 hold 也至少 2。终端不 move 时多读的槽不足 k+2，因此所有 input nodes 上 |M_t|≤L+k+2。这个上界包含 move 内 g，不要求两个 profiles 互为相反。

计数正确：H=N_h+kN_m，post singleton 数 S=N_h−N_m；每个 gap 的 right retained input 被算在 span 内，没有重复算 singleton。N_h≥2N_m 推出 S≥H/(k+2)。Prefix singleton 只增加分母。

β_k=0 仅给 P_m d_m=d_m，d_m=1_m⊗f，**不保证 slope 恢复**。第 67–75 行因此只消去 amplitude A，保留 affine-slope loss，单个 exact-k span 的平方误差至多 η²F m(m²−1)/12；move 数 O(H)，故 E=||(I−P)θ||²=O(H)。这与 partial-mode 例的 L₂=1/2 一致。

第 78–86 行的逐节点权重 λ_j=h_jᵀ(Pθ)_j=F g_j a_j+e_j 成立：因 constant 模式无损，e_j 只含固定长度 span 的 centered slope，|e_j|≤C₁，与其晚期 amplitude 无关；singleton 上 e_j=0。累计 post g 有固定界，Abel identity Σ_{j≤t}g_j a_j=a_tS_t−ηΣ_{j<t}S_j 给 O(t+1)，加上固定幅值 e_j 仍为 O(t+1)。于是全质量 N=Σλ=O(H)，并非未说明的 zero mass。

第 88–100 行用真实 p=Ph：D=||p||²≥F S≥F H/(k+2)，D≤F(H+n₀)。α=N/D=O(1)，v=Pθ−αPh 在 rangeP 且 Σh_jᵀv_j=0。因 (I−P)θ 与 Ph 正交，

\[
\|\theta-v\|^2=E+\alpha^2D=E+N^2/D=O(H).
\]

此 global repair 允许 prefix 系数非零，但其 mean=0、noise 和 full-health support 都实际保留；没有删除 prefix nuisance 或 reset。

每 input |h_jᵀp_j|≤F√m，singleton 为 F，所以修复后的所有 partial masses仍为 O(t+1)。Free initial level 强制总质量精确零，完整 rate-r class 的 support 是 rΣ|partial mass|=O(H²)。这里是完整 scalar z，既没有每坐标独立 offset，也没有仅 observed trace 的限速类。

Fenchel 第 109–115 行及 1/2 因子正确：对实际 observable v∈rangeP，G≥vᵀθ−||v||²/2−support；故 D_π≤||θ−v||²/2+support=O(H²)。M2S 的真实 retained-state pullback 使该 v 可执行，不需要额外 fast input/state data。因存在这条合法日历，D_H^*=inf_πD_H(π)≤CH²。

## 4. Lower：全部日历的正罚/零罚两分

第 119 行的 terminal dominance 合法：无最后任务义务时，可将最后一个没有后续 read 的 move 尾部改为持续 hold；原先所有 retained data 在 tail 改动前，保持同分布，新实验可以忽略追加读数，因此 G_new≥G_old、D_old≥D_new。对 endpoint H 被读的日历给统一 lower 就覆盖原全部 calendars。已读 prefix 令 post non-singleton spans 起点≥1。

取 ε=(4L_z+2)^{-1}、J₀=ceil(εH)。

**Case A：存在 ending t≥J₀ 的正罚 span。** Affine center A≥η(t+1)/2≥ηεH/2；β/m≥b_+。当 A≥2C_Kη/b_+，由 Z3 得 norm loss≥(b_+/2)mA²。选择同一合法 z=0 给 D_π≥||(I−P)θ||²/2，所以至少 b_+η²ε²H²/16。所需 H₀ 与日历和 span 长度无关，长 span 不破坏此界。

**Case B：所有 ending t≥J₀ 的 spans 都零罚。** 这些 span 长度≤L_z，覆盖 inputs J₀,…,H，因此数目 J≥(1−ε)H/L_z−O(1)。跨 J₀ 的第一个 span 不必始于 J₀；长度有界已足以让 late center A≥ηεH/2。

选单条完整 z_j=(r/2)g_j。所有 known g∈[−1,1] 给 |Δz|≤r；±z/2 两侧各满足 rate≤r/2，prefix free level 也合法。Healthy difference 输入为 (r/2)f g_j²；每 late span 的 right retained g²=1。Constant mode 在 rowspace 给

\[
\langle P_m\theta,P_m\widetilde h\rangle
=\tfrac r2FA\sum g_q^2+\text{fixed-length slope cross}
\ge\tfrac r2FA-C_0.
\]

Slope cross 用 Cauchy/contraction 和 m≤L_z 控制，不假设 projector entries 非负。这正是不能把 β=0 误写成 slope/full-input 恢复时仍成立的步骤。Σlate cross 的 H² 系数为 rFηε(1−ε)/(4L_z)。

Early spans ending <J₀ 的总长度≤J₀−1+n₀，amplitude≤ρ₀+ηJ₀，故 contraction/Cauchy 给 cross≥−(r/2)Fηε²H²−O(H)。||P\widetilde h||²≤(r²F/4)(H+n₀)=O(H)。代入同一 path 的半平方展开并舍去非负 oracle loss，得到

\[
D_\pi\ge\frac{rF\eta}{2}
\left[\frac{\varepsilon(1-\varepsilon)}{2L_z}-\varepsilon^2\right]H^2-O(H)
=\frac{rF\eta\varepsilon}{8L_z}H^2-O(H).
\]

最后恒等式正确，括号为 ε/(4L_z)>0。Early O(H)、late O(H) 和 threshold H₀ 都仅依 fixed contract。取 c 小于两 case 的常数最小值即可吸收剩余 O(H)，再对全部日历取 inf。这里数值 checks 没有替代任何 ∀π 步骤。

## 5. 新检查和非零 repair 的实际覆盖

新阶数脚本只用 Fraction，在两个植物、H=32/65/128 上给六条真实初始化日历。全部 N≠0，global repair 后质量精确零；Pv=v、energy identity 和完整 raw-state backward adjoint/variance 均 PASS。Partial-constant 模型的 oracle norm loss 分别 1/49、5/98、9/98，恰展示 β=0 而 slope loss 非零。十九项 L_z=2,…,20 的 ε bracket 检查 PASS，但一般恒等式已在上述代数中证明。

另一个 six-case local repair 补充独立于 Θ-calendar，六项 repair energy 全正；两项 low-rank witnesses 为：

| M2S 例 | N | D | α | N²/D | affine oracle norm loss |
|---|---:|---:|---:|---:|---:|
| scaled-copy singular | −10/3 | 77/9 | −30/77 | 100/77 | 0 |
| partial constant mode | −13/2 | 89/6 | −39/89 | 507/178 | 1/49 |

这些例包括真实 prefix、gap-right input、完整 scalar support 和实际 raw statistic，正式独立运行 stdout=保存 JSON。它们补上“存在实际 α≠0 的低秩 repair 分支”复现证据。**原 v1 的 972 个 local assertions 仍是全零 repair 的历史覆盖；不能用新六项倒写原大表计数。**

## 6. 接受范围与禁止的升级

接受 fixed-K 的阶数二分：β_k>0 沿已审 v1 给 positive sharp H^{5/2}；β_k=0 沿本补充给 Θ(H²)。后者没有 H² sharp coefficient，不能说“缺测无代价”。上界不从 v1 的 O_ξ(H²) 猜 ξ(H)，而是另造 full-input balanced calendar，因而没有交换未证的极限。

r>0、η>0、held g=±1、finite noise-recovery capacity、terminal 无任务义务、双向 exact-k 可重复和 diagnostic 无旁路必须保留。若 r=0、η=0、出现健康不敏感 held mode、H-dependent gain/rank/β，或加入 measurement noise、硬饱和/预算、部分 state sensors，不能直接迁移本结果。Constants 可依 L_z、b_+、Γ_K、k 与 profile admissibility；没有 uniform controller-family 结论。

若另取固定 additive bounded task-even Minkowski envelope 且含零、covariance/P 不变，先前已审 contraction bound 只给 deficit 增加 O(H²)，可以保留本 Θ(H²) 阶数，却不保证 H² 首项系数不变；这仍不是 multiplicative-parameter robustness 定理。

审查状态：**ACCEPTED WITH FIXED-SCOPE QUALIFIERS；非零 repair 新证据 REPRODUCED PASS；TeX compilation UNVERIFIED。**
