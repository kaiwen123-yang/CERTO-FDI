# 緊緻控制器族 uniform sharp 橋梁：獨立反駁式審查 v1

2026-10-07。**判定：接受定理 U 的 U1–U5，以及所列近優控制器序列趨於 c*=81/100 的結論；接受範圍嚴格限於共同固定 B≠0、Q≻0、固定維數、緊緻已知控制器族、每點嚴格 Schur、完整狀態讀數、同一完整 scalar nuisance 與可重複串接的雙向 exact-k(K) 合同。未發現該範圍內的承重反例或必須改變結論的數學漏洞。**

本審查採 proof-writer 的主張提取、依賴核對、反證／直接推導流程，逐式審查新的 uniform 量詞橋梁。固定 K 的 M2 sharp 定理依賴既有獨立審查；沒有重跑舊檢查表、D2 掃描或以有限網格代替全稱證明。下文補出 terminal packing、inactive cutoff 和共同餘項的可核推導，屬證明可讀性補強，不是定理條件的新增。

## 1. 冻結來源與精確範圍

所有下列檔案位於 `outputs/`；SHA256 綁定本次實際讀取版本。

|來源|SHA256|
|---|---|
|`compact_controller_uniform_bridge_v1.md`|`89762501f1272eb8b0ed5150985225655e62f0681d24c62c41729750dbcdf351`|
|`m2_problem_contract_v1.md`|`794c245d0fdb672021cb36566382d68834b2abe20331dde0bc01a0bc71671eae`|
|`m2_controlled_memory_theorem_v1.md`|`38d2aecf2d00a6a781f0a99f6448d93a4d2fcccd1e895526ca3c5fed2c3455b1`|
|`m2_independent_review_v1.md`|`17b27584e1333292d8135d67b8e96e446e0e6e57fc2ef676b6053b0121cc0fb6`|
|`controller_settling_tradeoff_v1.md`|`081fc156382680cf750c3a40c177e18eac58d627e6cdeeb7973f5a27ce1579ae`|
|`m2_controlled_memory_checks_v1.json`|`d99e688f7d527798edacc697e46822fd76898baa5f912aeafc8ecded9ec22559`|
|`controller_settling_checks_v1.json`|`0e7be10bdd4bf4e53749f706c562978f8ea0d446fc0824f4bdb0029b9f7cfcc2`|

完整讀取橋梁、M2 合同／證明／獨立報告及 settling 證明；JSON 僅讀取並核對證書內容與範圍。M2 JSON 的 60 個 finite calendars 和 8 個 larger sanity 仍全部 `repair_energy=0`，故不能新增宣稱「此次 uniform 證明已被非零修補數值全覆蓋」。既有獨立報告提供的不對稱非零修補見證，與正文的一般 contraction 證明分別成立。

需驗證的結論為

\[
\sup_{K\in\mathcal K}\left|H^{-5/2}D_H^{*,K}-C(K)\right|\to0,
\qquad C(K)=\frac{\sqrt2}{5}\sqrt{F\beta_K(k(K))r}\eta^{3/2},
\]

以及由此取 inf 的聯合漸近結論。沒有假定 C 在一般控制器族上連續或達到最小值；也沒有假定 finite-H optimizer 存在。

## 2. 共同 resolvent 與 transient：通過

K↦A−B_uK 連續，譜半徑在固定有限維數下連續。非空緊緻集且每點嚴格 Schur 因而給

\[
a_*:=\max_{K\in\mathcal K}\rho(A_K)<1.
\]

固定 a*<τ<1。每個 zI−A_K 在共同圓周 |z|=τ 可逆，逆矩陣在緊緻積集上連續，所以 R* 有限。matrix Cauchy 公式包括 j=0，且圓周長度為 2πτ，因此

\[
\|A_K^j\|\le R_*\tau^{j+1},\qquad
\sum_{j\ge0}\|A_K^jB\|\le\frac{R_*\tau\|B\|}{1-\tau}.
\]

