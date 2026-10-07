# Revision 4 局部修订定向复核 v1

日期：2026-10-07。审查者：`manuscript_full_review`。本报告只新增本文件，不修改主稿、旧审查、receipt、证明、检查程序或台账。

**最终结论（SHA `70dc68db61599470cb6cd82ff6a2f83bcd30cdd4db89675e8074eab4e146f302`）：R1/R2/R3 的 reader-facing 数学/文字接口已闭合；新增 N2/N3/N4 在固定范围内成立。初次局部复核发现的旧 Q 符号和缺失 Gaussian/统一路径量词，已由主稿拥有者局部修补，本轮实际复读确认。这不需要新理论、旧检查复跑或 D2 大扫描。R4/R5 与最终证书交付包验收保持 pending，不能据本次局部复核升级为提交验收。**

## 1. 版本绑定及实际阅读范围

|版本|文件|现场 SHA256|
|---|---|---|
|revision 3|`references/manuscript_working_history/6c7bcf574450f49bffe4ad127ab89ff7ada0afbc3e90e1e9eef59b971515f367.tex`|`6c7bcf574450f49bffe4ad127ab89ff7ada0afbc3e90e1e9eef59b971515f367`|
|revision 4 初次局部复核字节|当时的 `outputs/certo_fdi_control_memory_draft_v1.tex`|`7da2935ceac057cc7c624efa6044811e8c77b17d4cec0911e744bcebd9c685c4`|
|revision 4 最终冻结字节|`outputs/certo_fdi_control_memory_draft_v1.tex`|`70dc68db61599470cb6cd82ff6a2f83bcd30cdd4db89675e8074eab4e146f302`|

revision 4 初次字节为 1,345 行，最终字节为 1,350 行。本轮先读取初次 revision 4 receipt、revision 3→初次 revision 4 的完整 textual diff 和修订上下文，实际定向读取初次字节第 48–75、178–243、754–777、861–882、928–960、976–1044、1180–1220、1244–1253 行，并检索修订符号/相关量词。拥有者修补 E1/E2 后，现场复验最终 SHA/receipt，复读最终第 984–1026 行及第 1223 行的条件，并核新增 synthetic-noise 声明。**没有重新通读全部旧证明**。旧 revision 3 的完整 1–1265 行阅读及整稿结论仍由 `manuscript_full_review_v1.md` 的原 SHA 绑定承担。中间 SHA 只记录本轮实际观察到的版本，不声称另存了它的快照。

使用前次已经读取的 `paper-review/SKILL.md` 的具体位置、触发、证据及修补方式；本次不重新评分、不预测录用、不重新检索文献、不执行数值检查/编译或 D2 扫描。新增例的核对为下述有限手核，不冒充检查程序复现。

## 2. 逐项闭合状态

|审查项|revision 4 位置|判定|
|---|---|---|
|R1：positive exact coefficient 与 quadratic order|第 52–61 行，对照 `m2sreg:theorem`|**CLOSED**：明确 quadratic branch 无 leading constant；exact coefficient/growing holds 只归 positive branch；recoverable branch另用 bounded cumulative-task construction。|
|R2：块定义和 support notation|最终第 223–240、1192–1224、1249–1256 行|**CLOSED**：`s_l,L_l,c_l,A_l`、真实 input slots、gap centers、local indices、`q_t(lambda)` 均定义；最终第 1223 行尾部正确为 `q_t(lambda^0)!=0`。|
|R3：H120 nonlinear 风险接口|最终第 987–1026 行|**CLOSED FOR THE READER-FACING INTERFACE**：目标、总时长、固定方向、两侧阈值/误差/event、非正 gap 保守零、rounded display、每路径 unconditional Gaussian及统一覆盖量词均明确。最终supporting package可访问性仍待交付验收。|
|N2：已有 partial-score 例|第 766–776 行|**CLOSED WITH FIXED-SCOPE QUALIFIERS**：stable nilpotent、score preserved但slope残差非零；不冒称全部 input recovery。|
|N3：bounded-even quadratic 接口|`cor:even` 第 929–955 行|**CLOSED**：同一实际 envelope/P/E 固定，`D_odd*<=D_mix*<=D_odd*+O(H²)`，只保阶、不保 quadratic coefficient。|
|N4：joint deficit/white data定义|`thm:uniform` 第 863–875 行，以及第 275 行附近|**CLOSED**：joint identity及共同 oracle明示；白化实际 conditional innovation stack被命名。terminal zero-column一句另有非阻断措辞建议。|
|R4：四篇全文比较缺口|原 related-work 与 receipt remaining|**PENDING**：未因本轮文字编辑取得新全文或完成新 theorem-level comparison。|
|R5：真实编译/IEEE/PDF|receipt remaining及现有compile status|**PENDING**：本轮没有成功编译/PDF/实际双栏页数证据。|

