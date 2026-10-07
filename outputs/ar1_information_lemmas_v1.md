# 平稳 AR(1) 缺测信息：完整引理、全史 profiling 接口与跳变边界

版本 2026-10-07 / v1。此文件是独立数学推导；不把八例继承计算升级成有漂移最优日历定理。正式复现入口：`outputs/ar1_information_checks_v1.py`、`outputs/ar1_information_checks_v1.json`。在仓库根目录运行 `python outputs/ar1_information_checks_v1.py`；脚本只用标准库，stdout 应与保存 JSON 一致。主要新增是完整边界覆盖、精确多区间与任务端点分解、可证明的条件统一误差，以及对一个错误迁移桥梁的反例。标准 Gaussian/Markov/Schur 计算是工具，不作为 TAC 主创新。

## 1. 信息合同与量词

令 n≥1，完整时域是整数槽 {1,…,n}。噪声是共同的平稳零均值 Gaussian AR(1)：

\[
\epsilon_1\sim N(0,\sigma^2),\qquad
\epsilon_i=\rho\epsilon_{i-1}+\xi_i,\quad
\xi_i\overset{\rm iid}{\sim}N(0,\sigma^2(1-\rho^2)),\quad
\sigma>0,\quad -1<\rho<1.
\]

初始噪声与未来创新独立。固定确定性保留集合 R={t₁<⋯<tₚ}，使用该集合上**边缘**协方差 C_R=(σ²ρ^|tᵢ−tⱼ|)。不能把缺测创新填零后沿用全记录 precision。对两确定性均值差 x 定义

\[
Q_R(x)=x_R^\top C_R^{-1}x_R,\qquad
G_R(x)=\tfrac12 Q_R(x).
\]

G 是同协方差 Gaussian 两点实验的 KL，Q 是平方 Mahalanobis 距离。R=∅ 时二者取零。以下 ν 与 β 都是 **Q/Fisher 系数**；对应 KL 是系数再乘 x²/2：

\[
w_d=\frac{1-\rho^d}{1+\rho^d},\qquad
\nu=\frac{w_1}{\sigma^2}=\frac{1-\rho}{\sigma^2(1+\rho)},\qquad
\beta(k)=\frac{(k+1)w_1-w_{k+1}}{\sigma^2}.
\tag{1}
\]

复合模型若为 raw 观测 Y_i=s_i b_i+1_alt a_i+ε_i，则两侧全史 nuisance 的差分集合必须定义为

\[
\mathcal Z_n=\{b_0-b_1:b_0\in\mathcal B_{0,n},\ b_1\in\mathcal B_{1,n}\},\quad
x_i(z)=a_i-s_i z_i,\quad
\mathcal G_R=\inf_{z\in\mathcal Z_n}\tfrac12 Q_R(x(z)).
\tag{2}
\]

这里 inf 是同一对完整路径，不是每块重新挑 z。只有证明了差分集合恰为某个 Lipschitz 类后，才可用那个类替代 Z_n。对式 (2) 的称呼是“profiled pairwise KL / 几何分离量”；它不自动等于复合检验的 minimax risk 或 log-likelihood ratio，风险桥梁需另证。解调 D_s 后必须同时用 D_s C_R D_s；此文件所有任务例保持 raw C_R。

## 2. 引理 A：任意保留集合的精确能量

对 p≥1 和任意实 x，

\[
Q_R(x)=\frac{x_{t_1}^2}{\sigma^2}
+\sum_{j=2}^{p}
\frac{(x_{t_j}-\rho^{d_j}x_{t_{j-1}})^2}
{\sigma^2(1-\rho^{2d_j})},\qquad d_j=t_j-t_{j-1}.
\tag{3}
\]

**证明。** 对任意 d≥1，递推展开给出 ε_{i+d}=ρ^dε_i+∑_{h=1}^dρ^{d-h}ξ_{i+h}。后项与截至 i 的全史独立，其方差为 σ²(1−ρ²)∑_{h=0}^{d-1}ρ^{2h}=σ²(1−ρ^{2d})。不相交保留间隔的创新和独立。因而保留向量的 Gaussian 密度分解为首项 N(0,σ²) 与这些 d_j 步条件密度。对一个均值差 x 进行同一三角白化，得到首项 x_{t₁}，以及 x_{tⱼ}−ρ^{dⱼ}x_{tⱼ₋₁}，各自除以相应标准差。白化后 covariance 为单位阵，Gaussian KL 是均值差平方范数的一半，故得到 (3)。所有分母因 |ρ|<1 为正；ρ<0 只改变预测系数符号。□

