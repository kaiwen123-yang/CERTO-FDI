# 整稿内部反方审查 v1：固定合同的诊断信息理论稿

审查日期：2026-10-07。目标期刊：IEEE Transactions on Automatic Control，理论优先的 Full Paper 技术准备稿。审查者：`manuscript_full_review`。本报告只新增本文件，不修改主稿、冻结证明、检查程序或根台账。

**有限结论：当前文件已经构成可送技术预审的完整理论工作稿，但还不是可确认提交的稿件。本次全文读取未发现冻结合同内必须改变主要定理结论的承重数学反例；发现一项确定的主张同步错误及若干可直接修补的证明定义/呈现缺口。文献比较、IEEE 双栏排版和真实编译/PDF 验证仍未闭合。这个判断不等于全部理论已获外部验收，也不预测录用或给 TAC 评分。**

## 1. 版本、实际阅读和审查方法

本次现场 SHA256 为：

`6c7bcf574450f49bffe4ad127ab89ff7ada0afbc3e90e1e9eef59b971515f367`

对象为 `outputs/certo_fdi_control_memory_draft_v1.tex`，revision 3，59,880 bytes、1,265 行。已实际顺序读取 **1–1265 行全部内容**，包含 preamble、摘要、导言、全部正文定理/证明、完整 Appendix 和 10 项 bibliography。本报告行号与 label 均绑定这个 SHA；任何后续修改都需要新版本绑定。

采用 `C:/Users/ykw/.codex/skills/academic-research/paper-review/SKILL.md` 的批判性阅读、维度核对、major/minor 精炼和英文正式审查流程。根据任务要求，原技能的评分预测步骤改为定性证据判定，不使用会议评分量表或录用概率。

定向核读的既有依赖包括：`m2_independent_review_v1.md`、`m2s_independent_review_v1.md`、`m2s_recoverable_order_review_v1.md`、`compact_controller_uniform_review_v1.md`、`manuscript_integration_review_v1.md`、`m2s_regime_integration_review_v1.md`。也读取了 `d2a_protocol_v1.md`、`d2a_mean_risk_review_v1.md`、`d2a_source_map_v1.md`、`d2a_partial_first_success_v1.md`、`feedback_prior_art_fulltext_review_v1.md`、`control_design_prior_art_extension_v1.md`、`tac_venue_check_20261007.md` 和 revision 3 的 compile/status receipt；对旧 novelty audit/matrix 和当前状态文字只作相关段定向核对。

旧报告的旧主稿 SHA/行号没有直接充当 revision 3 的全文验收。它们提供有限依赖证据，本轮另把实际合并文本中的公式、量词、范围和证明连接逐段核对。没有重跑旧数值检查、D2-a 大递推/400 行扫描，没有开展新理论方向，没有重新取得或重审 17 项文献的原始全文，也没有尝试编译或修复编译运行环境。

## 2. 核心贡献及定性维度判定

这一稿的可守住主线是：**在固定、已知、无诊断旁路的稳定线性 Gaussian 输入实验中，完整健康漂移与真实缺测时钟产生一个可由 missing-span constant-force score loss 分类的日历信息亏损；正损失分支有匹配首项，零损失分支有匹配阶数；共同 SPD 的紧致控制器族允许联合渐近优化。** 最近凸均值集合的 Gaussian 风险接口、共同可逆变换和既有闭环主动诊断都作为工具或前史，不宜升级为本稿独占贡献。

