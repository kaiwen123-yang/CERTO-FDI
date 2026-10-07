# M1 scalar controlled-memory 主定理独立审查 v1

日期：2026-10-07。**数学判断：在冻结的完整输入健康类、确定性已知终点、固定 c∈(−1,1) 及双向 k 槽转换可行的标量协议内，converse 与 upper construction 的首项及常数匹配，未发现改变 T2 的承重漏洞；可接受其固定参数首项 sharp 结论。** 没有据有限枚举证明全称结论，也没有将其升级为饱和控制器、所有可读通道或真实 6R 定理。

发表/整稿前应补齐：block half-length 与 gap-length 的 m 符号冲突；明确两方向 k 槽转换与 join 的可行性；说明 max 的存在或使用 sup；正式 checks 增加非零 weighted mass 修补例。最后一项是计算覆盖不足，数学 U3–U7 本身已覆盖任意已知 |g|≤1，本轮还另核了一个真正非零的有限见证。

## 1. 冻结来源与实际覆盖

|文件|读取时 SHA256|
|---|---|
|`outputs/m1_problem_contract_v1.md`|`9d01225548c86481b88fb5fe50305a2a9ecf8364ea4a3116137b55c0540389a3`|
|`outputs/m1_controlled_memory_theorem_v1.md`|`0689f5ce730f656ba1fe6cfbf2b2f13be1da89ff0ff91d932c81efaeda913ffe`|
|`outputs/m1_controlled_memory_checks_v1.py`|`fe6a6771019451af2c24cf9ac3764cafc7cbe85d2917b2f89aed28bd5277f6f0`|
|`outputs/m1_controlled_memory_checks_v1.json`|`deda3a5015fce31f6adff15d65dae267ddf07a05739a95c84016627a8ed31ddc`|

完整读取合同和 Markdown 数学证明，按 T1–T3、P1–P2、G1–G6、C1–C6、U1–U13 逐式检查；读取正式 checks 的实现与保存结果。只为第 7 节的新不对称小例做有限 Fraction 运算，没有重跑1270个子集、129个完整日历或历史验证器。TeX只核对开头的合同/主定理与Markdown相符，未审全部排版源码，也未重试编译；既有平台编译失败不能写成数学或编译 PASS。

## 2. 合同、真实 likelihood 与完整健康量词：通过

固定 λ/K，`u_j=−Kx_(j−1)` 确实给 `x_j=cx_(j−1)+input+w_j`；没有把当拍 x_j 放进非因果反馈。已知 `x_(−n0)=0` 只固定状态初值，不固定健康 b 的自由水平；所有健康 input nodes j=−n0+1,…,H 仍进入 Z。

给定 retained times，从真实上一个 retained state 减去 `c^m x_prev`，得到 P1 的原始创新加权和。不同 input spans 不相交，B_m≥1，除以√B_m 后 covariance 为 qI；变换是对 retained record 的共同已知 invertible triangular transform，所以它与包括全部跨 block covariance 的原 state 联合分布等价。无需 stationary 初始化或分块 covariance reset。

T 的 rows 单位且互相正交，P=TᵀT 是完整 input 空间上的 orthogonal projection。故

\[
\|T(a-gz)\|^2=\|P(a-gz)\|^2,
\qquad G=\frac1{2q}\inf_{z\in Z}\|P(a-gz)\|^2.
\]

未读槽的 g z 与 a 同样经真实 span projection 进入随后读数。文本没有将 Z 换成 observed-node trace，亦没有忽略 missing input 的 nuisance。两侧分别允许 r/2，差分由 `b0=z/2,b1=−z/2` 精确实现，所以 r 的量词正确。

在本有限维 polyhedral Z 及线性 mean maps 下，差分 image 是闭多面体，最近距离达到；共同 qI 的 Gaussian 最近对风险接口可用。它不是未知 covariance、adaptively selected calendar 或真实机器人非 Gaussian 输出的接口。

若 terminal inputs 无后续 retained state，P 的相应列确实为0。把最后一次旧读数之后的 moves 替换为原 task 的持续读数，因因果性保留旧数据的逐完整路径分布；新数据包含旧 experiment，逐参数 KL 不减，同一全史 Z 的 inf 也不减。合同没有 terminal-task 义务，因此这一支配合法，求最优可限制最后 x_H 被保留。此时所有 input spans 覆盖完整时域；prefix 全部 singleton，a_prefix=0，没有额外 stationary/endpoint 信息项。

