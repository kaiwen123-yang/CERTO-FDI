# M2S 可恢复分支的阶数补充 v1：诊断亏损 Θ(H²)

2026-10-07。独立补充，不修改已冻结的 M2S v1 合同或归一化定理。本稿依赖 m2s_problem_contract_v1.md（SHA256 80a5a5d643432f54f1a2d9f3dc7a9e374528358c18e10beb6b0e1ac1d5b9e7d5）及 m2s_singular_memory_theorem_v1.md（SHA256 8ff2de70274973e4a9e104b26a5bf4be14e0e742998f2c562f6023e6316ab431）的共支持、真实 interval projection、β 单调性、有限恢复容量与 affine cross 引理。状态：完整证明，待独立审查；精确检查只为辅助证据。

## 1. 范围、量词与结论

固定严格稳定 A_K、full-column G∈R^{d×p}、非零 B∈range(G)，令 f=G†B、F=||f||²>0。初始状态已知，fixed n₀≥1 个 prefix states 全读，g=+1、a=0；post j=1,…,H 的 a_j=ρ₀+ηj，ρ₀≥0，η>0。Holding g=±1，missing |g|≤1 已知。完整两侧健康路径各速率≤r/2、free level，r>0；差分 z 的所有相邻 input slots 满足 |Δz|≤r。

达到性使用原 v1 已明确的双向 exact-k 已知 profile 操作，可在任意预定起点与 holds 重复串接。Profile 可随预定起点而变化，证明仅使用长度 k 和 |g|≤1；没有数据适应或植物 reset。若只有单向或不可串接操作，上界不自动成立。下界对原更广的全部允许日历成立。

定义真正 latent input orthoproject P_π、θ=(fa_j)_j、H_gz=(fg_jz_j)_j。精确信息是 KL/半平方距离：
\[
G_H(\pi)=\tfrac12\inf_{z:\,|\Delta z|\le r}\|P_\pi(\theta-H_gz)\|^2,\qquad
O_H=\tfrac F2\sum_{j=1}^H a_j^2,\qquad
D_H^*=O_H-\sup_\pi G_H(\pi).
\]
每个 span 包含 missing inputs 及其 right retained input。所有 actual retained state covariance、真实初始化与完整 input nuisance 都保留。

**定理 R.** 若 β_k=0，存在只依赖固定合同参数的常数 0<c<C<∞、H₀，使对所有整数 H≥H₀，
\[
cH^2\le D_H^*\le CH^2. \tag{R}
\]
没有断言 sharp H² 系数。结合 v1 的 positive-β sharp 分支：该固定合同下 leading deficit 的阶数为 H^{5/2} 当且仅当 β_k>0；β_k=0 时阶数为 H²。r>0、η>0、held g=±1 是下界的实质假设。

## 2. 有限零罚 span 与正罚分离

对所有整数 ℓ≥0，写
\[
\beta_\ell=(\ell+1)F-M_{\ell+1}^{\top}W_{\ell+1}^{\dagger}M_{\ell+1},\qquad
M_m=\sum_{q=0}^{m-1}A_K^qB .
\]
β₀=0，β_ℓ 非减，β_ℓ/ℓ→F>0。令
\[
L_z=\max\{m\ge1:\beta_{m-1}=0\},\quad
b_+=\inf_{m>L_z}\frac{\beta_{m-1}}m>0. \tag{Z1}
\]
集合是有限连续初段；β_k=0 给 L_z≥k+1≥2。v1 的恢复容量还给 L_z≤ν_R≤d-p+1。b_+ 严格正：比值尾部趋于 F，剩余有限个正值有正最小值。

令 d_m=1_m⊗f。正交投影性质给
\[
\beta_{m-1}=0\iff P_m d_m=d_m. \tag{Z2}
\]
对 affine span 的中心 amplitude A≥0，v1 已证的统一交叉界为
\[
\|(I-P_m)\theta_m\|^2
=\beta_{m-1}A^2+2\eta A L_{1,m}+\eta^2L_{2,m}
\ge \beta_{m-1}A^2-C_K\eta A m, \tag{Z3}
\]
其中 C_K=Γ_K(Σ_{q≥0}||A_K^qB||)²<∞，L₂≥0。没有反射对称假设，也没有单独初始化人工 blocks。

## 3. 上界：离线累计 task 平衡日历

选固定 L>n₀+k+2，累计 M_t=Σ_{j=-n₀+1}^t g_j。Prefix 后 M₀=n₀。当前任务 s∈{±1}。保持 s 并逐槽读，直到 sM_t≥L；若剩余 post slots 至少 k+2，执行一段双向 exact-k move，随后切换到 −s；否则余下全部 hold 到 H。

