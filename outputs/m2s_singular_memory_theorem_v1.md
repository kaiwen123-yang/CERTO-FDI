# M2S 定理 v1：共同Gaussian支持、输入模式恢复与归一化缺测罚

2026-10-07 / v1。状态：完整证明稿，待独立审查。先冻结 m2s_problem_contract_v1.md，SHA256 80a5a5d643432f54f1a2d9f3dc7a9e374528358c18e10beb6b0e1ac1d5b9e7d5。M2 Q≻0版本保持不变。本稿仍只含一个scalar nuisance、known fixed stable controller和retained full states。达到性明确采用标准两任务protocol中的双向exact-k移动：+→−与−→+均有known bounded profile，能与holds重复串接；若动作集合只含单向或不能串接，此稿只有converse自动成立，不能引用达到性。

## 1. 主结论：positive penalty与zero normalized penalty

固定已知严格稳定 A_K，noise factor G∈R^{d×p} fullcol、1≤p≤d，B∈range(G)且非零，初始x_{−n₀}=0已知，prefix全读，其他时间/任务/健康约定按冻结合同。令f=G†B，F=||f||²>0，

\[
M_m=\sum_{r=0}^{m-1}A_K^rB,\quad
W_m=\sum_{r=0}^{m-1}A_K^rGG^\top(A_K^r)^\top,\quad m=k+1,
\]

\[
\beta_k=mF-M_m^\top W_m^\dagger M_m\ge0.
\tag{T1}
\]

用O_H=(F/2)Σa_j²、D_H^*=O_H−sup_πG_H(π)，则：

1. 若β_k>0，

\[
D_H^*=\frac{\sqrt2}{5}\sqrt{F\beta_k r}\eta^{3/2}H^{5/2}
+o(H^{5/2}),
\qquad \xi_*=\frac{2\beta_k\eta}{Fr}.
\tag{T2}
\]

2. 若β_k=0，

\[
D_H^*/H^{5/2}\longrightarrow0.
\tag{T3}
\]

(T3)不声称更低指数或其sharp常数，也不把ξ*=0代入calendar。两个branches都来自完整quantifier下的exactexperiment，不由rankless Gaussian公式猜测。

3. β_k=0恰等价constant scalar mean mode 1_m⊗f被span压缩保留；这不等于全部latent inputs都可恢复。设noise reachability index ν_R，则

\[
\beta_k=0\ \Longrightarrow\ k<\nu_R\le r_\infty-p+1\le d-p+1.
\tag{T4}
\]

所以zero normalized penalty只能出现在k≤d−p；p=d时恢复M2的all k≥1 strict positivity。

## 2. 共同支持与精确信息：不能盲用伪逆

完整white latent input为ξ及mean θ=(f(a^h+gb^h))。Retained state data是

\[
Y=L_R(\theta+\xi),\qquad
L_R=R F_{A_K}\operatorname{diag}(G).
\]

因为B=Gf，所有h、所有完整健康路径的mean都在range(L_R)。所以所有Gaussian laws具有共同support range(L_R)，covariance L_RL_Rᵀ；不会有伪逆漏掉的hypothesis-specific确定性分量。

取rank-r SVD L_R=U_r Σ_r V_rᵀ。在实际共同data support上，Σ_r⁻¹ U_rᵀY与Y等价，noise为N(0,I_r)，mean为V_rᵀθ。因此任意两点KL精确为

\[
\tfrac12\|V_r^\top(\theta_1-\theta_0)\|^2
=\tfrac12\|\operatorname{Proj}_{row(L_R)}(\theta_1-\theta_0)\|^2.
\tag{P1}
\]

这是Gaussian共支持公式的证明，不假定ambient full covariance invertible。

Retained predictor的block-triangular变换S（diag为I_d）给actual innovation
x_{t_i}−A_K^{m_i}x_{t_{i−1}}；首项减已知init。S可逆，把L_R变为disjoint interval maps H_m=[A_K^{m−1}G,…,G]。Left乘可逆S不改变rowspace，故

\[
P_m=H_m^\top W_m^\dagger H_m,\quad P^2=P=P^\top,
\]

\[
G_H(\pi)=\tfrac12\inf_{z\in\mathcal Z_H}
\|P(a_f-H_gz)\|^2.
\tag{P2}
\]

