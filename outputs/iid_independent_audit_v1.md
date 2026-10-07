# 原 iid 主定理的独立审查 v1

审查日期 2026-10-07。范围仅限本次恢复的 `references/manuscript_20260909/model.tex`、`proof_sharp.tex`、`proof_finite.tex`、`results.tex` 中的 progressive sharp、finite-box 两条主定理及其直接合同。未读取/审查 constant-fault Appendix A，未重跑历史 MC，未核对外部引文全文、机械 D2-a 或整个稿件的新颖性。因此不能称“全稿独立审查通过”。

## 1. 结论与需要补清的事项

在固定参数、deterministic known-horizon、iid Gaussian、对称两侧完整健康路径、r>0、η>0、固定 n₀ 的声明范围内，未找到推翻 progressive sharp 或 fixed-box bounded-advantage 主结论的漏洞。宏分块全日历 converse、局部 support/KKT、terminal balancing 和两个主系数的因子 2 均可由原文恢复为完整论证。

仍建议在复用稿中做三项小修复/澄清：

1. `results.tex:123` 的“exact Gaussian requirement”应写 Λ=½(z_{1−α}+z_{1−β})_+²，或显式限定 α+β<1。目前平方不带正部对 α+β>1 的有限风险要求不正确。**不影响 α↓0 的主 detection-time 渐近**，因为固定 β 后最终满足这个条件。
2. `proof_finite.tex:10` 的配对 movement 明确选为“new observed run 前最后 k 个 excluded slots”。合同允许 duration≥k，若误解为任意较长 move 的前 k 槽，随后的 amplitude 上界 a_m+η(k+N_B) 就不成立。按“immediately preceding”的原意取最后 k 槽，证明可修复且常数无需改变。
3. `proof_sharp.tex:12` 和 `:36` 增加一两句：m=0 单独处理；macro clipping 截断的 observed run 首末 tent 为零，所有 macro 及 missing 区间用零插值，故是一个全史对手。现有公式本身有效，但这两句可防止误读为逐块独立挑 nuisance。

这些范围限定不能用于直接升级 colored candidate：iid task demodulation 不改变 σ²I，而 colored covariance 必须同步变为 D_s C D_s。

## 2. 审查版本绑定

本次读取的 SHA256：

|文件|SHA256|
|---|---|
|model.tex|05d652bef5209497428da3ce30854a13b5ca2ab34d08627c33adcd63ae688977|
|proof_sharp.tex|468c248f87dce51c0058e03e78c988ff2f05b4b2f76dcd1e6be2ef7bd49e3fd7|
|proof_finite.tex|d7ec2eff9bc36e778caeec13bcbb760ef0952786c80e11e5c617fbe953ff82c1|
|results.tex|cc659fa8e9d969c1ed9776e3a6f176ae31dcc8b9fe25461fe5540fe9a00b982c|

正式复现入口：`outputs/ar1_iid_audit_checks_v1.py` / `.json`，标准库 Fraction，432 个 exact cases，实际 exit=0。在仓库根目录运行 `python outputs/ar1_iid_audit_checks_v1.py`，stdout 应与保存 JSON 一致。work 保留初次执行痕迹，不是唯一证据。

## 3. 合同、差分集合与风险因子

`model.tex:15–37` 两假设可选不同完整健康路径；对称类的差分限幅 B=2b，差分速率 R=2r_d，槽速率 r=Rδ。观察 trace 的相邻约束应按真实槽距离 r(j_{i+1}−j_i)，不是按观察编号距离。任意 trace 节点的分段线性插值可实现该完整路径；z/2 与 −z/2 各自合法。因此差分量词正确，没有把单侧健康半径和差分半径混用。

`model.tex:43` 的 G=(1/(2σ²))min‖s−z‖² 是 pairwise KL，oracle 同样含 1/(2σ²)。在对称闭凸 Gaussian shift mean sets 中，z* 的 projection residual w=s−z* 给两侧分离超平面；最近 null mean 为 z*/2，最近 alternative mean 为 s−z*/2。这个具体合同下 minimax power Φ(‖w‖/σ−z_{1−α})=Φ(√(2G)−z_{1−α}) 的因子正确。该等式不能泛化到任意非凸 nuisance/不同 covariance/未知 target。

prefix 是零 fault target，不是 β(t₀)=0。Converse 选择 prefix 上 z=0 是合法对手子类，不是偷偷缩小原类；达到性 dual 在 prefix 上权重零也没有删除真实 prefix 约束。

## 4. 全日历宏分块 converse