第一次 threshold crossing 的 overshoot 小于 1。Move 仅改变 M 至多 k，所以新 opposite hold 开始时旧 sM 在 [L-k,L+k+1)。后续 opposite hold 到达阈值的长度在 [2L-k,2L+k+2] 内，特别至少 2 且固定有界。第一次 hold 至少 L-n₀>2。若末尾跳过 move，追加不足 k+2 个 held slots。故
\[
|M_t|\le L+k+2,\qquad\text{每个 post hold run 长度至少 2} \tag{U1}
\]
对足够大的 H 成立，且 endpoint H 被真实读取。Move 内同样有该累计界。整个算法只用已知 profile 和时钟。

记 post held inputs 数 N_h、moves 数 N_m，则 H=N_h+kN_m、N_h≥2N_m，真实 singleton spans 数 S=N_h-N_m。因此
\[
S\ge H/(k+2). \tag{U2}
\]
Prefix singleton spans 只增强此下界。此计数不可把 gap 的 right retained 点再次算 singleton。

固定 m=k+1。因为 P_m d_m=d_m，每个 move span 的 θ 投影误差只含 affine slope：
\[
\|(I-P_m)\theta_m\|^2
=\eta^2\|(I-P_m)(f(q-(m+1)/2))_{q=1}^m\|^2
\le \eta^2 F\,m(m^2-1)/12.
\]
Singleton 无损，moves 数≤H/k，所以全日历
\[
E:=\|(I-P)\theta\|^2=O(H). \tag{U3}
\]

令 h=(g_j f)_j、w=Pθ、p=Ph，λ_j=h_j^\top w_j。固定 span 长度和投影 contraction 给
\[
\lambda_j=F g_j a_j+e_j,\qquad |e_j|\le C_1,\quad e_j=0\text{ on singletons}. \tag{U4}
\]
这是逐 input slot 的 scalar weight；不是 retained-state 输出权重。令 post S_t=Σ_{j=1}^t g_j，(U1) 给 |S_t|≤2L+k+2。离散 Abel 恒等式
\[
\sum_{j=1}^t g_j a_j=a_tS_t-\eta\sum_{j=1}^{t-1}S_j
\]
给所有 partial λ sums 为 O(t+1)，全质量 N=Σλ_j=O(H)。Prefix 是固定长度、a=0，只改 O(1) 界。