|维度|定性判定|理由与限制|
|---|---|---|
|方法健全性|冻结合同内可作技术预审|真实 predictor/projection、两侧完整 scalar 路径、positive/zero 分支以及共同-SPD uniform 桥梁在当前文本中连贯；未发现改变主结论的反例。|
|写作清晰度|需修订|导言错误暗示 zero 分支也有 exact coefficient；附录块中心等符号未定义；同一主线被两套模型和较长重复证明分散。|
|贡献定位|有限支持，尚未完成最终新颖性判定|当前 17 项定向对照不能证明穷尽前史；4 项全文缺口保留，其中 2012 两篇是反馈/AFD 直接近邻。|
|验证严谨性|有限精确核对和单例证书定位正确|旧对称检查的零 repair 覆盖被明确披露；非零补充单列。非线性例是独立 comparator 的充分风险证书，未称 exact M2 实例。|
|评估完整性|足以支持当前窄主张，不能升级为完整扫描/硬件结论|H120 两个 finished cases 可作为示例；完整 D2-a、干净交付包验收、article PDF 和真实页数仍未完成。|

### 2.1 具体优点

1. **S1：全史和物理时钟始终一致。** 第 143–159、293–305 行保持已知零初始化、健康初值自由、固定无故障前缀、每侧 rate `r/2`、所有 missing input slots 上持续限速；Nature 在 deterministic calendar 后、noise 前选择完整路径。`eq:converse` 和 `m2sreg:zerocase` 都用一条完整合法健康差分并由两侧 `±z/2` 实现。
2. **S2：真实 retained experiment 而非删零/reset 近似。** 第 168–193 行的实际前一 retained state predictor 保留动态历史；`m2sreg:interval`、第 368–438 行在 singular 情况通过 common support/SVD 和 rowspace invariance 得到真正的 projection。没有使用错误的 pseudoinverse congruence。
3. **S3：正分支的 converse 与 attainment 针对同一日历类。** `eq:lower`、`eq:upper` 和 `m2sreg:symmetricupper` 中 gap norm loss 只 split 一次；上界方向位于真实 innovation range，weighted scalar mass 精确为零，局部 auxiliary levels 不冒充可拼接的 primal 健康路径。
4. **S4：零损失不是零代价。** `m2sreg:score`/`m2sreg:dimension` 只恢复 constant scalar score；`m2sreg:slopeloss` 保留 affine slope loss，`m2sreg:zero` 给 Θ(H²)，并在第 344 行明确不声称 sharp H² constant。
5. **S5：控制比较保持共同物理输入。** 第 743–760 行相同 `A,B_u,B,Q` 的两个 gain 只改变 `A_K`；完整 oracle 保持不变，且第 759–760 行排除 hardware-optimal 解读。`thm:uniform` 另证共同余项，没有把 pointwise little-oh 直接取 sup。
6. **S6：边界披露实质有效。** 第 72–77、156–162 行区分 controller 与 diagnostician 的状态权限；第 776–777、887–888 行限定 homogeneous settling；第 940–963 行隔离 nonlinear comparator、mirror 范围、point 下界零和未完扫描；第 965–976 行保留 fixed-rank 与共同-SPD uniform 的边界。

## 3. 必须修订和提交前必须关闭的缺口

下面区分“修正文稿即可闭合”和“最终提交前还缺验证/比较”。不是要求开展新数学方向或重跑已通过的数值表。

### R1 — 导言误把正分支的 exact coefficient 和日历归给零分支【确定的主张同步错误】

**位置：** 第 52–60 行，尤其第 57–60 行；对照 `m2sreg:theorem`/`m2sreg:zero` 第 339–345 行，以及第 584–653 行的 zero upper construction。

导言先说 fixed lower-rank image 可保存 score、optimal deficit 为 quadratic order，随后用 “Its exact leading coefficient” 和 “The same coefficient” 连接 linearly increasing hold lengths。最自然的语法先行词是刚介绍的二次阶分支；然而该分支明确没有 sharp H² coefficient，其已证明上界使用 profile-aware bounded cumulative task coefficient 的 calendar。正分支才使用参数 `xi*` 和线性递增的 symmetric block half/whole holds。

这会导致摘要/导言对承重结果的强度超过 theorem，而不是仅有措辞偏好。无需改定理，可把第 57–60 行替换为：

