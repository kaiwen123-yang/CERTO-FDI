# 固定终点风险代价推论 v1

2026-10-07。绑定现稿R7 source `a26c945e35a8da9c598a5b94fe34f528a19025a652b335a457c4f9fa65626eca`。**在已有精确线性合同和风险接口内，三个候选结论成立；这是现主定理的risk解释，待root/ar1独审，不列为独立主要创新。** 只新写本md、英文tex fragment及json，不改paper、不新开native tab、不编译、不重跑旧matrix/D2；四篇全文缺口不变。

## 1. 量词与结论

固定已知有限维Schur控制器、固定full-column Gaussian factor、非零$B\in\mathrm{range}G$、已知初始化/full-read prefix、完整retained states、每侧free-level全input-clock scalar健康path rate≤r/2，以及noise前选好的deterministic calendar和双向可重复exact-k profiles。固定miss $\varepsilon_{\rm m}\in(0,1)$，取$0<\alpha<1-\varepsilon_{\rm m}$后令$\alpha\downarrow0$。

令$\Lambda_\alpha=(z_{1-\alpha}+z_{1-\varepsilon_{\rm m}})^2/2$、$n=H_{\rm or}=\min\{H\ge1:O_H\ge\Lambda_\alpha\}$。$H_{\rm diag}$必须按**存在实际legal calendar/test**且uniform PFA≤α、power≥1−miss定义，不能把sup=Λ自动当可行。Oracle是ideal healthy-subtracted完整white record，不是仍有健康infimum的full-record experiment。

- $\beta_k>0$时：$H_{\rm diag}-H_{\rm or}=\frac{2C}{F\eta^2}\sqrt{H_{\rm or}}+o(\sqrt{H_{\rm or}})=\frac{2\sqrt2}5\sqrt{\beta_k r/(F\eta)}\sqrt{H_{\rm or}}+o(\sqrt{H_{\rm or}})$。
- $\beta_k=0$时：仅$0\le H_{\rm diag}-H_{\rm or}=O(1)$；不主张Θ(1)/统一正整数下界。
- 既有共同SPD紧致family：允许noise前选择known K，joint excess同式换$C$为$C_{\inf}=\inf_K C(K)$；不假k连续/min或sup达到。

这些都是计划的整数endpoint差，**不是sequential stopping、ARL或$\mathbb E\tau$**。共同prefix时长固定，若换物理时长，仅给该差乘同一slot duration。不能外推到独立D2的H≤600/f≤.045/event-budget域。

## 2. 完整反演证明

**Oracle量子。** 精确求和为
\[
O_H=\frac{F\eta^2}6H^3+
\left(\frac{F\rho_0\eta}2+\frac{F\eta^2}4\right)H^2+
\left(\frac{F\rho_0^2}2+\frac{F\rho_0\eta}2+\frac{F\eta^2}{12}\right)H.
\]
设$B_{\rm or}=F\eta^2/2$。因$n\to\infty$及minimality，$0\le O_n-\Lambda_\alpha<O_n-O_{n-1}=F(\rho_0+\eta n)^2/2=O(n^2)$。固定M、$0\le h\le M\sqrt n$时，精确cubic展开给$O_{n+h}-O_n=B_{\rm or}n^2h+O_M(n^2)$；固定整数L则误差降为$O_L(n)$。整数overshoot不能忽略，但正分支相对$n^{5/2}$是lower order。

**排除全部较早H。** $z=0$和projection contraction给任何π的$G(π)\le O_H$，故H<n一律不可行。正分支令$d=C/B_{\rm or}$，已有极限蕴含$e_n=\sup_{H\ge n}|D_H^*/H^{5/2}-C|\to0$。对每个整数$n\le H\le n+\lfloor(d-\delta)\sqrt n\rfloor$，$G_H^*-\Lambda_\alpha\le-B_{\rm or}\delta n^{5/2}+e_n n^{5/2}+O(n^2)<0$。这里使用同一个tail error，覆盖全部较早endpoint，没有假G*单调。

**真正的upper可行设计。** 取$H=n+\lceil(d+\delta)\sqrt n\rceil$和已证$\xi_*$calendar，$D(π)\le C H^{5/2}+M_KH^2$。于是$G(π)-\Lambda_\alpha\ge B_{\rm or}\delta n^{5/2}+O_\delta(n^2)>0$，exact风险接口提供实际test。可行endpoint集合非空、自然数最小值存在；再让δ↓0得首项。sup是否达到完全没有用到。