## 3. 初次发现及最终局部修补记录

### E1 — 初次第 1218 行的旧 Q 非零条件【最终已闭合】

初次复核文字为：

```tex
saturate $\Delta z=-r\Delta t\,\operatorname{sign}(q_t(\lambda^0))$ wherever $Q\ne0$.
```

`Q` 在本稿是 SPD process covariance，必定非零；所需条件却是 baseline scalar cumulative weight 非零。前半句已经正确改成 `q_t(lambda^0)`，尾部遗漏使此处仍不能字面作为 support saturation 的条件。

最小替换：

```tex
saturate $\Delta z=-r\Delta t\,\operatorname{sign}(q_t(\lambda^0))$
wherever $q_t(\lambda^0)\ne0$.
```

这不改变 support formula 或证明结论。最终字节第 1223 行已实际读到上述修补，R2 完整标为 closed。

### E2 — 初次第 993–998 行遗漏 Gaussian 和统一路径量词【最终已闭合】

初次段落给 comparator means、variance、好事件上的 physical/comparator 差和坏事件概率，随后使用 normal-tail bounds。**仅有均值/方差/好事件误差不能推出正态尾界。** 当时该独立 mechanical 段未显式说每条确定性完整路径对应的 comparator statistic 是 unconditioned Gaussian，且这些 m/e/V/delta bounds 统一覆盖整个允许类。前文 main model 的共同 Gaussian covariance不能替这个参数依赖的 nonlinear comparator补假设。

精确触发可以用一个两点随机变量说明：令 `X=sqrt(15)` 的概率为 `1/16`，`X=-1/sqrt(15)` 的概率为 `15/16`。它的均值为 0、方差为 1，但 `P(X>25/8)=1/16`，远大于本段约 `0.000967` 的正态尾保证。即使令 `e=delta=0`，mean/variance alone 仍不足。这个例只说明遗漏的分布条件，**不是冻结 D2 Gaussian comparator 证书的反例**。

初次建议用以下文字替换该段：

> For each admissible complete deterministic load path under hypothesis h, let Z_G^h denote the unconditioned Gaussian comparator of the fixed physical statistic Z. Uniformly over those paths, E Z_G^0 <= m_0, E Z_G^1 >= m_1 and Var Z_G^h <= V^+. On a good event E_h, |Z-Z_G^h| <= e_h, and Pr(E_h^c) <= delta_h. The event may depend on the same innovations; the risk proof uses event inclusion and a union bound rather than conditioning the Gaussian law on E_h.

保留现有阈值、`g_prot`、正 gap/非正 gap分支即可。这里每侧、每路径的 actual covariance 可以不同；统一 scalar variance upper bound足够，不需要新增共同 covariance 假设。固定方向在 data前选择、实际完整路径约束和固定 fault template仍沿 frozen protocol。

最终字节第 993–1003 行已实际读到：每个 allowed deterministic parameter/path `vartheta` 对应 `Z_G^{h,vartheta}~N(mu_{h,vartheta},V_{h,vartheta})`；means/variance/好事件误差/坏事件概率界 uniformly cover the frozen instance class；event可与同一innovations相关，推导不条件化Gaussian law。第 999–1001 行还说明 torque variance `10^-4`、encoder variance `(2pi/2^17)^2/12` 是synthetic independent Gaussian建模选择，不是实测hardware分布。这与前次读取的冻结protocol身份一致，不增加真实硬件结论。

因此 R3 的 reader-facing **数学接口**已标为 closed。最终可访问 certificate/supplementary package 仍是交付验收事项，不能由段落中 “accompanying” 一词证明已经完成打包、路径解析或新 ZIP 干净复现。

## 4. 已闭合内容的有限数学核对

### 4.1 R2 的 midpoint 与 gap offsets

revision 4 定义 `L_l=2(n_l+k)`、`s_l=sum_{i<l}L_i`、`c_l=(L_l+1)/2=n_l+k+1/2`。局部 inputs 为 `1,...,L_l`。

左 gap span含 slots `n/2+1,...,n/2+k+1`，center 为 `(n+k)/2+1`；右 gap span center 为 `3(n+k)/2+1`。相对 `c=n+k+1/2` 的 offsets正是 `1/2-(n+k)/2` 与 `1/2+(n+k)/2`。所以现有 affine pair loss的 half-slot中心项成立，`A_l=rho0+eta(s_l+c_l)` 与 packing首项一致。

