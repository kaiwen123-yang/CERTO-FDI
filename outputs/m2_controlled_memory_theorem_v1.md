# M2 fixed-order controlled-memory 定理 v1：完整状态与同一标量健康路径

2026-10-07 / v1。状态：完整证明稿，待独立审查。先冻结模型 m2_problem_contract_v1.md，SHA256 794c245d0fdb672021cb36566382d68834b2abe20331dde0bc01a0bc71671eae。M1合同及scalar证明不被本稿覆盖。本稿只扩展固定阶植物、full-state readings和共同scalar输入B；不是任意vector nuisance、partial observation或unknown controller定理。

## 1. 主定理

同一已知植物及causal feedback

\[
x_j=A x_{j-1}+B_u u_j+B(a_j^h+g_j b_j^h)+w_j,\quad
u_j=-Kx_{j-1},\quad A_K=A-B_uK.
\]

维数d固定，B≠0，Q≻0，w_j独立N(0,Q)，已知x_{−n₀}=0，fixed n₀≥1，A_K严格离散稳定。健康两侧各自幅值无界、rate r/2，实际完整scalar difference z rate≤r。任务g在held点±1、missing点预先已知且|g|≤1；换任务至少k槽missing，diagnostic只读retained full state，不读fast内部states/commands。Fixed H与template a_j=ρ₀+ηj（post-onset）、prefix为0，同冻结合同。

令

\[
F=B^\top Q^{-1}B>0,\quad
M_m=\sum_{r=0}^{m-1}A_K^rB,\quad
W_m=\sum_{r=0}^{m-1}A_K^rQ(A_K^r)^\top,\quad m=k+1,
\]

\[
\beta_K(k)=mF-M_m^\top W_m^{-1}M_m>0.
\tag{T1}
\]

完整state oracle为 O_H=(F/2)Σ_{j=1}^H a_j²，与K中性。在同一允许日历/完整健康类上，

\[
\boxed{
D_{K,H}^*=\frac{\sqrt2}{5}\sqrt{F\beta_K(k)r}\,
\eta^{3/2}H^{5/2}+o(H^{5/2}).}
\tag{T2}
\]

Terminal-balanced symmetric calendar取

\[
\xi_*=\frac{2\beta_K(k)\eta}{Fr}
\]

达到此leading coefficient。每个fixed ξ>0都有

\[
D_{K,H}(\pi_H^\xi)
\le\frac1{10}\left(\frac{2\beta_K(k)\eta^2}{\sqrt\xi}
+Fr\eta\sqrt\xi\right)H^{5/2}+O(H^2).
\tag{T3}
\]

Fixed-K constants允许依赖nonnormal transient；不要求||A_K||<1，也不把没有uniform稳定界的controller族下这些余项称一致。只声称首项sharp。

## 2. 共同动态与真实innovation投影

选固定factor L，Q=LLᵀ，f=L⁻¹B，||f||²=F。完整input white innovations ξ_j=L⁻¹w_j独立N(0,I_d)。令a_f=(f a_j)_j，healthy map H_g z=(f g_j z_j)_j。

前一真实retained state（首项为已知初始化）到下一state的span m：

\[
x_{t_i}-A_K^m x_{t_{i-1}}
=\sum_{j=t_{i-1}+1}^{t_i}A_K^{t_i-j}B(a_j^h+g_j b_j^h)
+\sum_{j=t_{i-1}+1}^{t_i}A_K^{t_i-j}w_j.
\]

其covariance W_m≽Q≻0。令

\[
H_m=[A_K^{m-1}L,\ldots,L],\quad
T_m=W_m^{-1/2}H_m,\quad
P_m=H_m^\top W_m^{-1}H_m.
\tag{P1}
\]

T_m T_mᵀ=I_d，P_m为orthogonal projector。不同spans在真实white input clock上不相交；堆叠得到TTᵀ=I、P=TᵀT。完整state输出covariance仍包含跨block项，conditional predictor包含真实前一state，因此这种input projection不是输出噪声reset。

真实information为

\[
G_{K,H}(\pi)=\frac12\inf_{z\in\mathcal Z_H}
\|P(a_f-H_gz)\|^2,\quad
\mathcal Z_H=\{z:|\Delta z_j|\le r\}.
\tag{P2}
\]