**Zero分支。** 用已证profile-aware实际calendar的$D(π_H^0)\le M_0H^2$。选固定整数L使$B_{\rm or}L>M_0$，则$G_{n+L}(π)-\Lambda_\alpha\ge(B_{\rm or}L-M_0)n^2+O_L(n)>0$。与oracle排除合得$0\le H_{\rm diag}-n\le L$。未知quadratic常数和同阶oracleovershoot都不能转成正时间常数。

**Joint分支。** 既有uniform theorem及共同strict-positive beta下界给$C_{\inf}>0$和一个uniform H-tail，故上述lower对全部K/π/较早H有效。固定δ后选择固定$K_\delta$满足$C(K_\delta)<C_{\inf}+B_{\rm or}\delta/2$，在$n+\lceil(C_{\inf}/B_{\rm or}+\delta)\sqrt n\rceil$用其explicit calendar，得到至少$B_{\rm or}\delta n^{5/2}/2+O_\delta(n^2)>0$的strict margin。先α极限后δ↓0即可；没有偷换pointwise与family优化或引入未知K的robust test。

## 3. Mills自推及risk尺度

$\phi(t)=(2\pi)^{-1/2}e^{-t^2/2}$，$I(t)=\int_t^\infty\phi(u)du$。$u/t\ge1$给$I(t)\le\phi(t)/t$；分部积分给$I=\phi/t-\int_t^\infty\phi(u)/u^2du\ge\phi/t-I/t^2$，故$t\phi/(t^2+1)\le I\le\phi/t$。在$t=z_{1-\alpha}\to\infty$取log，$\log(1/\alpha)=t^2/2+\log t+O(1)\sim t^2/2$；固定miss quantile只增加O(t)，所以$\Lambda_\alpha\sim\log(1/\alpha)$。因而$H_{\rm or}\sim(6\log(1/\alpha)/(F\eta^2))^{1/3}$，positive excess阶为$(\log(1/\alpha))^{1/6}$。这段是直接推导，没有借未经核对的外部文献。

## 4. 精确反例：不能普遍加强zero结论

用既有允许copy plant：$A_K=[[0,1/2],[0,0]]$、$G=B=e_2$，$n_0=1,\rho_0=0,\eta=1,r=1/100,k=1$，missing g=0双向profiles。$H_2=[e_1/2,e_2]$给$P_2=I_2,\beta_1=0$。重复post pattern +1,0,−1,0；H偶数时把末missing改为持续hold，确保H实际read，所有span≤2，故完整input投影P=I。

prefix $g_0=1$使完整累计$|S_t|\le3$。Abel给$|N|=|\gamma^T\theta|\le6H$，$D=\|\gamma\|^2\ge H/2$，repair coefficient $|N/D|\le12$。$v=\theta-(N/D)\gamma$的scalar总mass为0，partial masses≤18(t+1)。现有full-path support/observable dual给$D(π)\le9H^2/100+3609H/100<H^2/4$（所有整数H≥226，差为$H(16H-3609)/100>0$）。

取$\Lambda_H=O_H-H^2/4=H^3/6+H/12$及$\alpha_H=1-\Phi(\sqrt{2\Lambda_H}-z_{1-\varepsilon_{\rm m}})$，则α_H↓0、$O_{H-1}<\Lambda_H<O_H$且实际calendar的G>Λ_H。因此$H_{\rm diag}(\alpha_H)=H_{\rm or}(\alpha_H)=H$。该例仍有已证quadratic信息损失，却沿此序列没有额外整数endpoint；它反驳的是Θ(1)/统一正代价加强，不是O(1)候选。没有数值拟合、Monte Carlo或改变D2物理参数。

## 5. 交付与边界

英文fragment：`outputs/fixed_endpoint_horizon_corollary_v1.tex`，无preamble/documentwrapper，全部fresh label用sf:，可与现稿连接；静态label/ref核查通过，未编译或打开新tab。JSON记录scope、全部推导、source SHA与新做的exact Fraction多项式系数恒等式；不是重跑既有checks。三个候选在冻结合同内未发现反例，但仍须root/ar1对新字节独审后才考虑入正文；现R7未改。
