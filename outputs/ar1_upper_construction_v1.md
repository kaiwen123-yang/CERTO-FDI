# M0 AR(1) 的匹配达到构造：完整 precision 对偶与终点保留

2026-10-07 / v1。状态：本代理完整证明稿，待独立审查。合同严格采用 `outputs/problem_contract_v1.md` 的 M0：原 raw 观测、共同平稳 AR(1)、固定 n₀≥1、B=∞、固定 |ρ|<1、σ>0、k≥1、ρ₀≥0、η,r>0。不把每个人工块初始化为独立 stationary noise；不要求局部 primal 健康路径能跨块拼接。

## 1. 主结论及相对于逆界的状态

令

\[
\nu=\frac{1-\rho}{\sigma^2(1+\rho)},\quad
\beta=\beta_k=(k+1)\nu-\frac{1-\rho^{k+1}}{\sigma^2(1+\rho^{k+1})}>0.
\]

对每个固定 ξ>0，下面的 deterministic terminal-balanced calendar 满足

\[
D_H^\infty(\pi_H^\xi)
\le \frac1{10}\left(\frac{2\beta\eta^2}{\sqrt\xi}+\nu r\eta\sqrt\xi\right)H^{5/2}
+O(H^2).
\tag{U1}
\]

优化 ξ 后

\[
\xi_* = \frac{2\beta\eta}{\nu r},\qquad
\limsup_{H\to\infty}\frac{D_H^{\infty,*}}{H^{5/2}}
\le\frac{\sqrt2}{5}\sqrt{\nu\beta r}\,\eta^{3/2}.
\tag{U2}
\]

若这份 upper 通过独立审查，它与已审接受的 `colored_ar1_converse_v1.md` v1.1（SHA256 `7e81111f4fbfd568c7ab071dc7c838189ef0380c245e2de2580a34f6bb55f1f6`）共同给 M0 固定参数类的**首项 sharp** 信息亏损。当前文件不单方面把整条主定理升级为已验收；它不证明 M1 物理实现、新颖性或 TAC 投稿就绪。

## 2. 全史对偶及确切 signed 零矩

固定完整 calendar 的保留集合 R，C=C_R，P=C⁻¹，S=diag(s_i)。节点差分健康类 K=K_π(∞,r)，保留索引 t₁<⋯<t_N。其自由初始水平导致 support 有限当且仅当 ∑λ_i=0；在这个条件下

\[
h_K(\lambda)=r\sum_{i=1}^{N-1}(t_{i+1}-t_i)|Q_i|,
\qquad Q_i=\sum_{j\le i}\lambda_j.
\tag{U3}
\]

**证明。** ∑λ≠0 时以任意常数健康路径使 λᵀz→+∞。若 ∑λ=0，summation by parts 给 λᵀz=−∑Q_iΔz_i；每个 node increment 的绝对值≤rΔt_i，且这些增量可同时自由选取并线性插值，得 (U3)。这依赖 B=∞，没有暗中固定健康起点。

对任意 raw 统计方向 v，Gaussian quadratic 的 Fenchel inequality 给

\[
G_H^\infty(\pi)\ge v^\top a_R-\tfrac12v^\top C v-h_K(Sv).
\tag{U4}
\]

因为对每个同一完整路径 z，有 ½(a−Sz)ᵀP(a−Sz)≥vᵀ(a−Sz)−½vᵀCv，然后取 inf。以下令 **v=Pu**，其中 u 是一个全局 raw 辅助向量，不是健康路径。因 PC=CP=I，variance 精确为 vᵀCv=uᵀPu，包含全部跨块 covariance。

设 e=a_R−u，O_obs=½a_RᵀPa_R。由展开平方，(U4) 等价于

\[
D_H^\infty(\pi)
\le O_H-O_H^{obs}(\pi)+\tfrac12 e^\top P e+h_K(SPu).
\tag{U5}
\]

这条恒等变形不把已知均值 oracle 与 composite risk 混同；G 使用原合同的同一完整 nuisance class。

## 3. 日历：保留全局首末零辅助值

保留原固定 prefix，全部任务 +。对 planned H，先以预算 H−1 选择能放下的最多 symmetric blocks。第 ℓ 个 base hold 参数

\[
\bar n_\ell=2\left\lceil\frac{\xi\ell}{2}\right\rceil,
\quad L_\ell=2(n_\ell+k).
\]