這個步驟不要求矩陣 normal，不要求 ||A_K||<1，也不把 pole 上界當成 transient 上界。共同 Q≻0 給 W_{m,K}≽Q 和 ||W_{m,K}^{−1}||≤||Q^{−1}||。因此 C*=||Q^{−1}||S*² 是 M2 的共同 affine-cross 常數，且

\[
E_H\le C_*\eta(\rho_0+\eta H)H=O(H^2)
\]

對所有 K／calendar 一致。Cauchy 公式中的 τ 次方、積分長度和 B 因子沒有遺漏。

## 3. β 的正緊緻下界、長 gap tail 與 dead-slot：通過

每個固定整數 ℓ 的 M、W 是 A_K 的有限多項式，W≽Q，故 β_K(ℓ) 在 K 上連續。M2 嚴格正性使用 L 可逆：β=0 迫使 A_KᵀQ^{−1}B=Q^{−1}B≠0，產生 eigenvalue 1，與 Schur 矛盾。因 ℓ∈{1,…,kmax} 是有限集，β*lo>0 和 β*hi<∞ 成立；即使 k(K) 不連續也不受影響。

共同 tail 界

\[
\beta_K(\ell)\ge(\ell+1)F-C_*
\]

使 ℓ≥L*=max{kmax,⌈2C*/F⌉,1} 時 β_K(ℓ)/ℓ≥F/2。對 1≤ℓ≤L*，固定 K 的 gap deletion monotonicity 給 β_K(ℓ)≥β_K(1)≥β*lo。故

\[
\inf_{K,\ell\ge1}\frac{\beta_K(\ell)}\ell
\ge b_*:=\min\{F/2,\beta_*^{lo}/L_*\}>0.
\]

finite prefix 與 infinite tail 的銜接正確；沒有從有限 JSON 值反推無窮 tail，也沒有在這一界多乘 F。

## 4. Converse 的雙重 uniform 量詞：通過

固定 ε,θ∈(0,1)，L=⌊H^{3/4}⌋。M2 對任意日曆的 signed tent 仍是一條完整 rate-r scalar 路徑，兩側以 z/2、−z/2 分別實現原 rate-r/2 預算。gap 中包括右側 first-retained input 的健康差均為零，故同一 T 的 count 和 dead-energy 兩個界可保留。

W_K=(1−θ)β_K(k(K))≤β*hi，b_K≥b*，所以

\[
A\ge\frac{32F\beta_*^{hi}r}{\theta^2b_*^2}
\]

是所有 K 的共同充分 absorption 條件。late macro 的 A≥ηεH+O(1) 對所有 K 使用同一 H 閾值。M=0 的全 missing macro 由同一 dead-energy 下界處理，不需要排除這類 calendar。

令 Cmacro=rA/2·(1−rL/(4A))。late 時 rL/A=O_ε(H^{−1/4})，coefficient 近似的總誤差為 O_ε(H^{3/2}L)=O_ε(H^{9/4})；run-count 的 WA² 懲罰和 Riemann 誤差也為 O_{ε,θ}(H^{9/4})。affine cross 和 ΣCmacro L 為 O(H²)。所有係數只依共同参数及 β*hi、b*、C*，不依 K、k(K) 的連續性或 calendar。

因此 U3 的共同 R_{ε,θ}(H)=o(H^{5/2}) 存在。先用 sup_K C(K)<∞ 選 ε／θ，再取共同 H 閾值，得到

\[
\sup_K[C(K)-H^{-5/2}D_H^{*,K}]_+\to0.
\]

沒有將 K 依賴的 little-oh 不加證明地取 sup；split 同一 T 時也仍只付一次 E_H。

## 5. Terminal packing 與 inactive cutoff 的顯式共同界：通過

ξ_K=2β_K(k(K))η/(Fr) 落在固定 [ξlo,ξhi]⊂(0,∞)。以下補出橋梁第4節引用的共同常數。

base n_l=2⌈ξl/2⌉ 滿足 ξl≤n_l<ξl+2。M 個 base blocks 的總時長為

