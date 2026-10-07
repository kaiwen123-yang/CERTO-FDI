# D2-a 非线性余项改善的优先级判定 v1

2026-10-07。**不应为了把这组 point 行救到 90% 而单独开启完整 P6/D1.b/6R 分支。** 在相同 actual-direction statistic、已有均值证书、完整历史 Gaussian-comparator 方差和风险接口内，六个非退化 point 行即使移除全部非线性误差、事件预算，甚至进一步移除两侧 dynamic mean 损失，仍不能通过 PFA<.001、protected power≥.9 的充分接口。此结论改变“下一步是否必须投入 P6”的判断，不是再陈述原功效下界为零。

这不是 actual power 上界、point 不可检测定理、其他统计量或其他日历的全局下界。两个理想预算也不是重新认证的真实非线性实验。

## 1. 实际找到并冻结的数据

实际正式 Figure2 小表是 outputs/d2a_readout_figure_data_v1.json，**没有同名 CSV**。它保存 14 行精确有理端点，不只是显示小数；SHA256 为 8022e863c9b74179f01c3452e0028ab489aa84b7111823b8bd811aab2a816e97，snapshot UTC 为 2026-10-07T07:47:40.426945+00:00。其原 source 是 work/d2a_cert_review_bound_table.csv，当时 SHA 为 16f5b04e70d6246aee79a2186a6a2e197eb615fa0b5112c088302e59e6080f29。本评估不重新读取动态 live CSV。

固定子网格为 terminal-balanced，H={40,60,80,100,120,160,200}，每 H 两读出；未取 full400 未算行、未来 H 或选 best calendar。实际读取这 14 行对应的 12 个已有 CASE_RESULT.json 及小 receipt，所有 bytes SHA 与 frozen 小表一致；H40 两行没有 CASE 风险端点，按原 zero-direction 分类保留。所有原数均再次取 CASE 的 uniform_mean、uniform_variance、protected_risk 字段，与 frozen 小表逐项精确相等；小 receipt 仅绑定，未重新验证大 scientific witness。

协议 SHA 为 0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6。保持既有故障 ramp、healthy classes、physical/statistic direction 和 α/power 接口。子网格 H≤200 位于已接受 mean domain H≤600、实际 ramp≤.045；H160 实际 ramp=.012。

H160 three-block 独审 MD SHA ff64a112a69879ae12449d7ee79e1c66f4dedc7251c803180b3dc4c9fb63a8e8；mean-risk 独审 MD SHA 6a9cfb8009d2b424dfd29130c3d9140478531aeb74b326e917881eb35d7fe924。实际源 work/d2a_cert_case.py SHA b8bc6824a36ddfb021bbeded28a94ea8fca5833d6d170c3972f12512c6f63999，与该独审记录相符。

程序只 AST 读取源函数而不 import 科学模块。JSON 中 function_AST_source_segment_hashes 使用 ast.get_source_segment 的无末尾换行规范，不能与旧 inspect/source-block digest 混称同一算法；完整源文件 SHA 及精确端点绑定是此次一致性依据。

## 2. 两个预算，均保留统计量及 variance/history

记 m₀=mean_H0_upper，m₁=mean_H1_lower，d=mean_dynamic_loss_per_hypothesis，V₋=variance_lower、V₊=variance_upper。

- Budget A：仅设 error_H0=error_H1=event_failure_per_hypothesis=0；保留两侧 dynamic mean 损失。分离量 A=m₁−m₀。
- Budget B：进一步移除两侧已记账的 dynamic mean 损失。更乐观分离量 U=A+2d。

两侧 nuisance/healthy 支持、投影和权重 rounding 仍留；不是把健康输入当已知，也不是只删故障侧一份损失。程序还核对 U 与 fault_signal−2·health_support 的差只为 0 或 1/(5·10²¹)，来自原 outward rounding；U 略大的情况保留，对“改善无力达标”的判定更乐观。它没有把单侧 dynamic loss 再重复扣成总额。

每个 CASE 的 no_memory_truncation 和 no_covariance_reset 均为 true；cross_task_independence_assumed 为 false。variance 不因假想余项为零而重新计算，真实 moves 内创新和完整历史都保留。因此本预算分析不能解释成条件于 good event 后的真实 Gaussian power。

## 3. 不依赖浮点 quantile 的必要障碍

设 Q(t)=1−Φ(t)、φ(t)=exp(−t²/2)/√(2π)。对 t>0，分部积分给

\[
Q(t)=\frac{\phi(t)}t-\int_t^\infty\frac{\phi(u)}{u^2}\,du
\ge\frac{\phi(t)}t-\frac{Q(t)}{t^2},
\quad Q(t)\ge\frac{t}{1+t^2}\phi(t).
\]

以下都是严格有理支撑。由 unit circle 面积小于外接正方形面积，π<4，故 √(2π)<3。对 exponential Taylor 尾部，