每块 n=2m 的物理顺序为：m 个 +读数，k 槽 missing，n 个 −读数，k 槽 missing，m 个 +读数。局部 admitted times 为

\[
\{1,\ldots,m\}\cup\{m+k+1,\ldots,3m+k\}\cup\{3m+2k+1,\ldots,2(n+k)\}.
\]

在 H−1 预算中，把剩余 multiples of four 尽量均摊：若 Q=floor((H−1−∑2(\bar n_l+k))/4)，把 Q 个单位分给 M 个 blocks，每个单位令该 block 的 n 增加2，先分商再按预先固定的左至右顺序分余数。其余 **1–4 个 final +读数** 保留并给辅助向量 u=0。若一块都不能放下，则 stay；不影响渐近。

这是原 iid terminal-balanced packing 的一个 fixed one-slot modification。M=√(H/ξ)+O(1)，每块新增 n 为 O(1)，

\[
n_\ell=\xi\ell+O(1),\quad
a_\ell=\rho_0+\eta(x_\ell+c_\ell)=\eta\xi\ell^2+O(\ell+1),
\quad c_\ell=(L_\ell+1)/2.
\tag{U6}
\]

其中 x_ℓ 为 block 开始前的 post-onset 槽数。所有 constants 仅依固定参数，且 O(1) padding 一致于 block index。证明：base cumulative duration ξM²+O(M)，next block length O(M)，remaining multiples of four 数量 O(M)，均摊的每块增量 O(1)。固定保留一个末读数把 global endpoint 辅助值设零，只占 O(H²) 信息预算，不会留下 O(√H) 未完成长尾窗。

## 4. 每块辅助向量和早期条件

在 n=2m、center amplitude a=a_ℓ 的块，令 c₀=(k+1)/2。定义局部 **iid primal 型节点** z^loc（只用来生成 dual，不要求全局可拼接）：

\[
z_i^{+,L}=r(c_0+m-i),\quad 1\le i\le m,
\]
\[
z_i^-= -r[c_0+\min(i-1,n-i)],\quad1\le i\le n,
\]
\[
z_i^{+,R}=r(c_0+i-1),\quad1\le i\le m.
\]

若 a≥r(k+n−1)/2，称 block active 并令 raw u_i=a−s_i z_i^loc。否则该块所有 u_i=0。prefix 与 final 1–4 读数 u=0。由于 a_l~ℓ²、threshold~ℓ，只可能有固定有限个 early inactive blocks，其时间、幅值和总能量 uniformly O(1)。

对 active block：

- 每个真实 gap 的两个 raw 辅助端点相等，均为 W=a−rc₀。
- 0≤u_i≤a。
- ∑block s_i u_i=0：正负读数各 n 个，而且 ∑block z_i^loc=0。
- λ_i^0=s_i u_i=a s_i−z_i^loc 的 local support 为

\[
h_\ell^0=\frac{a r}{2}n(n+2k)
-4r^2\sum_{j=0}^{n/2-1}(c_0+j)^2.
\tag{U7}
\]

**(U7) 的完整证明。** 对 λ⁰ 的 partial sums Q_i，left +部分非负累增；负窗前半部分累减至0；负窗后半变非正；right +部分回升至0。因为 a≥最大|z^loc|，各 + residual≥0、各 − residual≤0，因而这些 sign 关系有效。每个 Q_i≠0 处，Δz^loc_i=−rΔt_i sign(Q_i)；中心 flat edge 的 Q_i=0；两个 gap edge Δt=k+1且Δz=±r(k+1)。用 (U3)，h_local(λ⁰)=(λ⁰)ᵀz^loc=a∑s_i z_i^loc−∑(z_i^loc)²。层值各出现四次，∑s z=r n(n+2k)/2，∑z²=4r²∑(c₀+j)²，得到 (U7)。局部目标只是 constant a；actual affine target 的差异由 (U5) 的 e 能量完整保留。

## 5. 全局 P 的边界修正：signed 总和恰为零

采用已证的 retained-block precision 分解（`ar1_information_lemmas_v1.md` 引理D）。令

\[
d_\rho=\frac{\rho}{\sigma^2(1-\rho^2)},\quad
c_\rho=\frac{\rho}{\sigma^2(1+\rho)},\quad m=k+1,
\]