\[
B_M=\sum_{l=1}^M2(n_l+k)=\xi M(M+1)+O((k_{max}+2)M),
\]

其中 O 常數共同。以 H−1 最大 packing 時，餘量小於下一個 block 長 2(n_{M+1}+k)=O(M+1)，共同係數只依 ξhi、kmax。把可分配的四槽均攤，每個 block 的 n_l 只增加一個共同有界的偶數，剩下1–4個 terminal +reads。因此存在 Cn<∞ 使

\[
\xi l\le n_l\le\xi l+C_n,\qquad
M=\sqrt{H/\xi}+O(1)
\]

共同成立。M=0 的有界小 H 不參與 asymptotic 閾值。

第 l 個 block 前至少經過 ξl(l−1) 槽，其 center amplitude 因此有共同下界

\[
A_l\ge\eta\xi_{lo}l(l-1).
\]

而 active 閾值的右側滿足

\[
\frac r2(k+n_l-1)\le\frac r2(k_{max}+\xi_{hi}l+C_n).
\]

左側為正係數二次式，右側為一次式，故存在共同有限 l0，使所有 l≥l0 均 active。l<l0 的總時長和 amplitude 均有共同上界，與 H／K 無關。這證明 inactive 只能發生於共同有限的 early blocks，而不是僅對每個 K 各自有限。

同時 A_l=ηξl²+O(l+1) 共同成立。因 ξlo>0，可逐項得到

\[
\sum A_l^2/n_l=O(M^4)=O(H^2),\quad
\sum A_l(n_l+k)=O(M^4)=O(H^2),\quad
\sum(n_l+k)^3=O(M^4)=O(H^2).
\]

這些分別控制 repair energy、support repair 和 auxiliary error；prefix／inactive 費用共同有界，1–4個 tail slots 費用 O(H²)。fixed gap 的 |L1|≤(kmax+1)C*/2，L2≤F(kmax+1)³，使 affine pair 的額外費用至多 O(M³)=O(H^{3/2})，均共同成立。

兩個 power sums 的共同版本是

\[
\sum A_l^2=\frac{\eta^2}{5\sqrt\xi}H^{5/2}+O(H^2),\qquad
\sum A_ln_l^2=\frac{\eta\sqrt\xi}{5}H^{5/2}+O(H^2).
\]

推導只用 Σl⁴=M⁵/5+O(M⁴)、ξ 的正上下界和上面的 O(l+1)／O(1) 界。所有 profiles 僅以 |g|≤1、projection contraction、D_l≥Fn_l 和 Ck≤2(kmax+2) 進入證明；不需要 profiles 隨 K 連續。

因此確有共同 CU，使 U4 成立。代 ξ_K 後 T3 首項與 C(K) 相同；U3／U4 合起來證明 U1。

## 6. 取 inf、k 跳變與唯一近優極限：通過

共同 oracle 使 exact identity

\[
O_H-\sup_{K,\pi}G_H(K,\pi)=\inf_KD_H^{*,K}
\]

成立。任意函数 f_H,C 若 sup|f_H−C|≤δ_H，則 |inf f_H−inf C|≤δ_H；套 U1 即得 U2，完全不需要先證明 inf／sup 達到。

**一般 k(K) 只有有限取值，並不自動只有有限跳點或使 C lower-semicontinuous。** 橋梁 U1／U2 不使用這種錯誤推論。第5節 scalar settling 的有限 plateau 與 lsc 則有額外證明：c_s=γ^{1/s} 在 compact interval 中只有有限個；c_s 本身使用短 k，從左連續，右極限因 κ 隨 k 嚴格增加而更大。因此 C(c_s)≤liminf_{c→c_s}C(c)，端點一側亦滿足，C 在整個閉區間 lsc。

settling 原稿的 strict fixed-k monotonicity 把每個 plateau 最佳放在包含的右端。精確 JSON 的 root isolation／正差證書把有限候選唯一最小值確定為 κ*=361/16561、c*=81/100，不依顯示小數排序。