Unknown只是一条scalar z，statistic方向v的healthy support权重是λ_j=(f g_j)ᵀv_j，finite support要求单个scalar约束Σλ_j=0，不是对每个state coordinate各设一个自由offset。

全state记录经共同已知可逆F_{A_K}和L⁻¹还原为同一输入实验，fault、health、noise同步变换，整个full-record composite风险保持，O_H=(F/2)Σa²。因此不同K改变的是删输出后的P(coupled dynamics)，不是免费改一个输出noise方差。

## 3. β严格正、monotonic及long-gap tail

在span m，constant fault的white input向量d_m=1_m⊗f，H_m d_m=M_m，故

\[
d_m^\top(I-P_m)d_m=mF-M_m^\top W_m^{-1}M_m=\beta_K(m-1)\ge0.
\]

若m≥2且β=0，则d_m在H_mᵀrowspace，存在y使H_mᵀy=d_m。最后两个input blocks给

\[
L^\top y=f,\quad L^\top A_K^\top y=f.
\]

第一式y=L^{-T}f=Q⁻¹B≠0，第二式A_KᵀQ⁻¹B=Q⁻¹B，迫使A_K有eigenvalue1，与严格稳定矛盾。故β>0，Q≻0和B≠0都在这里真正使用。

在同一个足够长initialized full-state实验中，扩大一个gap对应nested deletion，known constant scalar input的KL data processing给β_K(ℓ)随missing count ℓ非降。Loss只依该真实span，span外input lengths/g不影响该known-input比较。

严格稳定给finite

\[
S_B=\sum_{r=0}^\infty\|A_K^rB\|<\infty,\quad
C_K=\|Q^{-1}\|S_B^2.
\tag{B1}
\]

因为||M_m||≤S_B、W_m⁻¹≼Q⁻¹，β_K(ℓ)≥(ℓ+1)F−C_K，所以β_K(ℓ)/ℓ→F。于是

\[
b_K=\inf_{\ell\ge k}\beta_K(\ell)/\ell>0.
\tag{B2}
\]

还可不用扫无限ℓ给computable certificate：取L₀=max(k,ceil(2C_K/F))，tail比值≥F/2；finite前缀由monotonic≥β_K(k)/L₀。因此b_K≥min(F/2,β_K(k)/L₀)>0。

## 4. Matrix affine gap cross的calendar-uniform误差

对span input-center h_j=j−(m+1)/2，令d_h=(h_j f)_j，

\[
N_m=H_m d_h=\sum_j h_j A_K^{m-j}B,\quad
L_{1,m}=d_m^\top(I-P_m)d_h=-M_m^\top W_m^{-1}N_m,
\]

\[
L_{2,m}=d_h^\top(I-P_m)d_h\ge0.
\]

负号来自Σh_j=0。||N_m||≤(m/2)S_B，故

\[
|L_{1,m}|\le \frac m2 C_K.
\]

Affine white input x=(A+ηh_j)f，A≥0，exact norm loss

\[
L_m(x)=\beta_K(m-1)A^2+2\eta A L_{1,m}+\eta^2L_{2,m}
\ge\beta_K(m-1)A^2-C_K\eta A m.
\tag{G1}
\]

这一式不假定反射或normal A。末尾无后续read的moves由stay支配，故最优可限t_N=H；prefix全读，所以各non-singleton spans都在post-onset affine时域并互不相交，Σm≤H。所有A≤ρ₀+ηH，global cross error

\[
E_H=C_K\eta(\rho_0+\eta H)H=O(H^2)
\tag{G2}
\]

对每个允许日历一致。Missing inputs（该span的前ℓ点）a_j≤2A，于是全部gap实际norm losses T 满足

\[
T\ge\frac{b_K}{4}\sum_{j\in\mathcal D_\pi}a_j^2-E_H.
\tag{G3}
\]

## 5. 任意日历converse

固定ε∈(0,1)，late macros长度L=floor(H^{3/4})。在每条clipped observed run n，取完整scalar健康差

\[
z_i=g_i r\min(i,n-1-i),
\]

missing input nodes、right-first retained节点、run endpoints、prefix/macro外/tail取0。一个全史rate-r路径由两侧z/2、−z/2实现。令h=gz；non-singleton innovation spans（含right retained input）上h=0。Input white metric给exact

