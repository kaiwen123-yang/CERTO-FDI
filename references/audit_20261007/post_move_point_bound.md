# R1 移动后点读数：由现有状态管得到的条件上界

2026-10-07。本页只读取原始 R1 ZIP 的已有证书数组，进行输出线性支撑计算；没有运行包内代码、重算非线性轨迹、重证控制器或执行 D2-a 扫描。包内证书的完整验证由另一项独立验证负责。本页新增计算的有理数运算和向上舍入已检查；其物理适用性仍以继承证书成立为前提。

## 结果和适用时间

令 `n=0` 为一次移动结束、目标 hold 开始的时刻，快采样周期 `h=0.001 s`，`ρ=197/200`。在既有入段/hold 事件及参数域内，对真实第 4 关节点读数和承接同一完整创新历史的仿射比较读数，有

\[
 |Y_{4,n}-Y^g_{4,n}|\le\epsilon_{\rm pt}(n).
\]

| hold 快采样编号 n | 距离移动结束 | 向上取整后的点读数误差上界（Nm） |
|---:|---:|---:|
| 1500 | 1.50 s | 0.003399888498583189 |
| 1750 | 1.75 s | 0.003329342838665834 |
| 2000 | 2.00 s | 0.003327730233952521 |
| 2500 | 2.50 s | 0.003327692528745562 |

第一条完整 admitted slot 先经过 `1.5 s` settling，再经过一个 `0.25 s` slot，因此按槽末端点读数约定，对应 `n=1750`。原 admission 证书的 `first_passing_hold_step=1500` 表示**平均窗口的开始**，不能当成这个完整槽的末端。若实现把末端表示为最后一个窗口内快读数而有一拍偏移，先采用对所有 `n≥1500` 都成立的保守界 `0.003399888498583189 Nm`；最终必须把读数索引写进日历合同。

上表包络随 n 单调不增，但时间域限于继承事件所覆盖的 hold 段（原单过渡 admission 证书给出后续 250 s）；多段使用还要继承当前顶层的 source-return 与日历事件核算，不能把单段事件失败概率重复当成互相独立。

## 输出行和推导

保持阶段采用 frozen-M / no-C 控制器。状态为

\[
 X_n=(\omega(q_n-q_b),\ v_n,\ d_f(q_n-\ell_n)-v_n),\quad
 \omega=40,\quad d_f=500/3.
\]

对 `u_n-g_0(q_{m,n})` 的第 4 分量，包内已有精确行

\[
 Y_{4,n}=C_4X_n+D_4\nu_n+\zeta_n,\quad
 C_4=-M_{0,4:}[40I,80I,80I],\quad
 D_4=-(1600+80d_f)M_{0,4:}.
\]

真实系统与比较系统使用同一个当前创新，因此直接馈通和力矩噪声在差值中抵消。令 `r_e` 是移动末端有界 discrepancy 半径，`r_4` 是四个 250 步非线性阶段结束时的差值半径（这里下标 4 指第四阶段，**不是第 4 关节**）。继承证书给出，对 `n≥1000`，

\[
 |X_n-X_n^g|\le
 \rho^n H(r_e)+\rho^{n-1000}H(r_4)+H_aW_{\rm tail}, \tag{P1}
\]

\[
 H_j(b)=\sqrt{(P^{-1})_{jj}}\sqrt{b^\top|P|b},\qquad
 W_{\rm tail}=(0.00065,0.00062,0.00050,0.00033,0.00017,0.000075)^\top.
\]

因此新增点读数桥为

\[
 \boxed{\epsilon_{\rm pt}(n)=|C_4|
 [\rho^nH(r_e)+\rho^{n-1000}H(r_4)+H_aW_{\rm tail}].} \tag{P2}
\]

这里 `|C4|` 使用已保存的 M0 区间端点最大绝对值，因而也包住输出行系数的不确定性。证明只用线性支撑，没有把 discrepancy 当作独立噪声或高斯噪声。

在 `n=1750`，向上取整后的三部分分别是：移动 discrepancy 记忆 `0.000000000331758316 Nm`，hold 非线性过渡记忆 `0.000001649997874541 Nm`，持续尾项 `0.003327692509032977 Nm`。数值主要由持续尾项决定。

