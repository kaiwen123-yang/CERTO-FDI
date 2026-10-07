# 英文稿統計／oracle 接口定向獨立審查 v1

2026-10-07。**判定：接受本次凍結英文稿第201–233行的 Gaussian 最近對／fixed-calendar minimax-risk 接口，以及第318–346行 bounded-even 的 O(H²) 擾動界。polyhedral attainment、兩側 rate-r/2 的完整健康預算、ideal oracle 與 composite full-state information 的區別均正確。** 這是局部整合審查，不是全文審稿、引用來源核對、編譯驗收或錄用分數預測。

## 1. 綁定版本與實際閱讀

|來源|SHA256|
|---|---|
|`outputs/certo_fdi_control_memory_draft_v1.tex`|`0f24a30953681a51f392f65dc5ef88aa7eb64c6ff04c10c38ee9ba8b441168ff`|
|`outputs/m2_problem_contract_v1.md`|`794c245d0fdb672021cb36566382d68834b2abe20331dde0bc01a0bc71671eae`|
|`outputs/m2_controlled_memory_theorem_v1.md`|`38d2aecf2d00a6a781f0a99f6448d93a4d2fcccd1e895526ca3c5fed2c3455b1`|
|`outputs/m2_independent_review_v1.md`|`17b27584e1333292d8135d67b8e96e446e0e6e57fc2ef676b6053b0121cc0fb6`|
|`outputs/compact_controller_uniform_bridge_v1.md`|`89762501f1272eb8b0ed5150985225655e62f0681d24c62c41729750dbcdf351`|

英文稿實際閱讀區域為第108–234行 model／main theorem／fixed-calendar statistical meaning，以及第255–347行 settling／bounded task-even。未讀全文其餘 section／完整 Appendix，不將此範圍稱為「全文已獨立審查」。本檔僅新增審查文字，未修改稿件或主證明。

## 2. 兩側健康預算與最近差的精確實現：通過

設 N=H+n0，每側完整健康類為

\[
\mathcal B_{r/2}=\{b\in\mathbb R^N:|\Delta b_j|\le r/2\},
\]

初始 level 自由。其差集恰為 Z_H：任意 b0,b1 的差 rate≤r；反過來任意 z∈Z_H 可取 b0=z/2、b1=−z/2。故真正的兩側均值集合在 row-orthonormal T 白化後為

\[
\mathcal M_0=T H_g\mathcal B_{r/2},\qquad
\mathcal M_1=T a_f+T H_g\mathcal B_{r/2},
\]

且

\[
\mathcal M_1-\mathcal M_0
=\{T(a_f-H_gz):z\in\mathcal Z_H\}.
\]

TTᵀ=I、P=TᵀT 給 ||T v||²=||P v||²，因此文稿的 d²=2G 正是這兩個真實 Gaussian 均值集合之間的最小 Mahalanobis 距離。使用完整 z，包括 missing input nodes，沒有將 observed-node trace 的 slope 預算錯當完整預算，也沒有把各 block 初始健康 level 重置。

實現最近差 z* 時可直接取

\[
\mu_0^*=T H_g(z^*/2),\qquad
\mu_1^*=T a_f-T H_g(z^*/2).
\]

此 pair 同時滿足原兩側預算，沒有只存在 difference 而不存在兩侧 means 的缺口。

## 3. Polyhedral attainment：通過

Z_H 由有限個線性 inequalities 定義，free initial level 只使它無界，不改變其 polyhedron 性質。有限維 polyhedron 的線性像仍是 polyhedron，故最近差集合是非空閉集合。取任意一個候選差 v0；最小化可以限制在 ||v||≤||v0|| 的閉球內，交集緊緻，所以平方距離達到。此處不需要原 Z_H 緊緻，也不適用「任意 closed convex set 的線性像都閉」的錯誤泛化。

zero distance 時由這個 attained difference=0 得到真實均值集合交點，而不僅是兩集合距離為零。故第226–227行的 overlap 結論有足夠依据。

建議定稿時以一行明寫上面的兩侧均值集合與 b0=z*/2、b1=−z*/2 的實現，可讓讀者直接核對 attainment 的實驗意義；現在的論述已正確，不屬必須改變定理的問題。

## 4. 最壞 false alarm／power 的精確風險接口：通過

記 w=μ1*−μ0*、d=||w||>0。固定 μ1*，沿 convex M0 移動最近 μ0* 的一側方向，距離平方右導數非負，給 wᵀ(μ0−μ0*)≤0；固定 μ0* 同理給 wᵀ(μ1−μ1*)≥0。兩個不等式的方向與第209–210行一致。

真實白化資料有 covariance I，因此

\[
S=w^\top(\widetilde Y-\mu_0^*)/d
\]

variance 恰為1，null 下的 mean≤0，alternative 下的 mean≥d。threshold z_{1−α} 給 uniform size≤α 和 worst power≥Φ(d−z_{1−α})。在 realizing pair 上分別 mean=0,d，兩側界均達到。

任何 uniform-size≤α 的其他 test，在 μ0* 的 simple null 上仍 size≤α；Neyman–Pearson 的 simple-pair optimum 在 μ1* 上的 power 為 Φ(d−z_{1−α})。其 worst alternative power 不可大於在 μ1* 的 power，故文稿的 minimax optimality 結論成立，並未只證 detector 的充分條件。

