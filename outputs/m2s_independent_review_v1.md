# M2S v1 独立数学审查

日期：2026-10-07。审查者：novelty_theorems。只读冻结合同、证明和正式检查副本；没有修改源定理、根台账，也没有重跑正式大表。结论来自下述逐式推导，有限枚举只作为诊断证据。

**结论：在冻结合同的固定、已知严格 Schur controller，固定 full-column noise factor G，B∈range(G)\{0}，完整状态读出、一条标量全史健康路径、双向可重复 exact-k profiles 的范围内，M2S v1 的 positive-β sharp 定理、β=0 的 ordered-limit o(H^{5/2}) 结论和恢复容量上界可以接受。** 没有发现使该固定范围定理失效的数学缺口。该接受不包含尚未冻结的 Θ(H²) 补充，也不升级到未知秩、measurement noise、controller 族一致性、有限 actuator 预算或实际机器人。

## 1. 版本绑定与核查范围

| 文件 | SHA256 |
|---|---|
| m2s_problem_contract_v1.md | 80a5a5d643432f54f1a2d9f3dc7a9e374528358c18e10beb6b0e1ac1d5b9e7d5 |
| m2s_singular_memory_theorem_v1.md | 8ff2de70274973e4a9e104b26a5bf4be14e0e742998f2c562f6023e6316ab431 |
| m2s_singular_memory_checks_v1.py | c8bea30a8f07c30e7022ca7b29c7d35b4c08099009fd48a062d32bbb1b53d957 |
| m2s_singular_memory_checks_v1.json | 279f4d64d90021de274bfe5884e5ecfcb3a2f00d04bab224e1cf4ed04a18e239 |

本次实际复验以上四份哈希。下文行号指冻结 .md。另读正式 .py/.json 的 pseudoinverse、row projection、repair 和 statistic pullback 部分。此前接受的 M2 上下界骨架只在本次验证它的共支持、rank、有限 Γ 替换合法后继承。没有把编译状态当成数学检查：配套 .tex 的平台 compiler failure 仍是 UNVERIFIED。

## 2. Gaussian 共同支持与真正的 retained input projection

合同第 8–14、24–38 行是必要假设，而不是伪逆公式的技术便利。每个输入均为 G(θ_j+ξ_j)，其中 θ_j=f(a_j^h+g_j b_j^h)、f=G†B，故 retained mean 确实位于 range(L_R)。不同 hypothesis/健康路径只改变共同支持内的均值；不会产生 covariance kernel 中的确定性区分。若 B 不在 range(G)，这一点即失效，不能用有限伪逆二次型代替真实 KL。

证明第 50–67 行的 SVD 路径正确：L_R=U_rΣ_rV_rᵀ，在实际支持上 Y↦Σ_r^{-1}U_rᵀY 是信息等价变换，得到 covariance I_r 和 mean V_rᵀθ；KL 为 (1/2)||V_rᵀδθ||²。因此研究的是 latent input 空间里的 orthoproject，而不是把奇异 ambient covariance 当作可逆。

第 69–84 行没有使用错误的 Moore–Penrose congruence。Retained predictor 对真实 states 作可逆 block-triangular 左变换，把同一 L_R 化为互不重叠的 H_m=[A_K^{m−1}G,…,G]。可逆左乘保持 rowspace，因而真正的 projector 是 H_mᵀ(H_mH_mᵀ)†H_m。跨 states 的共同历史 covariance 在这个步骤中保留；独立性只来自 disjoint 原始 ξ intervals。没有缺测末端 reset。

一个可手核的警戒例：C=diag(1,0)，S=[[1,0],[1,1]]，则 (SCSᵀ)†=(1/4)[[1,1],[1,1]]，而 S^{-T}C†S^{-1}=diag(1,0)，二者不等。合法性来自共支持上的信息等价及 rowspace，不来自伪逆 congruence 恒等式。本稿采用前者。

Rank-adapted T_m=(U_mᵀW_mU_m)^{-1/2}U_mᵀH_m 满足 T_mT_mᵀ=I_{rank W_m} 和 T_mᵀT_m=P_m。冗余的 d 行 W_m^{†/2}H_m 不能宣称 covariance I_d；稿件第 84 行明确避免了这一误写。

完整 states 给 G†(x_j−A_Kx_{j−1})=θ_j+ξ_j，所以 P_full=I_{p(H+n₀)}。这既证明 full experiment 对已知 K 中性，也说明诊断端不能同时拿到 fast states/control commands；若拿到可逆反馈旁路，当前缺测合同会改变。

