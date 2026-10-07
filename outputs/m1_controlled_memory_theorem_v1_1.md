# M1 controlled-memory 定理 v1.1：共同输入植物下的匹配诊断亏损

2026-10-07 / v1.1。状态：原 v1 数学证明已获独立审查接受；本版仅编辑澄清和补充覆盖证据。主模型由先冻结的 m1_problem_contract_v1_1.md 给出，SHA256 96e3404ef50cacdb02aa79d2cade36993471b8b15e49a2e75329673cb3ccf378。本稿保持 causal u_j=−Kx_{j−1}、确定初始化、完整健康输入 nodes、gap 内已知 |g|≤1、实际 retained states 和整个创新历史。它不是将 M0 的 output mean 固定后免费改 noise correlation。

## 1. 主定理与真实控制作用

固定 λ,K，c=λ−K∈(−1,1)，q>0，n₀≥1，ρ₀≥0，η,r>0，k≥1。健康类幅值无界，两侧单独槽速率 r/2、差分速率 r。原完整-state oracle 为

\[
O_H=\frac1{2q}\sum_{j=1}^H(\rho_0+\eta j)^2.
\]

令 m=k+1，

\[
A_m=\sum_{\ell=0}^{m-1}c^\ell,\quad
B_m=\sum_{\ell=0}^{m-1}c^{2\ell},\quad
\kappa_c(k)=m-\frac{A_m^2}{B_m}>0.
\tag{T1}
\]

在冻结合同的同一确定性 known-horizon 日历类上，

\[
\boxed{
D_H^*=\frac{\sqrt2}{5q}\sqrt{\kappa_c(k)r}\,
\eta^{3/2}H^{5/2}+o(H^{5/2}).}
\tag{T2}
\]

达到日历为 terminal-balanced symmetric blocks，参数

\[
\xi_*=\frac{2\kappa_c(k)\eta}{r}.
\]

对每个固定 ξ>0，其 explicit 上界为

\[
D_H(\pi_H^\xi)\le
\frac1{10q}\left(\frac{2\kappa_c(k)\eta^2}{\sqrt\xi}
+r\eta\sqrt\xi\right)H^{5/2}+O(H^2).
\tag{T3}
\]

该定理的 proof 下面完整给出，原 v1 已由 m1_independent_review_v1.md 独立接受。只声称首项 sharp，不声称 H² 次阶 sharp、一般最优控制器或完整硬件风险。

完整记录 x=F_c(a+gb+w) 经同一个已知可逆 F_c⁻¹ 映射变为 input innovations：fault、health 和 noise 同步变换，完整实验及 oracle 对 K 中性。删除 state outputs 后创新 projection 随真实 c 改变，κ 进入匹配首项。所有控制器比较保持同一 λ、q、a、健康类、任务时间和诊断器信息限制；不是只改一个输出标准差。

## 2. 真正的 conditional innovation projection

从已知 x_{−n₀}=0 到任意 retained t_i，前一个 retained/known time 为 t_{i−1}。递推给

\[
x_{t_i}-c^{m_i}x_{t_{i-1}}
=\sum_{j=t_{i-1}+1}^{t_i}c^{t_i-j}
(a_j^h+g_j b_j^h+w_j),\quad m_i=t_i-t_{i-1}.
\tag{P1}
\]

除以 √B_m 后，每行 noise variance q。不同 spans 使用互不相交的原始 w_j，所以 rows 的创新独立。预测使用真实前一 state，包含所有跨 block memory。定义单位 row T_i=w_iᵀ/√B_m，P=TᵀT；则 TTᵀ=I，P²=P=Pᵀ，且

\[
G_H(\pi)=\frac1{2q}\inf_{z\in\mathcal Z_H}
\|P(a-gz)\|^2,\qquad
\mathcal Z_H=\{z:|\Delta z_j|\le r\}.
\tag{P2}
\]

输出联合 covariance qR F_cF_cᵀRᵀ 的所有跨 block 项都保留。(P1) 是这个联合实验的可逆 triangular conditional transform，不是对每块输出独立初始化。

