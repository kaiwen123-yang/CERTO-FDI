# D2-a 均值与双侧风险独立审查 v1

日期：2026-10-07。**结论：冻结 D2-a H0/H1 模板下，新增点均值代数、两侧健康支持、方向尺度、采样时刻与风险符号通过本轮定向数学审查；继承非线性管、共同收缩和事件含义仍为明确前提。** 这不是重新证明全部 R1，也不是完整 D2-a 扫描或 H* 验收。没有改变物理、协议、生成器、继承源码或文献资料；没有轮询代理进程或重跑大递推。

新增的承重范围条件是：**必须用当前固定故障模板及 H≤600 保证 f≤0.045，证明两 mirror 任务均被旧 equilibrium radii 包住；不能凭 mirror 对称直接宣称旧 Es 覆盖所有 f≤0.75。** 本轮小区间检查已经补出当前范围的包含见证，详见第 4 节。

## 1. 绑定版本、实际阅读与未覆盖范围

协议 SHA256：`0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6`。读取 `outputs/d2a_protocol_v1.md`、`d2a_source_map_v1.md`、`d2a_certificate_progress_v1.md`，及以下实现版本：

|文件|SHA256|
|---|---|
|`work/d2a_cert_case.py`|`48b471e39dbd3e87aea3abc927d3b456066fb3942e37f5e7603b15a1d3f56bb2`|
|`work/d2a_cert_verify.py`|`823cec27f8df46dec2bccfbbfcadc54680b22b6061f73515ac6b14d97677ec00`|
|`work/d2a_core.py`|`d14383c0fed9f740682c8b4671f36bb59cd295941603f96988c30336a3ead4f9`|

审查进行中根代理更新了运行记录/atomic-write 包装；随后实际重读了 `mean_certificate` 和 verifier，均值/支持/风险调用的数学逻辑未变。该后续快照的 `d2a_cert_case.py` SHA256 为 `4878af7950a3e4d11627d0bb250063c7369ec9f75457a171b3abaefd2fa64930`，`d2a_cert_verify.py` 为 `97caad8eac82c5c36eef5e3a4d5c7e20e9e2df6a26f9e4a278208634fc10d6c7`。以下行号以首次读取版本为准；函数名与字段名为稳定定位。新的运行记录机制不在本次数学审查范围。

沿 source map 的实际 R/D/DH 与 C/N/E/H 链读取：`stage_context.py`；`risk_and_control.py`；`segment_interface.py`；`event_accounting.py`；`actual_direction.py` 的权重、伴随递推、验算、方差合成；D 的 `parametric_model.py` 与 `derivative_certificate.py`；DH 的 `frozen_hold_certificate.py`、`point_readout.py`；B 的 `hold_intervals.py`；O 的 `sixr_interval_contract.py`；N 的 `certify_admission.py` 与 `notes/01_PROOFS_ZH.md`；E 的 `sample_sequence.py`；C 的 `calendar_model.py` 与 `context.py`；新增 post-move point bound。读取相关 JSON 的实际字段和两条 H120 case 的结果/回执。

审查没有重算 31,000 步 degree-8 递推、全部 nonlinear first-exit/LMI/M-matrix 证书，或全部机械轨迹。共享区间运算库的正确性沿用 R1；这里只调用它做有限个 6×6 inverse 和输出行包含检查。两个新 standard-library 回执确已存在，且其中 `case_result_sha256` 均匹配所读 CASE_RESULT；这验证文件绑定，不能独自代替下述数学证明。

## 2. pre-step 读出与同一比较过程

`sample_sequence.py:39–53` 的顺序为：取得当前编码器，使用更新前滤波状态，计算 command 和 residual，记录本拍输出，随后更新滤波器并传播 ZOH plant。因此本项目读 `Y_n` 而不是传播后的 `Y_(n+1)`。