## 3. 任意长度 gap 的 affine cross：通过

G1 的 `M=I−wwᵀ/B` 为PSD contraction。κ>0 由 Cauchy–Schwarz严格性得出（m≥2、c≠1）；κ 的 gap 长度单调性可用同一 full-input constant experiment 的 nested retained subsets 和 data processing证明，不需 c≥0。`|A_m|≤(1−|c|)^−1`、B_m≥1 还给有界 R_m，故 κ(ℓ)/ℓ→1，b_c>0。给出的 finite-prefix + 1/2 tail certificate 正确。

展开 `a=A1+ηh` 后，G3 三项完整，L2≥0，而

\[
|L1|\le\frac{|A_m|}{B_m}\sum_j|h_j|\,|c|^{m-j}
\le\frac{m}{2(1-|c|)^2}.
\]

没有使用 M0 的 reflection symmetry。P 的真实 non-singleton spans 在 post-onset input clock 上互不相交，且包括各自右 retained input，故 Σm≤H。所有 A≤ρ0+ηH，负 cross 总额最多 `η(ρ0+ηH)H/(1−|c|)^2=O(H²)`，对长 gap、dense/consecutive moves及任何日历一致。不能将这一估计误读成每个 gap 固定长度。

每个 missing output 对应其 span 前 ℓ 个 input nodes；a_j≥0且每个 a_j≤2A。因此 `Σ_missing a_j²≤4ℓA²`，配合 κ(ℓ)≥b_cℓ 及同一 cross error，G6 方向和常数正确。prefix全读使所有真实 gaps 位于 post-onset，未把0-prefix强行作 affine extension。

## 4. 全日历 converse 与同一 T 的 convex split：通过

在 clipped held run 上 `z=g r min(i,n−1−i)`，held g=±1，故 `h=gz` 为非负 tent。run endpoints、missing nodes、macro边界及prefix取0，使它成为单一完整 rate-r 路径；两个假设各取其一半。每个真实 non-singleton span 上 h=0，尤其包括该 span **右 retained input**；左 predictor state 已通过 P1 处理，不能重复算到 span。

因此用这一合法 z 评估 inf 的上界，orthogonal decomposition 给精确 C1：

\[
2qD\ge\|a\|^2-\|P(a-h)\|^2
=\sum(2ah-h^2)+\sum_{gaps}L_m(a).
\]

tent area 满足 `Σ min(i,n−1−i)≥(n²−2n)/4`（偶长等号、奇长多1/4）。高度≤rL/2，late amplitude≥A，使 C2 的 `C=r(2A−rL/2)/4` 正确。n=1等短run的负 area 下界只是更弱，未破坏不等式；M=0必须单独处理，正文已处理。

macro内相邻 clipped runs 之间的真实 gap 完全位于该macro，各 output gap≥k；它们在不同macro不重复。跨macro长gap可漏出第一项，但所有 missing nodes 仍各按所在macro进入 dead-energy 项。两条 C3 是对**同一个全局 T** 的下界。写 `(1−θ)T+θT` 后分别使用它们，cross error 为 `(1−θ)E_H+θE_H=E_H`，不双收 gap 信息。

Cauchy/AM–GM 给 C4。因为 C≤rA/2，

\[
A\ge\frac{32Wr}{\theta^2b_c^2}
\ \Longrightarrow\ \frac{\theta b_c A^2}{4}\ge2A\sqrt{CW}.
\]

因此 d 项可吸收。M=0,d=L时仍得到 C5，不需假设每macro存在读数、run平衡或 sparse switching。

L=floor(H^(3/4))、宏块数 O(H^(1/4)) 时：ΣA²=O(H^(9/4))，ΣCL=O(H²)；√C 的相对修正 O(L/A) 与 Riemann/未用tail各给 O(H^(9/4))。固定 ε、θ 的误差对 calendar 一致，随后按 `H→∞`、`ε↓0`、`θ↓0` 的顺序取极限，得到 C6 系数 `√2/(5q)√(κr)η^(3/2)`。没有偷偷使 ε、θ 随 H 缩小以抵消未控制的余项。

## 5. upper 的 input joins 与 weighted mass repair：通过