\[
2D_{K,H}(\pi)\ge F\sum_j(2a_jh_j-h_j^2)+T.
\tag{C1}
\]

没有stationary endpoint或prefix affine替换。每macro最小amplitude A、missing d、run数M、lengths n_i，有Σn_i=L−d。令C=r(2A−rL/2)/4>0，tent area/height给 saving≥CΣn_i²−2CL。

M−1个完整gaps都在macro内，β monotonic且center≥A，所以same global T的另一界为T≥Σmacros β_K(k)A²(M−1)−E_H。Cross-macro gaps不进入count，但是missing节点在(G3)中只按所在macro分配一次。先split同一T=(1−θ)T+θT，误差仍只E_H。

W=(1−θ)β_K(k)。M>0时Cauchy和AM–GM给normalized macro下界

\[
FC(L-d)^2/M+WA^2M+\theta b_KA^2d/4-WA^2-2FCL
\ge2A\sqrt{FCW}(L-d)+\theta b_KA^2d/4-WA^2-2FCL.
\]

A≥32FWr/(θ²b_K²)足以统一吸收d项；M=0,d=L时直接用dead term同样得
2A√(FCW)L−WA²−2FCL。
Late A=Θ(H)，所有日历最终都满足。主和√(2FrW)ΣA^{3/2}L；macro coefficient/取整/last incomplete Riemann项O(H^{9/4})，ΣA² O(H^{9/4})、ΣCL O(H²)、matrix cross E_H O(H²)。Constants依fixed K等参数而非calendar。

先取最优calendar，再H→∞、ε↓0、θ↓0，Riemann integral (2/5)η^{3/2}(1−ε^{5/2})H^{5/2}给

\[
\liminf_{H\to\infty}D_{K,H}^*/H^{5/2}
\ge\frac{\sqrt2}{5}\sqrt{F\beta_K(k)r}\eta^{3/2}.
\tag{C2}
\]

## 6. 达到日历：人工join是真实singleton innovation

预算H−1取最多even base n_l=2ceil(ξl/2) symmetric blocks：n=2m对应m个+read、k missing、n个−read、k missing、m个+read。余下multiples of four均摊，各n仅加O(1)，终点1–4个+state实际读取。则

\[
M=\sqrt{H/\xi}+O(1),\quad
n_l=\xi l+O(1),\quad
A_l=\rho_0+\eta(x_l+c_l)=\eta\xi l^2+O(l+1).
\tag{U1}
\]

人工join前末state和下一first state都是真实读数，下一input span仅长1。P在white input space按真实spans落入block、prefix和tail，故可写direct sum P_l。输出联合covariance仍跨block相关；没有重新生成任何state或innovation。

## 7. Vector auxiliary和单个scalar weighted mass修复

Active block条件A≥r(k+n−1)/2。c₀=(k+1)/2，取iid-type局部levels

\[
z_i^{+,L}=r(c_0+m-i),\quad
z_i^-=-r[c_0+\min(i-1,n-i)],\quad
z_i^{+,R}=r(c_0+i-1).
\]

Held input辅助U_j=f(A−g_j z_j^loc)，missing辅助U_j=fA；inactive、prefix、tail U=0。Inactive仅uniformly有限个earlyblocks，局部z仅用来生成dual不要求primal拼接。

Baseline scalar λ⁰在held节点为(g_j f)ᵀU_j=F(g_j A−z_j^loc)、missing为0。它sum0，完整node支持等于iid observed-time式乘F：

\[
h_l^0=F\left[\frac{Ar}{2}n(n+2k)
-4r^2\sum_{j=0}^{n/2-1}(c_0+j)^2\right].
\tag{U2}
\]

证明：threshold保证+residual≥0、−residual≤0，partial sums左右有正确sign、center与end归0；local saturatedΔz=−rΔt sign(Q)，gap跨度k+1；filled-zero weights保留这个物理跨度。Summation by parts和四重level计数即(U2)。

令h_l=(g_j f)_j，p_l=P_l h_l，

\[
N_l=h_l^\top P_lU_l,\quad D_l=\|p_l\|^2,\quad
\alpha_l=N_l/D_l,\quad v_l=P_lU_l-\alpha_l p_l.
\tag{U3}
\]

