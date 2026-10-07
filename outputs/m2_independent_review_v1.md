# M2 矩阵 controlled-memory 定理独立审查 v1

2026-10-07。**判断：在冻结的 fixed-order、fixed known strictly stable A_K、B≠0、Q≻0、完整状态读数和单条完整 scalar 健康路径合同内，匹配首项 sharp 证明成立，未见承重数学漏洞。** 正定 Q、完整状态和 scalar nuisance 都真正参与证明，不能泛化成 PSD、partial observation 或任意 vector nuisance 定理。

需要整稿/计算修订：区分 half-hold m 与 gap-length m；明确双向 k-slot 转换可串接及 max/sup 条件；补 α≠0 的不对称 gap profiles。现有68个 calendar 的修补能量全为0，本轮补了一个矩阵非零见证，但没有修改或重跑正式整表。

## 1. 冻结版本与审查覆盖

|文件|SHA256|
|---|---|
|`m2_problem_contract_v1.md`|`794c245d0fdb672021cb36566382d68834b2abe20331dde0bc01a0bc71671eae`|
|`m2_controlled_memory_theorem_v1.md`|`38d2aecf2d00a6a781f0a99f6448d93a4d2fcccd1e895526ca3c5fed2c3455b1`|
|`m2_controlled_memory_checks_v1.py`|`9e463be6d3b6a7bfe4fc2363674cfb2eaef79e21d40e669a3056df7683079420`|
|`m2_controlled_memory_checks_v1.json`|`d99e688f7d527798edacc697e46822fd76898baa5f912aeafc8ecded9ec22559`|

文件均在 `outputs/`。完整读取合同与 Markdown 证明，逐式核 T1–T3、P1–P2、B1–B2、G1–G3、C1–C2、U1–U11；读取正式 checks 实现和JSON结果。只执行第7节的有限2×2 Fraction代数。没有重跑150个 retained subsets、68个 calendars、413个局部修补，也没有审查/借用正在写的 M2S 主定理或其 β=0 regimes。

## 2. 因果植物、真实 retained experiment 和单条 Z：通过

`u_j=−Kx_(j−1)` 给已知 A_K=A−B_uK；状态初值为已知0，非 stationary 初始化。B 作用于同一个 scalar fault/health 输入，Q是原始过程创新协方差；不同K时保持植物A、B_u、B、Q及输入模板/健康类/信息权限。

固定 L 可逆、Q=LLᵀ、f=L⁻¹B，则F=||f||²=BᵀQ⁻¹B。跨真实 retained states 的 Markov递推给 H_m=[A_K^(m−1)L,…,L]，W_m=H_mH_mᵀ≽Q≻0。用W_m的正定平方根白化，T_mT_mᵀ=I_d，P_m=H_mᵀW_m⁻¹H_m为完整白色input空间orthogonal projection。

不同 spans 使用互不相交的原始innovations，前一 predictor是实际读到的state（首项为已知初始化），因此全局T/P等价于保留state联合Gaussian实验。state covariance的跨block项仍存在，不能据T的独立innovations写raw state blocks独立或reset。

健康差是同一完整scalar z，包括所有missing input nodes。两侧分别rate r/2，由z/2和−z/2实现；没有每个state coordinate独立的未知路径。任意vector dual v对应的scalar健康权重为 `(g_j f)ᵀv_j`，所以free healthy初值只要求一个weighted-zero约束。这正是P2的信息对象。

原完整input experiment共同可逆白化后oracle为 `FΣa_j²/2`。prefix fault=0，已知初始state不表示已知healthy初始level；所有prefix/state/innovation history均保留。terminal 无后续read时P未覆盖列为0；继续原task并追加reads是逐完整路径的信息支配，在无terminal task义务合同内合法，故最优可限x_H被读。

## 3. 严格 β、long-gap tail 和 affine cross：通过

constant white-input向量为 `d_m=1_m⊗f`，H_m d_m=M_m，故β=d_mᵀ(I−P_m)d_m≥0。若m≥2且β=0，则d_m在rowspace(H_m)，即H_mᵀy=d_m。最后两个input blocks给

\[
L^\top y=f,\qquad L^\top A_K^\top y=f.
\]

L可逆，第一式确定 `y=L^(−T)f=Q⁻¹B≠0`；第二式迫使A_Kᵀy=y，即单位特征值。严格稳定排除此情形，所以β>0。若Q奇异，不能取消Lᵀ；正文shift-register反例正确展示stable闭环也可β=0，故SPD不是装饰条件。

扩大同一gap对应同一个initialized full-state constant-input experiment的nested deletion；data processing给β(ℓ)非降。严格稳定（不要求normal或||A_K||<1）保证S_B=Σ||A_K^rB||有限，W_m⁻¹≼Q⁻¹给

`β(ℓ)≥(ℓ+1)F−C_K`，`C_K=||Q⁻¹||S_B²`。

