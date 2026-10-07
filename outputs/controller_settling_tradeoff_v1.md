# 受限控制、恢复时间与诊断记忆的权衡 v1

2026-10-07。**固定 k 时，κ 在 0≤c<1 上严格递减；同一恢复合同使 k(c) 阶梯式增长，κ(c,k(c)) 在 c→1 时发散。** 给定三个控制器中 c=0.9 最佳，但完整 compact 区间 [0.8,0.95] 的最佳点是 c=0.81。两者分别为有限族结果和经 plateau reduction 证明的全区间结果，不能混称。

本文件以 known constant input 的单内部 gap 信息为无条件结论。带健康漂移的联合设计只在第 8 节列明的 M1 sharp 假设下解释。本例不等于全扰动恢复证书、饱和控制器或完整 6R 最优控制。

## 1. 同一植物、输入、创新与信息权限

已读 `control_memory_example_v1.md`，SHA256 `5eb2f17dcedff0edc3d0c6891f10e3858485f4ff6ff5d25ce2b97c1590bf55b7`；以及新冻结的 `m1_problem_contract_v1.md`，SHA256 `9d01225548c86481b88fb5fe50305a2a9ecf8364ea4a3116137b55c0540389a3`。M1 的植物、外部输入与确定初始化持续演化，不能直接替换为 M0 的 stationary 输出实验。

固定 λ=1，使用因果反馈

\[
x_j=x_{j-1}+u_j+d^h+w_j,
\quad u_j=-Kx_{j-1},\quad c=1-K,
\quad w_j\stackrel{iid}{\sim}N(0,q),\ q>0.
\]

不同控制器使用同一 d^0=0、d^1=d、q、时域 H 和 x0=0，且 0<c<cbar<1。控制器内部仍可取得每拍状态；诊断器只取得 retained states，不取得删去的状态、逐槽控制命令或创新。若允许读取 K≠0 的控制命令，就可能反推旧状态，须重新定义比较实验；本文件没有给某个控制器免费添加这种旁路。

完整记录的共同可逆 innovation map 给 `Gfull=Hd²/(2q)`，与 K 无关。对于一个内部 gap，删去 k 个状态，保留 xℓ、x_(ℓ+k+1)，记 m=k+1、

\[
A_m(c)=\sum_{r=0}^{m-1}c^r,\qquad B_m(c)=\sum_{r=0}^{m-1}c^{2r},
\quad \kappa_c(k)=m-{A_m(c)^2\over B_m(c)}.
\]

真实条件 innovation 的均值为 dA_m、variance 为 qB_m，故精确

\[
Gfull-Gretained={d^2\over2q}\kappa_c(k).
\tag{C1}
\]

所有 c 下的状态均值和 covariance 均经同一个物理 F_c 改变；没有只改变噪声相关而固定输出信号。结果对 gap 位置不敏感，只要两端实际 retained 且给定 H 能容纳该 gap。

## 2. 固定 k 的正稳定记忆单调性

**命题 1。** k≥1 固定，则 c↦κ_c(k) 在 [0,1) 上严格递减，κ_0(k)=k，c→1 时 κ→0。k=0 时恒为0。若把“c≥0”理解成包含 c>1，则全域递减不成立；本命题只针对正稳定区间。

证明。令 R_m=A_m²/B_m。0<c<1 时 geometric sum 给