令 `e=q−q_task`、`X=(ωe,v,d_f(e−ell)−v)`，`ω=40`、`d_f=500/3`。保持 command 扣去同一名义重力后，其第四分量为

\[
Y^g_{4,n}=C_4X^g_n+D_4\nu_n+\zeta_n,
\quad C_4=-M_{0,4:}[40I,80I,80I],
\quad D_4=-(1600+80d_f)M_{0,4:}.
\]

D 的 `parametric_model.py:49–69` 正是这一行；本轮逐端点检查保存的 `PARAMETRIC_MODEL.json:C[0]` 包住从 `TANGENT_LIFTS.json:geometry.M0[3]` 构造的所有 18 个 C4 系数，结果为真。点读数没有额外平均系数。

固定完整确定性 β/f 路径后，Gaussian 创新的均值为零；完整历史与 move/filter memory 留在 `X^g`，故 `μ^g_(4,n)=C4 m_n`。N 的说明第 3、4 节明确区分 `X=m+g+d`、从真实入段状态启动的分析中间过程 `X^a`、从 `m_e+g_e` 启动的 Gaussian comparator `X^g`。新均值是 **Gaussian comparator 的确定性均值**，不是非线性真实状态的无条件期望；非线性差 `d` 的输出支持另付 remainder，允许依赖同一创新。

方差实现先把同一当前编码器创新的 state/direct 系数相加：`g_n=B_nᵀλ_(n+1)+Dᵀa_n`，再平方；move/settle 无读出权重仍传播 λ 和创新。`actual_direction.py:23–90` 的 `weights/proposal/verify_recursions` 支持点的一拍权重，不把点输出当平均 lift。初始化 Gaussian 分量为零，之后无 reset。

## 3. 点 equilibrium 恒等式及动态均值支撑

mirror 姿态满足累积角 `φ_b=π−φ_a`。因此 cos 项使 gp 翻号，sin 项的 K0/Kp 及质量内积的 M0/Ap 不变；外部关节 4 故障仍在物理同一方向。每个保持任务内令

\[
d_n=s\,g_p\beta_n+e_4 f_n,
\qquad L_{\beta_n}=M_0\omega^2+\beta_nK_p,
\qquad q^*_n=-L_{\beta_n}^{-1}d_n,
\qquad X^*_n=(\omega q^*_n,0,0).
\]

恒等式来自保持 tangent plant `(K0+βKp)e+d=u−g0(q_task)` 与 equilibrium command `(K0−M0ω²)e` 的消去；**K0 不能残留在 Lβ 内**。在平衡点上 v 与滤波差为零，βdot 惯量项也为零。由 `Lβq*=−d` 得

\[
C_4X^*_n=-\omega^2M_{0,4:}q^*_n
=d_{4,n}+\beta_n(K_pq^*_n)_4.
\]

这只是 instantaneous frozen equilibrium 的代数，不假设时变均值 `m_n` 真能跟随它。若 `|q*_n|≤Es`、`|m_n−X*_n|≤mbar(n)`，则逐点有

\[
|\mu^g_{4,n}-(s g_{p,4}\beta_n+f_n)|
\le {1\over50}|K_{p,4:}|Es+|C_4|mbar(n).
\]

`d2a_cert_case.py:119–151` 分开计算 equilibrium defect 与 `Cabs·state_tube`；点 branch 不调用 `mean_dynamic_per_slot`，没有使用动量窗口端点消去。

N 的 `certify_admission.py:75–80` 将 rate-only 见证定义为正小增益解，**不含 initialization**；`148` 的 entry.mean_radius 则是原 source mean 经移动齐次传播加 deterministic reference forcing 的界。新 point 管正确写为

\[
\bar m(n)=b_{rate}+\rho^nH(b_{init}),\quad
H_i(b)=\sqrt{(P^{-1})_{ii}}\sqrt{b^\top|P|b},\quad \rho=197/200.
\]