建议以 `p=n/2` 表示 half-hold，`m_gap=k+1` 表示 gap span，消除正文 m 双重含义。以下计数按这一明确区分检查。

每块实际读数为 +p、gap k、−n、gap k、+p；末读数和下一块首读数均真实 retained。后一 conditional span长度1，故 **input projection** 允许direct sum；这不表示原 state covariance跨块为0。H−1 packing和四槽 padding在有至少一块时留下1–4个+tail reads，使x_H保留。

padding每块只加O(1)：base未用预算小于下一个block的O(M)长度，平均到M块后的四槽单位数有界。于是M=√(H/ξ)+O(1)、n_l=ξl+O(1)、A_l=ηξl²+O(l+1)。未满一块的小H另取stay即可；这有限的初期不影响asymptotic claim。

active条件给所有 held U0∈[0,A]，missing U0=A。local z levels只生成 baseline direction，不被冒认成跨块可行对手。baseline λ0=(gU0)_held、missing填0，精确总和0；gap中插入0只是延长 partial-sum plateau，跨度仍k+1。局部最坏support式 U2 的符号和计数正确。

两gap各占 k个missing inputs加1个右held input，故2n个held inputs中恰有2个归 non-singleton，剩余 `2n−2` 个 singleton上Pg=g=±1，

\[
D=\|Pg\|^2\ge2n-2\ge n>0\quad(n\ge2).
\]

这里无需 missing g 非零，也无需 c 正号。每gap PU0 的L1≤m_gap A，baseline在它上仅有一个≤A的rightheld值；所以 N 的绝对值≤2(k+2)A。U3的 α=N/D 因此合法，且

\[
g^Tv=N-\alpha D=0,
\qquad Pv=v,
\qquad\|v-PU0\|^2=N^2/D\le C_k^2A^2/n.
\]

δλ=g⊙v−λ0精确零质量。利用 `||g⊙Pg||1≤L`，`L/n=2+2k/n≤k+2`，得到 U7。这里“gv”是Hadamard乘法；建议正式稿显式写diag(g)v，避免矩阵乘法歧义。

完整无界水平 rate-r 类的有限support需Σλ=0，且等于 `rΣ|Q_j|`。对零质量向量 `|Q_j|≤||λ||1/2`，所以 U8 成立。每块 δsupport 是 O(rA(n+k))；全史support用subadditivity或完整partial sums，不重置健康初值。N修复能量 ΣA²/n=O(H²)，δsupport ΣA(n+k)=O(H²)。这些步骤覆盖所有已知 bounded missing profiles，非只对反射/对称 profile。

## 6. dual、oracle pair 和 matching coefficient：通过

v∈range(P) 可由实际 retained conditional innovations构成：row系数Tv，完整input系数TᵀTv=v，variance为q||v||²。Fenchel下界因此使用同一实际Gaussian实验；support为h_Z(diag(g)v)。U10 来自

\[
\|a-v\|^2=\|(I-P)a\|^2+\|Pa-v\|^2,
\]

两项是 orthogonal input 能量，不是把 raw state blocks 独立化。

active pointwise error≤(η+r)(n+k)，长度2(n+k)，故辅助能量≤2(η+r)²Σ(n+k)³。inactive blocks uniformly有限，prefix target0，tail≤4点、幅值O(H)，全部合计O(H²)。再加修复能量给U11。对固定ξ，Σn³与ΣA²/n均为O(M⁴)=O(H²)，不会进入H^(5/2)首项。

两个gap input centers相对block center确为 `1/2−(n+k)/2`、`1/2+(n+k)/2`。几何weights均朝真实右held input，不能反射第二个gap。两者 affine norm loss的和正是 U12；common η/2 shift和L1项都保留。固定c,k下ΣA、Σ(n+k)²=O(H^(3/2))，故U13的误差阶正确。

于是

\[
2qD(\pi_H^\xi)\le2\kappa\sum A_l^2+r\sum A_l n_l^2+O(H^2),
\]

\[
\sum A_l^2=\frac{\eta^2}{5\sqrt\xi}H^{5/2}+O(H^2),\qquad
\sum A_l n_l^2=\frac{\eta\sqrt\xi}{5}H^{5/2}+O(H^2).
\]

