# M1 合同 v1：共同输入一阶植物、反馈记忆与状态缺测

冻结日期 2026-10-07。该合同先于 M1 sharp 推导冻结。它是 M0 之后的独立物理一致解析模型，不能把 M0 的 stationary output covariance 或固定输出均值直接代入。它不代表完整机械系统、饱和控制器、额外传感或实机协议已经验证。

## 1. 同一个植物与因果反馈

固定已知植物参数 λ 和控制器 K：

\[
x_j=\lambda x_{j-1}+u_j+\mathbf1_{h=1}a_j+g_j b_j^h+w_j,\qquad
u_j=-Kx_{j-1},\qquad c=\lambda-K,\quad |c|<1.
\tag{M1.1}
\]

这里控制采用前一个状态，闭环为 x_j=cx_{j-1}+输入；不是非因果的 u_j=−Kx_j。不同控制器比较保持 λ、外部故障输入 a、健康类 b、创新方差 q、观察时间和任务协议相同。所有输入经同一个 F_c 动态通道。模型没有另加 state measurement noise；w_j 独立 N(0,q)，q>0，且与两侧预先选择的健康路径独立。

初始 x_{−n₀}=0 已知，n₀≥1 固定。这里是已知确定初始化，不是 stationary 初始化。初始化后到终点的植物、反馈及创新持续演化，任何缺测或人工证明分块都不 reset。

本解析类暂不施加 actuator saturation、状态约束、tracking budget 或控制能量约束。若后来增加这些约束，须先验证合同非空与所用日历可实现，不能自动沿用本定理。固定已知 stable c 是本版参数；不允许 c 随 H 逼近单位圆后仍称余项一致。

## 2. 时域、任务与明确的读数限制

健康 prefix j=−n₀+1,…,0 全部读 state、任务 g=+1。之后 H 个 slots 在开始前已知。post-onset fault a_j=ρ₀+ηj，ρ₀≥0、η>0；prefix a_j=0。

保持任务 g=+1 或 −1，每槽读一次指定 scalar state x_j。任务转换至少 k≥1 个 consecutive slots 不向诊断器提供 state。移动中的 g_j 是预先已知的 deterministic 系数，满足 |g_j|≤1；不要求停止动态或停止故障/健康输入。固定 k 长移动有至少一个允许的 known profile；主定理的达到日历只需要它，且对其 gap 内具体 profile 不作调优。

诊断器仅取得 retained states、已知日历、g profile、植物/控制参数、fault template 和初始状态。运行控制器可以内部使用每槽 x_{j−1}；诊断器不读那些 fast internal states、控制命令或创新。这是明确的受限读数协议，不是对整台机器人的所有检测器声称信息极限。若控制命令可逐槽读取且 K≠0，可能反推被删状态，应另建实验。

允许较长转换、consecutive moves 与 empty round trips；日历和全部 g 在噪声产生前确定，nature 随后选择两条完整健康路径，再产生创新。未读数据仍影响后续 state。末尾没有后续读数的移动可替换成原任务继续读数；本版无终点任务义务。

## 3. 两侧完整健康路径和差分量词

每个假设各自选择 b^h，槽差分速率≤r/2，幅值无界、初始水平自由。两条路径不要求相同。实际差分 z=b^0−b^1 的完整输入节点类为

\[
\mathcal Z_H=
\{z\in\mathbb R^{H+n_0}:|z_{j+1}-z_j|\le r\}.
\tag{M1.2}
\]

z/2 与 −z/2 实现两侧路径，线性插值实现连续槽间路径。已知初始 state x_{−n₀}=0 不等于已知 b 的初始值。

M1 的未读槽健康输入也影响随后 state，所以不能只保留 observed health nodes 的 trace，再忽略 gap 中 z。所有 profiling 和对手构造使用同一条完整 z。不得逐 block 重置健康水平、植物状态或噪声状态。

## 4. 真正的保留状态条件似然

设 retained times t₁<⋯<t_N，令 t₀=−n₀ 为已知初始 state 的时间。每个 interval