source 用 `b_init=(40Es,0,0)`；post 再加 `entry.mean_radius`。旧 P inverse 的上对角、上平方根和有理向上舍入保持界方向。以组内非零读数的最小 point age 1749 取单调上界，再乘该组实际方向 L1 范数，覆盖组内所有读数。source 与 post 分类按是否已有移动，返回 + task 后也属于 post。

## 4. 两条继承链同一性与必须保留的 mirror 范围

D→DH 的以下文件与 C→N→E→H 的对应文件 **逐字节相同**，不是凭标题假定同一：

|相对各 HOLD 根的文件|共同 SHA256|
|---|---|
|`audit/FROZEN_HOLD_CERTIFICATE.json`|`78f624da10146ff3b9ed5a095b3795451e4f089b0a04b2b6862b1b2811320439`|
|`audit/DECAY_RATE_REFINED.json`|`475624ec8b1db419ecae6a956c597074a5d8f63ceb51ced787c1da75e3e1f847`|
|`audit/POINT_READOUT_CERTIFICATE.json`|`4f7252f24b8e79c70422df2de2f6720eea73ebd636306dea99117ac376db19ad`|
|`input/ROBUST_HOLD…/audit/TANGENT_LIFTS.json`|`939915931de3b7404106dd472b6dee5ebfe8d58c4ef27e828ff487f7525fd79a`|
|`input/ROBUST_HOLD…/input/READOUT…/frozen/robot_input.json`|`1355d3c33420b8ebe289c092f58a7edec03010e112e47f40ae8783347141e841`|

`frozen_hold_certificate.py:109–112` 生成旧 Es 时使用 `d=gpβ+e4 f`、`f∈[0,3/4]`。因为 β 同时进入 Lβ，且 f 只取非负，mirror 的 `−gpβ+e4f` **不能仅由对称性自动推出同一 Es**。

本轮使用保存的 16 个 flow-beta interval cells、同一 outward interval M0/Kp、按原 robot_input 和 sincos 库重建的 gp，对

`abs(inv(M0*1600+βKp)*(s*gpβ+e4*[0,fmax]))≤Es`

做有限维包含检查，未重跑 plant/adjoint 递推。结果如下；比值是各 cell/坐标 enclosure upper 除旧 Es 的最大值，严格包含判断用 Fraction：

|fmax|task + 最大比值|task − 最大比值|判断|
|---|---:|---:|---|
|H120 模板 `9/1000`|0.2681716053127183|0.2682526323932148|两侧包含|
|全 D2-a 网格模板 `9/200`|0.30372431044488685|0.3037388216374808|两侧包含|
|更宽物理允许域 `3/4`|0.9999999999934639|1.0000837306260308|旧 enclosure 未直接支配 task− 第 16 cell 的首坐标|

全网格包含的精确最大比值为

\[
R_+=\frac{102094608476524939210343028899}{336142366500000000000000000000}<1,
\quad R_-=\frac{204198972606288391933745457097}{672284733000000000000000000000}<1.
\]

H≤600 给总终点 `(H+4)/4≤151 s`；冻结模板 `f=3/10000·(t−1)_+` 因此 `f≤(3/10000)150=9/200`。H0 的 f=0 亦被包括。这**补足当前 point/average 管使用旧 Es 的条件**。旧 Esd 的生成式使用 `|gp|βdot_bound+fault_rate+|Kp|Es·βdot_bound`，在 Es 已包含实际两任务 equilibrium 后，对 mirror 不变；实际 fault rate 0.0003 小于旧 0.003 预算。故旧 Esd、rate_only 支撑可以在这份冻结模板内沿用。

宽域一行只是 enclosure 不支配，并不证明真实轨迹越界或旧论文错误；也不关闭所有 `f≤0.75` mirror 物理路径的独立审查。后续扩大故障模板/时域时必须重新检查这条条件。

## 5. 平均均值公式与采样时间