## 3. 固定植物的 Γ 界：只能在 range 稳定后用 inverse order

第 88–108 行推导成立。R_m=span(G,…,A_K^{m−1}G)，Cayley–Hamilton 给 R_d 不变，m≥d 时 range/kernel 不再变化。此后 W_m≽W_d 可以在同一个 reached subspace 上转成 inverse order；两边在共同 kernel 为零，故 W_m†≼W_d†。前 d 项有限给 Γ_K=max_{1≤m≤d}||W_m†||<∞。

不能在范围增长前使用 W_1† 作为上界。例如 G=e₂、A_K=[[0,1/2],[0,0]]：W_1†=diag(0,1)，W_2†=diag(4,1)。虽然 W_2≽W_1，ambient pseudoinverse order 不成立。稿件第 106 行正确划定这一边界。

Strict Schur 性给 S_B=Σ||A_K^rB||<∞，所以 C_K=Γ_K S_B² 有限。这是 fixed-controller 常数，不是整个稳定 controller 族的一致常数。第 267 行的 δ-copy 例显示到达秩可跳变、Γ 可按 δ^{-2} 发散；这阻止直接套用本 Γ-based uniform proof，但单个粗界发散本身不证明真实 uniform asymptotic 一定失败。

## 4. β、score 和恢复容量

第 112–135 行正确写出 β_k=d_mᵀ(I−P_m)d_m，d_m=1_m⊗f，因而 β≥0，β=0 iff d_m∈row(H_m)。对应的可观测对象是 constant scalar shift 的 likelihood score d_mᵀξ；不是所有 mp 维 inputs。

删除 retained rows 的 rowspace inclusion 给 β_ℓ 非降。Stable S_B 和固定 Γ 给 β_ℓ≥(ℓ+1)F−C_K；与 β_ℓ≤(ℓ+1)F 合用得 β_ℓ/ℓ→F。只有 β_k>0 才能据此及有限前缀得到 b_K=inf_{ℓ≥k}β_ℓ/ℓ>0。β_k=0 的 branch 没有偷用这个正下界。

第 137–143 行的 reachability-index 证明完整。若 R_{m+1}=R_m，则 A_K R_m⊂R_m，以后不再增长，所以 ν_R≤r_∞−p+1≤d−p+1。若 β_k=0，存在 y 使 Gᵀ(A_Kᵀ)^r y=f，r=0,…,k；ζ=(A_Kᵀ−I)y 与 R_k 正交。假设 k≥ν_R，则 ζ 与不变 R_∞ 正交，所有相邻差都为零，故该序列恒等于 f≠0；strict stability 又令它趋零，矛盾。故 k<ν_R，整数上即 k≤d−p。没有假设 full controllability，也没有假设 normal dynamics。

第 262 行的 partial-mode 例能阻止错误加强：d=3 nilpotent shift，G=[e₂,e₃]、B=e₂+e₃，H₂=[e₁,e₂,e₂,e₃]。常数 ray (1,1,1,1) 在 rowspace，但 rank(H₂)=3<4；P≠I，中心 slope ray (−1/2,−1/2,1/2,1/2) 的损失为 1/2。故 β=0 甚至不保证 affine slope 的完整恢复。只有另一个单通道 shift-register 例确实恢复整个短 span，不能把它推广到所有 β=0 系统。

## 5. Sharp positive branch 的上下界与因子

第 145–178 行把 M2 的 affine cross 替换成合法低秩公式。L₁=−M_mᵀW_m†N_m、||N_m||≤mS_B/2，故 |L₁|≤mC_K/2。所有 non-singleton spans 的 Σm≤H 且 A≤ρ₀+ηH，累积 cross 只有 O(H²)，不依赖 gap 反射对称。Terminal hold 支配和 prefix full read 保证 non-singleton spans 留在 affine post-onset 区域。

Converse 的 z 是 full-input 节点上一条 rate-r 路径，两侧实现 ±z/2；missing、gap-right read 和 run endpoints 都为零。只分割同一个实际 gap residual T 一次：其中 (1−θ) 用 β_k M 计价，θ 用 b_K 的 missing mass 计价。跨 macro gaps 只进入后者；没有重复收费。C、F、1/2 的摆放与 M2/M1 scalar reduction 一致，极限系数为 (√2/5)√(Fβ_k r)η^{3/2}。