因 F=1/q、β=κ/q，代入 C 得 U5 的係數

\[
\frac{\sqrt2}{5q}\sqrt{\frac{361}{16561}r}\eta^{3/2}.
\]

對任意 ε>0，取閉集合 Eε={c∈[4/5,19/20]:|c−c*|≥ε}。若它非空，lsc／compact／唯一最小值給

\[
\Delta_\epsilon:=\min_{c\in E_\epsilon}C(c)-C(c_*)>0.
\]

設 δH=sup_c|H^{−5/2}D_H^{*,c}−C(c)|→0。若 c_H∈Eε，則

\[
H^{-5/2}\{D_H^{*,c_H}-\inf_cD_H^{*,c}\}
\ge\Delta_\epsilon-2\delta_H,
\]

與 o(1) 近優條件矛盾。故 c_H→c*。此結論不包含未計算的收斂速度，也不聲稱 finite-H exact optimizer 已存在；若實際 joint pair (c_H,π_H) 近優，因 D_H^{*,c_H}≤D_H(c_H,π_H)，其控制器同樣趨 c*。

## 7. 反例嘗試及不接受的外推

**只有共同 pole 上界而無緊緻 transient 控制，不能取代第1節。** 取共同 Q=I₂、B=(0,1)ᵀ、

\[
A_N=\begin{pmatrix}0&N\\0&0\end{pmatrix}.
\]

所有 eigenvalues 都為0，但 S_B=1+N 無界；k=1 時 W₂=diag(1+N²,1)、M₂=(N,1)ᵀ，故 β_N(1)=1/(1+N²)→0。這個非緊緻族真實破壞 β／ξ 的正共同下界，說明 bridge 的 compact 性不是多餘裝飾。這不是其已聲明合同內的反例。

**finite-valued k 不保證 min 達到。** 在 scalar c∈[4/5,9/10] 上令 k(c)=1 當 c<9/10，k(9/10)=2。則 inf κ(c,k(c))=κ_{9/10}(1)=1/181，卻不達到；端點實值為2/91。這符合 bounded k 的一般形式，說明 U2 必須寫 inf，而不能從緊緻 K 單獨宣稱某個固定 K 達到。橋梁已正確保留這一區別。

**齊次 qualification 不能升級成完整 forced return。** e_{j+1}=ce_j+v_{j+1} 下，即使 |e0|≤E、c^sE≤ε，常數非零 forcing V 給 e_s=c^se0+V(1−c^s)/(1−c)，可任意大；Gaussian innovations 也有無界支撐。故 exact-k 兩方向 profiles 的真實重複可行性在 bridge 是解析合同的假設，並非 homogeneous inequality 的推論。U5 僅對這個合同成立，不能宣稱實機回管、飽和／actuator 預算或完整 noise-health-return 最優。

共同固定 SPD Q、B、原始 input budget、prefix、信息權限、deterministic calendar 都不可默默改變。singular／rank-changing noise、partial readings、unknown controller、H 隨動放寬穩定域不在此次接受範圍。

## 8. 定稿建議與驗收結論

建議整稿整合時保留本報告第5節的共同 packing／inactive cutoff 推導，並明寫一般 k(K) 無需連續、scalar settling 的 lsc 另證。這可避免讀者把 uniform theorem 看作把 pointwise little-oh 直接取 sup；數學結論本身不需修改。

共同 oracle 應在英文稿始終解釋為理想完整白色記錄且已扣除健康输入的 benchmark；它不是仍含健康 infimum 的 full-state composite information。此術語核對另列於 `manuscript_integration_review_v1.md`。

**接受：緊緻共同-SPD控制器族 U1／U2、共同 terminal-balanced U4、聲明的 homogeneous settling 合同 U5、以及 o(H^{5/2}) 近優序列 c_H→81/100。拒絕：把此接受解釋為任意穩定 controller family、完整 forced return、有限 H 風險／控制最優、硬件最優或整體投稿驗收。** 本次僅新增本審查文件，未修改根證明、稿件或台账。