\[
R_m(c)={1+c\over1-c}{1-c^m\over1+c^m},\qquad
{R_m'(c)\over R_m(c)}={2\over1-c^2}-{2m c^{m-1}\over1-c^{2m}}.
\]

因此 R'_m≥0 等价于

\[
\sum_{r=0}^{m-1}c^{2r}\ge m c^{m-1}.
\tag{C2}
\]

左侧 m 个正数的几何平均是 c^(m−1)，由 AM–GM 得到 C2。m≥2、0<c<1 时这些数不全相等，所以严格不等，R'_m>0，κ'_c(k)<0。c=0 用原有限和连续延拓，保持严格排序；m=1 直接给 κ=0；c→1 时 A_m→m、B_m→m，故 κ→0。证毕。

在 c>0 的有限和中，反转权重可见 `κ_c(k)=κ_(1/c)(k)`。例如 k=1，κ_1=0 而 κ_2=1/5，足以否定对全部 c≥0 的递减说法。c=1 与 c>1 均不在这里的控制器稳定合同内。

## 3. gap 长度单调性与 ceil 跳点

**命题 2。** 对每个 0≤c<1，κ_c(k) 严格随整数 k 增加。精确增量为

\[
\kappa_c(k+1)-\kappa_c(k)
={(B_m-A_m c^m)^2\over B_m(B_m+c^{2m})}>0,
\qquad m=k+1.
\tag{C3}
\]

证明。κ 是 least-squares residual：

\[
\kappa_c(k)=\min_t\sum_{r=0}^{m-1}(1-tc^r)^2.
\]

追加第 m 项并完成平方，即得 C3。对 0<c<1，逐项 `c^(m+r)<c^(2r)`（0≤r<m），所以 A_m c^m<B_m；c=0 时同样给正增量1。证毕。

此结果解释同一 c 在恢复时间增加一槽时出现的向上跳跃；不是把额外时长当成没有信息代价的货币收费。

## 4. 同一个齐次恢复合同

令固定 `a=ε/E∈(0,1)`、E>0、0<ε<E；固定移动槽数 `D=d_move∈Z_(≥0)`。恢复的齐次分量满足 `e_(n+1)=c e_n`，给定 |e0|≤E 时要求

\[
c^sE\le\epsilon,
\quad s(c)=\max\{1,\lceil\log(a)/\log(c)\rceil\},
\quad k(c)=D+s(c).
\tag{C4}
\]

这里 D 是整数槽数；连续移动时间若未给出采样/删槽规则，不能直接称为此模型中的整数 k。协议在 D 个移动槽及 s 个恢复槽中禁止诊断器读取状态，之后读取下一个状态，所以两 retained endpoints 的间隔仍为 k+1。

这是 **homogeneous component qualification**。创新与 d、健康扰动、参考强迫在缺测期间仍持续作用；`c^sE≤ε` 不保证实际 noisy/forced state 回到 ε 管，也不证明 nonlinear source-return。E/ε 在这里是共同的日历可行性驱动，没有被额外叠加成诊断噪声；若把未知 entry error 真正加入数据均值类，必须重新分析实验。M1 的 full-health return 和实际 tracking/actuator 约束仍须另建。

对 a∈(0,1)、0<c<1，最大值中的1实际上不会改变 ceil，因为对数比值正。更稳定的定义是：s 为满足 `c^s≤a<c^(s−1)` 的最小正整数，计算时使用 Fraction 幂比较，避免恰等号处的浮点 log/ceil 错一槽。

设 `c_s=a^(1/s)`。则

\[
s(c)=1\iff 0<c\le c_1=a,
\qquad s(c)=s\iff c_{s-1}<c\le c_s\quad(s\ge2).
\tag{C5}
\]

每个 plateau 的右端属于较短 s：恰好 `c_s^s=a` 时 s(c_s)=s；只有严格 c>c_s 才要 s+1。由命题1，κ(c,k(c)) 在各 plateau 内严格递减；由命题2，穿越右端进入下一 plateau 时有严格向上跳跃。

## 5. c→1：恢复时长增长使亏损发散

**命题 3。** D 固定、a∈(0,1) 固定，令 L=−log a>0、δ=−log c。则

\[
s(c)={L\over\delta}+O(1),\quad m(c)=D+s(c)+1,
\]

\[
\boxed{\delta\,\kappa_c(k(c))\longrightarrow
L-2\tanh(L/2)>0,}
\quad
\kappa_c(k(c))={L-2\tanh(L/2)\over1-c}+O(1).
\tag{C6}
\]

最后式也可先写成同分子除 δ 加 O(1)，再利用 `1/δ=1/(1−c)+O(1)`。ceil 带来的振荡和固定 D 只进入 O(1)，不会消除首项。

证明。`mδ=L+O(δ)`，而

\[
R_m(c)=\coth(\delta/2)\tanh(m\delta/2).
\]

用 `δ coth(δ/2)→2` 和 tanh 的连续性即得极限。正性可直接写为

\[
L-2\tanh(L/2)=\int_0^L\tanh^2(t/2)\,dt>0.
\]

进一步利用 tanh 在 L/2 邻域的有界导数与 `coth(δ/2)=2/δ+O(δ)` 得 O(1) 余项。证毕。

因此固定 k 的 c→1 零 gap loss 不能用于满足同一恢复合同的免费慢控制。严格固定的 uniform-stability family c≤cbar<1 本来不能趋近1；C6 描述放弃这个裕度之后的代价。若 H 固定，k(c) 很快超过可容纳的 gap 长度，协议首先变得不可行；不能把超过 H 的 C1 损失当成固定 H 实验的信息。边界数值序列首项 c=19/20 复用 compact 端点；后续 c>19/20 只演示解析极限，均不属于该 compact 设计族，也不能装入 H=12 的当前 gap 实验。

## 6. compact 区间的有限全局优化

**定理 4（known constant input gap 的全区间设计）。** 固定 a∈(0,1)、D∈Z_(≥0)，控制器区间

\[
\mathcal C=[c_{lo},c_{hi}],\qquad0<c_{lo}\le c_{hi}<1,
\]

且整个区间满足一个固定 uniform stable bound。若给定 H、gap 左端 ℓ，还要求 `ℓ+D+s(c_hi)+1≤H`，保证候选 gap 在所有控制器下可行。定义

\[
\mathcal E=\{c_{hi}\}\cup
\{a^{1/s}:c_{lo}\le a^{1/s}\le c_{hi},\ 1\le s\le s(c_{hi})\}.
\tag{C7}
\]

则 E 是有限集，并且

\[
\min_{c\in\mathcal C}\kappa_c(k(c))
=\min_{c\in\mathcal E}\kappa_c(k(c)).
\tag{C8}
\]

由 C1，这也给同一 H、d、q、known constant input、一个协议 gap 下最大 retained KL 的全区间控制器。

证明。由 C5，C 只穿过至多 s(c_hi) 个 plateau。每个非空 plateau 与 C 的交集均有一个**包含的**最大点，或为某个 c_s，或为 c_hi；左端是否开不影响右端属于本 plateau。若交集只剩一个点，该点仍在 E。命题1保证每个交集内的最小值就在其最大点；取有限个最小值得 C8。这个证明不把已证固定 k 单调性错误用于跨 plateau。证毕。

ceil ties 由 C5 完全规定。若区间上端 **不包含**，例如 `(0,cbar)`，不能直接声称全局 minimum 存在：需要把 cbar 当成不可实现的左极限候选，与所有真正包含的 plateau 右端比较；只有某个可实现点达到最小值时才存在 minimum，否则只有 infimum。例如 cbar≤a 时，只有一个 plateau 且严格递减，infimum 在排除的 cbar 处不达到。

若 H 不够覆盖区间，可行集合为 `s(c)≤H−ℓ−D−1`，亦即再截到一个闭阈值 `c≤a^(1/smax)`；smax≥1 时可以在所得 compact 区间应用 C7–C8，smax<1 则此 gap 协议无可行控制器。不能把不满足 H 的候选仍放入信息比较。

## 7. 精确的中间最佳例子与完整区间比较

取 D=0、a=81/100、E=1、ε=81/100；有限族

`c∈{4/5,9/10,19/20}`，对应 `K∈{1/5,1/10,1/20}`。可取 cbar=24/25，三者共用稳定裕度。对相同 H=12、ℓ=2、d=q=1，所有单 gap 可行。

|c|K|最小 s=k|精确 κ|显示值|
|---|---|---:|---|---:|
|4/5|1/5|1|1/41|0.024390243902439025|
|9/10|1/10|2|2/91|0.02197802197802198|
|19/20|1/20|5|5064645/111045881|0.04560858047494801|

恢复 minimality 使用精确幂：`(4/5)≤81/100`；`(9/10)>81/100` 而 `(9/10)²=81/100`；`(19/20)^4=0.81450625>81/100`，第五次幂小于81/100。故恰等号时中间控制器只付2槽，不能因浮点 ceil 多付1槽。

比较也全为有理数：

\[
\frac1{41}-\frac2{91}=\frac9{3731}>0,
\quad
\frac{5064645}{111045881}-\frac2{91}
=\frac{238790933}{10105175171}>0.
\]

**有限族最佳是 c=9/10**：比更快 c=4/5 多恢复一槽，但记忆收益抵过此代价；更慢 c=19/20 需要5槽，额外缺测主导。此处比较的是同一已声明 homogeneous qualification 与精确单 gap 信息，不是实机 tracking quality。

把可行控制器扩大到完整 [4/5,19/20] 后，C7 的候选如下：

|候选|k|κ 显示值|
|---|---:|---:|
|c1=81/100|1|0.021798200591751707|
|c2=9/10|2|0.02197802197802198|
|c3=(81/100)^(1/3)|3|0.024473329793291584|
|c4=(81/100)^(1/4)|4|0.027559619221950354|
|c_hi=19/20|5|0.04560858047494801|

81/100 的第五根大于19/20，不是区间内候选。两 irrational roots 用100次有理二分隔离：若 l≤c_s≤u，则命题1给 `κ_u(D+s)≤κ_(c_s)(D+s)≤κ_l(D+s)`。文件中的 root-power 包含与 κ 区间由 Fraction 严格核对，不以显示小数排名。

κ(c1)=361/16561；`2/91−361/16561=271/1507051>0`。其他候选的认证下端分别大于 `24473329/10^9`、`27559619/10^9`、`2280429/50000000`，都大于361/16561。因此 **compact 全区间的唯一最佳为 c=81/100、K=19/100、k=1**。这个较强结论不改变三点有限族结果，它说明有限候选枚举不可冒称完整 controller-class 全局优化。

## 8. 与 M1 sharp 的条件连接

M1 合同的候选首项为

\[
D_H^{*,c,k}=C_0\sqrt{\kappa_c(k)}H^{5/2}+o(H^{5/2}),
\quad C_0={\sqrt2\over5q}\sqrt r\,\eta^{3/2},
\]

其中 q、r、η 和原始输入/信息合同在控制器比较中共同。**本文件没有证明该公式。** 若根主证明在每个所比较 fixed c,k、同一 gap-profile/任务日历合同下同时给 converse 与达到，并确立各恢复日历真正可行，则有限族中 √κ 的严格排序给首项设计排序。因为控制器族有限，各自 o(H^(5/2)) 的最大值仍为 o(H^(5/2))，所以严格最小首项的控制器会在某个未量化的足够大 H 后成为该有限族的最佳；这不是给定有限 H 的风险证书。

对整个 compact 连续族，定理4只直接优化 κ 或已声明的候选首项函数。要把连续族首项最优升级为实际 `max_(c,π)G_H` 的渐近控制结论，还要根主证明给出 c/k 日历族上的一致余项、相同 oracle/input budget 和真实可行性。pointwise sharp 不足以交换 `H→∞` 与 `min_c`。增加 measurement noise、未知 c、actuator/tracking 约束、带扰动恢复或免费读取控制命令后，必须重新冻结实验，不能直接沿用这里的全区间结论。

## 9. 计算覆盖与复核

`controller_settling_checks_v1.py` 只用 Python 标准库。`controller_settling_checks_v1.json` 记录精确恢复时长、Fraction κ/严格差、root-power 隔离区间和 compact 最佳证书；3 个物理常输入实例还直接构造确定初始化的 `q F_cF_cᵀ`、对 retained principal covariance 做精确有理逆，验证相同 full KL=6 与 `full−retained=κ/2`。这是与 geometric-gap 公式独立的有限矩阵核对，不是只把公式重复计算一次。

100 个 rational diagnostics 检查了 fixed-k 排序、闭式与有限和一致及 C3 增量；它们支持实现，**不替代命题1–3的全称证明**。near-unit 序列只展示 C6 的尺度，已有 H12 不可行标记；未据数值序列证明极限。所有数据/公式输入固定，原文献与主台账保持不变。

复核入口：`python -S -X utf8 outputs/controller_settling_checks_v1.py`。结果是 `PASS_EXACT_FINITE_CHECKS_AND_CERTIFIED_COMPACT_EXAMPLE`；没有完整 nonlinear/hardware return 或 M1 sharp 验收的含义。