所有cross-block state covariance由L_R保留；独立的是原始ξ intervals，不是被重新初始化的states。

若希望显式rank-adapted Gaussian rows，选U_m为range(W_m) orthonormal basis，T_m=(U_mᵀW_mU_m)⁻¹/²U_mᵀH_m，则T_mT_mᵀ=I_{rank W_m}、T_mᵀT_m=P_m。不能宣称d个redundant rows W_m^{†/2}H_m的covariance是I_d。

完整state记录恢复G†(x_j−A_Kx_{j−1})，所以P_full=I_{p(H+n₀)}、full composite experiment及O_H对knownK中性。Fixed calendar的Gaussian凸检验可在上述common support rows里进行；不存在不同support造成的无限KL。

## 3. 为什么sup_m||W_m†||在fixed plant下有限

记

\[
\mathcal R_m=range(W_m)
=span\{G,A_KG,\ldots,A_K^{m-1}G\},
\quad \mathcal R_\infty=\bigcup_m\mathcal R_m.
\]

Cayley–Hamilton给R_d为A_K-invariant，R_m=R_d对所有m≥d。这个结论不要求normal或||A_K||<1。W_m≽W_d，且对m≥d两者具有相同range和kernel，因此在R_d上其正定inverse满足W_m†≼W_d†（ambient kernel上均为0）。于是

\[
\Gamma_K:=\max_{1\le m\le d}\|W_m^\dagger\|<\infty,\quad
\sup_{m\ge1}\|W_m^\dagger\|\le\Gamma_K.
\tag{R1}
\]

有限个m≤d的positive eigenvalues都非零，G fullcol且p≥1，所以Γ有限。不能用W_1†作为all m上界；例如shift register的range随m先增大，W_2†可能在W_1 kernel上非零。

Strict stability另给S_B=Σ_{r≥0}||A_K^rB||<∞。设C_K=Γ_K S_B²。所有fixed controller constants都可依noise-reach conditioning；没有uniform Γ族的结论不随之成立。

## 4. β geometry、monotonic、tail与恢复容量

令d_m=1_m⊗f。H_md_m=M_m，因此

\[
\beta_k=d_m^\top(I-P_m)d_m\ge0.
\tag{B1}
\]

β_k=0⇔d_m∈row(H_m)⇔存在y满足

\[
G^\top(A_K^\top)^r y=f,\qquad r=0,\ldots,k.
\tag{B2}
\]

这是constant mean模式的exact恢复条件。只证明一个已知constant shift的full score可保留，不要求P_m=I_{mp}。

Nested retained-state deletion给β_ℓ非降，即使Gaussians奇异也可用(P1)的rowspace inclusion：删行使noise map rowspace缩小，orthoproject information不增。Exactlocal gap loss与外部states无关来自实际predictor。且

\[
\beta_\ell\ge(\ell+1)F-C_K,\quad \beta_\ell/\ell\to F>0.
\tag{B3}
\]

若β_k>0，则b_K=inf_{ℓ≥k}β_ℓ/ℓ>0；例如L₀=max(k,ceil(2C_K/F))给b_K≥min(F/2,β_k/L₀)>0。β_k=0时不使用这个strict-positive b_K。

定义ν_R=min{m:R_m=R∞}，r∞=dimR∞。若R_{m+1}=R_m，则A_K R_m⊂R_m，后续不再增长。R₁ rank p，每次到达稳定前至少增长1维，所以

\[
\nu_R\le r_\infty-p+1\le d-p+1.
\]

若(B2)成立，ζ=(A_Kᵀ−I)y满足Gᵀ(A_Kᵀ)^rζ=0，r=0,…,k−1，即ζ⊥R_k。如果k≥ν_R，R_k=R∞为A-invariant，故上述annihilation对所有r≥0成立，序列Gᵀ(A_Kᵀ)^r y的相邻差永远0。初项为f，因此全序列恒为非零f。但strict stability令A_K^r→0，极限0，矛盾。这证明(T4)。此容量bound由noise rank与固定state order共同决定，不能让controller额外存储无限history后仍称同一类。

## 5. Matrix affine cross在全日历上的O(H²)