此证明也说明：平稳初始化是 σ² 的首项。已知非平稳初始方差、确定初始化、观测历史条件化均不服从本合同，必须重算首项或整个条件协方差。

## 3. 引理 B：常均值单 gap、多 gap、首尾缺测

假设 x_i=a 为已知常数。

1. 内部缺失 k≥0 个槽且两端保留，令 m=k+1。相对完整记录的损失是

   \[
   \Delta Q=a^2\beta(k),\qquad
   \Delta G=\frac{a^2}{2\sigma^2}\left[m\frac{1-\rho}{1+\rho}-\frac{1-\rho^m}{1+\rho^m}\right].
   \tag{4}
   \]

2. 对任意非空 R，设首缺 p₀=t₁−1、尾缺 p₁=n−tₚ、内部 gap k_j=t_{j+1}−t_j−1，则

   \[
   Q_{\{1,\ldots,n\}}(a\mathbf1)-Q_R(a\mathbf1)
   =a^2\left[\nu(p_0+p_1)+\sum_{j=1}^{p-1}\beta(k_j)\right].
   \tag{5}
   \]

   不要求 gap 长分离；两个 gap 可以仅被一个保留槽隔开。没有内部 gap 时和为空。

3. 全部缺测时损失为 a²[σ⁻²+(n−1)ν]；n=1 时为 a²/σ²。首/尾缺测但仍有至少一个保留读数时，每个缺失槽损失 νa²，不使用内部 β。

4. β(0)=0；k≥1 时 β(k)>0。ρ=0 时 β(k)=k/σ²。归一化等效损失槽数为 κ=β/ν=m−w_m/w₁，在 k=1、ρ=0、1/2、−1/2 时分别是 1、1/5、9/5。

**证明。** 将常 x 代入式 (3)：首项是 a²/σ²，d 步转移为 a²(1−ρ^d)²/[σ²(1−ρ^{2d})]=a²w_d/σ²。完整 n 槽因此为 a²[σ⁻²+(n−1)ν]。内部 m 次一步转移被一次 m 步转移替代，得到 (4)。并且 n−1=p₀+p₁+∑_{j=1}^{p-1}(k_j+1)，相减得到 (5)。p=0 单独按空观察零信息处理。k=0、ρ=0、κ 的数值均直接代入。

为证明严格正性而不依赖符号猜测，取局部 m+1 槽 precision P。删去内部 M={2,…,m}、保留两端 E 时，完成平方给出

\[
Q_{\rm local}(v)-Q_E(v_E)
=(v_M+P_{MM}^{-1}P_{ME}v_E)^\top P_{MM}
(v_M+P_{MM}^{-1}P_{ME}v_E)\ge0.
\tag{6}
\]

P_MM 正定。完整 AR(1) precision 的内部行是 σ⁻²(1−ρ²)⁻¹(−ρ,1+ρ²,−ρ)，对常向量 a1 的该行值为 νa。若 k≥1、a≠0，则 P_MM v_M+P_ME v_E=νa1≠0，式 (6) 严格正。用 (4) 得 β(k)>0。这里 Schur/完成平方只用于证明正性；主等式已由 Markov 密度推导。□

**范围。** 此精确可加性是对同一个已知常均值成立。不能在一般 x 或 profile inf 后把每个 gap 当作一个独立常均值实验。

## 4. 引理 C：任意均值、多 gap 的局部精确 loss

对内部 gap，端点为 ℓ、ℓ+m，m=k+1；局部损失为

\[
L_{\ell,m}(x)=\frac1{\sigma^2(1-\rho^2)}
\sum_{h=1}^{m}(x_{\ell+h}-\rho x_{\ell+h-1})^2
-\frac{(x_{\ell+m}-\rho^m x_\ell)^2}{\sigma^2(1-\rho^{2m})}.
\tag{7}
\]

其为正半定二次型，仅依赖这 m+1 槽均值，k=0 时恒为零。若 R 非空，完整损失是所有内部 (7)，加上首段

\[
L_{\rm pre}=\frac{x_1^2-x_{t_1}^2}{\sigma^2}
+\sum_{i=2}^{t_1}\frac{(x_i-\rho x_{i-1})^2}{\sigma^2(1-\rho^2)}
\tag{8}
\]

和尾段 ∑_{i=tₚ+1}^n(x_i−ρx_{i−1})²/[σ²(1−ρ²)]。每个整体局部项非负；不能按 (8) 中的个别减项判断符号。