\[
I_i=\{t_{i-1}+1,\ldots,t_i\},\quad
m_i=t_i-t_{i-1},\quad
B_m=\sum_{\ell=0}^{m-1}c^{2\ell}.
\]

真实递推给

\[
x_{t_i}-c^{m_i}x_{t_{i-1}}
=\sum_{j\in I_i}c^{t_i-j}
  (\mathbf1_{h=1}a_j+g_jb_j^h+w_j).
\tag{M1.3}
\]

这些 interval 的创新集合互不相交，条件 innovations 独立 Gaussian，variance qB_m。左 state 是真实已观察 state（或已知初始化），不是 artificial block stationarity。

定义 T_π 的第 i 行在 I_i 上为 c^{t_i−j}/√B_m，其他位置为0。则 T_πT_πᵀ=I_N，P_π=T_πᵀT_π 是完整输入空间上的 orthogonal projection。其每个非 singleton interval 的秩一块为 wwᵀ/B_m；singleton 为 identity。

任务符号不在 covariance 中免费切换。下式来自共同物理 F_c 的真实 conditional likelihood，而不是 task demodulation 后保留原 covariance：

\[
G_H(\pi)=\frac1{2q}\inf_{z\in\mathcal Z_H}
\|T_\pi(a-gz)\|^2
=\frac1{2q}\inf_{z\in\mathcal Z_H}
\|P_\pi(a-gz)\|^2.
\tag{M1.4}
\]

输出状态的联合 covariance 仍为 qR_πF_cF_cᵀR_πᵀ，包含跨 block 项；条件转换使用前一个真实 retained state，故与该联合实验严格等价。

若末尾尚有未被任何保留 state 覆盖的输入槽，T 的那些列为0、P在那里为0。主定理用末尾继续hold支配无后续读数的moves后，可以限制在 t_N=H；此时 intervals覆盖全部输入节点。不会假定一个没有读数的terminal interval也提供创新。

## 5. Oracle、风险及控制中性

完整状态实验由共同已知可逆映射 x_j↦x_j−cx_{j−1} 转换为独立输入创新实验。故

\[
O_H=\frac1{2q}\sum_{j=1}^H a_j^2,\quad
O_H^{obs}(\pi)=\frac1{2q}\|P_\pi a\|^2,\quad
D_H^*=O_H-\max_\pi G_H(\pi).
\tag{M1.5}
\]

完整记录的 oracle 和整个完整-record composite experiment 在控制器比较中均中性。删除输出后 P_π(c) 随实际闭环 c 改变，健康像与fault像也同步改变，所以保留实验的风险可以改变。

同协方差的两个 convex Gaussian mean classes 在本有限维 polyhedral 路径类下有最近对，fixed calendar 的最佳 level-α最坏 power 为 Φ(√(2G)−z_{1−α})。若做 finite-risk inversion，Gaussian requirement 使用 ½(z_{1−α}+z_{1−β})_+²。这个接口不等于 ARL、随机最短报警时间或硬件尾概率保证。

## 6. 要检验的主张和范围

单内部 gap 删除 k 个 state outputs，创新 interval 长 m=k+1。已知 constant input contrast 的 full-minus-retained loss 为 d²κ_c(k)/(2q)，其中

\[
A_m=\sum_{\ell=0}^{m-1}c^\ell,\quad
\kappa_c(k)=m-\frac{A_m^2}{B_m}>0.
\tag{M1.6}
\]

候选 fixed-parameter sharp coefficient 为

\[
\frac{\sqrt2}{5q}\sqrt{\kappa_c(k)r}\,\eta^{3/2}.
\tag{M1.7}
\]

冻结本合同不预设候选为真。需要任意允许日历 converse 与同合同下的 terminal-balanced 达到对偶，同时处理 gap内g、全史 health、确定初始化、affine非反射cross、所有完整输入 nodes的weighted总和、以及真正的条件创新跨block连接。

只对稳定通道或控制器有限族作真实比较；一般控制器最优、受限硬件执行、adaptive/unknown onset、固定有限幅值盒、未知 c 和 additive state measurement noise不在本版定理范围。