Span center h_j=j−(m+1)/2，d_h=(h_jf)_j，N_m=Σh_j A_K^{m−j}B。BecauseΣh=0，

\[
L_{1,m}=d_m^\top(I-P_m)d_h
=-M_m^\top W_m^\dagger N_m,\quad
L_{2,m}=d_h^\top(I-P_m)d_h\ge0.
\]

||M_m||≤S_B、||N_m||≤mS_B/2、(R1)给|L₁|≤mC_K/2。故affine interval mean中心A≥0的actual norm loss

\[
L_m=\beta_{m-1}A^2+2\eta A L_{1,m}+\eta^2L_{2,m}
\ge\beta_{m-1}A^2-C_K\eta A m.
\tag{A1}
\]

Terminal无后续read的moves由hold支配；限t_N=H，prefix全read，全部non-singleton input spans都在post-onset affine区域。其Σm≤H且A≤ρ₀+ηH，因此total cross费用≤E_H=C_Kη(ρ₀+ηH)H=O(H²)，calendar上一致。若β_k=0，则PSD还直接给L_{1,k+1}=0，不能由此宣称全部slope信息也保留。

## 6. Positive β branch的全日历converse

β_k>0时取合法全史zero-endpoint signed tents：late macros L=floor(H^{3/4})，每clipped held run z_i=g_i r min(i,n−1−i)，missing inputs、gap-right first read、run endpoints、prefix及其余时域均为0。h=gz在全部non-singleton spans为0，两侧健康由±z/2实现。一条完整路径，无初始level重置。

Orthoproject identity给normalized exact
2D_H(π)≥FΣ(2ah−h²)+T，其中T为同一gap residual=a的norm losses。每macro最小A、missing d、run数M，有C=r(2A−rL/2)/4，tent saving≥CΣn_i²−2CL。A1及β monotonic给same global T≥Σβ_k A²(M−1)−E_H；missing节点a≤2span-centerA及b_K>0给T≥(b_K/4)Σ A²d−E_H。Cross-macro完整gaps只在后者按每missing槽付预算；不会重复收β。

固定θ∈(0,1)，先在全局split T，W=(1−θ)β_k。M>0时macro normalized下界

\[
FC(L-d)^2/M+WA^2M+\theta b_K A^2d/4-WA^2-2FCL.
\]

AM–GM前两项≥2A√(FCW)(L−d)，A≥32FWr/(θ²b_K²)吸收d。M=0,d=L同一dead项直接得相同bound。Late A=Θ(H)确保所有日历最终都满足。主项√(2FrW)ΣA^{3/2}L，其余O(H^{9/4})+E_H O(H²)，uniformπ。Riemann integral(2/5)η^{3/2}(1−ε^{5/2})H^{5/2}，先infπ、H→∞、再ε,θ↓0给liminf≥(√2/5)√(Fβ_k r)η^{3/2}。所有support/pseudoinverse依赖已在前节验证，不借ambientGaussian density。

## 7. Upper：所有ranks下都成立的weighted修复

对每个fixed ξ>0，同M2的H−1 terminal-balanced symmetric blocks：base n_l=2ceil(ξl/2)，block half-hold h_l=n_l/2个+read、k missing、n_l个−read、k missing、h_l个+read；padding均摊、剩1–4个tail states实际read。实际join有相邻true states，下一span singleton，所以input P按genuine intervals落入block，不fake初始化。
M=√(H/ξ)+O(1)、n_l=ξl+O(1)、A_l=ηξl²+O(l+1)。

Active若A≥r(k+n−1)/2。Auxiliary U_j=f(A−g zloc)在held点、fA在missing点，local iid-type levels与M2(U2)相同；inactive/prefix/tail为0，只有finiteearlyinactive。Baseline scalarλ⁰=F(g A−zloc)在held、0在missing，sum0、support

\[
h_l^0=F[Ar\,n(n+2k)/2-4r^2\sum_{j=0}^{n/2-1}((k+1)/2+j)^2].
\]

Same partialsum/saturated slope证明确切保持physical gap跨度k+1；无额外健康level固定。令h_l=(g_jf)_j，p_l=P_l h_l，N=h_lᵀP_lU，D=||p_l||²，v_l=P_lU−(N/D)p_l。因为G fullcol，singleton P_1=I_p；每block除两gap-right inputs外的2n−2个heldsingleton给