> The quadratic branch is an order-sharp result; no leading quadratic constant is claimed. In the positive-score-loss branch, the exact leading coefficient depends on the missing-span information penalty and the healthy drift rate, and is attained by a terminal-balanced calendar with linearly increasing hold lengths.

保留 `m2sreg:zero` 的 constants only fixed-contract、无 controller uniform/no sharp constant 限制。摘要第 18–20 行目前已经正确区分 leading sharpness 与 quadratic order。

### R2 — 明确定义上界构造的块起点、中心、长度和累计权重【证明可审查性缺口，可局部修补】

**位置：** Appendix 第 1101–1112 行；第 1136–1140、1164–1171 行；对应 `eq:baseline`、`eq:support` 和两 gap-center 公式。

第 1111 行使用 `x_ell+c_ell` 定义 `A_ell`，但全文没有定义 `x_ell` 和 `c_ell`。第 1166/1171 行使用 `L_ell` 而未定义；第 1138/1168 行用 `Q`/`Q_j` 指 partial sums，却未明确其 scalar 定义，且全稿 `Q` 已表示 process covariance。读者无法独立确认关键 `1/2` center offset 的来源。

对当前真实 block slots，以下定义直接补足原证明，不改变系数：

\[
x_\ell=\sum_{i<\ell}2(n_i+k),\qquad
L_\ell=2(n_\ell+k),\qquad
c_\ell=n_\ell+k+\tfrac12,\qquad
A_\ell=\rho_0+\eta(x_\ell+c_\ell).
\]

`x_ell` 是 block 左边界之前的 post input 数，局部 inputs 为 `1,...,L_ell`；center 是这些 inputs 的 midpoint。两 gap spans 均含右 retained input，故中心相对这个 midpoint 正是 `1/2 ± (n_ell+k)/2`。这验证现有 pair loss 公式可保持，不能随意把 midpoint 写成 `n_ell+k`。

再明确 `z^{+,L}`、`z^{+,R}` 的局部索引为 `i=1,...,n/2`，`z^-` 为 `i=1,...,n`；将 partial sum 改名如 `q_t(lambda)=sum_{j<=t}lambda_j`，在 full-clock support 公式首次出现处定义。用 `q_t(lambda^0)` 解释 baseline sign/saturation，避免与 covariance `Q` 混淆。这属于必要的证明定义完善；未发现因此需要重做主定理。

### R3 — 非线性风险表需要自足的统计接口和证书入口【保留数值主张时必须补】

**位置：** 第 934–963 行，尤其第 944–957 行。

H120 数字与本次所读 `d2a_mean_risk_review_v1.md` 两条 frozen case 相符；point 的 0 已正确解释为充分保证未过。正文却没有给出目标 `PFA<10^-3`、power `>=0.9`，也没有定义 “Protected gap”、实际固定方向、两侧均值/误差/event obligations 或可定位的 certificate。于是 reader 不能从稿件本身判断表内数字意味着什么，更不能以 §4.1 的 exact common-covariance Gaussian 最近对公式替它封口。

当前 certificate 的接口可以简写为：对固定 statistic `T` 和各侧 comparator，`mu0<=m0`、`mu1>=m1`、variance `<=V+`，好事件上真实/比较统计量误差 `<=b_h`，每侧坏事件概率 `<=delta_h`。阈值为

\[
t=m_0+b_0+(25/8)\sqrt{V^+},\qquad
g=m_1-b_1-t.
\]

`Protected gap` 就是这个 `g`。PFA 用 Gaussian tail upper 加 `delta0`；`g>0` 时 power lower 是 `1-tail_upper(g/sqrt(V+))-delta1`，`g<=0` 时当前证书只返回保守 0。事件可依赖同一 innovations，推导用事件包含/union bound，不声称条件 Gaussian。

正文至少应给这段接口、风险目标、H120 总终点时间 `(120+4)*0.25=31 s`，并指向精确方向、mean/remainder/event/variance budgets 和标准库回执的可交付附录/补充材料。数字来自 source-bound exact certificates，显示值应加近似符号或注明仅展示舍入值；point 的 `0.0181313` 是实际 `V+=0.018131329975...` 的向下显示舍入，不应直接作为可重新运算的上界端点。