除以2q后得到T3；ξ*=2κη/r给与C6完全相同的 `√2/(5q)√(κr)η^(3/2)`。r始终是两假设差分速率、q是原始输入创新variance，没有漏掉1/2或将output variance当q。c=0恢复κ=k；负c不需修改本证明。上下界在同一fixed-parameter合同内匹配首项，但其H²/H^(9/4)余项不同，故没有次阶sharp结论。

## 7. 正式 checks 的覆盖缺口与新非零修补见证

读取JSON发现：120个 `finite_dual_cases` 与9个 `larger_checks` 的 `repair_energy` **全部为0**。代码在两gap使用相反的同形 profile；两个压缩spans的U0也相同，N恰好跨gap抵消。故计数“695个 repair energy checks”是真的执行次数，但不能表达为695次非零修补已核；它们没有检验 α≠0 的核心路径。应新增两gap不互为相反的profile，保持 |g|≤1。

本轮独立小例取 `c=−1/2,k=1,n=4,A=10,r=1,η=1/7`，block长度10，完整input arrays为

\[
g=(1,1,1/3,-1,-1,-1,-1,-2/3,1,1),
\]
\[
U0=(8,9,10,9,8,8,9,10,9,8),
\quad\lambda0=(8,9,0,-9,-8,-8,-9,0,9,8).
\]

真实 spans 是 singletons 1、2、5、6、7、10，及 [3,4]、[8,9]。用Fraction rank-one projections直接算得

|量|精确值|
|---|---|
|N=gᵀPU0|8/15|
|D=||Pg||²|383/45|
|α=N/D|24/383|
|repair energy=N²/D|64/1915|
|repaired weighted mass gᵀv|0|
|h_Z(λ0)|100|
|h_Z(δλ)|10251/383|
|h_Z(g⊙v)|35773/383|

另逐项核 `Pv=v`、D≥2n−2、U5/U7、`h_Z(g⊙v)≤h_Z(λ0)+h_Z(δλ)`，全部成立。以a_j=A+η(j−11/2)计算真实两个gap的loss，结果 `178309/490`，与U12完全一致。该例使用允许的负c及不对称有理profile，α真正非零；它支持实现与计数，不替代前述全称证明。未写入或修改原 checks 文件。

原始方向PU0在此例有非零weighted mass 8/15，因Z含自由水平，其健康support无穷；所以修补是必要的，不只是改变一个较小的有限误差常数。

## 8. 必须明确的整稿细节与结论边界

1. **符号：** gap span用m_gap=k+1，block half-hold用p=n/2。当前第5–6节的m同时表示两者，可能被读成n=2(k+1)，必须修正。输入点逐项乘法写diag(g)v或g⊙v。
2. **可行性：** terminal-balanced upper要求 +→−、−→+ 两种k槽转换均合法，可重复串接，并允许join/tail +reads。无状态、输入限幅、tracking或终点任务义务的本标量类自然可按合同构造；若“至少一个允许profile”是更窄物理协议，应补明两方向和串接条件，否则converse仍成立而达到不自动成立。
3. **max：** 若每个calendar有固定合法profile，calendar集合有限，max存在。若profile也优化且其允许集合为整个闭盒[-1,1]，对每个固定mask，G是连续函数族（indexed by z）的inf，故upper semicontinuous；compactness给max，有限mask union亦可。若允许profiles只是未声明的非闭子集，写sup或先补存在性条件；matching上下界本身不依赖max是否达到。
4. **计算：** 正式checks增加α≠0的asymmetric profiles，并用新版脚本/JSON哈希绑定报告。不要把全部零修补例的计数当成已检验一般修补。
5. **控制和读数：** 控制器内部读完整state，而诊断器不读fast states/control commands，这是基本合同。若K≠0的逐槽command也给诊断器，内部missing states可能被恢复，不能保留同一信息下界。
6. **范围：** fixedknownc、q>0、fixedn0、已知增长模板、全史无界幅值限速健康、确定性已知终点日历和共同初始状态。没有证明未知c、adaptive/unknown-onset、additive state measurement noise、固定有限盒、饱和/全扰动恢复或实机6R。c随H逼近1、或对连续gain族交换inf与limit，仍需一致余项；fixed-gain leading coefficient比较不能改写成finite-H所有风险最优。

本轮结论可以用于接受**这份冻结标量原型的 fixed-parameter 首项sharp证明**，同时把上述四项整稿/计算修订纳入台账。它不替代原创性对照、实际控制可行性或整篇TAC验收。