末尾无后续 state 读数的移动被原任务继续读数支配：改变只发生在最后一次原读数之后，旧读数分布不变，新实验包含旧 experiment，故逐完整路径 KL 以及取 inf 后 G 都不减。于是求最优可以限于最后 state x_H 被保留；prefix 全读，所有 non-singleton input spans 都来自真实内部 output gaps。后文在这个支配类上 P 的 spans 覆盖完整输入时间。

## 3. Constant gap 与 affine 非反射 cross 的全日历控制

对于 ℓ 个 missing state outputs，input span m=ℓ+1，取 weights w_j=c^{m−j}，j=1,…,m。full innovation information 减去压缩 information 的 norm-square loss 是

\[
L_m(x)=x^\top M_mx,\quad
M_m=I-\frac{ww^\top}{B_m}\succeq0,\quad \|M_m\|\le1.
\tag{G1}
\]

Constant contrast A 的 loss 为 κ_c(ℓ)A²。κ>0 由 strict Cauchy–Schwarz：A_m²<mB_m，m≥2 且 c≠1。κ_c(ℓ) 随 ℓ 非降，可以在同一已知确定初始化植物上依次扩大同一个输出 gap，得到 nested retained experiments，再用 Gaussian KL data processing。该 loss 与 gap 外的长度/输入无关，原因是 (P1) 中每个 span 独立条件创新。

又 κ_c(ℓ)/ℓ→1，因此

\[
b_c:=\inf_{\ell\ge k}\frac{\kappa_c(\ell)}{\ell}>0.
\tag{G2}
\]

一个可计算 tail certificate 是 κ_c(ℓ)≥ℓ+1−(1−|c|)⁻²，故 ℓ≥ceil[2/(1−|c|)²] 时 κ_c(ℓ)/ℓ≥1/2，剩余 finite positive 前缀取最小即可。

M1 的 M_m 不具备 M0 的反射对称性，不能删掉 affine cross。用 input span center 展开更直接：h_j=j−(m+1)/2，x=A1+ηh，A为该 span 上的 affine center amplitude≥0。定义

\[
L_{1,m}=\mathbf1^\top M_mh
=-\frac{A_m}{B_m}\sum_jh_j c^{m-j},\qquad
L_{2,m}=h^\top M_mh\ge0.
\]

于是精确

\[
L_m(x)=\kappa_c(\ell)A^2+2\eta A L_{1,m}+\eta^2L_{2,m}.
\tag{G3}
\]

由 B_m≥1、|A_m|≤(1−|c|)⁻¹、|h_j|≤m/2，

\[
|L_{1,m}|\le\frac{m}{2(1-|c|)^2},\quad
L_m(x)\ge\kappa_c(\ell)A^2-\frac{\eta A m}{(1-|c|)^2}.
\tag{G4}
\]

所有 non-singleton spans 在完整 input clock 上互不相交、包含各自右 retained input；∑m≤H，A≤ρ₀+ηH。因此对**任意允许日历，包括长 gap、dense moves**，所有 negative affine cross 的总费用至多

\[
E_H=\frac{\eta(\rho_0+\eta H)H}{(1-|c|)^2}=O(H^2).
\tag{G5}
\]

这比逐 gap reflection 假设弱，也不需要假定负 cross 只出现在有限长度。它是全称代数 bound，不是数值经验。

每个 gap 的 missing output nodes 就是 input span 前 ℓ 个 nodes，它们 a_j≤2A。因此 ∑missing a_j²≤4ℓ A²。设全部真实 gap norm losses 的和 T，则 (G2)–(G5) 给

\[
T\ge\frac{b_c}{4}\sum_{j\in\mathcal D_\pi}a_j^2-E_H.
\tag{G6}
\]

## 4. Converse：同一个完整健康路径和宏块两预算

固定 ε∈(0,1)，把 late [ceil(εH),H] 分成完整长度 L=floor(H^{3/4}) 的 macros。在每个 clipped observed run 长 n 上取

\[
z_i=g_i r\min(i,n-1-i),\quad i=0,\ldots,n-1,
\]

prefix、missing nodes、run endpoints、macro外及未使用尾段都取 z=0。保持节点 g=±1；该 signed tent 给单一全史 rate≤r 的 z，两侧由 z/2 与 −z/2 实现。令 h=gz。每个真实 non-singleton input span 上 h=0，包括该 span 右 retained input，故 gap residual a−h 恰等于 a。左 prior retained input 也取0，但它不属于这个创新 span，不能误把它再重复计入 gap loss。

