# R1 理论源范围及 next_proofs 的模型连接

2026-10-07。本页源审查仅通过 Python `zipfile` 对原始 R1 ZIP 就地只读；未解压、未执行包内代码、未运行 verifier、未执行 D2-a 日历扫描。这是源证据审查及一项继承状态管的线性支撑计算。另一个独立核验环节现已完成实际 R1 包的完整 verifier 新运行，exit=0，详见 `r1_verification.md`；这里不重复计为本页执行。

结论：R1 足以把通用 `next_proofs.tex` 的 post-move point 半径具体化，新增条件上界见 `post_move_point_bound.md`：第一完整槽末端 `n=1750` 的上界为 `0.003329342838665834 Nm`。R1 也给出了实际 sampled controller、参数域、完整历史比较系统与入段管，因此能为 D1.b 定义实际变分问题；但包内没有完整六关节三阶参数管/ε3。协方差导数包和二阶 toy 算例都不能替代这一缺口。

## 精确包内路径及实际读取范围

归档：`C:\Users\ykw\Downloads\CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919_R1_20260926.zip`，目录清单有 463 个 member。

```text
R = CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919/
C = R + input/CERTO_FDI_STAGE_D1_CALENDAR_RISK_20260919/
N = C + input/CERTO_FDI_STAGE_D1_NONLINEAR_ADMISSION_20260919/
E = N + input/CERTO_FDI_STAGE_D1_ENTRY_LTV_20260913/
H = E + input/CERTO_FDI_STAGE_D1_HOLD_REDESIGN_20260912/
B = H + input/CERTO_FDI_STAGE_D1_ROBUST_HOLD_20260912/
O = B + input/CERTO_FDI_STAGE_D1_READOUT_20260911/
D = R + input/CERTO_FDI_STAGE_D1_COVARIANCE_DERIVATIVE_20260918/
```

这里的别名逐层展开是唯一完整 member path，未混用 D 下另一个 HOLD_REDESIGN 副本。

**全文读取：**本地 `outputs/next_proofs.tex`；包内 `R/README.md`、`R/MASTER_REPORT.md`、`R/notes/01_PROOFS_ZH.md`、`D/notes/01_PROOFS_ZH.md`、`N/notes/01_PROOFS_ZH.md`；另外为核对输出定义读取 `H/src/point_readout.py`、`E/src/sample_sequence.py`、`O/frozen/sampled_model.py`，以及小型 `H/audit/POINT_READOUT_CERTIFICATE.json`。

**只阅读相关行段：**`R/THEORY_NOTES.tex`、`D/THEORY_NOTES.tex`、`N/THEORY_NOTES.tex`；`H/src/second_variation_exact.py` 的模型、scope、矩和核构造段；`N/src/certify_admission.py` 的状态管、P、H、输出及证书序列化段。选段范围覆盖本报告公式，不代表三份 TeX 全文审稿。

**只查看结构或提取指定字段：**`N/audit/ADMISSION_CERTIFICATE.json`、`H/audit/FROZEN_HOLD_CERTIFICATE.json`、`H/audit/DECAY_RATE_REFINED.json`、`B/audit/TANGENT_LIFTS.json`。这四个文件的数值用途和字段清单见 `post_move_point_bound.md`，内容哈希保存在同目录的 `post_move_point_support.json`。没有读取全部 nested 数据、压力测试轨迹或全部 parametric model 数组。仅清单查看过的 `SECOND_VARIATION_EXACT.json`、`PARAMETRIC_MODEL.json` 不算内容审查。

## 已有物理和观测合同

`R/notes/01_PROOFS_ZH.md` 第 7–15 行固定 deterministic physical paths：

\[
|\beta|\le0.02\ {\rm kg},\quad |\dot\beta|\le0.001\ {\rm kg/s},\quad
0\le f\le0.75\ {\rm Nm},\quad |\dot f|\le0.003\ {\rm Nm/s}.
\]

快采样 `h=0.001 s`，槽长 `δ=0.25 s`，原始编码器/力矩独立高斯创新；参数路径不能按诊断创新选择。结论是对每条固定路径的统一概率界，并非所有路径共享一个同时高斯事件。