`risk_and_control.py:32–51` 的平均支撑来自 tangent plant 动量恒等式：窗口平均的动态偏离由质量动量端点、βKp displacement 和采样名义重力项界住。`2/δ=8` 解释 `8*mean_momentum_radius+mean_gradient_radius`；K0 的采样间位置差被 `h|K0|v_cont` 支撑支付。它支持同一 affine/Gaussian comparator，并非把 nonlinear momentum remainder 当 Gaussian 均值。

该公式的静态健康项是**连续窗口平均** β。平均后的健康路径仍满足幅值盒和 `|βbar(t_next)−βbar(t)|≤rate·真实窗口平移间隔`；所以它进入用于方向支撑的 nodal 外包络，尽管这个 trace 集通常更小。新代码以离散平均采样中心记录时间，连续中心与离散中心相差共同 h/2，**相邻窗口平移间隔相同**，因此健康支持无需另付一个健康偏移；此处没有声称两种平均路径类相等。

固定 ramp 的连续窗口平均与 250 pre-step 样本平均相差 `κh/2=3/20000000` Nm。新 average branch 正确把这一误差按 `Σ|a_i|` 加入动态修正，而 signal 采用实际离散平均时刻。当前 onset 恰在槽边界；前缀均为无故障，之后各完整读数窗上的 ramp 仿射，故平均函数值等于函数在样本平均时刻的值。若将来 onset 放进窗内，此等价需要重新处理。

点索引是 `250(s+1)−1`，时刻 `(250(s+1)−1)h`，在槽末可用；没有新增 n=槽末 的 encoder/transducer 创新。post 首点 age1749 采用已声明 age≥1500 的 εpoint；移走前仍须完成1750步。每组 source/post 全史初始化独立于是否读出，未把零权重的前缀/移动创新删除。

## 6. 健康支持、方向舍入与双侧量词

令精确 raw residual `v=y−p`，设计集合 K(B,r) 对称；exact KKT 给

\[
h_K(v)=v^\top p=\sum_i|q_i|r\Delta j_i+B\sum_i|\eta_i|.
\]

`d2a_cert_verify.py:17–31` 检查 primal feasibility、stationarity、edge/pin complementary slackness 和 objective；generator 另核 `v·y−hK(v)=||v||²`。这些检查没有把 raw gap 错写成 ||v||。

实际 difference box/rate 是 `Btrue=2 gpmax·0.02`、`rtrue=2 gpmax·0.001δ`，γ=max(Btrue/B,rtrue/r)，于是 Ktrue⊆γK。单个假设健康类是差分类的一半。若 vr 为舍入残差、d 为其上范数，physical direction `a_i=s_i vr_i/d`，则

\[
\sup_{\beta^h}\sum_i a_i s_i g_{p,4}\beta_i^h
\le \frac{\gamma h_K(v)+B_{true}\|v_r-v\|_1}{2d}.
\]

所以 health 的 `/2` 有明确单侧来源；两假设可以各自选完整不同路径，H0 上界和 H1 下界分别支付同一 health。不是只付一次 difference budget，也未在两假设间共享 nuisance。

`normalize_raw` 用 Fraction 的 nearest-even 10^-12 舍入，只在精确 Σv=0 时修正最后分量；再以有理上平方根归一化，保证实际范数≤1。原始 KKT support 用 v，舍入余量用 `Btrue*rounding_l1/(2d)` 单列；均值、remainder、方差和 signal 后续都用同一实际 physical 方向。节点 Δj 包含 k 个缺測槽两端的 k+1 时间差；代码采样时刻检查未压缩 gap。

## 7. remainder、事件与风险封口

source/post nonlinear remainder 半径来源正确分开：point/source 来自同内容的 POINT_READOUT_CERTIFICATE；point/post 来自 age≥1500 的新支撑；average/source 与 average/post 使用冻结精确值。每侧 `b_h=Σ|a_i|ε_segment`。dynamic mean correction 是 comparator 的均值支撑，remainder 是真实−comparator 的路径误差，两者对象不同，均需支付；未以 Gaussian covariance 吸收 remainder。

