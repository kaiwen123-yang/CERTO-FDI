# 固定终点推论独立审查 v1

2026-10-07。结论：**ACCEPTED WITH FIXED-SCOPE QUALIFIERS**。已完整读取候选 MD、TeX fragment、JSON，并实际核对 R7 主稿的模型、主定理、风险接口、显式达到性上界、零分支构造及 compact-SPD uniform 证明。未发现须修复的数学或量词缺口。这是既有信息定理在固定终点 Gaussian 风险下的推论，不是新的主要定理或 TAC readiness 判定。

## 版本与审查范围

| 输入 | SHA256 |
|---|---|
| fixed_endpoint_horizon_corollary_v1.md | 47e9f15a41e90ce71c262dce4c725ec3cc7bda41760fc865bb8d5302ce5ade0e |
| fixed_endpoint_horizon_corollary_v1.tex | 1992ab48efc850e4fd01ac11bc7260d6dc849f44dfc5696ed8b63ee2efdad2e0 |
| fixed_endpoint_horizon_corollary_v1.json | a3d814e8e1297f014186aff1b712bdd10b134dbf2748c561d53e39c6540f2117 |
| certo_fdi_control_memory_draft_v1.tex，R7 | a26c945e35a8da9c598a5b94fe34f528a19025a652b335a457c4f9fa65626eca |

既有依赖版本也吻合：M2S 主证明 8ff2de70274973e4a9e104b26a5bf4be14e0e742998f2c562f6023e6316ab431；quadratic-order 证明 5b04f87f23fbfe1d2bc1fb1fbb791e783a47e029c7cdf130e1c000dd22d0f4f1；compact bridge 89762501f1272eb8b0ed5150985225655e62f0681d24c62c41729750dbcdf351。此次依据实际 R7 的相关数学段落审查新推论，不重审这些已接受证明的所有旧计算表。

主稿定位：模型行 94–176；主定理及显式上界行 178–231；风险接口行 262–295；共同 SPD uniform 定理行 401 起；显式正分支证明至行 970；profile-aware 零分支上界行 972–1042；compact uniform 证明行 1151 起。候选 TeX 定位在以下各项列出。

不编辑主稿、候选或根台账；不编译；不运行 D2、旧矩阵检查或 SDK。新的有限 Fraction 核算仅核常数 36、9/100、8/25 和阈值 16·226−3609=7，不以有限计算证明全称命题。

## 1. Operational feasibility 与完整健康类

候选 TeX 行 7–25、57–64 正确继承已知 fixed-controller/common-support 模型。两侧健康类是完整 input clock 上各自相邻速率至多 r/2、自由初值的 scalar 路径；差类恰为速率 r 的完整路径，而非仅保留点、定初值或 boxed nuisance。主稿风险段落实际给出闭 polyhedral mean image、最近差及两条合法路径 b⁰=z*/2、b¹=−z*/2。由最近点分离和真实简单对的 Neyman–Pearson 下界得到每个实际日历的充要条件

\[
\exists\ \text{test}:\quad
\sup_{b^0}P_0(\text{reject})\le\alpha,\quad
\inf_{b^1}P_1(\text{reject})\ge1-\varepsilon_{\rm m}
\quad\Longleftrightarrow\quad G_{K,H}(\pi)\ge\Lambda_\alpha .
\]

固定 miss∈(0,1)、α∈(0,1−miss) 保证 quantile sum 为正，因此平方阈值没有丢失符号条件。检验阈值、日历及控制器均事先确定；反馈自身仍由真实状态因果产生，不能把“noise 前选 K”理解为 noise 前选择所有反馈动作。

Hdiag 按实际 π/test 的存在定义。下界只用 G* 严格小于阈值；上界用显式 π 的严格超阈值。没有在 sup G=Λ 时推定可行，也没有要求有限 H 的最优日历存在。Oracle 是 ideal healthy-subtracted white record，非仍带健康 profiling 的 full record。采用 z=0 和 orthoprojector contraction 得 Gπ≤O_H，对所有实际日历成立，故所有 H<Hor 均排除。

## 2. 精确 oracle、整数 overshoot、所有较早终点

候选行 67–117 的 cubic 与系数正确。令 B=Fη²/2、n=Hor，则

\[
O_H=\frac{F\eta^2}{6}H^3+
\left(\frac{F\rho_0\eta}{2}+\frac{F\eta^2}{4}\right)H^2+
\left(\frac{F\rho_0^2}{2}+\frac{F\rho_0\eta}{2}+\frac{F\eta^2}{12}\right)H.
\]

O_H−O_(H−1)=F(ρ₀+ηH)²/2>0。由整数最小性，0≤O_n−Λ<O_n−O_(n−1)=O(n²)，而非 o(n²)。对于 h≤M√n，cubic 余项由 nh²、h³、nh、h²、h 组成，一致为 O_M(n²)；固定 L 时余项 O_L(n)。这些界不能互换。

