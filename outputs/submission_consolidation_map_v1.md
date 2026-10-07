# Submission consolidation map v1

日期：2026-10-07。产物：`outputs/submission_body_consolidated_v1.tex`。本子任务只新写 body fragment 与本映射文件；原主稿、冻结证明、旧报告和台账未改。`work/consolidate_submission.py` 与本映射脚本只是中间文件。使用 paper-writing 和 proof-writer 技能；评分/录用预测与新方向均不在本次范围。

## 1. 字节绑定与范围

- 主稿基线为 revision 4，SHA256 `70dc68db61599470cb6cd82ff6a2f83bcd30cdd4db89675e8074eab4e146f302`；交付时再次核对保持相同。
- 新 fragment SHA256：`7ced33a8641dc8ccb0b216684f68d13f2f26334effa16ccf3dceaea98001a6d9`；58,147 bytes，1164 行。
- 无 documentclass、preamble、document 环境；原有 theorem/proposition/corollary 环境由 host 提供。正文、数学证明、13 项 bibliography 已全部内联。
- 所有 48 个新 label 均用 `sf:`；原 35 个 label 全部有下表去向。新补 `sf:path`、`sf:predictor`、`sf:penalty`、`sf:block`、`sf:support` 等用于明确共用定义。
- 未在本子任务编译：没有成功 compilation、PDF、双栏页数或 layout 验证的主张。根若另行编译集成主稿，结果应由新的实际 receipt 绑定；本记录不提前宣称通过。
- 本次压缩是文本/组织修订，不是新数学接受、外部理论验收或投稿就绪判定。旧整稿报告绑定 revision 3；局部报告绑定 revision 4。此新 fragment 仍需根复审，不能把旧 SHA 的审查结论自动迁成新文件接受。

## 2. 阅读与来源 SHA

实际读取主稿全部段落，定向交叉核对冻结 common-support/zero/uniform 源及其已审量词，读取整稿/局部审查的修订要求。文献元数据与 support locator 由根的 citation_preflight 子任务新交付，正文保留其已核范围。

|来源|SHA256|
|---|---|
|`outputs/certo_fdi_control_memory_draft_v1.tex`|`70dc68db61599470cb6cd82ff6a2f83bcd30cdd4db89675e8074eab4e146f302`|
|`outputs/m2s_singular_memory_theorem_v1.md`|`8ff2de70274973e4a9e104b26a5bf4be14e0e742998f2c562f6023e6316ab431`|
|`outputs/m2s_recoverable_order_v1.md`|`5b04f87f23fbfe1d2bc1fb1fbb791e783a47e029c7cdf130e1c000dd22d0f4f1`|
|`outputs/compact_controller_uniform_bridge_v1.md`|`89762501f1272eb8b0ed5150985225655e62f0681d24c62c41729750dbcdf351`|
|`outputs/m2s_independent_review_v1.md`|`83f711812f92bd0cfe4f0ed5e158e8ff5c9005cf58006613fec25599a640c448`|
|`outputs/m2s_recoverable_order_review_v1.md`|`c32efb758b39e3b3f1d11e8219ee365f50fb33f84eb44857739620d8e99571c8`|
|`outputs/compact_controller_uniform_review_v1.md`|`35f627a5fc637fe255b00c982768daf4067837e81a70060368783fd7a90ecd71`|
|`outputs/manuscript_full_review_v1.md`|`c5a9f25560120d5194c10345af3113f37f67d5aaa86853f5f8aa020856c5a103`|
|`outputs/manuscript_local_revision_review_v1.md`|`a5ce449508692a7f1c24602e37602eb4255553284fad4a9ef8190c72c22bfcf0`|
|`outputs/submission_bibliography_verified_v1.tex`|`cf0ce385edee79785471d656f4113dd32fd0c88d3ea8e1f5fae174e2cf67671a`|
|`outputs/control_settling_figure_v1.pdf`|`1505b858adab675e4585ce854d469cb35068ff48903be9b6db42cec9ed9a7524`|
|`outputs/control_settling_figure_caption_v1.md`|`daa3083745143935c9eaa2329dfbcf7b8f556f3338f2eab69774dca6fae03d1b`|