以 (P2) 评估该合法全史对手，利用 orthogonal decomposition，得到**精确** normalized converse

\[
2qD_H(\pi)\ge
\sum_j(2a_jh_j-h_j^2)+T.
\tag{C1}
\]

没有 stationary endpoint 项，也无需改变零-target prefix 为 affine extension；full input metric 是 iid，prefix已经 singleton/零对手。

在 macro 内令最小 amplitude A、missing 槽 d、clipped run 数 M、其 lengths n_i，∑n_i=L−d。late A=Θ(H)。令

\[
C=\frac r4(2A-rL/2)>0.
\]

Tent height≤rL/2，area≥(n²−2n)/4，给

\[
\sum_{\rm macro}(2ah-h^2)\ge C\sum_i n_i^2-2CL.
\tag{C2}
\]

M−1 个 runs之间的真实 gaps 完全位于 macro、每个 output gap length≥k；input span center≥A。由 κ 单调和 (G4)–(G5)，同一个全局 T 满足

\[
T\ge\sum_{\rm macros}\kappa_c(k)A^2(M-1)-E_H,
\quad
T\ge\frac{b_c}{4}\sum_{\rm macros}A^2d-E_H.
\tag{C3}
\]

M=0 时第一式仅更弱。跨 macro gaps 不进入第一项，但是每个 missing 槽只按所在 macro 分配到第二项。先将同一全局 T 写成 (1−θ)T+θT、θ∈(0,1)，分别用两界，误差仍是 E_H，不重复收两次完整 gap loss。

令 W=(1−θ)κ_c(k)。M>0 时 Cauchy 与 AM–GM 给 macro normalized 下界

\[
C\frac{(L-d)^2}{M}+WA^2M+\frac{\theta b_c}{4}A^2d
-WA^2-2CL
\ge2A\sqrt{CW}(L-d)+\frac{\theta b_c}{4}A^2d-WA^2-2CL.
\tag{C4}
\]

A≥32Wr/(θ²b_c²) 足以由 C≤rA/2 得 θb_c A²/4≥2A√(CW)。所以 missing d 项被统一吸收。M=0,d=L 时直接由 dead 项和同一吸收条件得到相同 macro 下界

\[
2A\sqrt{CW}\,L-WA^2-2CL.
\tag{C5}
\]

无需规律 run lengths、gap 上限、任务平衡或 sparse switches。固定 ε,θ，主项为 √(2rW)∑A^{3/2}L，所有 macro leftovers/取整/coefficient误差 O(H^{9/4})，∑A²=O(H^{9/4})、∑CL=O(H²)，另加 E_H=O(H²)，calendar 上一致。Riemann和为 (2/5)η^{3/2}(1−ε^{5/2})H^{5/2}+o(H^{5/2})。先取 calendar 最小 deficit，H→∞后再ε↓0、θ↓0，得到

\[
\liminf_{H\to\infty}\frac{D_H^*}{H^{5/2}}
\ge\frac{\sqrt2}{5q}\sqrt{\kappa_c(k)r}\eta^{3/2}.
\tag{C6}
\]

## 5. 上界日历及真实 input projection 的人工 join

使用 M0 upper 同样的 terminal-balanced packing，但预算 H−1、最后1–4个 + state实际读出。Base n_l=2ceil(ξl/2)，block n=2h包含 h个+读数、k个missing、n个−读数、k个missing、h个+读数。Padding multiples of four 均摊，每块 n 只加 O(1)。记 L_l=2(n_l+k)、center c_l=(L_l+1)/2、start x_l，A_l=ρ₀+η(x_l+c_l)，则

\[
M=\sqrt{H/\xi}+O(1),\quad
n_l=\xi l+O(1),\quad A_l=\eta\xi l^2+O(l+1).
\tag{U1}
\]

每块 join 前后的 states 都是真实已读取的 +states。下一块首 read 的 conditional span 长1，只包含下一槽 input innovation。故全局 P 在 input空间的真实 spans 全部落在相应 block/prefix/tail，允许写 P=direct sum P_l；这不是把 state outputs或其联合covariance设为独立。Condition predictor中的前一block末state保留，其history未丢。