对长度 L 的 macro，d 个 excluded 槽和 m 个 clipped observed runs，有 m−1 个完整隔离区间位于 macro 内，每个至少 k excluded 槽，所以 m≤d/k+1。初末 clipped run 不需要各自再支付 k；这正是“+1”的来源。允许 consecutive moves、empty round trips、unbalanced holds、全部不观测，都不会使 run count 失效。

每条 clipped run 的 signed tent 为 z_i=εr min(i,n−1−i)。它的首末 observed 值为零，内部斜率≤r；macro 外与 missing 槽填零，所有 pieces 合起来成为一个合法完整路径，且 prefix 上为零。因此可将各 macro 的贡献同时放入同一个全史対手。

若 A 是 macro 最小 amplitude，C=r(2A−rL/2)/4≥0，则

\[
\sum_{\rm obs}(2\epsilon a z-z^2)\ge C\sum n_i^2-2C(L-d).
\]

这里 tent height≤rL/2，∑min(i,n−1−i)≥(n²−2n)/4。对 m≥1 用 Cauchy 和 run count 得 ∑n_i²≥k(L−d)²/(d+k)；对 m=0，L=d，原 lower bound A²L−2CL 仍有效。令 y=d+k 后，展开成

\[
(A^2+Ck)y+Ck(L+k)^2/y-2Ck(L+k)-A^2k-2CL
\]

的代数正确，AM–GM 得原 Ψ。它的正部可以使用，因为零对手总能给非负 saving/dead contribution。

固定 ε>0，late macros L=⌊H^{3/4}⌋、A=Θ(H)，C=(rA/2)(1+o(1)) 在 calendar 上一致。所需余项逐项为：

|项|所有 macros 累计|
|---|---|
|A²k|O(H³/L)=O(H^{9/4})|
|CL、CkL|O(H²)|
|C 对 rA/2 的相对 O(L/H) 误差|O(H^{9/4})|
|最后不足 L 的 macro / Riemann 分段误差|O(H^{3/2}L)=O(H^{9/4})|

故余项均 o(H^{5/2})，且没有在任意日历上隐藏 O(H^{5/2}) 尾块。leading 为 √(2kr)∫_{εH}^H(ηt)^{3/2}dt=(2√2/5)√(kr)η^{3/2}(1−ε^{5/2})H^{5/2}，作用于 **2σ²D**。先取 calendar 最优再 liminf、最后 ε↓0 的顺序正确。

## 5. Support 函数、局部投影与全史达到性

在一个局部 symmetric block，n=2m、c₀=(k+1)/2，原 z 层值最大为 r(c₀+m−1)=r(k+n−1)/2。条件 a 大于该值时，+ 区域 residual 非负、− 区域 residual 非正。正负层值成对，故 ∑w=0。

对 unbounded-level、rate-limited trace，support finite 的必要条件正是 ∑w=0。令 Q_i=∑_{j≤i}w_j，summation by parts 给

\[
w^Tz=-\sum_iQ_i(z_{i+1}-z_i)\le r\sum_i\Delta t_i|Q_i|.
\]

原局部 z 在每个 Q_i≠0 边界满足 Δz_i=−rΔt_i sign(Q_i)，因此等号成立。中心 flat edge 对应 Q=0；两个 movement edge 的时长是 k+1 而不是 k。由 support 等号与 w=s⁰−z 得 convex projection 条件，故这不是只靠视觉形状猜出的局部 optimizer。

独立 exact calculation 验证了 k=1,…,6、n=2,4,…,24、两种 rational r、a 在 threshold/threshold+1/3/threshold+100 的全部 432 cases：rate feasibility、zero sum、edge complementarity、support equality、L_c 因子、reflection affine cancellation。公式

\[
2na^2-\|w\|^2=ar\,n(n+2k)-4r^2\sum_{j=0}^{m-1}(c_0+j)^2
\]

与原 L_c 完全一致。

对 affine actual target，w 与 ε reflection symmetric，local t−c antisymmetric，故 wᵀε(t−c)=0；以及 ∥s∥²=2na²+η²M₂。global support≤∑local supports 来自完整路径的 restriction，方向正确。只有 **dual directions** 被拼接；没有要求局部 primal optimizers 在 block 接缝处可拼接。zero-weight prefix/early blocks/unused tail 没有缩小实际实验的全史 nuisance 类。

## 6. Terminal balancing 和 sharp 系数