事件预算按完整 N/M 日历 union bound，保留 entry ellipsoid，每假设各付 δ。它不是所有 β 路径共享的一个同时 Gaussian 事件，也不条件化 Gaussian 分布。可用性以前置 segment-component return 和 nonlinear event implication 为条件；本轮读到了这些前提及存储 PASS，没有重新证明全部 first-exit。

固定统计量 T 的比较均值 μ0≤m0、μ1≥m1，每侧 variance≤V+，在相应好事件有真实比较差≤b_h。阈值

\[
\tau=m_0+b_0+\tfrac{25}{8}\sqrt{V^+}
\]

由事件包含给 `PFA≤Mills_upper(25/8)+δ`。令 `g=m1−b1−τ`。g>0 时，使用上标准差会缩小 standardized gap，因此

\[
Power\ge 1-Mills_{upper}(g/\sqrt{V^+})-\delta.
\]

g<0 时同向代入 V+ 不合法；当前实现最终强制 power_lower=0、miss_upper=1，保持保守。g=0 时 Mills(0)=1 亦只给保守 0。两个假设共享的 V+/δ 是覆盖全部允许确定性 β 路径的统一上界，允许各侧真值不同；代码没有假设同一 nuisance、相同实际 covariance 或两侧事件独立。

Mills 的有理下取 score、π 下端/平方根下界和指数上界方向正确。**一项非承重实现边界：** `risk_and_control.py:mills` 在入口检查 x≤0 之后将 score 向下截到10^-8；若 `0<x<10^-8`，会变成0并除零。当前两条 H120 score 没有这一情况，因此不影响所读数字；更广扫描应在新 wrapper/风险函数中将截零后的 score 直接返回保守1，继承源码保持不变。若已遇到此边界，保留失败/未计算行，不能删行或继续用未认证值。

## 8. 本轮已读的两条 H120 结果及准确解释

|量|average250|point_last_fast_read|
|---|---:|---:|
|case status|CERTIFIED_TARGET_PASS|VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET|
|V+|6.707394193949089e-7|0.018131329975796643|
|V+/认证 nominal 下界|1.0028910017365418|1.000587124689431|
|comparator health support /侧|0.010317906286114138|0.01039337030208965|
|dynamic mean loss /侧|0.0006531678378915718|0.006952402019068342|
|nonlinear remainder /侧|0.00087461118293476|0.017780164622732283|
|protected gap|0.011132514958694141|−0.45331242649371334|
|PFA upper|0.0009671225919270282|0.0009671225919270282|
|power lower|0.9999999999793365|0|
|event upper /侧|2.0663426223280132e-11|同左|

两 case 的 CASE_RESULT 哈希分别为 `ea3d478e7797533a0b0c3967a7293a4ac305010c9c6d00dca30da141aedcd46f`、`7d9b216a2049a9d13665fbd0d35c43a960f9584c4312d6e4a2bc16b9e5a4472e`，均与所读标准库回执一致。回执中的 `independent_point_mean_proof_review_completed=false` 是生成时状态，本轮不修改它；可由根代理将本报告作为新增独立数学审查证据链接。

本轮新增均值代数审查支持在上述继承条件和固定模板内接受 average 的风险通过、point 的风险目标失败。point 的 0 是充分保证退化，不能改写成真实 power=0、物理不可行或信息论不可检测。两个方差比通过1%流程门也不证明 iid。H120 是已认证实例，不是首个成功 H*；全部更早网格/族成员仍须完整处理。

下一步只需保留本报告的模板范围条件，给 tiny-positive Mills score 加保守分支，再按冻结协议继续全表；无需为本次均值审查重跑相同 R1 完整 verifier 或两个未改 case 的大伴随递推。