## 6. 输入辅助向量与 weighted 总和修复

在 block n=2h、A=A_l，定义 c₀=(k+1)/2 和局部 iid 型 levels

\[
z_i^{+,L}=r(c_0+h-i),\quad
z_i^-=-r[c_0+\min(i-1,n-i)],\quad
z_i^{+,R}=r(c_0+i-1).
\]

若 A≥r(k+n−1)/2，称 active：
held inputs 取辅助 U_i^0=A−g_i z_i^loc，missing inputs 取 U_i^0=A。Inactive blocks全部 U^0=0，prefix/tail U^0=0。这里只用局部 levels生成统计方向，不把它们声称为跨块合法健康路径。Inactive仅uniformly有限个earlyblocks。

Baseline λ_l^0 在 held inputs 为 g_i U_i^0、missing inputs为0，满足 ∑λ_l^0=0。它在完整 input nodes上的 support 与observed-node iid式完全相同，因为填入zero权重只产生跨gap的partial-sum plateau，时间跨度仍k+1：

\[
h_l^0=\frac{A r}{2}n(n+2k)
-4r^2\sum_{j=0}^{n/2-1}(c_0+j)^2.
\tag{U2}
\]

完整证明：+residual≥0、−residual≤0；其partial sums在lefthalf≥0、negative center归0、righthalf≤0、end归0。Q≠0时 Δz^loc=−rΔt sign(Q)，centerslope0对应Q0。Summation by parts和四重layer计数给 h^0=(λ^0)ᵀz^loc，即(U2)。

设 p_l=P_l g_l，并令

\[
N_l=g_l^\top P_lU_l^0,\quad
D_l=\|p_l\|^2,\quad
\alpha_l=N_l/D_l,\quad
v_l=P_lU_l^0-\alpha_l p_l.
\tag{U3}
\]

N_l 是完整 input weighted sum，不是 observed signs 的未加权和。Inactive取 v_l=0。两真实 gap各压缩 fixed m=k+1 个inputs；其余 2n−2 个held输入是singletons且g²=1，所以

\[
D_l\ge2n-2\ge n>0.
\tag{U4}
\]

P_lU_l^0 与 baseline 仅在两个gap spans不同。对每span，projection的L₁范数≤√m‖P U‖≤mA；baseline在该span只含rightheld点、绝对值≤A，且 |g|≤1。因此取 C_k=2(k+2)，

\[
|N_l|\le\|\operatorname{diag}(g_l)P_lU_l^0-\lambda_l^0\|_1\le C_k A,\quad
|\alpha_l|\le C_k A/n.
\tag{U5}
\]

修复使 **g_lᵀv_l=0精确成立**，并且 v_l=P_lv_l。Energy cost精确

\[
\|v_l-P_lU_l^0\|^2=\frac{N_l^2}{D_l}
\le C_k^2A^2/n.
\tag{U6}
\]

这一步覆盖所有已知 |g|≤1 的missing profiles、包括zero/constant/alternating，且包括negative c；没有假设Pu非负。

## 7. 修复后的全史 support 与 Gaussian dual

定义 δλ_l=diag(g_l)v_l−λ_l^0。由于 repaired weighted sum为0和baseline sum为0，∑δλ_l=0。又 ∥diag(g_l)p_l∥₁≤√L_l‖p_l‖≤L_l，L_l=2(n+k)，所以

\[
\|\delta\lambda_l\|_1
\le C_k A+|\alpha_l|L_l
\le C_k(k+3)A.
\tag{U7}
\]

对任意 zero-mass λ supported in length L contiguous input block，自由level且rate r的完整健康类有

\[
h_{\mathcal Z}(\lambda)=r\sum_j|Q_j|,
\quad |Q_j|\le\|\lambda\|_1/2,
\quad h(\lambda)\le r(L-1)\|\lambda\|_1/2.
\tag{U8}
\]

因而 δλ support每块 O(rA(n+k))，累积 O(H²)。Baseline support由完整路径restriction给≤∑h_l^0；没有把healthy paths重新初始化。全局 v 是各repaired v_l及零prefix/tail，属于range(P)，且 **∑g_j v_j=0**。于是