\[
B_m(u,v)=A_m(u^2+v^2)-2\gamma_muv,
\quad A_m=\frac1{\sigma^2(1-\rho^{2m})}-\frac1{\sigma^2(1+\rho)},
\quad\gamma_m=\frac{\rho^m}{\sigma^2(1-\rho^{2m})}.
\]

对每个 consecutive retained edge，precision 有 d_ρ(e_i−e_j)(e_i−e_j)ᵀ；每个 gap 有 [[A_m,−γ_m],[−γ_m,A_m]]；整体还有 νI 与**仅全局首末** c_ρ diagonal corrections。人工 symmetric block 的 boundary 没有任何额外 stationary initialization。

定义 \(w_m=(1-\rho^m)/(1+\rho^m)\)，以及

\[
\delta_m=A_m-\gamma_m
=\frac1{\sigma^2(1+\rho^m)}-\frac1{\sigma^2(1+\rho)}
=\tfrac12\left(\frac{w_m}{\sigma^2}-\nu\right).
\tag{U8}
\]

在本 calendar，所有 consecutive retained edges 的 s 相同；每个真实 gap 的 s_left=−s_right 且 u_left=u_right=W（inactive块时W=0）。全局首末 u=0，所以 c_ρ corrections消失。于是 **exact vector identity**

\[
SPu=\nu Su
+\sum_{\substack{(i,j)\text{ consecutive}\Delta t=1}}
s_i d_\rho(u_i-u_j)(e_i-e_j)
+\sum_{gaps}\delta_mW s_{left}(e_{left}-e_{right}).
\tag{U9}
\]

每个校正项的 signed 总和为0，Su 在每个块总和为0，prefix/tail为0，故 **∑SPu=0 精确成立**，不只是 small-error。ρ<0 时 d_ρ或δ_m可负，identity与总和仍不变；support估计取绝对值。

注意 v=Pu 可在 prefix、人工 block boundary 和尾读数产生 nonzero 统计权重；不把这些实际读数删掉。u=0 只表示辅助向量设零，并不声称 v 也为零。

## 6. 全史 support 上界及跨块余项

Sublinearity、(U3)、全史 K 的 block restriction、以及每个zero-mass pair的support=rΔt|coefficient|，给

\[
h_K(SPu)\le\nu\sum_{\ell\ active}h_\ell^0
+r|d_\rho|V_H
+r(k+1)|\delta_m|\sum_{gaps}|W|,
\tag{U10}
\]

其中 V_H=∑_{consecutive retained edges}|u_i−u_j|，含 prefix join、人工 block joins 和 final zero join。

Within active blocks每个同任务 adjacent增量≤r，故内部variation≤2r∑n_l。跨block/全局首尾joins用0≤u≤a_l得 boundary variation≤2∑a_l（inactive blocks的u=0不增加这个界）。所以

\[
V_H\le2r\sum n_\ell+2\sum a_\ell=O(H^{3/2}),\quad
\sum_{gaps}|W|\le2\sum a_\ell=O(H^{3/2}).
\tag{U11}
\]

因此 covariance-induced校正support是 O(H^{3/2})。这里所有λ都作用于同一全史类；没有把每块独立 nuisance support当作 equality，只用正确方向的 restriction upper bound。

由 (U7) 丢掉负平方项，

\[
\nu\sum h_\ell^0\le\frac{\nu r}{2}\sum a_\ell n_\ell^2
+\nu r k\sum a_\ell n_\ell
=\frac{\nu r}{2}\sum a_\ell n_\ell^2+O(H^2).
\tag{U12}
\]

有限个 inactive blocks只改变 O(1)。校正的 gap pair虽幅值 O(a_l)，其跨度固定 k+1，累计只 O(H^{3/2})；不是遗漏 O(a_l²) gap费用。

## 7. 实际 affine e 能量与完整 oracle gap费用

对 active block，actual a_i=a_l+η(t_i−c_l)，故

\[
e_i=a_i-u_i=\eta(t_i-c_\ell)+s_i z_i^{loc},\quad
|e_i|\le(\eta+r)(n_\ell+k).
\]

完整 stationary AR(1)及任意 principal retained covariance满足 ‖P_R‖≤C_ρ=(1+|ρ|)/[σ²(1−|ρ|)]。因此