**证明。** 在完整式 (3) 中，保留槽之间未缺测的项全部消去；每个含缺测区间留下该区间的一步总和减一次跳转，得到 (7)。首项和末段相减得 (8) 及尾式。局部正半定性由对该局部完整记录删去其内部、前缀或后缀的式 (6) 得到。不同缺测连通分量共享端点也不影响这种代数分解。□

## 5. 引理 D：保留块分解与双端任务边界

把非空 R 分为 B 个最大连续保留块。令

\[
c_\rho=\frac{\rho}{\sigma^2(1+\rho)},\qquad
d_\rho=\frac{\rho}{\sigma^2(1-\rho^2)}.
\]

块间第 j 个 gap 两保留端为 u_j=x_ℓ、v_j=x_{ℓ+m_j}，m_j≥2。则**对任意 x**，

\[
Q_R(x)=\nu\sum_{i\in R}x_i^2
+c_\rho(x_{t_1}^2+x_{t_p}^2)
+d_\rho\sum_{\substack{i,i+1\in R}}(x_{i+1}-x_i)^2
+\sum_{j=1}^{B-1}B_{m_j}(u_j,v_j),
\tag{9}
\]

\[
B_m(u,v)=\left[\frac1{\sigma^2(1-\rho^{2m})}-\frac1{\sigma^2(1+\rho)}\right](u^2+v^2)
-\frac{2\rho^m uv}{\sigma^2(1-\rho^{2m})}.
\tag{10}
\]

ρ<0 时 c_ρ、d_ρ 或 B_m 可以为负；Q 总体仍正定。不能把所有边界单项解释成正的信息损失。

**证明。** 完整一个连续块 I 的式 (3) 展开平方并收集系数，得到

\[
Q_I(x)=\nu\sum_{i\in I}x_i^2+c_\rho(x_{\min I}^2+x_{\max I}^2)
+d_\rho\sum_{i,i+1\in I}(x_{i+1}-x_i)^2.
\tag{11}
\]

内部 x² 系数为 ν+2d_ρ=(1+ρ²)/[σ²(1−ρ²)]，两端系数 ν+d_ρ+c_ρ=1/[σ²(1−ρ²)]，交叉系数为 −2d_ρ。单槽块把两端同一个 x 计两次：ν+2c_ρ=σ⁻²，因此 (11) 也成立。将各块 (11) 相加，后续块的首项 v²/σ² 被重复当作独立初始化。由 (3)，应把该首项替换成 (v−ρ^m u)²/[σ²(1−ρ^{2m})]。内部两端 correction 合起来变为

\[
c_\rho u^2+(c_\rho-\sigma^{-2})v^2
+\frac{(v-\rho^m u)^2}{\sigma^2(1-\rho^{2m})}.
\]

展开后两个平方项具有同一系数 1/[σ²(1−ρ^{2m})]−1/[σ²(1+ρ)]，交叉项如 (10)，故 (9) 成立。□

当 u=v=A 时 B_m=(w_m−w₁)A²/σ²；当 u=A、v=−A 时 B_m=(w_m⁻¹−w₁)A²/σ²。二者差

\[
B_m(A,-A)-B_m(A,A)=\frac{4\rho^m A^2}{\sigma^2(1-\rho^{2m})}.
\tag{12}
\]

这个端点乘积项是 constant β 之外必须保留的任务边界信息；它是精确公式，不是由仿真拟合的“额外常数”。

## 6. 引理 E：局部近常值 gap 的显式统一误差

若 |x_{ℓ+h}−x_ℓ|≤Lh (h=0,…,m)，令 A=x_ℓ，

\[
C_\rho=\frac{1+|\rho|}{\sigma^2(1-|\rho|)},\quad
S_m=\sum_{h=0}^{m}h^2=\frac{m(m+1)(2m+1)}6,\quad
D_m=C_\rho L^2S_m.
\]

则

\[
|L_{\ell,m}(x)-\beta(m-1)A^2|
\le2|A|\sqrt{\beta(m-1)D_m}+D_m.
\tag{13}
\]