第 180–232 行的 upper 对所有 ranks 都合法。关键分母来自 retained singleton input maps P₁=Gᵀ(GGᵀ)†G=I_p，而不是 I_d，因而 D=||P_l h_l||²≥F(2n−2)≥Fn。任意 known missing |g|≤1 只影响固定两 span 的 N；|N|≤C_kFA，repair energy N²/D≤C_k²FA²/n。修复后 h_lᵀv_l=0，在标量健康路径中只需这个一个 weighted mass 约束；不需要每个 state coordinate 分别 mass-zero。

Support correction 使用全史标量路径的 partial sums；修复总量 O(FA)，block 长度 O(n+k)，Σ后为 O(H²)。Auxiliary error 和 Σ FA_l²/n_l 均为 O(H²)。第 207 行用真实 predictor statistic c_m=W_m†H_m v_m：latent mean/variance 分别 v_mᵀθ、||v_m||²，因为 H_mᵀc_m=P_m v_m=v_m。这给实际 retained 数据上的统计量，不是虚构 ambient Gaussian rows。

因此 U3 的系数 [2β_kη²/√ξ+Frη√ξ]/10、ξ_*=2β_kη/(Fr)、oracle 的 F/2 和两 gap 的 factor 2 相互吻合。Positive β 固定时 ξ_*>0；达到性需要冻结稿开头明示的双向可重复 exact-k profiles。如果动作集合没有这类重复路径，只能接受 converse。

## 6. β=0 ordered limit 和不可升级的边界

第 234–239 行是有效的两次极限：任取 fixed ξ>0，先 H→∞，得 limsup D_H^*/H^{5/2}≤Frη√ξ/10；然后 ξ↓0，配合 D_H^*≥0 得零极限。O_ξ(H²) 可随 ξ 发散，不可在这一证明中直接选择 ξ(H) 或 ξ=0。v1 没有这样做。

本审查接受的是 o(H^{5/2})，不是 Θ(H²)，也不是 H² sharp constant、finite-H 无缺测罚或 full-input recovery。后续 Θ(H²) 证明必须独立给下界、可实现日历和任意 missing g 的 support/control，而不能把 U3 里 ξ 置零。

同 plant/noise 例的 ε 固定在一次比较内，ε>0 的 F=1 和 β_copy(1)=ε/(ε+γ²) 正确；ε=1/100、γ=1/2 给 1/26。ε=0、k=1 的 β=0 与 ε=0、k=2 的 β=1 也正确。固定 B/G、共同 k、gain norm ≤1/2 和齐次 contraction 条件没有替代 actuator command/power 限制；这仍是 ideal linear-gain comparison。

## 7. 正式 checks 的实际覆盖

保存 JSON 为 PASS，证明列出的各计数与实际表的类型吻合：共支持/伪逆、full-record 中性、β/reach/affine cross、rank 稳定后 inverse order、global dual、真实 statistic pullback 及 partial-mode 例。没有把这些有限行当作全称证明。

**972 次 local repair/support assertions 的实际 repair energy 全为 0。** 原因是 v1 配对 gap profiles 互为相反；稿件第 275 行已明确披露。因此 v1 大表本身没有覆盖 α≠0 的分支。正文 U1/support 推导对任意 |g|≤1 的证明仍成立，但后续非对称非零 witness 应单独计数。此前 M1/M2 非零 witness 不自动替代本低秩模型的复现证据；未冒算到本次 972。

## 8. 可保留与必须保留的限制

- 可保留：冻结 fixed-K 的 positive β sharp、zero β ordered o(H^{5/2})、constant-score rowspace characterization、k≤d−p 的有限零罚容量、同 plant/common-noise 的理想线性 gain 例。
- 必须保留：共同支持 B∈rangeG；完整状态与无诊断旁路；固定已知 G/rank/K；标量全史路径及双向可重复 exact-k profiles；positive 与 zero 分支各自量词；uniform controller 结论另证；数值表全零 repair 的实际覆盖；Θ(H²) 尚未纳入 v1；编译未验证。
- 不可推出：部分观测、未知 onset/adaptive policy、任意 vector nuisance、measurement noise、饱和或真实 6R 最优控制、仅凭 stable poles 的 uniform theorem、完整 TAC goal 已完成。

审查状态：**ACCEPTED WITH FIXED-SCOPE QUALIFIERS；Θ(H²) supplement PENDING 独立审查。**
