# AR(1) 全日历 converse v1：独立逐式审查

日期 2026-10-07。审查对象：`outputs/colored_ar1_converse_v1.md`，SHA256 `2580ab1a028a924443d7cf645e636069da7a011af1da3e0af6a345b30e88d901`；并对照 `outputs/problem_contract_v1.md` 的 M0 raw 合同及独立 AR(1) 引理。没有参与该 converse 文件的写入；本审查不修改原文件。

## 1. 判定

在所写固定参数、n₀≥1 固定、B=∞、确定性 known-horizon calendar、|ρ|<1、σ>0、k≥1、r,η>0 的 M0 合同中，逐式检查后**接受 T1 作为全日历 liminf 下界**。未找到会使 T1 失败的量词、端点、负相关或因子 2 漏洞。这个结论不构成 same-coefficient upper bound，也不接受“colored sharp 已证”的升级。

有两处建议在后续整合中写清，属于可直接补完的论证细节：

1. Prefix 替换后的信息和 oracle 暂记为 G̃、Õ、D̃，再写 D̃−D=O(H^{3/2}) uniformly。否则 L5 的 D 容易被误解为替换前的 original D 而遗漏一次误差。
2. L6 到 L8 中先在全局层面把同一 T 分成 (1−θ)T+θT，再分别用 run-count 和 dead-budget 下界，之后按 macro 汇总。这个顺序是有效证明；不是把跨 macro gap 的完整 loss 同时分摊到两个 macro。

下面给出每个依赖的独立核验，及能直接补入稿件的谱界与 b_* 有效下界。

## 2. L1：局部 gap 矩阵、中心反射、因子

对 span m=l+1 的局部向量，其 full energy 减端点边缘 energy 是

\[
Q_{local}(x)-Q_{end}(x_{end})=
\sum_{h=1}^m\frac{(x_h-\rho x_{h-1})^2}{\sigma^2(1-\rho^2)}
-\frac{(x_m-\rho^mx_0)^2}{\sigma^2(1-\rho^{2m})}.
\]

所以 loss 矩阵确实包括**两个保留端点**，不是只在 missing 坐标上放一个条件 precision。它是 full precision 减嵌入后的 endpoint marginal precision，完成平方后 PSD。多个 gap 的 Markov transitions 相减给精确相加；无需 gap 分离或噪声 reset。

完整局部 stationary covariance 和端点 covariance 都在反射下不变，故 M 与 reflection J 对易。1 为 symmetric，h_j=j−m/2 为 antisymmetric，因此 1ᵀMh=0。在 q=Q/2 约定下，loss 正好 β_l A²/2+η² hᵀMh/2。E_l≥0；没有漏半因子。这个结果也对 ρ<0 成立。

应用到 zero-endpoint 对手时，x=a 的范围必须覆盖全部局部 l+2 槽，含两保留端点。引理3 构造确实如此，不仅 missing 上 z=0。

## 3. β_l 的正性、单调与 b_*

把 w₁=(1−ρ)/(1+ρ)、w_m=(1−ρ^m)/(1+ρ^m)，A_m=∑ρ^j、B_m=∑ρ^{2j}，独立展开得

\[
\frac{w_m}{w_1}=\frac{A_m^2}{B_m},\qquad
\frac{\beta_l}{\nu}=m-\frac{A_m^2}{B_m}.
\]

对 m≥2，Cauchy–Schwarz 等号要求 (1,ρ,…,ρ^{m−1}) 常值，即 ρ=1，已排除。所以 β_l>0，包含 ρ=0 与负相关。不能用“ρ≠0”排除 iid；原文正确使用 ρ≠1。

单调性也有效：固定足够大完整序列，令 R_l 删掉同一左端后的 l 个 consecutive nodes，R_{l+1} 再删掉一个旧右端。R_{l+1}⊂R_l，两边仍保留新的右端；known constant mean 的 full-minus-observed loss 只依赖 l，故 KL data processing 给 β_{l+1}≥β_l。右端位置移动不破坏 nested experiment。

β_l/l→ν>0，加上每个固定 l 的严格正性，给 b_*>0。可以给一个可计算版本，避免把 b_* 当作数值搜索的未证常数：令