\[
h_{\mathcal Z}(gv)\le\sum h_l^0+O(H^2)
\le\frac r2\sum A_l n_l^2+O(H^2).
\tag{U9}
\]

实际可用统计量由retained conditional innovations形成：row方向 Tv，其input方向是v=TᵀTv，noise variance q‖v‖²。Gaussian Fenchel给

\[
G_H(\pi)\ge\frac1q
\left[a^\top v-\frac12\|v\|^2-h_{\mathcal Z}(gv)\right].
\]

因此exact

\[
2qD_H(\pi)\le
\|(I-P)a\|^2+\|Pa-v\|^2+2h_{\mathcal Z}(gv).
\tag{U10}
\]

这两个orthogonal能量部分来自实际全projection，非独立state block variance替代。

## 8. Auxiliary error 与 affine oracle费用

每个 active input点 |a_i−U_i^0|≤(η+r)(n_l+k)。Held点包含η(t−center)+g zloc；missing点包含η(t−center)。Prefix误差0，有限inactive blocks合计O(1)，tail至多4点、每点a=O(H)。故

\[
\|a-U^0\|^2
\le2(\eta+r)^2\sum(n_l+k)^3
+4(\rho_0+\eta H)^2+O(1)=O(H^2).
\]

Projection contraction和(U6)给

\[
\|Pa-v\|^2\le2\|a-U^0\|^2
+2C_k^2\sum A_l^2/n_l=O(H^2).
\tag{U11}
\]

Input gap centers与M0 retained-endpoint centers不同，不能直接抄反射式。对本block，两gap input centers相对block center为 1/2±(n_l+k)/2。用(G3)，κ=κ_c(k)、L₁=L_{1,k+1}、L₂=L_{2,k+1}，其sum norm loss精确为

\[
2\kappa(A_l+\eta/2)^2
+\frac{\kappa\eta^2}{2}(n_l+k)^2
+4\eta(A_l+\eta/2)L_1+2\eta^2L_2.
\tag{U12}
\]

于是

\[
\|(I-P)a\|^2=2\kappa\sum A_l^2+O(H^{3/2}).
\tag{U13}
\]

这保留非反射cross而不宣称它为0。所有gaps都在post-onset区间，prefix/tail是singletons无额外loss。

## 9. Matching coefficient 与余项

合并(U9)–(U13)：

\[
2qD_H(\pi_H^\xi)\le
2\kappa\sum A_l^2+r\sum A_l n_l^2+O(H^2).
\]

由(U1)，∑l⁴=M⁵/5+O(M⁴)，

\[
\sum A_l^2=\frac{\eta^2}{5\sqrt\xi}H^{5/2}+O(H^2),\quad
\sum A_l n_l^2=\frac{\eta\sqrt\xi}{5}H^{5/2}+O(H^2).
\]

得到(T3)。ξ*=2κη/r的AM–GM最小系数为(√2/(5q))√(κr)η^{3/2}，与(C6)匹配，推出(T2)。r始终是两侧差分速率，q是同一物理输入创新variance。c=0给κ=k，恢复iid theorem；negative c按原模型成立。

## 10. 受限已知 gain 比较的解析结论

令 R_m(c)=A_m²/B_m=m−κ_c(k)。对0<c<1，

\[
R_m(c)=\frac{1+c}{1-c}\frac{1-c^m}{1+c^m},\quad
\frac{d}{dc}\log R_m(c)
=\frac2{1-c^2}-\frac{2m c^{m-1}}{1-c^{2m}}>0.
\]

最后严格正来自 B_m=∑c^{2j}>m c^{m−1}（AM–GM，m≥2且c<1）。故κ严格递减于[0,1)。对c<0，triangle给 |A_m(c)|≤A_m(|c|)、B_m(c)=B_m(|c|)，于是κ_c(k)≥κ_|c|(k)，非零negative时严格。

因此在任意预先指定的已知finite controller族，可比较其匹配首项并取最小κ，完整oracle相同。如果额外指定理想线性gain的固定稳定裕度族 |λ−K|≤c_bar<1，则其**首项系数**在 c=c_bar、K=λ−c_bar取唯一最小（c_bar>0）。这不是finite-H所有风险最优、actuator-constrained控制最优，或允许pole随H逼近1的结论。