本映射引用这些版本来说明编辑来源，不改写源文件内的旧待审/接受/检查/编译历史。没有重跑旧 M1/M2/M2S checks、没有启动 D2 或产生新的 finite-risk scan 结果。

## 3. 结构与旧 label 映射

正文结构为：问题/相关工作 → 一个 retained-state 实验 → 两分支主定理与 score/capacity/strict-SPD 特化 → 固定日历风险 → 控制意义/齐次 settling/共同-SPD uniform → bounded-even → 有限检查与独立 nonlinear H120 例 → 限制。附录 A 集中共支持/SVD、真实 projector、Gamma/tail/affine、完整路径 support 和 observable dual；B 给 positive converse/attainment；C 给 zero 上下界；D 给 settling/uniform；E 给 bounded-even。

|原 label|新 label / 定位|完整证明或解释位置|
|---|---|---|
|`thm:main`|`sf:two-regime; sf:spd`|正文两分支主定理与 SPD 特化；附录 A 的 strict-positive 证明、附录 B 上下界|
|`eq:sharp`|`sf:positive`|正文主定理；附录 B 的匹配系数|
|`eq:upper`|`sf:upper`|正文主定理；附录 B 的 packing/dual/两项幂和|
|`m2sreg:section`|`sf:model; sf:results; sf:geometry`|共同模型、主结果、附录 A；删掉模型二次定义|
|`m2sreg:plant`|`sf:plant`|正文共同物理 plant/feedback/noise 模型|
|`m2sreg:interval`|`sf:interval; sf:predictor`|正文真实 retained predictor；附录 A 共同支持/SVD/rowspace|
|`m2sreg:information`|`sf:information`|正文 exact KL/ideal oracle/deficit；附录 A 合法性|
|`m2sreg:theorem`|`sf:two-regime`|正文同一主定理；附录 B positive、附录 C zero|
|`m2sreg:positive`|`sf:positive`|合并旧 SPD 同公式；附录 B|
|`m2sreg:zero`|`sf:zero`|正文 order sharp；附录 C 两侧完整证明|
|`m2sreg:capacity`|`sf:capacity`|正文 score/capacity proposition；附录 A|
|`m2sreg:score`|`sf:score`|正文 rowspace/score 条件；附录 A 等价性|
|`m2sreg:dimension`|`sf:capacity-bound`|正文恢复容量；附录 A invariance/stability contradiction|
|`m2sreg:gamma`|`sf:gamma`|附录 A reached-subspace 稳定后的伪逆统一界|
|`m2sreg:tail`|`sf:tail`|附录 A beta monotonic/tail；附录 B/C 分别使用不同正下界|
|`m2sreg:affine`|`sf:affine`|附录 A exact constant-slope cross；两分支均使用|
|`m2sreg:crossbudget`|`sf:cross-budget`|附录 A 全日历 O(H²) cross 总预算|
|`m2sreg:symmetricupper`|`sf:upper`|正文主定理；附录 B 单份 observable attainment|
|`m2sreg:balance`|`sf:balance`|附录 C profile-aware 全输入 cumulative g 界|
|`m2sreg:slopeloss`|`sf:slope-loss`|附录 C score0 仍可能损失 slope 的 O(H) oracle loss|
|`m2sreg:globalrepair`|`sf:global-repair`|附录 C global observable scalar mass repair|
|`m2sreg:support`|`sf:zero-support; sf:support`|附录 C O(H²) 支持界；附录 A 共用完整支持公式|
|`m2sreg:dual`|`sf:dual`|附录 A 共用 range(P) 实际 statistic/Fenchel；附录 C 应用|
|`m2sreg:positivecase`|`sf:zero-positive-case`|附录 C all-calendar 下界 case A|
|`m2sreg:zerocase`|`sf:zero-preserved-case`|附录 C all-calendar 下界 case B，含 early/late cross|
|`prop:settling`|`sf:settling`|正文 plateau proposition；附录 D 单独证明|
|`thm:uniform`|`sf:uniform`|正文 compact common-SPD theorem；附录 D 共同余项证明|
|`cor:even`|`sf:even`|正文两个 regime 的固定 E 结论；附录 E contraction 证明|
|`sec:proof`|`sf:geometry; sf:positive-proof`|旧 SPD 附录的共用 geometry 与 positive proof 分置 A/B，仅保留一份|
|`eq:affine`|`sf:affine`|旧 SPD 与 generalized exact affine 同式，集中附录 A|
|`eq:converse`|`sf:converse`|附录 B 一个全史 signed-tent path 和 same T|
|`eq:lower`|`sf:lower`|附录 B calendar-uniform liminf 系数|
|`eq:baseline`|`sf:baseline`|附录 B 零总质量 baseline，保留完整 block-slot 支持计数|
|`eq:support`|`sf:positive-support; sf:support`|附录 B repaired block 支持界；共用 exact support 在 A|
|`eq:dual`|`sf:dual`|共用 observable dual 集中 A；B 保留 energy/support/gap 计算|