正分支 C>0，d=C/B。单参数极限保证尾部误差 e_n=sup_(H≥n)|D*_H/H^(5/2)−C|→0。这是收敛序列尾部的定义结果，不是另加 uniformity 假设。对固定 δ∈(0,d)，全部整数 n≤H≤n+floor((d−δ)√n) 同时满足

\[
G_H^*-\Lambda\le-B\delta n^{5/2}+e_n n^{5/2}+O(n^2)<0 .
\]

这里先让 n 大到 C−e_n>0，然后利用 H^(5/2)≥n^(5/2)。因此 lower 真正排除了全部更早终点，既未只核一个边界 H，也未假 G*_H 单调。

## 3. 正分支实际达到性与系数

候选行 119–133 使用主稿 sf:upper 所给实际 terminal-balanced π_H^ξ*，并非 D*_H 的上界替代存在性。ξ*=2β_kη/(Fr) 是固定正数，故 O_ξ*(H²) 可由一常数 M_K 控制。

在 H=n+ceil((d+δ)√n)，

\[
D_{K,H}(\pi_H^{\xi_*})\le CH^{5/2}+M_KH^2,\qquad
H^{5/2}=n^{5/2}+O_\delta(n^2),
\]

从而 Gπ−Λ≥Bδ n^(5/2)+O_δ(n²)>0。风险接口提供一个真实 test，可行整数集合非空，最小元素因此存在。上下夹逼再 δ↓0 得

\[
H_{\rm diag}-H_{\rm or}
=\frac{2C}{F\eta^2}\sqrt{H_{\rm or}}+o(\sqrt{H_{\rm or}})
=\frac{2\sqrt2}{5}\sqrt{\frac{\beta_k r}{F\eta}}\sqrt{H_{\rm or}}
+o(\sqrt{H_{\rm or}}).
\]

因子 2、η 幂次及 KL 半范数约定一致。floor/ceil 仅贡献 O(1)，对 √n 首项无影响。参数 r、η、K、G、k、prefix、ρ₀固定，miss 固定，只有 α↓0。

## 4. 零分支固定整数界及反加强例

候选行 135–151 的 M₀ 来自主稿行 979–1042 的真实 profile-aware calendar。该构造平衡全部已知 g，包括 gap profile；free-level 支持由精确零 scalar mass 处理。因此不是从 infimum 或 ordered ξ-limit 误取一个实际 O(H²) 日历。

选固定正整数 L=floor(M₀/B)+1 即可 B L>M₀。对充分大的 n，

\[
G_{K,n+L}(\pi^0_{n+L})-\Lambda
\ge (BL-M_0)n^2+O_L(n)>0.
\]

故 0≤Hdiag−Hor≤L。L 与 α 无关；finite early horizon threshold 不影响 α↓0。不能因 D*=Θ(H²) 就把时间差推成 Θ(1)：oracle 离散 overshoot 也是 O(n²)。

候选行 198–236 的 copy-plant 例独立核验通过。A_K=[[0,1/2],[0,0]]、G=B=e₂、n₀=1、ρ₀=0、η=1、r=1/100、k=1、gap g=0，符合原模型。两输入 span map 为 [e₁/2,e₂]，故 P₂=I₂；单输入也无丢失，β₁=0。每个有限 H 的 +,0,−,0 日历最后 missing 可改为继续 holding，因此 H 已读且所有 span≤2；未执行的下一次 switch 不构成日历约束。主模型没有要求每次 hold 至少两槽。

含 prefix 的累计 g 有绝对值至多 3。用 Abel 可得 |N|≤6H、D=Σg²≥H/2、|N/D|≤12；observable v=θ−(N/D)γ 精确零 mass，完整 partial masses≤18(t+1)。因此

\[
D(\pi)\le36H+\frac1{100}18\sum_{t=0}^{H-1}(t+1)
=\frac9{100}H^2+\frac{3609}{100}H<\frac{H^2}{4},\quad H\ge226.
\]

最后不等式差为 H(16H−3609)/100>0。取 Λ_H=O_H−H²/4=H³/6+H/12，则 O_(H−1)=O_H−H²/2<Λ_H<O_H。固定 miss 下定义 α_H=1−Φ(√(2Λ_H)−z_(1−miss))，确有 α_H↓0、α_H<1−miss、Λ_(α_H)=Λ_H。实际日历严格超阈值，故 Hdiag(α_H)=Hor(α_H)=H。此例反驳普遍的正整数增量或 Θ(1)，不否定 O(1) 本身；也没有修改 D2。

## 5. Joint compact-SPD 分支

候选行 153–176 仅调用主稿 sf:uniform 的共同 plant/B/Q≻0、健康类/fault/prefix/时钟/信息、非空紧致已知 gain set、每个 A_K strictly Schur、k(K)∈{1,…,kmax}。因此 F 和 O_H 对 K 共用，Cinf>0。它没有套到 rank-changing singular family。