\[
D\ge F(2n-2)\ge Fn,\quad
|N|\le C_kFA,\quad C_k=2(k+2).
\tag{U1}
\]

后者因与zero-mass baseline的差只在两个fixed-m spans，contraction给每span∑|h_jᵀ(PU)_j|≤mFA、baseline rightheld贡献≤FA。Thus h_lᵀv_l=0 exact，v_l∈rangeP，repair energy=N²/D≤C_k²FA²/n。此结论不要求rankW_m=d。

δλ_j=h_jᵀv_j−λ⁰_j也sum0，||δλ||₁≤C_k(k+3)FA，因为Σ|h_jᵀp_j|≤LF。Full scalar路径support=rΣ|partialsum|≤r(L−1)||δλ||₁/2，所以global correctionO(H²)。Full restriction/sublinearity给

\[
h_{\mathcal Z}(\lambda)\le(Fr/2)\sum A_l n_l^2+O(H^2).
\]

Actual统计量可以不用虚构d维I-covariance：每span coefficient c_m=W_m†H_m v_m作用于真实predictor创新。其latent noise方向H_mᵀc_m=P_mv_m=v_m，variance||v_m||²、mean v_mᵀθ，故global v真实可实现。Fenchel即

\[
2D_H(\pi)\le||(I-P)a_f||^2+||Pa_f-v||^2+2h(\lambda).
\tag{U2}
\]

Auxiliary error||a_f−U||²=O(H²)，repair ΣFA_l²/n_l=O(H²)，contraction给middle termO(H²)。

两个gap input中心相对block center为1/2±(n+k)/2。Fixed k时exact pair oracle norm loss为

\[
2\beta_k(A_l+\eta/2)^2+\frac{\beta_k\eta^2}{2}(n_l+k)^2
+4\eta(A_l+\eta/2)L_{1,k+1}+2\eta^2L_{2,k+1}.
\]

故oracle loss=2β_kΣA_l²+O(H^{3/2})（β=0时还可更小，但不需要）。最后

\[
D_H(\pi_H^\xi)\le
\frac1{10}\left(\frac{2\beta_k\eta^2}{\sqrt\xi}
+Fr\eta\sqrt\xi\right)H^{5/2}+O_\xi(H^2).
\tag{U3}
\]

该上界对β≥0都成立，且全部noise/healthy历史一致。

## 8. 两branch的最终limit

β_k>0时优化ξ*=2β_kη/(Fr)，U3与positive converse同一coefficient，得T2。

β_k=0时0≤D_H^*≤D_H(π_Hξ)，每个fixed ξ>0给
limsup D_H^*/H^{5/2}≤Frη√ξ/10。只在这个H limit之后让ξ↓0，得T3。O_ξ(H²)可依ξ并发散，因此没有隐含允许ξ(H)任意趋0，也没有声称一个ξ=0 calendar。更低指数/positive coefficient需要新的下界和构造；本稿不推测。

## 9. 同一plant、noise和gainnorm的memory例

取A_plant=0、B_u=I₂、B=e₂。两known gainsK₀=0、K_copy=−N_γ，
N_γ=[[0,γ],[0,0]]，γ=1/2。Closed matrices为0与N_γ，均zero poles、gain∞norm≤1/2，且同一one-step homogeneous contraction bound为1/2。固定外部noise covarianceQ_ε=diag(ε,1)；ε>0取G=diag(√ε,1)，ε=0取G=e₂。F均1；此ε是各次比较的固定physical noise参数，不由controller免费改变。

Exact

\[
\beta_0(k)=k,\quad
\beta_{\rm copy}(1)=\frac{\epsilon}{\epsilon+\gamma^2},\quad
\beta_{\rm copy}(2)=\frac{\gamma^2+2\epsilon}{\epsilon+\gamma^2}.
\tag{E1}
\]

因为m≥2时W_m=diag(ε+γ²,1)、M_m=(γ,1)，而0-controller只保留最后input的常均值信息1。ε=1/100、k=1时β_copy=1/26，baseline1，leading penalty coefficient比1/√26。ε=0、k=1时right state=(γ previous input,current input)，γ≠0时whole input span可恢复、β=0；这里||A_copy||∞=1/2<1，因此zero-β不要求noncontractive homogeneous dynamics。k=2时β_copy=1仍positive、baseline2，leading coefficients比1/√2。