原 `thm:main` 的正定过程噪声结果保留为主定理的 positive branch 和 `sf:spd` 的 strict-positive 特化，未丢掉其系数、所有 fixed-xi 上界或 controller-fixed 限制。原 M2S 主定理统一为 `sf:two-regime`，未将 zero branch 的 order sharp 改成 leading-constant sharp。

## 4. 量词和承重内容核查

|项目|新稿的具体保全|
|---|---|
|共同支持|fixed known strictly Schur A_K；full-column G；0≠B∈rangeG；real initialized mean 在相同 retained noise image；reduced SVD 与 rank(W_m) 白行；用可逆 predictor 左变换的 rowspace invariance，不用伪逆 congruence。|
|状态/clock/路径|known x_-n0=0、fixed full-read prefix、a=0 prefix；Nature 在离线 calendar 后、noise 前选两条完整 scalar paths；每侧 rate r/2、free level；z rate r 在全部相邻 input 槽含 missing 槽；没有 state/noise/health reset。|
|诊断权限|held full states；内部 fast states、commands 与旁路仍不读；controller 获得 feedback state 的权限不等于 diagnostician 权限；无硬 actuator/state/tracking budget。|
|calendar 对齐|converse 保留所有至少 k 的 longer gaps；upper 保留任意预定起点双向 known exact-k repeated concatenation 与 |g|≤1；no terminal task；unread tail 由 holding 支配。|
|true intervals|gap 的 m=k+1 inputs 含 right retained input；单例 projector 是 I_p；joins 用相邻 real states，不假造 independent output 初始化；last retained state 后的 input rows/columns 为零。|
|oracle/risk|O_H 是理想 healthy-subtracted complete white record；full composite 仍 inf_z；half-square KL 保留；polyhedral image closed，nearest difference attained，±z*/2 实现两侧预算；size-power exact condition、overlap case 与 NP simple-pair lower 均保留。|
|Gamma/tail/affine|reached subspace 在 d 后稳定再比较 W_d†/W_m†；固定 Gamma_K；beta 非减、tail linear；L1=-MᵀW†N、L2 explicit；矩阵 cross 不假反射，总 O(H²)。|
|positive converse|one global legal signed tents，missing/gap-right inputs 为零；same T 先一次 convex split；cross-macro missing 节点只付一次；M=0 单独处理；宏 H^(3/4)，calendar-uniform 阈值/余项；先 optimal deficit/H limit 再 epsilon/delta→0。|
|positive upper|s_l/L_l/c_l/A_l 精确定义；c_l=n_l+k+1/2，gap center offsets 1/2±(n_l+k)/2；H-1 packing+bounded padding+1–4 tail reads；local levels 仅 dual；baseline zero scalar mass/full-clock partial support；v=PU−(N/D)Pgamma，D≥F(2n−2)，one scalar weighted repair；energy/support O(H²)；actual W†Hv predictor statistic。|
|zero branch|仅 constant score preservation，不保证 slope/whole input recovery；upper 平衡 full cumulative g（含 missing profiles）、singleton count、Abel/global repair/support；lower 有 late positive span 或所有 late spans≤L_z 两分；z=(r/2)g 是一个完整路径，right-held g²=1，early negative cross 单付，epsilon=(4L_z+2)^−1；无 sharp H² 常数。|
|uniform 控制|独立 common fixed Q≻0/B/plant/path/prefix/readout；nonempty compact gains 每点 Schur；bounded integer k(K)，exact profiles；common resolvent/transient、beta/b bounds、xi positive compact、padding/inactive cutoff/余项；一般取 inf，不假 minimum 或 finite-H optimizer；未扩至 singular/rank-changing。|
|settling/even|settling 的 equality 用短 s、finite candidates、near-unit limit 和 unique c*=.81/near-optimal convergence 保留；只是 homogeneous qualification。even 是实际 Minkowski difference，fixed E、contains zero、unchanged projection；positive coefficient unchanged、zero quadratic order 保留，不保 quadratic coefficient。|
|H120 独立风险|与 exact main Gaussian experiment 分开；每参数/path unconditional Gaussian comparator，means/variance/error/event 统一两侧 bounds；same-noise good event 使用 inclusion+union，不条件化 Gaussian；positive protected gap 方可代 upper variance，nonpositive certificate返回0；display decimals不做risk endpoint。|