主稿实际 uniform 证明给所有 K 的统一 converse remainder，且 explicit ξ_K packing/repair 上界也统一。故 sup_(H≥n,K)|D*_KH/H^(5/2)−C(K)|→0，可以同时排除所有 K/π 和所有较早 H。不能用 pointwise 极限代替这一 tail，但候选没有这样做。

对固定 δ>0，infimum 定义给固定 Kδ，使 C(Kδ)<Cinf+Bδ/2；在 n+ceil((Cinf/B+δ)√n) 使用该 Kδ 的实际日历，有至少 (Bδ/2)n^(5/2)+O_δ(n²) 的严格 margin。先 α 极限、后 δ↓0；无需 inf attained、k 连续、profile 连续或最优 controller 存在。允许事先选择已知 K，绝不等价于检验面对未知 K 的 worst-case robustness。

## 6. 风险尺度和可用边界

候选行 179–195 的 Mills 自推正确：对 t>0，tφ(t)/(t²+1)≤1−Φ(t)≤φ(t)/t，给 log(1/α)=t²/2+log t+O(1)∼t²/2。固定 miss quantile 只增加 O(t)，因此 Λα∼log(1/α)，Hor∼(6log(1/α)/(Fη²))^(1/3)。正分支 excess 阶为 log(1/α)^(1/6)。

这些是计划的整数固定 endpoint；不是 sequential stopping、ARL、expected stopping、未知 onset 或 data-adaptive calendar 的结论。若报告物理时间，差乘同一个固定 slot duration，不能混用 D2 的 nonlinear boxed/risk-certificate 域或有限 H≤600、ramp≤.045 证据。α→0 的渐近不能作为 D2 域无限延长的证明。

## 7. 静态集成与结案

fragment 14 个新 label 唯一，与当前 R7 无 collision；ref/eqref 均可在 fragment+R7 中解析。无 documentclass；低控制字节违规为 0、tab 为 0、孤立 CR 为 0。此为源静态检查，**未编译，不是 compile/layout PASS**。

发现的必须修复项：无。可在既有固定合同内纳入正文，最终 host 集成仍应保留本次绑定与正常编译/布局验收。此次接受不关闭原完整目标、full400、最终 ZIP 或四处 fulltext gaps。


## 8. 最终 fragment 局部差异补绑定（2026-10-07）

本附录仅接受下列新字节版本；上文初审输入 1992ab48… / a3d814e8… 及其定位继续作为历史绑定保留，不静默替换。附录前 review MD SHA 为 96b550bc572756d646bd989af8ff1e24f2bca4f8462c525dc9b163b685c883da，JSON 为 95803e0753589ced1cac35eedce7aa7abb03018e663255a51385f1e71353a887。

最终 TeX SHA256：d60b75fb81d3bb1da1e2e507588d41cd8442cb4531b222b8cf13a24fae853287。最终候选 JSON SHA256：9b20b8c19ff51aa1402fb93cbaba43a29252f4712c88e98c29cc8a9abce3a088。候选 MD 仍为 47e9f15a41e90ce71c262dce4c725ec3cc7bda41760fc865bb8d5302ce5ade0e；R7 主稿仍为 a26c945e35a8da9c598a5b94fe34f528a19025a652b335a457c4f9fa65626eca。

实际从两个源码重新生成 unified diff，确认恰有五组局部修改：positive coefficient、joint coefficient、positive strict-margin 三处 equation 分行；copy 例局部 repair scalar 从 a 改名为 α_rep，三个出现均一致；Λ_H=O_H−H²/4 追加已在原 MD 并已审的等式 H³/6+H/12。原 TeX/JSON 快照实测恢复到 1992ab48…/a3d814e8…，没有仅信任作者提供的 diff。撤去局部改名和显式等式后，去除 aligned/对齐符/分行/空白间距的源码规范串完全相同。候选 JSON 唯一变化字段为 fragmentSHA256。

显式 cubic 在 F=η=1、ρ₀=0 下确由 O_H=H³/6+H²/4+H/12 得到；不是新假设或新增量词。改名避免与 fault amplitude 混淆，未把 repair coefficient 当风险 α。全部固定健康类、actual-calendar/test 存在性、all-earlier-H 下界、固定整数 L、common-SPD 族及非 sequential/D2 边界完整保留。14 labels 仍唯一，host collision/unresolved ref 为零，低控制字节、tab、孤立 CR 均为零。

限定结论：最终 d60b75fb… TeX 与 9b20b8c1… JSON **ACCEPTED WITH THE SAME FIXED-SCOPE QUALIFIERS**。不重复旧证明、旧检查、D2 或编译；本附录仍不是 compile/layout PASS。主稿未编辑。