本条不要求为单例新增完整 400 行结果。若只保留这个独立例，现有两条证书可以支持它；若后续增加 all-family H* / shortest-time 主张，则另需完成相应全成员、前驱闭合和交付包验收。不得把后来 H100 等部分 first-success 状态自动写入此冻结 H120 单例的主张。

### R4 — 最近邻全文与正式引文定位仍有缺口【最终提交前的贡献定位缺口】

**位置：** Related work 第 79–132 行、bibliography 第 1215–1264 行；已有 `novelty_audit_v1.md`、`control_design_prior_art_extension_v1.md`、`feedback_prior_art_fulltext_review_v1.md`。

现稿第 110–112、124–126 行有限 coverage 声明正确，也没有 “first” 主张。当前证据为原 M0 15 项、11 项全文定向检查/4 项全文缺口，再加 M2 的 Kim ECC2013 和 Raimondo Automatica2016 两篇 primary 全文定向核查；**17 项有限对照不是 17 篇完整逐行审查，也不是已形成与当前 M2S/uniform 定理逐项同合同的穷尽比较。**

四项全文缺口是 Esna Ashari/Nikoukhah/Campbell 两篇 2012 反馈/AFD 近邻，以及 Cheng–Steinberg 1991、Coster–Cheng 1988 两篇趋势/换级设计近邻。前两篇本轮所读追索报告中 23 个新入口仍未取得全文；“未取得”不能变成 “不覆盖”。原 15 项 matrix 的合同是 M0，不能把其 NO_DIRECT_M0_COVERAGE 原样作为本稿 M2/M2S/uniform 的历史排除证据。

提交前应把 **sharp calendar law / preserved-score capacity / compact common-SPD uniform bridge** 这三类具体贡献与最接近的可读原始结果对齐，并对上述缺口维持未审状态或取得可核全文后有限核查。不能要求穷尽世界文献，也不能在这些直接近邻仍未读时把 “no first claim” 当作已经完成创新性论证。全文取得失败并不使其余技术工作停止。

正式参考文献还需 source-bound 的 IEEE metadata 清理。当前手工 bibliography 10 项均在正文被引用；本轮没有发现必须依靠一个未定义 cite-key 才能成立的主论证。`convex` 支撑经典最近对工具，而本稿另证明 unbounded polyhedral attainment 和两侧实现，因此没有盲用 compact-set 前提。正式稿宜提供具体节/命题定位，并定向引用已经读过的 Ossenkopf 对称 real-dead-time 优化等最接近的来源；不能只把未提交的“accompanying literature audit”当作读者可访问的相关工作论证。缺少所有 17 项的 bibliography 本身不构成错误，关键是与正文实际比较相匹配。

### R5 — 真实编译、PDF 与 IEEE 版面尚未验证【明确的提交验收缺口】

**位置：** 第 1–3、8、28–34 行；`manuscript_compile_status_v1.json`、`manuscript_revision_3_receipt.json`、`tac_venue_check_20261007.md`。

当前是 `article[11pt]` + geometry 的技术稿，作者为 placeholder，尚非 IEEE 双栏。现有 compiler 对 revision 3 返回 `Unable to find standard directories for platform`，没有 source diagnostics，`compilation_verified=false`、`pdf_verified=false`。已有 lexical/ref static PASS 不能替代编译；平台目录失败也不能推断数学/TeX 源码必然错误。

提交前必须取得一次成功编译的真实 article PDF，核显示、ref/cite 编号、长公式/表、实际双栏页数、作者信息与适用 venue 格式。官方要求按现有 `tac_venue_check_20261007.md` 有限定位；提交时仍须重新核当时规则。现在没有页数证据，不能凭 1,265 source lines 判断超过或符合 TAC 页数。也不能假定 supporting file 能承接所有承重证明后自动满足篇幅规则。