正分支 converse 的分配标量使用 `delta`，而 `theta` 始终为故障 latent vector，避免压缩后符号撞名。held vector使用 gamma，而 h_l^0仍为 scalar baseline support。tent indexing/held fourfold level计数写显式，是原算法已有的初等推导展开，不是新增定理或合同变更。

## 5. 仅重复/运行状态的删除或搬移

- 删除工作稿 Draft status、compiler/job/goal/research-workflow 字句；scientific scope 和有限验证边界另在 reader-facing 正文保留。
- SPD 模型的 L/inverse 版本并入 G/pseudoinverse 共支持模型；其 strict-positive 证明在附录 A 保留；重复 positive statements/proofs不再独立占一节。
- 原 M2S positive proof 的“precise replacements in thm:main”依赖语言改为一份完整共支持证明。共用 support/Fenchel/实际-statistic 在附录 A 写一次，B/C 保留各自构造与预算计算，不指未附 MD。
- settling、uniform、bounded-even 的证明移到同一 fragment 的 D/E 附录；正文定理、例、量词、科学限制不删除。未把承重证明转移到未附外部文件。
- source compiler/history/review comment不进入 reader-facing bibliography；其精确 locator/范围仍保存在已交 verified bibliography 和 citation support artifacts，本映射有 SHA 绑定。

## 6. 图、文献和独立数值边界

图仍只有既有 `control_settling_figure_v1.pdf`，置于 settling 例后、uniform theorem 前，完整保留已有 caption 的物理约定、端点/tie、三点族与 continuum区分、无随机CI以及 homogeneous-only 限制。没有重生成图。`IfFileExists` 加 `ifdefined includegraphics` 双重fallback；没有图片时保留同一位置、解析结论的文字框和完整 caption，不依赖该文件读证明。host 可用 graphicx 显示图；数学内容无需外部项目文件。

原10 bibkey 全保留；另内联已读的 switchcost、multipleplays、ossenkopf，共13条。body保留 error limit→sluggish parameter limit 顺序、known iid/sequential Bayes/switching-delay scaling和real-dead-time对照。四个全文比较缺口逐项点名：2012两篇 feedback/AFD、Cheng–Steinberg1991、Coster–Cheng1988。未取得全文不能被metadata核对或模型摘要替换成 theorem coverage/no coverage。

有限检查仍披露150 retained-subsets/68 calendars；原 symmetric repair=0 的覆盖与 asymmetric nonzero witness/六例低秩 supplement分开。H120表只保留 finished terminal-balanced average/last-point两行；PFA<1e−3与protected power≥.9、31秒、fixed方向、两侧 dynamic mean loss/physical error/bad events及f≤.045的frozen-ramp enclosure域均保留。400-row族未完全certified，不推 all-family shortest-time/sequential optimum；point证书下界0不是 actual power0。

## 7. 本次静态核验与剩余边界

新fragment静态核验：48 labels唯一且sf前缀；ref/eqref/cite均解析；13 bib项均被引；begin/end环境计数平衡；无documentclass/preamble/documentwrapper。这些只说明本次文本连接，不是编译PASS或新数学验收。主稿/冻结来源SHA未改。

剩余：根复审新fragment、已知四篇全文比较缺口、最终证书可访问交付包、正式IEEE格式与成功PDF/实际页数。压缩本身不关闭这些事项。