平均读数的记忆项还带有

\[
 \frac{1-\rho^{250}}{250(1-\rho)}.
\]

点读数没有这个因子，也不能使用平均读数的动量端点消去。因此上述点半径约为顶层 post-move average 半径 `0.0001682123399333 Nm` 的 19.8 倍，平均读数的均值、方差和风险证书不能直接移植过来。

## 系数的精确来源

原包：`C:\Users\ykw\Downloads\CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919_R1_20260926.zip`。

以下别名只是 ZIP 内目录缩写；逐层连接即可得到唯一的完整 member path：

```text
R = CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919/
C = R + input/CERTO_FDI_STAGE_D1_CALENDAR_RISK_20260919/
N = C + input/CERTO_FDI_STAGE_D1_NONLINEAR_ADMISSION_20260919/
E = N + input/CERTO_FDI_STAGE_D1_ENTRY_LTV_20260913/
H = E + input/CERTO_FDI_STAGE_D1_HOLD_REDESIGN_20260912/
B = H + input/CERTO_FDI_STAGE_D1_ROBUST_HOLD_20260912/
```

| 打开文件及字段 | 本页用途 |
|---|---|
| `N/audit/ADMISSION_CERTIFICATE.json`: `rho`, `entry.bounded_move_defect_radius`, `tail.start_step`, `tail.initial_nonlinear_gap`, `tail.W_candidate` | ρ、r_e、1000、r_4、W_tail |
| `H/audit/FROZEN_HOLD_CERTIFICATE.json`: `witnesses.acceleration_gain` | H_a，18×6 已存非负有理数矩阵 |
| `H/audit/DECAY_RATE_REFINED.json`: `candidates[rho="197/200"].P` | 同一 discounted metric P |
| `B/audit/TANGENT_LIFTS.json`: `geometry.M0[3]` | 第 4 关节的 M0 有理区间，构造 |C4| |
| `H/src/point_readout.py`: 第 7–9 行 | 已有点读数行及其线性支撑方式 |
| `N/src/certify_admission.py`: 第 88–102、206–223、225–229 行 | P、H、四阶段 r_4、尾项、平均窗口时间含义 |
| `N/notes/01_PROOFS_ZH.md`: 第 104–149 行 | 真实初值中间过程、移动 discrepancy 与 hold 非线性差值的分解 |

计算只取上述 JSON 字段。没有读取全部嵌套数据集；没有 import 或执行 archive 中任何 Python 文件。`P^{-1}` 由 `fractions.Fraction` 精确 Gauss–Jordan 求得，并检查 `P P^{-1}=I`。平方根用整数平方根给出向上取到 `10^-18` 的有理上界，并逐个检查平方不小于被开方数；幂与点积均使用有理数，表内结果也向上取到 `10^-18`。P 的正定性、共同收缩和 H_a 的动态意义沿用原证书前提，本计算没有重新证明这些前提。

可复查的独立脚本与逐字段哈希记录分别为同目录下 `post_move_point_support.py`、`post_move_point_support.json`。脚本只依赖 Python 标准库，从指定原始 ZIP 读取系数，无 `work/` 缓存依赖；可运行 `python post_move_point_support.py --zip "R1归档的完整路径"`，会在脚本目录写出 JSON。第二个文件还保存由平均记忆 prefactor 反推的更紧移动记忆项；上表统一采用较直接的坐标支撑式 P2，避免混用两套输出估计。

表内的保守界是确切有理数：`3399888498583189/10^18 Nm`（n=1500）与 `3329342838665834/10^18 Nm`（按 n=1750 的端点约定）。前者可作为有一快拍端点歧义时的统一准入点界。原证书的 P、管和事件前提仍必须成立；这里的严格算术不意味着独立完成了全部继承验证。

## 此结果没有完成的事项

这只是 post-move **point remainder radius**。D2-a 若改用点读数，还需要：按实际槽末端重建完整创新系数和有色协方差；点读数的真实均值/两类最坏间隔；参数域统一的误差预算与日历事件分配。不能把 S/M 两个平均方向的已存风险数称为点读数风险结果。本页也不提供 D1.b 三阶 ε3：P1 的 discrepancy 包含物理参数、故障、移动及非线性贡献，不能改名为三阶统计余项。
