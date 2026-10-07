# M2S 合同 v1：共同噪声输入像、低秩创新与完整状态

冻结日期 2026-10-07。独立于已冻结M2 v1，不覆盖Q≻0合同/证明。本版只推广process noise秩，仍只用一条scalar healthy path和retained full states。

## 1. 同一植物与共同输入像

\[
x_j=A_K x_{j-1}+B(\mathbf1_{h=1}a_j+g_j b_j^h)+G\xi_j,
\qquad A_K=A-B_uK,\quad \xi_j\overset{iid}{\sim}N(0,I_p).
\]

固定维数d，G∈R^{d×p} full column rank，1≤p≤d，B∈range(G)且B≠0，A_K固定已知严格离散稳定。两侧健康参数选择不影响G、K或innovation law。Full state初始x_{−n₀}=0已知，n₀≥1固定，所有state/noise/health持续演化，不reset。

因G fullcol，f=G†B是唯一preimage，B=Gf，F=||f||²>0。Fault、health和noise同时经F_{A_K}传播；不存在一个只变noise、固定output mean的比较。Q=GGᵀ可奇异，但mean输入严格在相同noise image。B不在range(G)、unknown G/rank/K、measurement noise、arbitrary vector nuisance均不属于本版。

## 2. 原scalar path/time/task合同保持

Prefix j=−n₀+1,…,0全部读full state，g=+1、a=0。Post-onset H已知，a_j=ρ₀+ηj，ρ₀≥0、η>0。两侧各自完整scalar b^h rate≤r/2、幅值无界、free initiallevel；差分z=b^0−b^1满足|\Delta z_j|≤r，r>0，两侧由z/2、−z/2实现。

Holding g=±1，每槽读full state。每次change至少k≥1槽missing；其中g预先已知、|g|≤1，fault/healthy/noise输入继续作用。允许长moves/consecutive/emptyroundtrips，fixedk移动有known允许profile。Diagnostic不读取fast internal states/control commands，controller反馈可以内部使用state。H、calendar和g先选，nature据此选full paths，再产生innovations。无terminal task obligation，无后续read的terminalmoves可被hold支配。

本版仍无actuator saturation、state/track budgets或实机动作。Controller gainnorm约束不是actuator command hard bound；如以后加入后者必须重新验证可实现性。

## 3. 共同Gaussian支持不能省略

观测states由共同linear map L_R=R F_{A_K}diag(G)作用于latent white input ξ及mean θ=(f(a+gb))得到。每个healthy/fault mean都位于range(L_R)，所以每个parameter下Gaussian support相同；确定性state关系不携带被伪逆遗漏的额外hypothesis信息。

Retained predictor的invertible triangular变换把L_R变成disjoint interval maps
H_m=[A_K^{m−1}G,…,G]。每interval covarianceW_m=H_mH_mᵀ可奇异，mean在其reached subspace。只在该subspace使用Gaussian likelihood；不能把W_m†当成对支持不同Gaussian laws通用的KL公式。

Span projection

\[
P_m=H_m^\top W_m^\dagger H_m
\]

是latent input空间orthoproject。Global P按真实input intervals组成，observedstate联合cross-block covariance仍保留。Rank-adapted白化可以用range(W_m)的orthonormal basisU_m，row map为
(U_mᵀW_mU_m)^{-1/2}U_mᵀH_m，row covarianceI。不能宣称W_m^{†/2}H_m的d个冗余rows都有I_d covariance。

## 4. Oracle、信息与目标

完整states可由G†(x_j−A_Kx_{j−1})恢复所有latent input innovations；full experiment对knownK中性，

\[
O_H=\frac F2\sum_{j=1}^H a_j^2,\qquad
G_H(\pi)=\frac12\inf_{z:\ |\Delta z|\le r}
\|P_\pi(a_f-H_gz)\|^2,
\]

其中a_f=(f a_j)_j、H_gz=(f g_j z_j)_j。定义D_H^*=O_H−sup_πG_H(π)；不依赖日历最大值是否达成。

令m=k+1，

\[
M_m=\sum_{\ell=0}^{m-1}A_K^\ell B,\quad
W_m=\sum_{\ell=0}^{m-1}A_K^\ell GG^\top(A_K^\ell)^\top,\quad
\beta_K(k)=mF-M_m^\top W_m^\dagger M_m\ge0.
\]

候选characterization：

- 若β_K(k)>0，D_H^*=(√2/5)√(Fβ_K(k)r)η^{3/2}H^{5/2}+o(H^{5/2})，ξ*=2β_K(k)η/(Fr)。
- 若β_K(k)=0，只尝试证明D_H^*=o(H^{5/2})。不把ξ*=0代入packing，不预设更低阶指数或其sharp系数。
- β=0对应constant scalar mean mode在compressed interval中可恢复，不等于所有latent inputs都可恢复。
- 稳定有限阶noise reachability可能给有限零罚gap长度；需严格验证，不把高阶state或任意vector uncertainty自动加入。

## 5. Uniformity与控制比较

Noise-reached subspaces可能随K变化，W_m†的范数不能用GGᵀ的伪逆作全m Loewner upper bound。需要先证明每个fixed(A_K,G)在有限阶reachability稳定后的sup_m||W_m†||有限；controller族下uniform reachability/coercivity另证。

真实controller比较保持A,B_u,G,B,a,health类、time和readout合同相同。只比较先取H→∞的fixed-gain leading penalty，不声称finite-H controller最优、未读hardware数据可用性或硬限幅可实现。