## 4. 非阻断改进建议

### N1 — 合并论文主线，减少 SPD/M2S 的重复定义和证明

第 134–216 行先给 SPD 模型/定理，第 279–438 行重新建 M2S，随后 M2S positive proof 第 446–582 行重复大量主 Appendix 第 989–1213 行。把全文完整 proof 留在工作稿有审查价值，但正式版本会使 reader 在到达 control consequences 前绕过 460 行 rank-sensitive proof，难以判断独立贡献究竟有几项。

建议既有内容重排为：一个 common-support 模型和主 two-regime theorem；SPD strict-positive 作为特化；共用 affine/tent/repair 核心证明只写一次，singular 替换和 zero-branch 另分；controller uniform 保留为共同-SPD 的单独推论。不要用删掉承重 proof 代替这种压缩。此建议无需新研究，也不意味着当前重复证明有数学矛盾。

### N2 — 给 zero branch 一个现有可手核例

`m2sreg:capacity` 当前完全抽象，读者需在 3 页以上证明中理解为何 stable plant 的 singular image 可以保留 score。已有独审的 partial-mode 例可以以短段/小示意纳入：三维 nilpotent shift，`G=[e2,e3]`、`B=e2+e3`，`H2=[e1,e2,e2,e3]`，constant score 无损而 rank `H2=3<4`、centered affine slope 仍有损。它直接解释 “score preservation != all-input recovery”，比增加新算例更有读者价值。这里只建议重用既有冻结例，未在本次重算或声明新的复现。

### N3 — 显式同步 bounded-even 的两个分支结论

导言第 69–70 行说 bounded-even 同时保留 positive leading law 和 recoverable quadratic order；`cor:even` 第 901–903 行仅明示 `thm:main` 的 positive coefficient。当前 contraction proof 使用真实 input orthoproject，对固定 common-support singular 情况也可用。因此可补一行：在 `m2sreg:zero` 条件下，同一固定 `E`、含零的实际 Minkowski envelope 给

`D_odd* <= D_mix* <= D_odd* + O(H²)`，故保留 Θ(H²)，不保证 H² coefficient 不变。

该结论可直接由已有证明得到，不是需要新增理论的缺口；但把适用的 projection、实际差集和 theorem label 写明更容易与导言对应。若 `E_H` 没有 convexity/closedness 等风险接口条件，不应另外宣称 mixed problem 的最近对 test 也 automatically exact minimax；本 corollary 目前只声明信息扰动，没有作该错误升级。

### N4 — 明写 joint deficit 的定义和少量符号

`thm:uniform` 第 835–837 行使用 `D_H^{*,K}` 和 “joint deficit”，前文用 `D_{K,H}*`。补

`D_H^{*,K}:=D_{K,H}*`、`D_H^{joint}:=O_H-sup_{K,pi}G_{K,H}(pi)=inf_K D_H^{*,K}`

可让一般 noncontinuous `k(K)` 下的 inf 结论一眼可核。第 248 行的 `tilde Y` 可定义为 stacked whitened conditional innovations。SPD 部分的 `T/P` 宜明写对未观测 terminal inputs 为零列，与第 315 行 singular 定义一致。数学上这些对象可由当前上下文恢复，因此不单列为承重错误。

### N5 — 让 control 意义与信息权限更靠近首个设计结论

第 72–77、156–162 行已经说明 controller 拿到反馈所需 states，而 diagnostician 只看 retained states，不看 fast states/commands。`thm:uniform` 不应被介绍为信息无条件的物理控制极限；其意义来自这份 telemetry/admissibility 合同。建议在 control consequences 开头用一段说清任务在解析模型中的影响由 `g` 与 declared blackout 表示，repeatable exact-k 是假设；若控制端完整 telemetry 或可揭示隐藏 states 的 command 也提供给检测端，则实验改变。