\[
C_\rho=\frac{1+|\rho|}{\sigma^2(1-|\rho|)},\qquad
M_0=\max\{1,\lceil 2C_\rho/\nu\rceil\}.
\]

因为 w_m/σ²≤C_ρ，β_l/l=ν+(ν−w_m/σ²)/l≥ν−C_ρ/l，因此 l≥M₀ 时 β_l/l≥ν/2。于是

\[
b_*\ge\min\{\nu/2,\ \beta_l/l:\ k\le l<M_0\}>0,
\]

空有限集时仅取 ν/2。这里是固定通道结论；若让 ρ随H逼近±1，需要重新证明 uniformity，不能沿用本 lower bound。

## 4. L3 与缺测端点

本合同 prefix 全保留，首个 post-onset missing gap 的左端最早是 j=0，其仿射 a₀=ρ₀≥0。后续 gap 左端也非负。因此 gap 的 A=(a_left+a_right)/2≥0，所有内部 missing 值≤a_right≤2A。这个非负条件没有被 prefix 的早期可能负 affine extension 破坏，因为 prefix 内没有 gap。

于是 ∑_gap a_j²≤4l A²，2Δq_gap≥β_l A²≥(b_*/4)∑_gap a_j²。对全部真实 gaps 相加得到 L3。常数 1/4 有效；不需要 gap 长度等于 k 或短于 macro。

## 5. 固定 prefix 替换的 calendar-uniform 谱界

对完整 stationary AR(1) precision P，内部绝对行和为 C_ρ，端点绝对行和为1/[σ²(1−|ρ|)]≤C_ρ，单槽时为σ⁻²≤C_ρ。因此 ‖P‖₂≤C_ρ，亦即 λ_min(C_full)≥1/C_ρ。主子矩阵 C_R 满足 λ_min(C_R)≥λ_min(C_full)，所以 **所有 calendar 的 ‖C_R⁻¹‖≤C_ρ**，不依赖 H、R 或 gap 长度。

替换只改变固定 n₀ 个 target entries，其 ordinary norm 与 white norm 都为 O(1)。对同一个白化 mean set，distance 函数是 1-Lipschitz，故平方距离差≤‖δtarget‖(d_old+d_new)。0 在 nuisance 类中，距离≤white target norm=O(H^{3/2})，得 G̃−G=O(H^{3/2}) uniformly。Oracle 用同样 norm identity 也有此 bound。故 D̃−D=O(H^{3/2})，不影响 T1。这个步骤没有把 prefix nuisance 固定成0；只是对 converse 对手选择了0。

## 6. Terminal domination 与全内部 gap

把最后一次有读数之后的所有 moves 改为原 task hold，会保留原数据并添加读数。对同一个完整 z，新增 Gaussian marginal experiment 的 KL不小于原 experiment。对共同 full-history class 取 inf 后仍保持 ≥，所以最优 G 可限制在终点被观察的 calendar。若 post-onset 原本没有读数，则从 prefix 之后全部 stay，同样包含原数据。

n₀≥1 且 prefix 全保留给左端；终点被保留给右端。因此每个 post-onset excluded 连通区间均是内部 gap。不需要硬给 initial/terminal missing 套内部 β；本限制消除了那些边界。支配步骤依赖 M0 的允许 hold/无终点任务约束，未来物理系统若强制返回指定任务，则要重审。

## 7. Zero-endpoint 全史对手与 L4–L5

每个 clipped observed run 的 first/last tent 都为0；macro boundaries、missing、prefix 和未使用尾段也为0。线性插值形成一个全史 z，斜率≤r，z/2与−z/2可实现原两侧单独健康路径。s可能在 gap 内变化，但 z=0，所以 h=s z 仍为全史非负、r-Lipschitz；在任务间的任何端点都为0。

L4 full-energy identity 对 singleton 和负ρ都正确。原始 full affine a 的增量为η，x=a−h 的增量≤η+r，故 derivative energy difference有固定每槽 bound，总计O(H) uniformly。首末 h=0使 c_ρ endpoint correction **精确相消**，不存在O(H²)漏项。Gap全部局部节点的 h=0使其 loss等于 a 的 L1。

因此评估一个合法全史对手 gives

\[
2\widetilde D\ge\nu\sum_R(2ah-h^2)+2\sum_{gap}\Delta q_{gap}(a)-O(H),
\]