原 planned blocks n_l=2ceil(ξl/2) 的 cumulative duration 为 ξM²+O(M)，所以 M=√(H/ξ)+O(1)。选 maximal fit 后剩余 duration O(M)；将其 multiples of four 均摊到 M 个 blocks，每个 n_l 仅改 O(1)，余下 <4 槽。这避免未结束最后长块损失 O(H^{5/2})。

因 n_l=ξl+O(1)、a_l=ηξl²+O(l+1)：每块 dead energy leading 2kη²ξ²l⁴；每块 local L_c leading rηξ³l⁴。∑l⁴=M⁵/5+O(M⁴)，其余每块 O(l³) 等项总和 O(M⁴)=O(H²)。M₂ 每块 O(l³)，tail <4 槽 ×O(H²)，也是 O(H²)。只有有限个 early blocks 失效，因为 a_l~l²、threshold~l。

得到原 unwhitened coefficient (1/5)(2kη²/√ξ+rη√ξ)。它在 ξ*=2kη/r 取最小值 (2√2/5)√(kr)η^{3/2}。除以2σ²后正是 (√2/(5σ²))√(kr)η^{3/2}。上下界同合同、同固定参数范围，且余项/首项→0，故原 iid **首项 sharp** 声明有完整支撑。达到性 O(H²) 与 converse O(H^{9/4}) 不同不妨碍首项 sharp；没有对应 H² 次阶匹配结论。

计划时域 inverse：oracle leading c₃=η²/(6σ²)，deficit coefficient c_{5/2}=√2√(kr)η^{3/2}/(5σ²)。u=c_{5/2}/(3c₃)=(2√2/5)√(kr/η)，与原 correction 一致。固定 prefix、intercept 与 rounding 只影响更低阶。结果不是 ARL 或 adaptive stopping-time 定理。

## 7. Fixed finite box 的完整追踪对手

原 proof_finite 使用一个全史 bounded-rate tracker，prefix 上0、随后向当前 observed task 的 εB 端点移动，末端不强制返回0。把所有 deficiency 分配给最近 observed-run target 更新即可实现同一个路径；unobserved empty moves 不必给 nuisance 加上额外任务义务。

每个 observed deficiency 为

\[
2a(B-\epsilon z)-(B^2-z^2)\le4Ba,
\]

target endpoint 到达后为零。N_B=ceil(2B/r)+1 给最多 N_B 个 deficient reads。对每个新 observed run，选其前**最后 k 个 excluded 槽**作为 disjoint paired budget；设该 k 槽开始 m，则 assigned read amplitude≤a_m+η(k+N_B)。paired missing 的 oracle-minus-baseline excess≥k(a_m−B)_+²。其余 missing excess≥0。每项可能欠账至多

\[
[4BN_B(a_m+\eta(k+N_B))-k(a_m-B)_+^2]_+.
\]

其关于 m 最终是负二次式的正部，故全部可能 start indices 的和有限，且真实 calendar 只能取其中一个无重复子集。这给 calendar-uniform C₁，不取每块独立 nuisance、不重复拿同一个 movement 付两笔账。初始 approach 的早期亏损与末端 free-value 处理正确。

stay 下丢掉 rate 和 prefix loss 只扩展最小化可行类，给 G_stay≥∑(a−B)_+²/(2σ²)，方向正确。相反，整史 constant z=B 是合法对手，其 prefix loss n₀B² 正是原 lower bound 的常数。故 D_stay=P_B(H)+O(1)，全 calendar lower bound D≥P_B−C₁/(2σ²) 给 best-switching advantage≤C_B。完整多项式 P_B 的 H² 和 H 系数因子均正确。

这个结论依赖固定 B,r,η>0；r=0、B随H增长、向极点逼近的 colored channel 均不在此审查结论内。

## 8. 与 colored 研究的可继承/不可继承接口

可以继承：两侧差分量词、完整路径可实现性、zero-endpoint macro tent、局部 support restriction、terminal-balanced packing 以及 iid 因子核对。

不能直接继承：Euclidean support formula 对 raw colored x 的应用、missing samples 的逐槽 oracle-minus-observed budget、constant β 对任意任务跳变 residual 的替换、iid zero-frequency ν 对所有 endpoint terms 的删去。

本轮独立 AR(1) 推导的 reflection lemma 支持 zero-endpoint 对手路线：当 z 在 gap 全部局部槽**含两个保留端点**为0且 a仿射时，exact KL gap loss为 β(k)a_center²/2+η²E_k/2、E_k≥0。全史 affine metric saving 的 derivative correction 可用 tent h=s z 的限速及首末零值控制；跨 macro gap 的 dead budget 则仍需另外严谨分配。