`N/notes/01_PROOFS_ZH.md` 第 17–27 行和 `E/src/sample_sequence.py` 第 30–54 行给出实际采样顺序：读编码器，使用旧 filter state 求速度，求 command，保持 command 传播连续 plant，正常更新 filter。状态/滤波器不重置。保持控制器为

\[
u=g_0(q_m)+M_0(q_b)a_c,
\]

移动控制器为

\[
u=g_0(q_m)+c_0(q_m,\widehat v)+M_0(q_m)a_c,
\quad a_c=\ddot q_d-1600(q_m-q_d)-80(\widehat v-\dot q_d).
\]

实际 plant 的显式模型接口为

\[
\dot q=v,\quad
M(q,0.4+\beta)\dot v=u-c(q,v,0.4+\beta)-g(q,0.4+\beta)
-\dot\beta A_p(q)v-e_4f.
\]

上述 plant 公式见 `E/src/sample_sequence.py` 第 30–34 行；该文件本身的 RK4 三路径 QA 是数值压力检查，不是流映射的区间证明。

`R/notes/01_PROOFS_ZH.md` 第 19–28 行的比较系统保留全历史：

\[
X_{n+1}=A_n(\theta)X_n+B_n(\theta)\nu_n+b_n(\theta),\quad
Y_n=C_nX_n+D_n\nu_n+\zeta_n,
\]

\[
\lambda_T=0,\quad \lambda_n=A_n^\top\lambda_{n+1}+C_n^\top w_n,\quad
g_n=B_n^\top\lambda_{n+1}+D_n^\top w_n,
\]

\[
V_\theta=q_\nu\sum_n\|g_n\|^2+R_\tau\sum_nw_n^2.
\]

实际平均方向在 250 个快读数上权重均分，move/settling 权重为零，但这些时段的状态和创新不能删掉；同一创新的 direct/state 通路须相加后再平方。换成点读数时只改变输出权重/索引，仍须重建该完整历史系数。

## 移动后点读数桥

`N/notes/01_PROOFS_ZH.md` 第 37–67、104–149 行把入段状态分成 `x_e=m_e+g_e+d_e`；其中 `m_e` 是比较均值，不必是真实非线性期望，`d_e` 可与 `g_e` 相关。移动噪声与入段高斯协方差始终保留。

同文第 104–112 行先引入具有真实入段初值的 affine auxiliary process，再与初值为 `m_e+g_e` 的 Gaussian comparator 比较；第 116–149 行给四个 250 步阶段和 tail。由此得到

\[
|X_n-X_n^g|\le\rho^nH(r_e)+\rho^{n-1000}H(r_4)+H_aW_{\rm tail},\quad n\ge1000.
\]

`H/src/point_readout.py` 第 7–9 行确认 hold 的真实输出是 scaled state 的线性函数，选第 4 关节行 `C4=-M0,4:[40I,80I,80I]`。因此乘以该行的绝对值就是一个具体 post-move point 界，而非再次套用平均窗口的误差。其数值、时间索引、条件和精确源字段已单列在 `post_move_point_bound.md`。

原 `POINT_READOUT_CERTIFICATE.json` 的局部 hold 界是约 `0.00426727559637605 Nm`；scope 明写同一 local hold event 与 initialization。这个旧值不能不经入段传递就移用到 post-move。顶层 average source/post 半径分别是 `0.00020947927106454` 与 `0.0001682123399333 Nm`，也不能统一使用较小者。

## D1.b：能接上的实际变分问题与尚缺的导数管

通用 `next_proofs.tex` 的噪声同伦 `ν_n↦λν_n` 应施加在上面完整 sampled controller/plant 上，保持同一 deterministic calendar、完整 filter state 和所有历史创新。固定物理路径后，令实际连续状态流的右端为 `F(t,z,u;θ)`；command 和 filter jump 也属于 sampled map。以真实零噪声受迫轨迹 `z^0` 为基准，而不是固定平衡点或平均比较均值。

对任一光滑联合映射，把状态、held command、当期创新都纳入自变量，其一至三阶 λ 变分满足链式结构

\[
\dot z^{(1)}=F_z z^{(1)}+F_u u^{(1)},
\]