例：k=1，c=0,1/2,−1/2的κ分别1、1/5、9/5。保持同一physical a,b,q和calendar budget，optimal deficit leading coefficient相对c=0分别为1、1/√5、3/√5；此比较同步改变输出fault像、health像、state covariance，而完整Σa²/(2q)不变。该“memory保存缺测输入”机制是实际反馈结构的作用，不是只缩小输出noise。

本节只比较先取H→∞的fixed-gain系数。如需对H-dependent gains或compact gain族下的joint优化交换inf与limit，需另行记录uniform constants；本稿不利用那个额外结论。

## 11. 精确计算、证据边界及待审点

正式复现入口为 outputs/m1_controlled_memory_checks_v1.py / .json，只用标准库Fraction及整数isqrt。在仓库根目录执行 python outputs/m1_controlled_memory_checks_v1.py，stdout应与保存JSON一致；work保留首次执行副本，正式output与其SHA256逐份一致。实际exit=0：

- 1270个已知zero初始化植物 retained子集合：直接state联合covariance求逆与input projection信息逐例相等；包含未观察terminal和empty subset。
- 35个完整state记录控制中性检查。
- 320个affine中心crossbound、κ monotonic/tail证书。
- 72个positive pole κ单调、72个negative comparison。
- 129个完整terminal-balanced calendars，含129个range(P)/weighted总和/dual deficit/oracle affine pair恒等式，695个local repairenergy/support证书。
- g missing profile取zero、leftconstant、linear、alternating；c取−4/5,−1/2,0,1/2,4/5，k=1,2,3；小H=32,64，另H=256,1024,4096大calendar sanity。计算q=1、n₀=3，一般q和fixedn₀由正文证明覆盖。

数值normalized趋向只用于实现sanity，不作拟合或proof。重点独立审查：完整state likelihood→projection、所有input nodes的健康量词、long gap affine cross全局误差、两次T预算误差只付一次、weighted零矩分母、gap right retained input归属、join singleton真实性、修复energy/support的O(H²)、U12中心偏移与½因子。没有运行历史MC、D2-a或硬件。

TAC整体目标仍需文献主定理对照、有限机械实现与D2-a、整稿及实际包验收。这个M1解析主张即使通过审查，也不自动完成整个长期goal。

配套standalone TeX已请求built-in editor打开；compiler返回平台错误 Unable to find standard directories for platform，无source diagnostics。编译状态为 UNVERIFIED (platform compiler failure)，未安装替代TeX运行时。数学证明、脚本执行与编译状态分别记录。

## v1.1 版本绑定与新增覆盖

原 v1 proof SHA256 0689f5ce730f656ba1fe6cfbf2b2f13be1da89ff0ff91d932c81efaeda913ffe；m1_independent_review_v1.md 的原 v1 审查绑定保留。本版是独立文件，未覆盖原稿。只澄清半hold h=n/2 与 gap span m=k+1、双向 exact-k profile 可重复串接、最优信息的 sup、scalar gz/gv 的逐节点含义。

达到性使用 +→− 和 −→+ 两个方向的预先已知 exact-k bounded moves，可在预定起点与 holds 重复串接。无需 profile 对称，也不要求有限-H sup 达成。Scalar gz=diag(g)z，gv=diag(g)v；所有支持函数与零质量约束仍在完整 input nodes 上。

正式新增证据 outputs/memory_asymmetric_repair_checks_v1.py/.json 仅运行六个非对称局部 cases，两个 gap profiles 分别 1/3、−2/3。两例 M1、两例 M2、两例 M2S 全有 N≠0、α≠0、repair energy>0，并验证真实 initialized retained-state statistic 的 pullback 和方差。原 m1 v1 的完整 calendar checks 中所有 repair energy 为零（镜面对称 profiles）；原 local certificates 验证代数界，但不能称其已练到非零修复分支。旧大表未重跑。

非零 scalar 见证 c=−1/2、k=1、n=4、A=10、r=1 给 N=8/15，D=383/45，α=24/383，repair energy=64/1915；未修复总质量非零，在 free-level 健康类上的支持函数是无穷，修复后总质量精确零。详见 memory_asymmetric_repair_supplement_v1.md。编译状态仍单独标 UNVERIFIED（built-in compiler platform failure），不将 source 或 checks PASS 等同编译成功。
