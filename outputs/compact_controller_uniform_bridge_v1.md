# 正定过程噪声下的紧致控制器族：一致sharp与联合设计桥梁 v1

2026-10-07。根代理完整证明稿，**待独立审查**。本稿补M2 fixed-K与连续设计之间的量词缺口；不覆盖奇异noise rank-changing族，不改D2-a或真实机器人return合同。

## 合同与结论

保留M2共同植物、B≠0、Q≻0、r/eta>0、rho0≥0、fixed n0≥1、full retained states、完整scalar nuisance、noise前确定性日历和双向可重复exact-k moves。允许控制器来自非空紧致集 \(\mathcal K\subset\mathbb R^{p\times d}\)，对每个K，\(A_K=A-B_uK\)严格Schur。原始A、B_u、B、Q、r、eta、prefix和diagnostic权限在族内相同。令缺测最小长度 \(k(K)\in\{1,\ldots,k_{max}\}\)，每个K的两方向exact-k(K) known profile可反复串接、|g|≤1；无需profiles随K连续。

固定K对应同一M2 calendar类 \(\Pi_K\)。完整oracle始终 \(O_H=F\sum a_j^2/2\)，\(F=B^TQ^{-1}B\)。\(D_H^{*,K}=O_H-\sup_{\pi\in\Pi_K}G_H(K,\pi)\)。写

\[
C(K)=\frac{\sqrt2}{5}\sqrt{F\beta_K(k(K))r}\eta^{3/2}.
\]

**定理 U。** 在上述合同内，

\[
\sup_{K\in\mathcal K}\left|\frac{D_H^{*,K}}{H^{5/2}}-C(K)\right|\longrightarrow0.
\tag{U1}
\]

因此同一oracle下的联合最优亏损满足

\[
\frac{O_H-\sup_{K\in\mathcal K,\pi\in\Pi_K}G_H(K,\pi)}{H^{5/2}}
\longrightarrow\inf_{K\in\mathcal K}C(K).
\tag{U2}
\]

若C在族上达到最小值，固定该K并用M2 terminal-balanced构造渐近达到联合首项。不声称有限H最优控制器存在或已求得；k(K)非闭跳变及profile不连续都可影响有限H存在性。

## 1. 一致稳定常数不是仅口头要求

谱半径在有限维矩阵中连续。紧致\(\mathcal K\)且每点严格Schur，给\(a_*:=\max_K\rho(A_K)<1\)。选\(a_*<\tau<1\)。在紧致积集 \(\mathcal K\times\{|z|=\tau\}\)上，每个\(zI-A_K\)可逆，resolvent连续，故

\[
R_*:=\sup_{K,|z|=\tau}\|(zI-A_K)^{-1}\|<\infty.
\]

由matrix Cauchy积分（闭曲线包住全部spectrum），对j≥0，

\[
A_K^j=\frac1{2\pi i}\oint_{|z|=\tau}z^j(zI-A_K)^{-1}\,dz,
\quad \|A_K^j\|\le R_*\tau^{j+1}.
\]

于是 \(S_*:=\sup_K\sum_{j\ge0}\|A_K^jB\|\le R_*\tau\|B\|/(1-\tau)<\infty\)。这是同一紧致族的真实uniform transient控制；并非只对H-dependent任意bounded poles作推断。Q固定正定，\(W_{m,K}\succeq Q\)，故所有m/K有\(\|W_{m,K}^{-1}\|\le\|Q^{-1}\|\)。

令\(C_*:=\|Q^{-1}\|S_*^2\)。原M2所有affine gap cross可统一用\(C_*\)，总负费用\(E_H\le C_*\eta(\rho_0+\eta H)H=O(H^2)\)。

## 2. 正beta和dead-slot下界一致

每个固定整数ℓ≥1的\(\beta_K(\ell)=(\ell+1)F-M^TW^{-1}M\)在K上连续。M2正性证明用Q可逆与单位eigenvalue矛盾，因此每个K均有beta>0。有限\(1\le\ell\le k_{max}\)与紧致性给

\[
0<\beta_*:=\min_{K,1\le\ell\le k_{max}}\beta_K(\ell),
\quad \beta^*:=\max_{K,1\le\ell\le k_{max}}\beta_K(\ell)<\infty.
\]

可保守取beta*上界\((k_{max}+1)F\)。Tail统一为\(\beta_K(\ell)\ge(\ell+1)F-C_*\)。令整数\(L_*=\max\{k_{max},\lceil2C_*/F\rceil,1\}\)，则ℓ≥L*时beta/ℓ≥F/2，1≤ℓ≤L*时monotonic给beta≥beta_K(1)≥beta_*。故

\[
b_*:=\min\{F/2,\beta_*/L_*\}>0,
\quad \beta_K(\ell)/\ell\ge b_*\quad(\ell\ge1).
\]

比M2各自\(b_K\)更保守，但足以给calendar/controller双重一致的converse。

## 3. Converse余项和两重极限一致

按M2已审证明固定epsilon,theta∈(0,1)，macro长度L=floor(H^(3/4))。所有K/日历采用同一个完整input signed-tent结构。F、r、eta不变；gap count费用用各自beta_K(k(K))，dead-slot用公共b_*，affine总误差用C_*。