又β≤(ℓ+1)F，所以β(ℓ)/ℓ→F。L0=max(k,ceil(2C_K/F))的tail≥F/2，有限prefix由monotonic给β(k)/L0，B2的严格正 b_K及其下界正确。实际“computable”证书需给一个已验证的有限S_B上界；一般stable矩阵可选择||A_K^s||<1的有限power，再给block-geometric尾和，不能从有限160个β值反推无穷tail。

正式checks五个model所用norm multipliers可独立核：zero2为1，diagonal2的Σ||A^r||1≤2，rotation2因||A||1=9/10得≤10，Jordan3的binomial展开给2+4+8=14；nonnormal2用两列的geometric和可得≤26/3<18。结合||A^rB||2≤||A^r||1||B||1与对称Q⁻¹的spectral norm≤row∞norm，其Sbound/Ccross使用方向安全。

对于d_h=(h_j f)_j，d_mᵀd_h=FΣh_j=0，所以L1=−M_mᵀW_m⁻¹N_m的负号正确。||N_m||≤mS_B/2给|L1|≤mC_K/2，L2≥0，因此 G1 完整保留nonreflection cross，不假定A_K normal。

non-singleton spans包含右retained input，互不相交且位于post-onset affine区间，Σm≤H。故所有negative cross一次合计为 `E_H=C_Kη(ρ0+ηH)H=O(H²)`，对任意calendar、任意long gap/dense moves一致。每个missing amplitude≤2A，G3的 b_K/4 系数正确，没有额外F：β及b_K本身已经以white-vector能量单位包含F。

## 4. Converse 的 F、两侧量词和同一个 T：通过

signed tent是在完整input nodes上的一条合法scalar z；held g=±1，故h=gz为非负tent，missing、run endpoints与right-first retained input均取0。z/2与−z/2各满足原单侧rate预算。gap中所有white healthy blocks f h均为0，所以从同一P得到

\[
2D\ge F\sum(2ah-h^2)+T,
\]

T为所有实际matrix gap norm losses之和。F仅乘iid white saving；gap项T已含β/F，不能再乘F。

macro tent area≥(n²−2n)/4、高度≤rL/2，给C=r(2A−rL/2)/4；saving≥F(CΣn_i²−2CL)。macro内完整gaps给同一T的count界，G3给同一T的dead-energy界。split `(1−θ)T+θT` 后cross error仍 `(1−θ)E_H+θE_H=E_H`，没有双收T。

Cauchy/AM–GM的主项是 `2A√(FCW)(L−d)`，W=(1−θ)β(k)。利用C≤rA/2，吸收条件为

\[
A\ge\frac{32FWr}{\theta^2b_K^2},
\]

与正文一致。M=0,d=L也由dead项覆盖，不需每macro有读数或runs平衡。L=H^(3/4)下macro取整、coefficient与未用tail误差O(H^(9/4))，ΣA²为O(H^(9/4))、ΣCL为O(H²)，cross为O(H²)，对calendar一致。

固定ε/θ先取H极限、随后ε/θ趋0，Riemann主项和归一化2D给 `√2/5·√(Fβr)η^(3/2)`。没有漏掉1/2、没有以observed-node健康trace替代完整Z，也没有把不同macro对手当独立paths。

## 5. Upper 的实际join、分母与vector修补：通过

terminal-balanced两侧join states均实际读到，下一span长度1；所以P在white-input空间按block direct sum。这不是state covariance独立。H−1 packing及四槽均摊保证最终1–4个tail reads；base leftover O(M)平均到M块，每n只加O(1)，从而U1正确。未形成一块的小H可用stay，不影响asymptotic结论。

用p=n/2表示half-hold时，active条件使held scalar auxiliary∈[0,A]，missing为A，vector auxiliary都乘同一个f。baseline scalar权重是F(gA−zloc)，其总和0与support恰为M1 baseline乘F；补missing零权重保留真实k+1时间跨度。

令h=(g_j f)_j、pvec=P h、N=hᵀPU、D=||pvec||²。除两个gap-right inputs外，剩余2n−2个held inputs为singleton且P=I_d，所以

\[
D\ge F(2n-2)\ge Fn>0.
\]

这需要full-state reading；partial outputs不能自动沿用。

每gap `Σ|h_jᵀ(PU)_j|≤√(mF)||PU||≤mFA`，baseline在span中只含一个≤FA的rightheld值，因此|N|≤C_kFA、|α|≤C_kA/n。`v=PU−(N/D)P h` 精确给hᵀv=0与Pv=v；energy为N²/D≤C_k²FA²/n。N²有F²、D下界有F，因此修补energy只剩一个F，正文因子正确。