\[
e\le\frac{65}{24}+\frac{1/120}{1-1/6}<\frac{11}{4},\qquad
e^{1/2}\le\frac{13}{8}+\frac{1/48}{1-1/8}<\frac53.
\]

第一式尾部从 n=5 起 successive term ratio≤1/6；第二式从 n=3 起 ratio≤1/8。所以 e^(9/2)<(11/4)^4(5/3)<100。Mills lower bound 立即给

\[
Q(3)>\frac{3}{10\cdot3\cdot100}=\frac1{1000},
\qquad Q(1)>\frac1{2\cdot3\cdot(5/3)}=\frac1{10}.
\]

因此 α<.001 所需标准 Gaussian q_FA>3；power≥.9 所需 q_power=Φ⁻¹(.9)>1。即使采用精确 Gaussian tails 而非已有更保守 Mills upper，现有 mean-envelope/variance 接口也至少需要

\[
\text{分离量}\ \ge (q_{\rm FA}+q_{\rm power})\sigma
>4\sigma\ge4\sqrt{V_-}.
\]

这只是在相同均值端点和方差界接口内的门槛，**不表示端点和方差极值在真实 healthy class 同时取到**，所以不能据此推 actual power 上界。若 U≥0 且 U²<16V₋，该接口无法达标；若分离量为负，当然更不可能通过同一充分接口。

程序以 Fraction 精确计算六行，均得到更强的

\[
5U^2<V_-,\qquad\frac{U^2}{16V_-}<\frac1{80}.
\]

所以最乐观 Budget B 的分离不足半个 comparator 标准差，而接口门槛超过四个。A≤U，Budget A 也全部受阻。没有 normal 库、double quantile、回归拟合或有限样本 MC。

## 4. 有限逐行结果

下面仅显示精确分离量的 10⁻⁶ 格 outward 区间；证明和 JSON 保存原 Fraction。每行 V₋ 都严格介于 .018110 与 .018111。

| H | Budget A 分离区间 | Budget B 分离区间 | 精确 B 障碍 U²<16V₋ | A/B 能否通过同一 90% 接口 |
|---:|---:|---:|---|---|
| 40 | 无风险端点 | 无风险端点 | 不评估 | 原 zero direction，不能称 actual power=0 |
| 60 | [−.003821,−.003820) | [.001109,.001110) | 成立，且 5U²<V₋ | 均不能 |
| 80 | [−.003207,−.003206) | [.005846,.005847) | 成立，且 5U²<V₋ | 均不能 |
| 100 | [−.000595,−.000594) | [.011068,.011069) | 成立，且 5U²<V₋ | 均不能 |
| 120 | [.003037,.003038) | [.016942,.016943) | 成立，且 5U²<V₋ | 均不能 |
| 160 | [.017612,.017613) | [.035809,.035810) | 成立，且 5U²<V₋ | 均不能 |
| 200 | [.036894,.036895) | [.058138,.058139) | 成立，且 5U²<V₋ | 均不能 |

实际 guarded_risk 源行 86–100 固定 null threshold z=25/8，并用 gap sign 选择 V₊/V₋。另一个精确检验为 U²<(625/64)V₊，六行全部通过；故这两个理想预算代入原 z 后仍为 negative gap，按原代码只能返回 zero protected-power lower bound。这里新证明的是**删除全部这些预算仍受阻**，并非把原 zero lower bound 重新包装成实际功效零。

average 原 deterministic 证书 H100/H120/H160/H200 已达标，且 PFA<.001；H60/H80 原未达标，H40 原方向退化，均保留。H160 是已独审的 earliest declared terminal average、至少三完整块代表例，不用为 point 对照强行获得成功才算这个现主稿例子有效。

## 5. 决策与复现

在此次明确目标下，P6 余项收紧不是必要下一动作：保持现有 average deterministic 代表证书，并优先完成已授权的 full400/最终编译与实际交付证据。不要仅为这六个 fixed point 行开完整 D1.b/6R 新分支。若以后真正要研究其他 statistic、更多时间、方向或控制选择，应另立目标和合同；此评估没有授权或预先断言那些途径结果。

复现入口：outputs/d2a_remainder_priority_assessment_v1.py。运行 python -S -B -X utf8 后仅 stdout JSON，与 outputs/d2a_remainder_priority_assessment_v1.json 对应。输入 SHA、12 CASE/receipt 小绑定、原 exact fields、两个 separation、strict obstruction margin 及有限 rational-tail 支撑均记录在 JSON。

脚本 fail-closed 核 frozen 14 keys、12 small CASE/receipt hashes、协议、原数一致性、两侧 budget 和 history flags；不 import 科学源、不解压/重 hash 大 witness、不执行 verifier、无科学/矩阵重跑、不修改参数/协议/主稿/root claims/live 输出。此交付不是新 paper principal theorem，也不关闭 full400 或整个 goal。