不要求为此扩展 noisy partial sensors 或硬件实验。既有 equal-pole/nonnormal 数字已显示 controller memory 的作用，同时没有 actuator/state/tracking budget，不能直接比较实际效率/安全性。

### N6 — 把 runtime 工作流状态留在交付收据

第 28–34、975–976 行的“独立审查已过”“扫描仍在运行”“final manuscript acceptance unfinished”等是研究工作状态，不是科学结论。技术审查稿可以保留；正式稿宜把版本/接受状态移到审查 receipt，将科学范围写成可长期成立的 limitation。“incomplete”比暂时的“still running”更稳健。本次没有读取 OS 扫描进程，不作实时运行断言。

## 5. 承重假设、量词和接口逐项核对

|承重对象|当前文本判定|禁止的外推/解释|
|---|---|---|
|两侧健康预算、free initial level|第 146–151、232–240、295–305 行一致；difference rate r 由两侧 rate r/2 精确实现。|不能把 observed trace 当完整路径；不能逐 block 重置 level；不能改成各 coordinate 独立 vector nuisance。|
|ideal oracle|第 182–193、263–267 行正确：健康被理想扣除的 complete white record；composite full-state 仍有 inf_z。|O_H 不等于仍未知健康的 full record；full-record control neutrality 不表示健康漂移消失。|
|SPD positive sharp|`thm:main`、`eq:sharp` 与 Appendix 的 leading coefficient 和 xi* 因子一致；Q 可逆参与 strict beta>0。|不是 H² 匹配；不是任意只知稳定 poles 的 controller uniform。|
|fixed common-support singular|`m2sreg:plant` 要求 full-column G 和非零 B 在其 image；SVD/predictor rowspace 使伪逆 KL 合法。|B 不在 rangeG 会出现确定性区分/不同支持；不能按有限伪逆二次型假装真实 KL。|
|positive vs zero sharp 程度|定理和 proof 正确分离 leading-coefficient sharp 与 order sharp；R1 是导言错误。|beta=0 不等于完全创新恢复、不等于零亏损、不包含 sharp H² constant。|
|calendar lower/upper 合同|缺测至少 k；upper 需要任意预定起点双向已知 exact-k 可重复串接、hold/tail read 合法；terminal task 未约束。|若只有一方向或不可重复动作，上界不自动成立；lower 的 all-calendar 不能替其补可实现性。|
|compact-SPD uniform|`thm:uniform` 共同固定 Q≻0/B/prefix/path、compact gain family 每点 Schur、bounded integer k、known profiles；resolvent/tail/packing 给共同余项。|不延伸 fixed singular Gamma 到 rank-changing/nearly singular 族；一般 k 不连续也不保证 min attained。|
|settling 与 control optimization|`prop:settling` 的 finite plateau/endpoints 与 equality tie 明确；第 876–888 行 scalar lsc/unique optimum 和 near-optimal convergence 依 uniform。|homogeneous c^sE<=epsilon 不保证 forced/noisy full return；不存在硬预算下的 hardware-optimal 或 finite-H risk-optimal 结论。|
|Gaussian fixed-calendar risk|polyhedral image closed/closest difference attained；两侧 means 各可实现；separating inequalities/NP simple pair 给精确 size-power。|只对固定 H/K/pi、共同已知 covariance 和该 convex Gaussian experiment；不是 adaptive/sequential、未知 covariance 或 nonlinear comparator 风险。|
|bounded-even|实际 Minkowski difference、固定 E、含零及同一 projection 支持 O(H²) 扰动。|不覆盖 multiplicative 参数/改变 covariance/support；不保证 quadratic coefficient  unchanged。|
|有限检查和 nonlinear comparator|第 921–963 行披露 old repair zero、新非零补充、H120 两条证书、partial sweep、mirror fixed-ramp 域。|不能把 1% variance certificate ratio 当 iid；point certified lower=0 不是 actual power=0；.045 域不是整个 .75 force box。|