\[
\dot z^{(2)}=F_z z^{(2)}+F_u u^{(2)}
+D^2F[(z^{(1)},u^{(1)})^{\otimes2}],
\]

\[
\dot z^{(3)}=F_z z^{(3)}+F_u u^{(3)}
+3D^2F[(z^{(1)},u^{(1)}),(z^{(2)},u^{(2)})]
+D^3F[(z^{(1)},u^{(1)})^{\otimes3}].
\]

数字控制律在每一步需对应传播 command 的一至三阶导数；hold command 仍含 `g0(qm)`，因此不能因为最终 hold residual 线性就把状态映射当成线性。move command 还含 `M0(qm)`、`c0(qm,vhat)`。物理路径导数 `βdot` 是 plant 的已有项，不能遗漏。

对于只在 hold 读取的输出，其输出映射本身二、三阶导数为零，这是可利用的实质简化。若实际全历史状态三阶同伦导数有分量管 `|∂λ³X_n|≤W_n`，则统计量的余项可收紧为

\[
 |R_3|\le \frac16\sum_{n\in\mathrm{hold\ reads}}|a_n|\,|C_{4,n}|W_n.
\]

但 R1 尚未提供这些 `W_n`，也未给实际 sampled maps 的统一一至三阶导数、全同伦区间 `λ∈[0,1]` 的管及实际六关节的 `b,Q`。现有状态管可作为构建共同状态域的候选；必须检查它对缩放创新和所有 λ 的事件/初值封闭性，不能由 λ=1 的结果自动宣布同伦管已证。共同 affine 收缩 P 也不能直接当成真实 nonlinear Jacobian 的收缩证书。

### 不能混用的两种已有“导数证书”

1. `D/notes/01_PROOFS_ZH.md` 第 27–51 行对**冻结 affine comparator 的载荷参数** `θ=β/0.02` 求导：`λ'_n=Aᵀλ'_{n+1}+(A')ᵀλ_{n+1}`、`g'_n=Bᵀλ'_{n+1}+(B')ᵀλ_{n+1}`、`V'=2q Σgᵀg'`。其 degree-8/复半径 2 展开和 Cauchy 余项主要控制载荷参数族；它不是实际 nonlinear flow 的噪声同伦三阶导数。第 73–97 行确实包含 `βdot` 和 slow-path 转移误差，但同样限于该比较族。
2. `H/src/second_variation_exact.py` 第 1–2、54–67 行直接声明只证明一个指定 rational polynomial comparison model。代码使用 **2 个状态、标量创新**，有理 A、B、H，时长 4/8/12；精确核与 Wick 等式可以验证二阶代数/尾界接口，却不是六关节流导数或 ε3。

`N/notes/01_PROOFS_ZH.md` 第 175–177 行也明确说移动 discrepancy 包含物理强迫、参数和非线性随机项，不能叫三阶余项；`R/MASTER_REPORT.md` 第 37、49 行把 full-6R D1.b 明确列为开放项。

## D2-a 可以和不能继承的范围

当前顶层的 S/M 已认证对象是固定实际日历、固定平均读数方向。S 42500、M 76000 个快步；M 的 4 槽 healthy prefix、10 次移动、184 个 admitted readings 和 156 个非零权重属于具体实验，见 `R/README.md` 第 58–63 行与 `R/MASTER_REPORT.md` 第 7–28 行。这些数字不是点读数风险，也不是所有日历的最优值。

用于下一步的合法接口是：固定一个读数约定和方向，计算真实均值支持区间、两类有色方差上下界、各读数 source/post remainder 半径以及原始日历事件成本，然后使用 `next_proofs.tex` 的两侧误差充分条件。第一条成功日历只能叫给定离散清单和证明协议中的 first success；不能跳过前驱，也不能直接叫 continuous optimum、minimax 或 earliest possible。新点半径本身不完成这些步骤。

顶层将漂移/故障路径域固定为原域，source-return 的 discrepancy 相对余量仅约 `0.0770%`；`R/notes/01_PROOFS_ZH.md` 第 70–90 行要求到达后至少 1750 个 hold 快步用于源管返回。不能用 admission 开始于 1500 步的事实缩短下一次移动前的完整 reading/return 合同。独立性与初始化也不能因跨窗协方差数值小而改写。