\[
e_R^\top P_R e_R\le C_\rho\sum_{i\in R}e_i^2
\le C_\rho\left[2(\eta+r)^2\sum n_\ell(n_\ell+k)^2
+4(\rho_0+\eta H)^2+O(1)\right]=O(H^2).
\tag{U13}
\]

Prefix actual target与u都为0；tail至多4槽；inactive early blocks整体O(1)。这个范数界保留了所有 gap端点和跨块 covariance，没有用“局部独立variance”。

每块两个真实 gap中心离block center ±(n_l+k)/2。借已证的 affine reflection gap identity，令 E_k≥0为固定局部斜率系数，则**精确**

\[
O_H-O_H^{obs}(\pi_H^\xi)
=\sum_\ell\left[\beta a_\ell^2
+\frac{\beta\eta^2}{4}(n_\ell+k)^2+\eta^2E_k\right]
=\beta\sum_\ell a_\ell^2+O(H^{3/2}).
\tag{U14}
\]

所有 gaps处于post-onset affine区间；首个prefix/首block间无missing，最后是读数，不存在未声明initial/terminal loss。

## 8. 汇总、首项与优化

(U5)、(U10)–(U14) 得

\[
D_H^\infty(\pi_H^\xi)
\le\beta\sum_\ell a_\ell^2
+\frac{\nu r}{2}\sum_\ell a_\ell n_\ell^2+O(H^2).
\tag{U15}
\]

利用 (U6) 和∑_{l≤M}l⁴=M⁵/5+O(M⁴)：

\[
\sum a_\ell^2=\frac{\eta^2}{5\sqrt\xi}H^{5/2}+O(H^2),\quad
\sum a_\ell n_\ell^2=\frac{\eta\sqrt\xi}{5}H^{5/2}+O(H^2).
\tag{U16}
\]

得到 U1。ξ*=2βη/(νr)为两个正项的 AM–GM 等号位置，最小系数为 (√2/5)√(νβr)η^{3/2}，给 U2。ρ=0时 ν=σ⁻²、β=kσ⁻²，恢复iid系数；ρ<0没有额外假设。

证明义务核对：同一calendar、同一完整nuisance class；全局signed零矩exact；只用一次全局P_R；所有跨人工block covariance进入vᵀCv；gap endpoint correction显式；fixed prefix保留；末尾1–4读数实际保留；affine差异O(H²)；fixedparameter误差o(H^{5/2})。没有声称 H² 次阶sharp。

## 9. 小型精确检查与正式复现

正式复现入口 `outputs/ar1_upper_checks_v1.py` / `.json` 只用标准库 Fraction 和整数 isqrt。仓库根目录执行 `python outputs/ar1_upper_checks_v1.py`，stdout应与保存JSON一致。39个full calendars验证 exact signed zero、precision pair identity、全史support upper、dual deficit identity、affine oracle gap identity；其中30个直接逐元素计算完整 C_R v=u、vᵀC_Rv=uᵀP_Ru，跨块covariance未删除。410个 active localblocks核对 (U7) support/KKT pairing。计算用σ=1、n₀=3，ρ取 −4/5、−1/2、0、1/2、4/5，k=1,2,3，小H=32,64；另H=256,1024,4096的大calendar exact检查覆盖negative/zero/positiveρ。实际 exit=0；一般σ、任意固定n₀≥1由正文证明覆盖。

较大calendar的normalized upper与candidate数值只是实现sanity check，不用于拟合或证明极限。全称与余项由上述证明承担；没有执行历史MC、机械D2-a或硬件。

## 10. 待审项

独立审查重点：(U9) precision分解和signed零矩；(U10)全史support restriction的方向；globalendpoint u=0但v可非零的区别；earlyinactive只有限；terminalpacking的uniform O(1)；(U13)原target prefix/tail；以及每个U式的½因子。审查前保持“匹配upper证明稿”。下一步可与已审converse集成，但TAC主目标还需控制系统桥梁、文献全文对照、有限实例与整稿验收。

配套独立TeX已请求built-in editor打开，但compiler返回平台错误 `Unable to find standard directories for platform`，无源码诊断。编译状态为 **UNVERIFIED (platform compiler failure)**；未安装替代运行时。正式脚本实际执行成功，数学状态与编译状态分别记录。