Absorption条件可统一为\(A\ge32F\beta^*r/(\theta^2 b_*^2)\)，late A≥eta epsilon H+O(1)最终对所有K成立。其余macro误差O(H^(9/4))与O(H²)的常数只依公共参数、epsilon/theta、beta^*/b_*/C_*；无K或calendar依赖。

故有一个\(R_{\epsilon,\theta}(H)=o(H^{5/2})\)，使同时对每个K成立

\[
\frac{D_H^{*,K}}{H^{5/2}}
\ge\sqrt{1-\theta}(1-\epsilon^{5/2})C(K)
-\frac{R_{\epsilon,\theta}(H)}{H^{5/2}}.
\tag{U3}
\]

先选epsilon/theta使\([1-\sqrt{1-\theta}(1-\epsilon^{5/2})]\sup_K C(K)\)任意小，再取足够大H使公共R/H^2.5小。得到
\(\sup_K[C(K)-D_H^{*,K}/H^{5/2}]_+\to0\)。没有在K依赖的H阈值之间偷换极限。

## 4. Attainment及其余项一致

取每个K的\(\xi_K=2\beta_K(k(K))\eta/(Fr)\)。由第2节，

\[
0<\xi_*^{lo}=2\beta_*\eta/(Fr)\le\xi_K
\le2\beta^*\eta/(Fr)=\xi_*^{hi}<\infty.
\]

k仅取有限集合，xi在一个固定正紧致区间。Terminal packing n_l=xi*l+O(1)和M=sqrt(H/xi)+O(1)的取整、padding/tail界因此一致。已知moving g在[-1,1]内使每block方向修补常数\(C_k=2(k+2)\)≤2(k_max+2)；singleton denominator≥Fn，repair/support bounds不含其它K常数。

Auxiliary inactive条件A≥r(k+n−1)/2最终在统一有限l₀之后成立：A=eta xi l²+O(l+1)、n=xi l+O(1)，xi下界正、k有限。这个l₀内的时间与amplitude有统一上界，不随H/K增长。Fixed-span affine coefficients有统一界：\(|L_1|\le(k_max+1)C_*/2\)，\(L_2\le F\sum_{j=1}^{k_max+1}(j-(k_max+2)/2)^2\)可用更保守\(F(k_max+1)^3\)。

因此原M2达到证明的power sums、aux energy、repair、support及affine pair误差均存在公共\(C_U<\infty\)，使所有K同时有

\[
D_H^{*,K}\le D_H(K,\pi_H^{\xi_K})
\le C(K)H^{5/2}+C_UH^2.
\tag{U4}
\]

U3/U4给U1。对统一误差取inf_K不改变误差界，U2成立；sup/infs无需先证明有限H达到。

## 5. 齐次settling例的实际渐近联合结论

取M1同植物、q/r/eta、full-state和noise条件，\(c\in[4/5,19/20]\)，同一\(\gamma=81/100\)、\(d_{move}=0\)。最小整数恢复s满足c^s≤gamma，因此k(c)∈{1,…,5}。每个c的两方向exact-k(c)已知profile及重复转换作为此解析协议的假设；没有额外扰动回管或actuator预算。

已证明的plateau方法和精确root isolation给\(\min_c\kappa_c(k(c))=361/16561\)，唯一达到点\(c_*=81/100\)。定理U于是给

\[
\inf_{c,\pi}D_H(c,\pi)
=\frac{\sqrt2}{5q}\sqrt{\frac{361}{16561}r}\eta^{3/2}H^{5/2}
+o(H^{5/2}).
\tag{U5}
\]

固定c*的terminal-balanced日历达到**同一齐次qualification解析实验**上的联合首项。这里把原“连续首项函数最佳”补成了真正联合渐近信息最佳，而没有变成finite-H统计最优。

此外C(c)在每个plateau连续，右侧跨阈值跳到更大的kappa，阈值本身取较短k；所以C在紧致区间上lower-semicontinuous。对于任意epsilon>0，排除c*的epsilon邻域后仍为紧致，C有严格更大的最小值。由U1，任意满足\(D_H^{*,c_H}\le\inf_cD_H^{*,c}+o(H^{5/2})\)的控制器序列都趋c*。不需有限H exact optimizer存在，不给未计算的收敛速度。

## 审查入口与限制

依赖 `m2_controlled_memory_theorem_v1.md` 和其独立报告；plateau/361/16561依赖 `controller_settling_tradeoff_v1.md` 及精确JSON。本文未重复运行这些旧checks，补的是全称量词/一致余项证明，不用网格数值假装uniform theorem。

应重点反驳：紧致严格Schur是否真的给uniform resolvent、positive beta inf、xi/inactive cutoff是否一致、k跳变的inf及lsc、真实双向profiles/return的合同。Q或B若变、noise rank变化、controller集非紧致、H-dependent放松稳定域、测量noise或实际forced return都不自动适用。若固定族中Q/B变化，可以另给uniform正定/F bounds，但本稿没有证明或授权该扩展。