**证明。** 局部 loss 是 (6) 给出的 PSD 矩阵 M，且 0≼M≼P。局部完整 AR(1) precision 的端点绝对行和为 1/[σ²(1−|ρ|)]，内部绝对行和为 C_ρ；因此谱范数 ≤C_ρ。m=1 时 M=0，结论直接成立。写 x=A1+δ，δ_h=x_{ℓ+h}−A，则 δᵀMδ≤C_ρ∑δ_h²≤D_m，1ᵀM1=β(m−1)。PSD Cauchy–Schwarz 给 |1ᵀMδ|≤√(βD_m)。展开 xᵀMx=A²β+2A1ᵀMδ+δᵀMδ，即得 (13)。□

## 7. 定理 F：条件全史 profile 的 O(n²) 统一桥梁

固定 K≥1、A₀≥0、L≥0。对每个 n，非空完整路径集合 X_n 满足

\[
\forall x\in X_n:\quad |x_i|\le A_0n,\quad |x_{i+1}-x_i|\le L\quad(1\le i<n).
\tag{14}
\]

日历必须保留 1,n，每个内部 gap 长度 1≤k_j≤K。J 为其数目，ℓ_j 为左端，m_j=k_j+1。定义同一全史路径上的 surrogate

\[
T_R(x)=\nu\sum_{i=1}^n x_i^2-\sum_{j=1}^J\beta(k_j)x_{\ell_j}^2.
\tag{15}
\]

令 β_*=(K+1)ν、D_*=C_ρ L² S_{K+1}。则所有这些 x、R 同时满足

\[
|Q_R(x)-T_R(x)|\le E_n,
\quad E_n=2|c_\rho|A_0^2n^2+|d_\rho|(n-1)L^2
+J\{2A_0n\sqrt{\beta_*D_*}+D_*\}.
\tag{16}
\]

故在**相同** X_n 上，

\[
\left|\inf_{x\in X_n}\tfrac12Q_R(x)-\inf_{x\in X_n}\tfrac12T_R(x)\right|\le\tfrac12E_n.
\tag{17}
\]

由于 J≤n，E_n=O(n²)=o(n^{5/2})；若 |ρ|≤q<1、σ≥σ_min>0、A₀,L,K 固定，则这个 O(n²) 对通道族也一致。

**证明。** 用完整块恒等式 (11) 与 (14) 得 |Q_full−ν∑x²|≤2|c_ρ|A₀²n²+|d_ρ|(n−1)L²。由于两端保留，没有 prefix/suffix 项，(7) 给 Q_R=Q_full−∑L_{ℓ_j,m_j}。对每个 gap 用 (13)，且 β(k_j)=m_jν−w_{m_j}/σ²≤(K+1)ν，因为 w_m>0；S_m≤S_{K+1}。三角不等式得到 (16)。点态不等式 T_R−E_n≤Q_R≤T_R+E_n 对同一非空 X_n 取 inf，即得 (17)，无需最小值可达、无需交换逐块 inf 与求和。最后 J≤n、上述常数在声明通道族下有界，完成阶数结论。□

**不适用之处。** 健康差分 z Lipschitz 并不使 raw x=a−s z 在任务切换处 Lipschitz。无界幅值 nuisance 类也不自带 (14) 的 envelope。定理 F 只在先证明有效候选/近最优路径可约束到这样的 X_n 后可用；不允许自行把 Z_n 截断或平滑。它证明一个条件桥梁，不证明原 TAC 主猜想。

## 8. 反例 G：合法全史 nuisance 否定对所有路径的 constant-gap 迁移

取 σ=1、ρ=1/2、每个 gap 缺一槽 k=1；因此 ν=1/3，β(1)=1/15。令 n=H 为足够大的完全平方数，J=√H 个内部 gap 彼此分离（例如缺测点 g_j=⌊jH/(J+1)⌋，j=1,…,J）。两端保留。健康差分取同一合法全史路径 z_i≡H，故速率为 0；暂取 signal a_i≡0。任务 s 在每个 gap 的缺测槽之后翻转，缺测槽仍取左侧任务。raw mean contrast x_i=−s_iH。

每个 gap 局部完整均值是 (A,A,−A)，A=±H。两一步 full energy 为 A²/3+3A²，保留两端的二步跳转 energy 为 5A²/3。故

\[
L_{\ell,2}(x)=\frac53H^2,\qquad
\beta(1)x_\ell^2=\frac1{15}H^2,\qquad
L-\beta x_\ell^2=\frac85H^2.
\tag{18}
\]

引理 C 精确相加：真实 Q loss 与 constant-gap 替代的误差为 (8/5)JH²=(8/5)H^{5/2}，对应 KL 误差为 (4/5)H^{5/2}。这个 nuisance 是完整路径、无重置；raw covariance 未解调，因而不是误用协方差制造的伪例。它推翻了“对所有合法 z，以 βx_left² 替换每个 gap 且误差统一为 o(H^{5/2})”的命题。