δλ_j=h_jᵀv_j−λ0_j为零质量，`Σ|h_jᵀpvec_j|≤||h||||pvec||≤LF`给U7。完整scalar Z的support为rΣ|partialsum|，每partialsum≤L1/2；累计δsupport为O(FrΣA(n+k))=O(H²)。这是全史support，不是逐块重置未知level；missing g可以为任意已知[-1,1]数，不要求P U非负、g有reflection或dynamics可对角化。

实际statistic可用Tv作用于真实conditional innovations，variance=||v||²。Fenchel及orthogonal decomposition给U9；没有再乘/除q，因为Q已被L白化。辅助energy全体乘F，tail O(H²)、finiteinactive O(1)、Σn³与ΣA²/n为O(H²)，给U10。

## 6. Affine pair、首项与同B/Q控制比较：通过

两gap input centers的共同偏移为1/2，具体为 `1/2±(n+k)/2`。不反射第二gap的matrix weights，所以U11的两个center amplitude之和是2(A+η/2)，cross为4η(A+η/2)L1，另有βη²(n+k)²/2及2η²L2；所有项正确。fixed k/K下ΣA与Σ(n+k)²=O(H^(3/2))，故oracle gap loss为2βΣA²+O(H^(3/2))。

结合support/repair，

\[
2D(\pi_H^\xi)\le2\beta\sum A_l^2+Fr\sum A_l n_l^2+O(H^2),
\]

两power sums给T3，ξ*=2βη/(Fr)与converse匹配，支持固定参数首项sharp。Scalar reduction Q=q、B=1 gives F=1/q、β=κ/q，所以系数还原为M1的 `√2/(5q)√(κr)η^(3/2)`；没有将F或β误平方。

给定同一Aplant、B_u=I、B=(1,2)、Q的两controller，确实分别产生diagonal与nonnormal AK且特征值相同。小Fraction复算确认 `F=29/4`、`βdiag=1343/344`、`βnonnormal=18007/10456`。因此所列leading deficit比值有效，完整oracle不变。它不比较actuation/energy/tracking预算，也不支持实际机器人最佳controller；large-H sanity按各model调整r不能用于真实跨controller排名，文稿已正确区分。

## 7. 现有checks未覆盖α≠0，新增矩阵见证

读取JSON：60个finite calendars和8个larger sanity的repair_energy全部0。三类missing profiles使两gap的g互为相反、U的span模式相同，N跨gap抵消。413个repair equality checks确实执行，但没有检验非零α；应加不对称profile。

本轮使用同一nonnormal2 channel、L=[[1,0],[1/3,2/3]]、f=(1,5/2)，取k=1、n=4、A=10、r=1、η=1/7；10个input nodes为

`g=(1,1,1/3,−1,−1,−1,−1,−2/3,1,1)`，

`U_j=f·(8,9,10,9,8,8,9,10,9,8)_j`。

真实spans为singletons1、2、5、6、7、10及[3,4]、[8,9]。用2×2 W inverse/rank projection独立计算：

|量|精确值|
|---|---|
|F|29/4|
|N=hᵀPU|−22863/1307|
|D=||Ph||²|628321/10456|
|α|−182904/628321|
|repair energy=N²/D|4181734152/821215547|
|repaired weighted mass|0|
|baseline support|725|
|δsupport|443834782533/3284862188|
|repaired support|2475297671605/3284862188|
|matrix affine pair loss|351922007/1024688|

逐项核Pv=v、D≥F(2n−2)、U5/U6/U7及support subadditivity；affine pair loss也与U11一致。所有运算为Fraction，α真正非零，未重跑原整表。未经修补的PU有非零healthy weighted mass，完整Z含自由level，support会无穷；修补不是可略工具。

## 8. 整稿修订与边界

- 将half-hold写p=n/2、gap span写m_gap=k+1；当前m有两种含义。正文scalar weighted λ也宜显式定义为h_jᵀv_j。
- Upper需要 +→− 与−→+ 两方向k槽转换均可反复串接、实际+join/tail读取合法。本无state/actuator/tracking限制类可按已知profile构造；更窄physical protocol需单独验证。
- 若g profile是固定或全闭盒[-1,1]内可选，max可由有限mask及upper-semicontinuous G在compact profile集上达到；未声明的非闭允许集应写sup或补存在性，系数证明不依赖max达到。
- 增加不对称profile/nonzeroα正式checks后绑定新哈希，不将全部零修补计数称为一般修补的数值覆盖。
- 本审查不接受M2S新稿或β=0 regimes。SPD/full-state/scalar-Z、common B/Q、known stable AK、deterministic initialization/calendar是本次通过范围；unknown/partial/singular/multiplicative models另审。
- 固定K首项排序不等于finite-H risk最优；没有actuator预算不能冒称机器人最优。H-dependent或不受uniform transient控制的K族不可沿用这些余项。编译状态与数学/有限算术状态分开，本审查没有证明TeX编译成功。

结论限于**当前冻结M2完整状态标量健康输入原型的首项sharp证明**，不自动关闭TAC整体goal或机械实现/新颖性验收。
