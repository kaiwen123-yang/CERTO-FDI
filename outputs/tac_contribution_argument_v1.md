# TAC贡献论证与完整网格写入点 v1

绑定revision6 source `8eaa707d…55e0e6e`；现有root回执为11页。只整合已存17项对照和已审proof范围，不改稿、不再取得/重读原论文、不编译或跑D2。精确定位、SHA和选例证据在同名JSON。

**主论点是固定信息合同下的全日历信息亏损，而非Gaussian最近均值、滤波、Markov sensing、switching cost或反馈主动诊断的首创。** 17项记录中13项有有限全文定位、4项全文缺口；旧M0矩阵不能直接升级成R6历史排除。

|需要读者相信的结果|已有primary支撑及当前位置|主要质疑与已有回应|
|---|---|---|
|正损失时全日历同首项 $D^*=CH^{5/2}+o(H^{5/2})$，$C=(\sqrt2/5)\sqrt{F\beta_k r}\eta^{3/2}$|Nitinawarat TAC2013 Prop.1/Thms.1–2；Markov Thm.5.1；Vaidhiyan Thm.6、Lambez Thm.1；Allan/dead-time与switchback已有设计前史。`sf:two-regime`、附录B。|不是仅在对称族内最优：任意calendar的完整健康tent、长/跨macro gap和same-T一次分配给逆界；真实observable weighted repair给同系数上界。有限扫描不承担全称证明。|
|$\beta_k=0$给$\Theta(H^2)$及score容量$k\le d-p$|GJN/JN的Gaussian/affine几何是工具；`sf:capacity`、附录A/C。|不等于全部input恢复：已有$P_2\ne I_4$而slope损失$1/2$的例；zero上下界均按完整clock和两侧预算证明。仅固定known noise image/full states，无sharp quadratic常数或measurement-noise稳健性。|
|同物理输入下，完整记录中性而missing-span罚依控制器|Kim2013 §V-C/Remark3、Raimondo2016 Thms.4–5及Classens固定K滤波已有前史；`sf:control`。|共同$B/Q$的equal-pole例回应“只是改噪声”；真实演化后删state改变rowspace。允许fast-state/command旁路就改变实验；不称hardware-optimal或比既有受约束AFD更广。|
|共同SPD紧致族可联合优化首项|已有反馈/input design不是首创；`sf:uniform`、附录D。|不直接优化pointwise little-oh：共同resolvent、beta下界、packing/inactive cutoff证明统一余项。一般取inf；scalar settling另证唯一极小。齐次settling不保证noisy/forced return，奇异rank-changing族不在范围。|

最近对风险接口仍归功于既有Gaussian凸工具。非线性例另付逐path无条件Gaussian comparator、两侧mean/remainder/event与完整历史variance预算；不是线性锐律的实验验证。bounded-even仅为固定加性envelope的$O(H^2)$推论。固定known plant、free-level scalar路径、retained full states和预定calendar这些条件不能缩成一般机器人极限。

四缺口具名保留：Esna Ashari–Nikoukhah–Campbell的 *Effects of feedback on active fault detection*（2012）和 *Active Robust Fault Detection in Closed-Loop Systems: Quadratic Optimization Approach*（2012）；Cheng–Steinberg *Trend robust two-level factorial designs*（1991）；Coster–Cheng *Minimum Cost Trend-Free Run Orders of Fractional Factorial Designs*（1988）。metadata/snippets不能填成theorem noncoverage。

## 完整400行的有限写入方案

1. **先闭合数据再替换文字。** 保留12个冻结H、两个readout、五个固定成员及每H的全部switch-then-stay S，共400身份。全表保留重复/退化/物理、KKT、mean、variance、event失败；没有bound用NA，unfinished前驱禁止首成功。交付exact budgets、case/direction/protocol/receipt绑定及各类覆盖计数。
2. **Section VI替换/add位置。** H120主表可换成六族×两readout的12行“first certified grid point/覆盖”摘要；H120精确行与预算入full-grid supplement，R6历史保留。Figure2扩到全部12H的terminal-balanced配对曲线，保留nonpass及明确缺值；全族/H/S状态矩阵入补充。仅在闭合后替换“400未完成”一句；主定理/附录和有限合同不改。
3. **首认证与旗舰例分开。** 原≥3完整块只是选例准则，不是证书合格前提。小calendar JSON和strict CSV均确认H100/H120为2块，H160为3块$n=(12,14,18)$、时长41s；H160 average已认证达标（$V^+\approx6.191051394\,10^{-7}$），point同例有有效bound但目标未达。建议主代表换H160，并单独保留terminal average首网格H100/26s和H120/31s历史，不删早期行或称全日历最优。

各族H*须全部更早H和该H各S已处理，遵守最高certified power/最小S并列规则。若point全网格未过，只能写“该冻结充分证书未建立目标保证”；不等于actual power为零/不可检测。若≥3块实例全未过，照实记选例准则未满足，不改参数救结果。按实际threshold分解 $g=(m_1-m_0)-(b_0+b_1)-(t-m_0-b_0)$，最后项含向上sqrt界，不能用display decimals重算；dynamic loss已在mean端点内不能重付，event概率不混进幅值预算，variance比不叫普遍readout增益。全网格结果仍是既定family/grid的有限比较，不是sequential或global最短时间。

## 英文贡献段建议

Within a known stable linear plant with common Gaussian input support, complete retained states, and scalar healthy inputs with free levels and full-history rate bounds, we prove a sharp information deficit over all deterministic task calendars. Positive missing-span loss of the constant-force score yields matching five-halves-order bounds with the same leading coefficient and an observable terminal-balanced construction; zero score loss yields matching quadratic-order bounds without a claimed quadratic coefficient. The classification concerns a scalar score and does not imply recovery of all latent inputs. Keeping the physical force, noise and observation contract common, we identify controller-dependent gap penalties and prove uniform leading-order design over compact controller families with common positive-definite process noise. Established convex Gaussian methods provide the fixed-calendar testing interface. The nonlinear example supplies separate finite sufficient risk certificates rather than an instance of the linear asymptotic theorem.