當 0<α,β<1 且 α+β<1，z_{1−α}+z_{1−β}>0，因此

\[
\Phi(d-z_{1-\alpha})\ge1-\beta
\iff d\ge z_{1-\alpha}+z_{1-\beta}
\iff G\ge\tfrac12(z_{1-\alpha}+z_{1-\beta})^2.
\]

第224行沒有漏掉 1/2，也沒有把平方不等式延伸到 quantile sum 為負的區域。d=0 時兩假設含同一 distribution，uniform size≤α 意味 worst power≤α；當 α+β<1 時不能滿足目標 power≥1−β。

此結論針對已固定 H、K、π 的 convex Gaussian experiment。它不直接提供對所有 physical faults、機械量 error events 或未知 covariance 的風險保證，也不把 asymptotic D 首項變成給定 finite H 的 risk 證書。

## 5. Oracle 與 full-state composite information：通過，但建議提前命名

第229–232行明確把 O_H 定義為 ideal healthy-subtracted complete white record 的 KL benchmark，並說它不同於 full-state composite information。這個区别正确且必要。

具體地，理想扣除健康 input 後 simple means difference 為 a_f，所以

\[
O_H=\tfrac12\|a_f\|^2=\tfrac F2\sum a_j^2.
\]

如果所有 state 都讀取但仍有未知健康路徑，則 P=I，真實 composite 信息仍為

\[
G_{\mathrm{full}}(g)=\tfrac12\inf_{z\in\mathcal Z_H}
\|a_f-H_gz\|^2,
\]

一般小於 O_H，且取決於任務 g。full-state 可逆 dynamic map 使這整個 composite experiment 對 K 中性；O_H 也對 K 中性，但两者不是同一对象。

例如當 g 恒為+1且 r≥η，prefix 保持 z=ρ0+η、post-onset 取 z_j=a_j，就有一條合法 rate-r 路徑：prefix 內 slope=0、onset 接合 slope=0、其後 slope=η。post-onset residual 全為0，仅 prefix 留下固定 residual，故 G_full≤Fn0(ρ0+η)²/2=O(1)，而 O_H 為 Θ(H³)。這直接展示全讀狀態不會因名為 oracle 就自動消除健康混淆；實際 composite 值必須從完整 Z infimum 算出。

又因 z=0 允許且 P 是 contraction，所有 calendar 均有 0≤G≤O_H，所以 D=O_H−G 非負。沒有另加一份 budget，也沒有在 controller 比較中只改 output variance 而固定 signal。

**局部表述建議：** 第156行首次介紹 O_H 時即加「ideal healthy-subtracted complete-record benchmark」，可避免讀者在讀到第229行之前把它誤認為 full-state composite 信息。第161–163行的 control-neutral 事實本身正確，應維持「完整 experiment 中 fault／health／noise 同步變換」的說法。

## 6. Bounded-even 差集與 order-two 擾動：通過

每側 |e_j^h|≤E/2 導致差 e=e0−e1 滿足 |e_j|≤E；若每側完整自由 box，任意這樣的差可由±e/2 實現。文稿對更一般允許類另外明確假設 actual complete difference class 為 gZ_H+E_H 且0∈E_H，因而沒有以單側 envelope 偷換實際兩側差集。

||P(fe)||≤E√(FN)=R，所以 d_mix∈[(d−R)_+,d]。若 d≥R，(d²−(d−R)²)/2=dR−R²/2≤dR；若 d<R，d²/2≤dR。因此

\[
0\le G_{odd}-G_{mix}\le dR
\le FE\sqrt N\,A_H=O(H^2).
\]

0∈K 给 d≤√F A_H；固定 ρ0、η、n0 下 A_H=O(H^{3/2})。相同 calendar class 取 sup 后，0≤sup G_odd−sup G_mix≤同一界，所以 D_mix*−D_odd* 的界方向正确。共同 F／E／n0 也使这一扰动在本次已接受的 compact controller family 上一致，可维持相同首项，但文稿目前仅声明 fixed-K 版本。

unrestricted even difference class 若包含 a，取 e=a,z=0 即产生 overlap；文稿第345–346行正确。这里的 E 固定不可随 H 同阶增长后仍称 O(H²) 低阶项。

## 7. 与新 uniform 桥梁整合的范围

当前冻结英文稿第313–316行仍正确地说 pointwise sharp 不能单独交换 continuous controller 优化与 H 极限。它尚未整合新桥梁，不属于当前稿错误。将新定理整入时，应同时给 compact、每点 Schur、共同固定 SPD Q／B、bounded k、双向 repeatable exact-k 和统一余项，随后才将 [4/5,19/20] 的 c*=81/100 升级为实际联合渐近信息最优，并说明近优控制器序列收敛。

第269–270行已经正确限制为 homogeneous qualification；仍应维持它与完整 forced/noisy return 的区别。finite family、single-gap ranking、leading coefficient ranking、uniform joint asymptotic optimum 和 finite-H risk 是不同的结论，不能在整合时混写。

**此次没有需要拒绝的局部数学接口。建议提前命名 ideal oracle，并增加两侧 means／realizing-pair 的一行定义。引用 `convex` 的原文来源与该局部模型是否逐项匹配、全文符号和编译状态不在此次审核范围。**