与 L5一致。这里 q=Q/2、T=2∑Δq，ν、β均Fisher系数。转换回 D 可再加 prefix O(H^{3/2}) 误差，仍低阶。

## 8. L6–L8：跨 macro 预算、m=0 与 θ 吸收

对 macro 中 m 个 clipped runs，任何相邻两run的整个 gap及两个 retained endpoints均位于该 macro 内；所以有 m−1 个真实完整 gaps，each length≥k。它们属于不同 macros 时互不重复。跨 macro 的 gap 不进这个第一 bound。m=0 时负数 β_k A²(m−1) 只是允许的较弱下界。

第二 bound按每个 late macro 的 excluded槽分配 ∑A²d。各缺测槽只属于一个 macro，虽其所属完整 gap 可能跨多个 macro。L3作用于**完整 gap总loss**，而不是在每个 clipped gap 都另收一次β。因此第二 bound也有效。

全局 T≥F_run 和 T≥F_dead 给 T=(1−θ)T+θT≥(1−θ)F_run+θF_dead。两界可组合，即使 F_run因m=0有负项。这是一个 T 的 split，未重复使用两份 gap信息。

L6的 tent area/height下界正确。m>0时 Cauchy gives Σn_i²≥(L−d)²/m。令 W=(1−θ)β_k>0，AM–GM

\[
\nu C (L-d)^2/m+WA^2m\ge2A\sqrt{\nu CW}(L-d)
\]

方向与因子正确。吸收 condition为 θb_*A²/4≥2A√(νCW)。C≤rA/2，所以一个足够条件是

\[
A\ge\frac{32\nu Wr}{\theta^2b_*^2}.
\]

固定 θ>0、ε>0，late A≥ηεH最终对全部 calendars满足该 condition。m=0时 d=L，health area0，dead term θb_*A²L/4本身就≥2A√(νCW)L，再减原弱常数项即得 L8。没有除以0，也没有假设观测覆盖率下界。

## 9. 一致余项、极限顺序与 T1常数

固定 ε、θ后，L=H^{3/4}、A=Θ(H)，C=(rA/2)(1+O(H^{-1/4}))。主和为 √(2νrW)∑A^{3/2}L，误差O(H^{9/4})；ΣA²=O(H^{9/4})，ΣCL=O(H²)，最后未用 macro的 Riemann误差O(H^{9/4})。prefix改动O(H^{3/2})、full derivativeO(H)更低阶。所有 constants与 calendar 无关。

故对 **2D** 的 liminf下界为 (2√2/5)√(νr(1−θ)β_k)η^{3/2}(1−ε^{5/2})。先对calendar取最小deficit，再H→∞，再ε↓0、θ↓0，得到 D的系数 √2/5，精确匹配 T1。θ不能随H未经证明地快速趋零；当前 sequential limits正确。

## 10. 小型精确核验及不覆盖范围

正式复现入口 `outputs/ar1_converse_checks_v1.py` / `.json` 只用 Fraction，ρ∈{−4/5,−1/2,0,1/2,4/5}：419次β ratio identity/单调/finite-tail b_*证书核对；15次θ吸收；2630次m>0 AM–GM squared inequality；15次m=0边界。实际 exit=0。在仓库根目录运行 `python outputs/ar1_converse_checks_v1.py`，stdout 应与保存 JSON 一致。该程序不给全称证明，数学判断由上述各段推导承担。L1另有独立35个affine reflection exact checks。

本审查不证明upper construction、finite-H detection threshold、任何controlled-plant realizability、controller-uniform asymptotic或新颖性。不能据T1直接报告sharp、最优检测时域或TAC投稿就绪。

## 11. v1.1 澄清修订复核

2026-10-07，再读 root 的两处澄清改动。新 `colored_ar1_converse_v1.md` SHA256 为 `7e81111f4fbfd568c7ab071dc7c838189ef0380c245e2de2580a34f6bb55f1f6`。该版显式区分 affine-prefix 替换后的 D̃ 与原 D，并保留 uniform O(H^{3/2}) 转回误差；另先在全局层面 split 同一个 T 后，再分别应用两界并按宏块汇总。两改动准确落实本审查建议，没有修改原 T1 的合同或系数。接受该 v1.1 的 bound-only 状态；无需重跑未改变的精确检查。