对k=1两者已满足同一one-step contraction≤1/2约定；若要求exact two-step homogeneous extinction，则common k=2且两个closed matrices都满足A_K²=0。不能给予controller不同的移动时间。Common plant、B、Q_ε、r、η、prefix、state sensors和k保持不变。Gainnorm≤1/2不意味着controller commands满足同一finite actuator hard bound或control power预算；本例仍是明示的ideal linear-gain comparison。

## 10. Constant模式恢复不等于所有inputs恢复

先把scaled copy扩为d=3、A_copy只把x₂复制进x₁，第三坐标独立：G=[e₂,e₃]、B=e₂，p=2、F=1。H₂=[γe₁,0,e₂,e₃] rank3<latent input dimension4；force-channel sufficient score可恢复、但第三coord的前一input没有恢复，β₁=0而P₂≠I₄。
更强的区别：d=3 nilpotent shiftN₃，G=[e₂,e₃]、B=e₂+e₃，p=2、F=2。k=1，H₂=[e₁,e₂,e₂,e₃] rank3<latent input dimension4，但constant ray(1,1,1,1)在rowspace（statefunctional y=(1,1,1)）。β₁=0，同时P₂≠I₄、部分latent noise/input modes丢失。Slope coefficientL₂=1/2非零。这反例防止把T3错误改写为“全部创新已恢复”。
d阶shift register、G=B=e_d、p=1则对k≤d−1确实有P=I_{k+1}、β=0，对k≥d β=k+1−d，达到T4的d−p容量上界。

## 11. Rank变化和模型边界

若在ε=0的2D例把N换成δN，任何δ≠0仍可从右state恢复两input，β₁=0；δ=0时β₁=1。固定process G/B，所有poles都0，gainnorm可≤1，但reached-subspace rank在δ=0改变，W₂†范数可按δ⁻²增长。这里information关于gain可以不连续。它不推翻fixed-K定理，也不凭这个粗bound断言uniform asymptotic必失败；它说明不能只给稳定pole范围就自动引用本Γ-based uniform proof。Unknown exact rank或measurement noise必须另建experiment。

B∉rangeG时两个Gaussian支持可能不同，伪逆norm可能遗漏确定性区分，不能沿用本公式。Arbitrary vector uncertainty、partial observation、未知controller、hard saturation、finite健康幅值盒、adaptive/unknown onset均保持在本版外。

## 12. 复现与待审范围

正式standalone入口 outputs/m2s_singular_memory_checks_v1.py / .json，只用标准库Fraction。仓库根目录执行 python outputs/m2s_singular_memory_checks_v1.py，stdout应与保存JSON一致；正式副本与实际PASS的work副本SHA256逐份相同。实际exit=0：690组Moore–Penrose四恒等式，450个joint Gaussian mean∈covariance image及direct-C† KL对真实projection；60个complete-record中性；285个β monotonic/rowspace/cross；275个reach-index positive bound；281个rank稳定后W_d†−W_m† PSD；186个global calendars与oraclepair/dual身份、186个实际raw state statistic/variance pullback、972个local repair/support bound；8个ε共plant公式。另验证两个β0而P非I的partial-mode例。没有random MC或外部数值库。

Coverage限定：v1两gap profiles互为相反，所有972次repair energy assertions实际值为0；它们验证了这些输入的bounds，但没有覆盖alpha≠0。非对称、非零repair将由单独supplement检验，不在v1数字中冒算。

Root需要重点独立审共同支持、true triangular rowspace变换、Γ有限proof（不能用Q†错误上界）、恢复容量ν_R、β0 ordered limit、每个F/½因子、噪声rank变化scope以及实际统计量可用性。数学证明与有限checks分开；不据这些产物宣布整个TAC研究goal完成。

Standalone TeX已请求built-in editor打开；compiler返回平台错误 Unable to find standard directories for platform、无source diagnostics。编译状态UNVERIFIED (platform compiler failure)，未安装替代运行时。源码另查tab、孤立CR及低控制byte，不能把数学审查接受写成编译PASS。