**它没有推翻主 candidate。** 在此零 signal 例中，z≡0 也合法，profiled KL 为零；上述 z≡H 不一定是最小化路径。因此不能由点态反例推出 profile inf 后的 H^{5/2} 系数为假。另有一个合同边界：如果 oracle 对缺测槽不定义任务/均值，就不存在这里的完整 loss 比较，但保留数据的式 (9)–(12) 仍成立。实际 candidate 必须先冻结 oracle 定义。

## 9. 定理 H：保留 raw 任务边界的全 nuisance 统一 O(n) 桥梁

这个结果比定理 F 更适合原 raw 合同；它不把边界压成单个常值 β，而保留式 (10) 的端点结构。

设 signal 满足 |a_{i+1}−a_i|≤η。令实际非空差分集合 Z_n 中的**每条完整路径**满足 |z_{i+1}−z_i|≤r，且不要求任何幅值上界。s_i∈{−1,+1}，x_i(z)=a_i−s_i z_i，covariance 仍是 raw C_R。R 为任意固定非空保留集合。将其分成连续且任务符号恒定的块；若相邻保留槽任务不同，即使没有 missing，也必须分块。定义边界集合 E 为相邻保留索引对 (t_j,t_{j+1}) 中满足“t_{j+1}−t_j≥2 或 s_{t_{j+1}}≠s_{t_j}”的所有对。它们的 span 为 m_j≥1。式 (10) 也定义 m=1，并且 B₁(u,v)=d_ρ(u−v)²。

定义

\[
S_R(z)=\nu\sum_{i\in R}(a_i-s_i z_i)^2
+c_\rho(x_{t_1}(z)^2+x_{t_p}(z)^2)
+\sum_{(\ell,\ell+m)\in E}B_m(x_\ell(z),x_{\ell+m}(z)).
\tag{19}
\]

则对全部 z∈Z_n 同时成立

\[
Q_R(x(z))-S_R(z)=d_\rho\sum_{\substack{i,i+1\in R\\s_{i+1}=s_i}}
\big[(a_{i+1}-a_i)-s_i(z_{i+1}-z_i)\big]^2,
\tag{20}
\]

\[
|Q_R(x(z))-S_R(z)|\le |d_\rho|(n-1)(\eta+r)^2.
\tag{21}
\]

因此，无需幅值 envelope、无需最小值可达，

\[
\left|\inf_{z\in Z_n}\tfrac12Q_R(a-sz)-\inf_{z\in Z_n}\tfrac12S_R(z)\right|
\le\tfrac12|d_\rho|(n-1)(\eta+r)^2=O(n).
\tag{22}
\]

ρ≥0 时 S≤Q≤S+误差；ρ<0 时 S−误差≤Q≤S。该结论同样对 |ρ|≤q<1、σ≥σ_min>0、固定 η,r 一致。空 R 的两个 inf 均为零。

**证明。** 引理 D 的分块论证不要求块最大；可以在相邻但不同任务符号的两个保留槽之间再切一刀。此时跨块 span m=1，将 (10) 代入得到 B₁=d_ρ(u−v)²，所以该切分仍精确。式 (9) 的 within-block 差分项只保留相邻、被观察且具有相同 s 的项，其余全部进入式 (19) 的边界 B。因 x_{i+1}−x_i=(a_{i+1}−a_i)−s_i(z_{i+1}−z_i) 在同任务相邻槽成立，得到 (20)。每一平方项 ≤(η+r)²，项数≤n−1，得到 (21)。在同一全史 Z_n 上对点態上下界取 inf，得到 (22)；正负号由 d_ρ 的符号决定。虽然 S 单项可能不凸、可能为负，(21) 和 Q≥0 保证它在该 Lipschitz 类上有下界，故 inf 的比较合法。□

**意义与限制。** 这里的 surrogate 是“retained bulk + exact all boundaries + stationary endpoints”，并不是“full bulk − constant β gaps”。它对原 raw 合同保留了任务跳变及整个差分路径集合，无界幅值不妨碍 O(n) 误差。因为 E 中每个 B 的端点平方/乘积在 z=O(H) 时可以是 O(H²)，约 √H 个边界可以影响 H^{5/2} 首项，不能从 (22) 再自行删掉这些项。达到 candidate 的剩余问题已经缩小为：在这个确定性的全史二次变分问题中，最优/近最优 z 的双端值如何随日历变化？