除两个gap-right inputs外，其他2n−2个held inputs为singleton，P=I_d且||h_j||²=F，因此

\[
D_l\ge F(2n-2)\ge Fn.
\tag{U4}
\]

Difference scalar weights h_jᵀ(P_lU)_j−λ⁰只在两个fixed-span intervals内。每span projection contraction给

\[
\sum_j|h_j^\top(P_lU)_j|
\le\sqrt{mF}\|P_lU\|
\le mFA,
\]

baseline仅该span右held一点、绝对值≤FA。所以C_k=2(k+2)满足

\[
|N_l|\le C_kFA,\quad |\alpha_l|\le C_k A/n.
\tag{U5}
\]

**修复后h_lᵀv_l=0精确成立**，v_l∈range(P_l)。只有scalar healthy初始自由level，单个scalar weighted mass约束恰足；未引入vector nuisance。Energy cost

\[
\|v_l-P_lU_l\|^2=N_l^2/D_l\le C_k^2 F A^2/n.
\tag{U6}
\]

Inactive选v=0。所有known |g|≤1 profiles与negative/rotating/nonnormal dynamics均被这些norm bounds覆盖。

## 8. 健康support修复累计O(H²)

δλ_j=h_jᵀv_j−λ⁰_j有sum0。又

\[
\sum_j|h_j^\top p_j|\le\|h_l\|\|p_l\|\le L_lF,
\]

所以

\[
\|\delta\lambda_l\|_1\le C_kFA+|\alpha_l|L_lF
\le C_k(k+3)FA.
\tag{U7}
\]

完整scalar路径类对zero-mass向量的support是rΣ|partialsum|，每partialsum≤L₁/2，length L block support≤r(L−1)L₁/2。修复每块cost O(Fr A(n+k))，总和O(H²)。Global v为各range(P_l) vectors和零prefix/tail，Pv=v，Σ_j (g_jf)ᵀv_j=0 exact。Sublinearity与full-path restriction给

\[
h_{\mathcal Z}(\lambda)\le\sum h_l^0+O(H^2)
\le\frac{Fr}{2}\sum A_l n_l^2+O(H^2).
\tag{U8}
\]

没有逐block重置健康level；actual noise方向由Tv作用于真实conditional innovations，variance=||v||²。Gaussian Fenchel给
G≥a_fᵀv−||v||²/2−h(λ)，从而

\[
2D_{K,H}(\pi)\le
\|(I-P)a_f\|^2+\|Pa_f-v\|^2+2h(\lambda).
\tag{U9}
\]

## 9. 能量与matrix affine oracle pair

每个active input的aux scalar误差≤(η+r)(n+k)，因此
||a_f−U||²≤F[2(η+r)²Σ(n_l+k)³+4(ρ₀+ηH)²+O(1)]=O(H²)。
(U6)与projection contraction给

\[
\|Pa_f-v\|^2\le2\|a_f-U\|^2+
2C_k^2F\sum A_l^2/n_l=O(H^2).
\tag{U10}
\]

两gap input centers相对blockcenter仍为1/2±(n_l+k)/2。对fixed m=k+1，(G1)中β=β_K(k)、L₁、L₂固定。其exact总loss是

\[
2\beta(A_l+\eta/2)^2+\frac{\beta\eta^2}{2}(n_l+k)^2
+4\eta(A_l+\eta/2)L_1+2\eta^2L_2.
\tag{U11}
\]

所以||(I−P)a_f||²=2βΣA_l²+O(H^{3/2})；没有删掉nonreflection cross。Prefix/tail为singletons，g profile只影响healthy image，不改变known fault oracle pair。

汇总(U8)–(U11)：

\[
2D_{K,H}(\pi_H^\xi)\le2\beta\sum A_l^2+Fr\sum A_l n_l^2+O(H^2).
\]

Power sum给ΣA_l²=η²H^{5/2}/(5√ξ)+O(H²)、ΣA_l n_l²=η√ξ H^{5/2}/5+O(H²)，推出(T3)，ξ*=2βη/(Fr)匹配(C2)，得(T2)。M1作为d=1,Q=q,B=1恢复F=1/q、β=κ_c(k)/q，系数完全一致。

## 10. 固定物理植物上同极点controller例