没有发现以下常见承重错误：在 singular Gaussian 上直接宣称 ambient covariance identity；把不同 block 健康对手拼成 independent paths；gap norm loss 重复收费；未经 weighted mass 修复使用自由 level support；把 homogeneous qualification 当 complete forced return；把共同-SPD uniform 定理外推到 singular/rank-changing families。本表是本轮文字与推导检查结果，不是对此领域全部可能反例的排除证明。

## 6. 英文正式审查摘要（不评分）

### Summary

The manuscript studies deterministic diagnostic calendars for a known stable linear plant with fully retained states outside declared blackouts and a complete rate-limited scalar healthy input under each hypothesis. Relative to an ideal healthy-subtracted complete-record benchmark, it proves a sharp H^(5/2) deficit when a missing span loses the constant-force score, and a Theta(H²) deficit when that score is preserved. A separate compact common-SPD controller-family result supports joint leading-order design; a nonlinear mechanical certificate is presented as an independent finite-risk illustration.

### Strengths

The information geometry is derived from genuine retained-state predictors and common Gaussian support. The complete healthy-path budgets, initialization, transition clock, and diagnostic information restrictions remain consistent across the two regimes. The converse and observable dual constructions address arbitrary calendars without resetting state history or nuisance levels. The manuscript also separates fixed-controller singular statements from the stronger common-SPD uniform result and accurately limits its homogeneous settling example.

### Required revisions

1. The Introduction currently attributes an exact leading coefficient and linearly increasing holds immediately after the quadratic branch. The quadratic result is only order sharp and uses a different upper construction; this paragraph must explicitly assign the coefficient and growing-hold calendar to the positive branch.
2. The upper proof must define its block start, midpoint, length, and scalar cumulative weights. These definitions are needed to verify the half-slot gap-center offsets and the full-clock support formula without reconstructing unstated notation.
3. If the nonlinear numerical table is retained, the risk targets, protected-gap definition, two-sided comparator/error/event interface, and source-bound certificate entry points must be provided. Its sufficient guarantee cannot be obtained merely by invoking the exact common-covariance nearest-set interface.
4. The closest prior-art comparison and IEEE/PDF preflight remain incomplete. The selected literature review is finite and includes four full-text gaps, with two directly relevant 2012 feedback/AFD papers still unreviewed at theorem level. The compiler failure is an environment diagnostic and provides no successful article PDF or page-count evidence.

### Suggested improvements

Consolidate the duplicated SPD and common-support models/proofs around one two-regime contribution, retain the distinct scope of the controller-uniform theorem, and include a short existing score-preserving example that still loses an affine slope mode. State the joint deficit identity and the bounded-even implication for the quadratic branch explicitly. Keep transient research-workflow status outside the eventual reader-facing paper.

### Limited readiness judgment

This is a complete and technically reviewable working draft. Within the frozen contract, this full-text review did not identify a counterexample that requires changing the principal theorem statements. The definite claim mismatch and notation gaps are locally repairable. Submission readiness is not established because the final prior-art comparison, reader-facing certificate presentation, IEEE format, and successful PDF verification remain open. No acceptance forecast or external full-theory acceptance is asserted.

## 7. 最小闭合顺序

1. 在同一主稿修 R1，补 R2 的精确定义；同步 N3/N4 的 theorem references 与 joint/oracle notation。
2. 对既有内容做主线压缩，补 R3 的单例 risk/certificate 说明；保持 finished H120 与 incomplete sweep 的边界。
3. 完成有限最近邻 contribution 对齐和 formal bibliography，维持未获全文项目的实际状态；随后换正式模板并取得成功编译/PDF，核实际版面。

这些步骤不要求先完成新数学研究、重复旧检查或把本报告改写成“全文全部理论已外部验收”。当前可用状态应写为：**FULL TEXT READ; FIXED-CONTRACT TECHNICAL REVIEW COMPLETED WITH REQUIRED EDITS; SUBMISSION PREFLIGHT INCOMPLETE.**
