# 有界任务偶偏差扰动界独立审查 v1

2026-10-07。**判断：在同一共同输入Gaussian模型、相同B/噪声/投影、固定E及同一calendar集合的Minkowski包络合同内，B1的calendar-uniform信息差界和B2的最优亏损界成立，inf/sup方向及两侧预算正确。** 它保存已证明的H^(5/2)首项，但不是finite-H O(1)平移，也不是参数改变covariance的定理。

## 来源与覆盖

完整读取 `outputs/bounded_even_bias_corollary_v1.md`，SHA256 `7483128fec16576869fe0f94fdc22f8e9e8d824bd3dc97e8e47f8bf06ae9c24b`；核对M1/M2的共同input、deterministic初始化、真实P及同oracle条件。M2合同sha `794c245d0fdb672021cb36566382d68834b2abe20331dde0bc01a0bc71671eae`，M2证明sha `38d2aecf2d00a6a781f0a99f6448d93a4d2fcccd1e895526ca3c5fed2c3455b1`。没有读取/接受另一代理正在写的M2S主定理、common-support扩展或β=0两种regime结论。

本审查是距离与优化量词的数学审查，不需重跑M1/M2正式checks；没有修改原推论、合同或台账。

## 1. 类包含、同B及共同covariance：正确

每侧附加输入为同一B e_j^h，|e_j^h|≤E/2，差分幅值≤E；因此白化后仍沿同一f。E是固定的额外scalar幅值预算，不是把B改成未知量，也不是加入任意vector偏差。两侧各付E/2，差分类只用E，不应再无故乘2。

推论明确使用完整input差分包络 `g·Z+E_H`，其中0∈E_H、每e满足|e_j|≤E。所有nodes，包括missing及prefix，使用同一个P。若e与b被强制相关，实际差分类可能只是这个Minkowski类的子集；推论针对已声明包络，不自动表示独立变量就是实际physical model。对较窄实际类，只能依据真实包含关系解释其界，不能自动宣称信息单调下降。

B、噪声Q（或输入noise factor G）、calendar、feedback和Gaussian comparator相同；健康路径确定且与创新独立。所以增加e只增加均值类，不改变covariance或P。若e是mass/plant/sensor multiplicative parameter并改变噪声/动态支持，此条件失效，B1/B2不能调用。

## 2. Projection contraction与距离两边：正确

固定π，令t=P(fa)，K={P(fgz):z∈Z}，L={P(fe):e∈E_H}，N=H+n0。原Z含0，故0∈K；附加类含0，故0∈L，K⊆K+L。P是同一真实白色input空间的orthogonal projector，||P||≤1。因此

\[
\sup_{l\in L}\|l\|\le E\sqrt{FN}=R_H,
\quad d=dist(t,K)\le\|t\|\le\sqrt F A_H.
\]

第一个√F来自同B的白化向量f，第二个√F来自fault目标；乘积为F，不是F²或遗漏F。对于每个k∈K、l∈L，

`||t−k−l||≥||t−k||−R_H`。

对k/l取inf，再结合距离非负，给 `d_mix≥(d−R_H)_+`；而类包含给d_mix≤d。两边方向正确，不要求最近对在这一扰动步骤达到。对均值Gaussian信息G=d²/2，分别处理d≥R_H和d<R_H，得到

\[
0\le G_{odd}(\pi)-G_{mix}(\pi)
\le dR_H\le F E\sqrt N A_H.
\]

d=0、E=0等退化情况同样成立，未把负的d−R_H直接平方。式中Π变化只改变P，而其contraction常数始终1，所以这个上界对全部calendar一致；没有每块重新选独立nuisance或忽略gap健康输入。

## 3. 最优information的sup与同oracle差：正确

设C_H=FE√N A_H，对每个π有

`Godd(π)−C_H≤Gmix(π)≤Godd(π)`。

对**相同calendar集合**取sup：

\[
\sup G_{odd}-C_H\le\sup G_{mix}\le\sup G_{odd}.
\]

使用相同完整oracle O，

\[
D_{mix}^*-D_{odd}^*
=\sup G_{odd}-\sup G_{mix}\in[0,C_H].
\]

这不要求两类有同一个最优calendar，也不要求sup被达到。不能在新增模型改变实际可行calendar集合或控制输入预算后沿用此sup比较；当前纯additive同B解析合同保持它们相同。

## 4. 渐近阶数与已有主定理的连接：正确但有条件

fixedn0、fixedE/F、ρ0/η固定的ramp满足A_H=O(H^(3/2))、√N=O(H^(1/2))，所以C_H=O(H²)=o(H^(5/2))。因此：

- 若原亏损为已验收的 `C0 H^(5/2)+o(H^(5/2))`，新增包络类保留同一C0。
- 若原亏损只是o(H^(5/2))，新增仍为o(H^(5/2))，不能自动给出更精确阶数。
- 若另一个独立结果已证明原亏损Θ(H²)，类包含给同阶下界、C_H给同阶上界，新增也Θ(H²)，但H²首项常数可能改变。

最后一条只是逻辑条件推论，不表示本报告已证明或接受M2S的β=0 baseline regimes。E若增长、n0不再固定、B/Q改变或hypothesis covariance不同，应重新比较C_H与主项，不能隐藏这些量词。

## 5. 可接受范围及应明确的表述

1. 对M1/M2的共同SPD Gaussian input和已证明P表示，推论可以直接接受。对thin G、PSD Q等情形，纯距离lemma仍只要求一个真实共同-support的P/信息表示；该表示及原sharp/β=0结果须由相应扩展独立验收。本报告不借另稿升级M2 theorem。
2. Minkowski包络是一种明确均值不确定性类；强制相关的e/b、未知plant或非线性参数不得未经包含证明改称该包络。原D2-a没有因此增加真实偶偏差参数或改noise。
3. 这是至多O(H²)的信息扰动界，不是每个calendar信息只改O(1)或逐点精确常值平移。保持H^(5/2)首项不等于保持H²常数或finite-H功效。
4. 原文“无界偶输入可模仿故障”宜精确为：若扩大的偶差分类包含故障模板a，取z=0、e=a即可使信息为0。仅去掉幅值盒、但仍有其他rate/shape约束，并不能凭“幅值无界”单独推出a属于该类。

上述补明不改变B1/B2的证明。**可接受当前同B、fixed bounded-E、unchanged covariance的完整input Minkowski包络推论；不接受任何未声明的multiplicative parameter或其他噪声/信息权限扩展。**