这个比较不改变B,Q或fault/health输入。取

\[
A_{\rm plant}=\operatorname{diag}(4/5,3/5),\quad B_u=I_2,\quad
B=(1,2)^\top,\quad
Q=\begin{pmatrix}1&1/3\\1/3&5/9\end{pmatrix}.
\]

于是F=29/4。两已知causal反馈：

\[
K_d=\operatorname{diag}(3/10,7/20),\quad
A_{K_d}=\operatorname{diag}(1/2,1/4),
\]

\[
K_n=\begin{pmatrix}3/10&-2\\0&7/20\end{pmatrix},\quad
A_{K_n}=\begin{pmatrix}1/2&2\\0&1/4\end{pmatrix}.
\]

特征值都为1/2、1/4，第二个nonnormal transient更大，但Q、B和完整oracle完全相同。k=1的exact系数

\[
\beta_{K_d}(1)=1343/344,\quad
\beta_{K_n}(1)=18007/10456.
\tag{E1}
\]

因此匹配leading deficit系数之比为
√[(18007/10456)/(1343/344)]，约0.664。矩阵状态耦合改变了missing-span中fault/health/noise的共同传播与保留信息；只看闭环极点或单槽output variance不能给这个比较。本例属于已声明无饱和/actuation预算的fixed linear-gain family；不把它宣称为实际机器人controller最优或无控制代价。

任意声明的finite known-controller family可用β_K比较其fixed-gain leading coefficients，F共同且positive。一般多变量全局K优化、未知K、没有uniform transient界的H-dependent family均未证明。

## 11. Q≻0承重边界反例

若擅自把Q允许退化，β严格正不再成立。Stable shift register

\[
A_K=\begin{pmatrix}0&1\\0&0\end{pmatrix},\quad
B=(0,1)^\top,\quad Q=BB^\top
\]

有x_j=(v_{j-1},v_j)，v_j=a_j+g_jb_j+ξ_j、ξ iid N(0,1)。删去x_{ℓ+1}但保留x_{ℓ+2}完整vector，即恢复两slot inputs；k=1 gap loss为0。W₂=I₂、M₂=(1,1)，若错误使用Q的pseudo-inverse F=1会得到2−M₂ᵀW₂⁻¹M₂=0。此例在main theorem之外，但说明Q≻0不是可默许省略的technical装饰。

## 12. 精确计算与验收范围

work/m2_checks.py/.json使用标准库Fraction，q已吸收进Q，fixed n₀=3。实际exit=0：150个initialized full-state retained subsets直接output covariance逆对input projection；20个complete-record中性；160个β positive/monotonic与affinecrossbounds；68个完整matrix calendars验证single weighted zero、range(P)、dual及oraclepair；413个local repair/support certificates；1个singular-Q boundary。覆盖2D diagonal/nonnormal/rotating和3D Jordan稳定模型，以及zero/linear/alternating gap g。Large H=256,1024 sanity按每model调整r令ξ*=1，只是parameter-normalized实现检查，不用于跨controller性能ranking或数值拟合proof。

矩阵稳定使用各model的显式norm summability certificate，特别nonnormal不假设||A_K||<1。正式入口 outputs/m2_controlled_memory_checks_v1.py / .json。在仓库根目录执行 python outputs/m2_controlled_memory_checks_v1.py，stdout应与保存JSON一致；正式副本与实际PASS的work副本SHA256逐份一致。Source proof和有限checks分开。

重点独立审查：rowspace β strict；full状态Markov→white projection；scalar nuisance单约束；center cross长gap uniform budget；global T误差只付一次；actualjoin singleton；D≥Fn；vector contraction bounds的F因子；统计量Tv真实可用；U11输入center偏移；真实plant同B,Q controller比较。

本稿不自动关闭长期TAC goal。文献承重定理核对、受限控制可实现性、D2-a全表与机械噪声/误差接口、完整论文及实际发布包验收仍需推进。

独立TeX已请求built-in editor打开，compiler返回平台错误 Unable to find standard directories for platform、无source diagnostics。编译状态UNVERIFIED (platform compiler failure)；未安装替代运行时。扫描各outputs TeX无9/10/13外的低控制字节，源码转录检查与数学证明/脚本PASS分别记录。