### 引理 I：仿射 signal 的 gap 中心反射恒等式

对局部 gap 的全部 m+1 槽令 h_j=j−m/2 (j=0,…,m)，其均值差为 x_j=A+ηh_j。设 M 是局部 loss (7) 的矩阵，E_k=hᵀMh，k=m−1。则

\[
L(x)=\beta(k)A^2+\eta^2E_k,\qquad E_k\ge0.
\tag{23}
\]

因此 KL loss 精确为 β(k)A²/2+η²E_k/2≥β(k)A²/2，适用于负 ρ 和 k=0。

**证明。** 令 J 为局部 m+1 维反射矩阵。平稳 covariance 的条目只依赖 |i−j|，故 J C J=C，进而 J C⁻¹ J=C⁻¹。保留两端的 covariance 同样在交换两端时不变，将其 precision 嵌入完整维度后也与 J 对易。M 是这两个 precision 的差，因此 JMJ=M。J1=1、Jh=−h，故 1ᵀMh=(J1)ᵀM(Jh)=−1ᵀMh=0。引理 B 给1ᵀM1=β，展开仿射二次型得 (23)。M≽0 给 E_k≥0；k=0 时 M=0。□

**用于 zero-endpoint tent 对手的条件。** 若 raw x=a−s z，且 a 在 gap 上仿射，那么需 z 在 gap 的全部局部 m+1 槽都为零，**包含两个保留端点**，才能把 x 取成这里的 a。只在 missing 槽令 z=0 不能推出 (23)。这条反射恒等式可用于 converse 构造，但并未解决 macro 分块中跨宏边界 gap 的 dead-budget 分配。

## 10. 已证、未证与下一条可执行桥梁

**已证：** 任意保留集合的 exact marginal likelihood energy；known constant mean 的单/多 gap 精确 loss，含首尾、负 ρ、k=0、全缺测；任意均值的局部 loss 与保留块端点二次型；局部 near-constant error；有明确线性 envelope 与全局 Lipschitz 的全史 profile 统一 O(n²) 误差；raw 合法 nuisance 下一个错误 uniform bridge 的 H^{5/2} 反例；保留 raw task/missing 双端边界的整个无界幅值 Lipschitz nuisance 类统一 O(n) profile 桥梁；仿射 gap 的 exact reflection cancellation 与非负中心斜率余项。

**未证：** 原 nuisance 全类的最小化路径可满足定理 F；保留任务端点乘积项后的最优漂移路径/日历常数；候选 (√2/5)√(νβ(k)r)η^{3/2} 的上下界与一致小余项；oracle 与任务缺测的物理合同；控制器族改变 signal、nuisance、covariance 的同步可实现性。以上均不得写成已证 sharp 结论。

**下一步可执行：** 依 (19)–(22)，对同一 z 的 Lipschitz 多面体研究 retained bulk 与双端边界构成的变分问题。数值最小化应优先用 Q_R 的凸平方形式（S_R 拆开的矩阵可能无约束下不凸，但在声明类中与 Q 差 O(n)）。先比较 iid 最优/近最优路径上的端点 z/H 是否可趋零；若不能，双端项可能改变 candidate 首项。不要删除 endpoint stationary 项，除非另外证明它们最多 O(H²) 或在所需尺度中可忽略。

## 11. 计算支持及证据边界

配套程序只用 Python 标准库 Fraction。ρ∈{−4/5,−1/2,0,1/2,4/5}，n=1,…,8，对每个 n 的全部 2^n 个保留集合枚举（含空集合）：2550 次 rational covariance inverse 对 Markov formula；2550 次 constant multigap/boundary formula；2550 次 arbitrary-mean block identity；2550 次 raw 全史 uniform bridge 恒等式及误差检查。另有 35 个 k=0,…,6 的 local smooth bound 检查、35 个 affine reflection 恒等式检查，以及 H=16,64,256 三个 raw jump 反例。

检查实际 exit=0。有限枚举支持实现与因子核对；全称结果由上述证明承担。没有执行机械 D2-a，也没有据这些小计算声称最优日历或风险定理。

配套 `.tex` 已请求 built-in editor 打开，但当前 built-in compiler 返回平台错误 `Unable to find standard directories for platform`，没有给出源码错误诊断。因此该 TeX 源码的编译状态是 **UNVERIFIED (platform compiler failure)**。未安装替代 TeX；数学推导与脚本执行状态不依赖此编译结果。