`q_t(lambda)=sum_{j<=t}lambda_j`、`1<=t<L_l` 给局部零总质量向量的 full-clock rate support `r sum_t |q_t|`；missing weights为零时累计平台仍跨真实missing slots。第1198–1199行已把 positive/negative局部索引范围写明。

### 4.2 R3 的风险方向、两侧预算和显示精度

在最终段落已明确的 unconditioned Gaussian comparator前提下，现有

`t=m0+e0+(25/8)sqrt(V+)`、`g_prot=m1-e1-t`

方向正确。null好事件上 physical rejection被 comparator正尾事件包含；备择好事件上 miss被 comparator负尾事件包含。positive protected gap时用 variance upper缩小标准化间隔，给保守功效；nonpositive gap不能沿同方向替换 upper variance，现稿已明确返回 zero certificate lower。这不要求好事件与 innovations独立。

average/point各侧 deterministic allowance、dynamic mean loss、delta显示值与前次已读 frozen mean/risk review一致；mean endpoints已含 dynamic loss，`e_h`另付 physical-comparator discrepancy，没有重计同一对象。最终第1016–1017行明确 exact endpoints而非display decimals用于risk，关闭了 point variance向下显示舍入被当成可运算上界的问题。表内 point 0、actual power区别和 `.045` frozen-ramp域仍保留。

### 4.3 N2 的 partial-score 例

新段落的 `A_K` 是三维 nilpotent shift，因此 strictly Schur；`G=[e2,e3]` full column，`B=e2+e3`在 noise image，`f=(1,1)`、`F=2`。

`H2=[e1,e2,e2,e3]` 的 rowspace为向量 `(a,b,b,c)`，constant ray `(1,1,1,1)`在其中，rank三、`P2!=I4`。centered slope `(-1/2,-1/2,1/2,1/2)` 的投影是 `(-1/2,0,0,1/2)`，残差 `(0,-1/2,1/2,0)` 的平方范数为 `1/2`。因此所有新数值和score/full-recovery区别正确。

应用 quadratic theorem隐含沿用本节的 `k=1`、`r,eta>0`、held signs与repeatable exact-one-slot profiles；新例没有移除这些合同条件。可选地加 “For k=1 under the preceding task protocol” 帮助读者定位，但不是必须改变定理的缺口。

### 4.4 N3 与 N4

bounded-even envelope含零，所以 `G_mix<=G_odd`、相同 oracle下 `D_mix*>=D_odd*`。真实 orthoproject使额外 bounded input的 norm至多 `E sqrt(FN)`；fixed E给统一 calendar差额 O(H²)。odd quadratic下界 cH²因此保留，mix upper仍为 CH²+O(H²)。现稿没有声称 sharp quadratic coefficient不变，也没有新增 mixed非凸类的 exact minimax detector声明。

common-SPD theorem中相同 oracle给 exact joint identity `O_H-sup_{K,pi}G=inf_K(O_H-sup_pi G)`。无需 min/sup attainment；当前 `k(K)`有限而可能不连续的条件仍被保留。新增定义没有把该统一结论迁到 singular/rank-changing族。

## 5. 一项非阻断措辞建议

第 182 行写 “Columns after an unobserved terminal state have zero contribution in T/P.” 更精确的对象是**最后一个 retained state之后、直至H的input columns**；如果terminal state指x_H，“after”容易被读成H之后的空列。

建议改成：

> Columns of T corresponding to inputs after the last retained state are zero; the corresponding rows and columns of P are zero.

singular section原有 “zero on any unobserved terminal inputs” 已表达正确对象，主proof的terminal-hold dominance没有改变。本项是消歧建议，不单独构成承重反例。

## 6. 状态边界

本次可确认的接受范围是 **revision 3→最终 revision 4 局部修订及上述既有示例/推论接口**。R1/R2/R3和N2/N3/N4均已关闭；E1/E2保留为本轮发现及拥有者修补的历史记录。未发现要求改变calendar定理结论或新增研究才能修复的错误。第5节terminal-column措辞仍是非阻断建议。

R4的四篇全文、有限coverage对齐和正式引用仍pending；R5仍是平台编译/PDF/IEEE实际版面缺口。D2-a完整扫描/最终包未由本轮运行或验收，本稿仍只报告finished H120单例。可用状态应为：

**LOCAL REVISION REVIEW COMPLETED AT SHA 70dc68db61599470cb6cd82ff6a2f83bcd30cdd4db89675e8074eab4e146f302; R1/R2/R3/N2/N3/N4 CLOSED; R4/R5 AND FINAL DELIVERY PREFLIGHT PENDING.**