Singleton P₁=I_p，故
\[
D:=\|p\|^2\ge FS\ge FH/(k+2),\qquad D\le F(H+n_0). \tag{U5}
\]
修复
\[
\alpha=N/D=O(1),\qquad v=w-\alpha p,\qquad Pv=v,\qquad
\sum_j h_j^\top v_j=0. \tag{U6}
\]
正交性给
\[
\|\theta-v\|^2=\|(I-P)\theta\|^2+\alpha^2D=O(H). \tag{U7}
\]
每 input |h_j^\top p_j|≤F√m（singleton 为 F）；因此修复后的所有 scalar partial masses 为 O(t+1)。对无幅值盒的完整 Lipschitz path class，零总质量的精确支持函数为
\[
h_{\mathcal Z}(\lambda')=r\sum_{t=-n_0+1}^{H-1}
\left|\sum_{j=-n_0+1}^{t}\lambda'_j\right|=O(H^2),\qquad
\lambda'_j=h_j^\top v_j. \tag{U8}
\]
该式由逐槽增量求和分部获得，free initial level 强制零质量；不零质量时支持无穷。

对任意 v∈range(P)，Fenchel/平方展开给
\[
G_H(\pi)\ge\langle v,\theta\rangle-\tfrac12\|v\|^2-h_{\mathcal Z}(\lambda'),
\quad
O_H-G_H(\pi)\le\tfrac12\|\theta-v\|^2+h_{\mathcal Z}(\lambda'). \tag{U9}
\]
(U7)–(U8) 得 CH²。Range(P) 使 v 是实际 retained full states 的可观测线性统计量（v1 已证明 supported Markov pullback）；不是内部 fast inputs 的额外数据。因此 D_H^*≤CH²。

## 4. 下界：每个日历的两分情形

终末未读 move 可改为 hold 到 H；观察支配意味着最优 sup 可限制至 endpoint H 被读取的日历。全 input spans 因而覆盖 post 1,…,H，prefix 单独 singleton。对全部这样的日历给一致下界，就给原 sup 的一致下界。

取
\[
\varepsilon=\frac1{4L_z+2},\qquad J_0=\lceil\varepsilon H\rceil. \tag{L1}
\]

### 情形 A：有正罚 interval ending t≥J₀

该 span 在 post affine 区，起点≥1，所以其中心 amplitude
A≥η(t+1)/2≥ηεH/2，即使 span 很长也成立。β_{m-1}/m≥b_+。H 足够大时 A≥2C_Kη/b_+，(Z3) 给
\[
\|(I-P_m)\theta_m\|^2\ge(b_+/2)mA^2.
\]
以 z=0 为 profile 候选，G≤||Pθ||²/2；故
\[
O_H-G_H(\pi)\ge\tfrac12\|(I-P)\theta\|^2
\ge \frac{b_+\eta^2\varepsilon^2}{16}H^2. \tag{L2}
\]
这个 H₀ 与日历/span 无关。

### 情形 B：所有 ending t≥J₀ 的 spans 都零罚

这些 late spans 长度≤L_z，且 P_m d_m=d_m。覆盖 inputs J₀,…,H，故 late spans 数
\[
J\ge (H-J_0+1)/L_z=(1-\varepsilon)H/L_z-O(1). \tag{L3}
\]
每个 late span 的 center amplitude A≥ηεH/2 对足够大 H 成立，因为其长度固定≤L_z。不是假定 span 首点恰等 J₀。

选择一个依日历的合法完整差分 path
\[
z_j=(r/2)g_j,\qquad \widetilde h_j=f g_j z_j=(r/2)f g_j^2. \tag{L4}
\]
|g_j-g_{j-1}|≤2 给 |Δz|≤r；b⁰=z/2、b¹=−z/2 分别速率≤r/2，prefix free level 允许此选择。Holding right retained input g²=1；gap 内无须 g 符号恒定。

对一个 late 零罚 span，θ=A d_m+η f centered-time。由 P_m d_m=d_m，
\[
\langle P_m\theta,P_m\widetilde h\rangle
=\frac r2 FA\sum_{q=1}^m g_q^2
+\eta\langle P_m(f\,centered\text{-}time),P_m\widetilde h\rangle
\ge \frac r2 FA-C_0, \tag{L5}
\]
其中 C₀ 仅依 L_z,F,r,η；右 retained g²=1 保证 Σg²≥1。第二项用 Cauchy 和 m≤L_z 控制。没有对 P 的 entries 假设正性。结合 (L3)：
\[
\sum_{\rm late}\langle P\theta,P\widetilde h\rangle
\ge \frac{rF\eta\varepsilon(1-\varepsilon)}{4L_z}H^2-O(H). \tag{L6}
\]

Early spans ending <J₀ 的 inputs 全在 j<J₀（prefix 可含），Σm≤J₀-1+n₀。Projection contraction、Cauchy 给每span cross≥−(r/2)F√{m Σa_j²}；再用 a_j≤ρ₀+ηJ₀，
\[
\sum_{\rm early}\langle P\theta,P\widetilde h\rangle
\ge-\frac r2 F\eta\varepsilon^2H^2-O(H). \tag{L7}
\]
Prefix a=0，fixed ρ₀,n₀ 只进入 O(H)。另外
\[
\|P\widetilde h\|^2\le\|\widetilde h\|^2
\le (r^2F/4)(H+n_0)=O(H). \tag{L8}
\]
把 (L4) 的单条合法 path 代入 inf，展开半平方：
\[
O_H-G_H(\pi)\ge
\tfrac12\|(I-P)\theta\|^2+
\langle P\theta,P\widetilde h\rangle-
\tfrac12\|P\widetilde h\|^2.
\]
舍去非负 oracle loss，(L6)–(L8) 得
\[
O_H-G_H(\pi)\ge
\frac{rF\eta}{2}\left[
\frac{\varepsilon(1-\varepsilon)}{2L_z}-\varepsilon^2
\right]H^2-O(H)
=\frac{rF\eta\varepsilon}{8L_z}H^2-O(H). \tag{L9}
\]
最后等式使用 ε=(4L_z+2)^{-1}。该 coefficient 严格正。

两情形给 c 可取小于
\[
\min\left\{\frac{b_+\eta^2\varepsilon^2}{16},
\frac{rF\eta\varepsilon}{8L_z}\right\}.
\]
所有 O(H) 常数仅依 fixed plant/contract，无日历依赖。于是 inf_π deficit≥cH²；与上界合并证得 (R)。

## 5. 证据、冻结边界与复现

正式辅助脚本 outputs/m2s_recoverable_order_checks_v1.py，报告同名 .json。它检查两个植物、三个 horizons 共六个新的 bounded-cumulative calendars、真实投影的 global mass repair、支持函数、实际 raw-state pullback 与 variance，验证这两个植物的 finite recovery lengths，并以 Fraction 检查 L_z=2,…,20 的十九个 ε bracket 恒等式。不是用有限样本代替 ∀日历证明，也不重跑 M2S v1 大表。

新的非对称局部修复证据另见 outputs/memory_asymmetric_repair_checks_v1.py/.json：六个 cases 的 N、α、repair energy 全非零；原 v1 镜面对称 cases 的 repair energies 全为零，不能声称已覆盖 nonzero repair。

本补充不改变 M2S v1 的 frozen o(H^{5/2}) 声明；只有独立审查接受本补充后才升级可恢复阶数。TeX 已打开并调用 built-in compiler，仍返回平台错误 “Unable to find standard directories for platform”；源码保留，compilation UNVERIFIED，没有安装 TeX。没有硬件、uniform controller-family 或 generic partial-observation 推广。
