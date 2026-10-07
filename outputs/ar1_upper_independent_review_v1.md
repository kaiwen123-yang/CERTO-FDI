# 匹配达到构造的独立审查 v1

2026-10-07。根代理审查`ar1_upper_construction_v1.md`，冻结SHA256 `3de88ca76f497e2836e01abd8a1e9e997741a1af5b337f4a37964409735948b2`。审查者没有写该upper证明；逐式读U1–U16，并对照原iid局部KKT、AR(1)原始边界分解和已审converse。本审查不是数值拟合或全稿验收。

## 判定与范围

**接受U1–U2。** 在同一个M0固定参数、n0≥1、B=∞、deterministic known-horizon合同下，upper与已审T1的首项常数匹配，余项分别O(H²)与o(H^(5/2))，足以得首项sharp：

\[
D_H^{∞,*}=\frac{\sqrt2}{5}\sqrt{νβ_k r}\,η^{3/2}H^{5/2}+o(H^{5/2}).
\]

不接受H²次阶sharp、有限H误差常数、完整机械闭环的同一定理、一般控制器最优、随机/自适应日历或穷尽新颖性升级。合并正式TeX尚须核对符号和公式转录，编译状态另记。

## 核对1：Fenchel方向与半因子

对同一z，½(a−Sz)ᵀP(a−Sz)≥vᵀ(a−Sz)−½vᵀCv；对原完整类取inf给U4。令v=Pu，Oobs减掉对偶的Gaussian部分恰为½(a−u)ᵀP(a−u)。因此U5的三个成本是oracle缺测、辅助误差能量、健康支持，半因子正确，没有把profiling换成oracle测试。

## 核对2：全局precision与精确零矩

Retained precision的各连续边为dρ(e_i−e_j)(e_i−e_j)ᵀ，各gap边为[[A_m,−γ_m],[−γ_m,A_m]]，另有νI与仅全局首末cρ项。这由AR(1)边缘似然收集系数得到，跨人工块边界没有另加stationary项。

所有连续保留边两端任务相同；真实gap端点任务相反，辅助u两端恰相等。对gap取Pu得到δ_mW的两个相等raw权重，经S后为一正一负；连续边经S后也为相反的一对。νSu每块和为零。全局首末u=0使最后两个stationary修正消失。故U9及ΣSPu=0严格成立，包括负ρ，不需要再作近似中心化。

辅助u与统计方向v不同。prefix及尾部u=0不意味着v=0；Pu可能在相邻位置产生非零权重。这些真实读数及其协方差都保留，方差恒等式vᵀCv=uᵀPu使用一次完整C。

## 核对3：全史健康支持

自由初值下support有限的条件Σλ=0正确。逐增量自由选取给hK(λ)=rΣΔt|partialsum|。每个two-node zero-sum correction的support为rΔt|coefficient|，所以对U9使用sublinearity得到U10，符号方向正确。

局部λ0=as−zloc满足原iidKKT：局部各+residual非负，各−residual非正，累计权重与每个饱和增量互补，中心flat边的累计权重为零。故h0=(as−zloc)ᵀzloc=a r n(n+2k)/2−4r²Σ(c0+j)²。原稿的Lc与h0不是同一式，upper在U7正确区分二者。

全局路径restriction给hK(global λ0)≤Σh_local；没有要求局部primal路径能拼接。人工块间的辅助跳变进入连续边pair correction，其support跨度为1；真实gap correction跨度为k+1。两者按实际时间支付。

## 核对4：余项

每块内部u的同任务variation≤r，各块中心幅值a_l=O(l²)。人工接缝、初末join总variation≤2Σa_l加O(H)内部项，故O(H^(3/2))；两个gap端点W每块≤a_l，同为O(H^(3/2))。负ρ的dρ、δ_m取绝对值后都是固定常数。

实际a−u包含仿射增长η(t−c)和局部zloc，逐点为O(n_l+k)。统一谱界||P_R||≤(1+|ρ|)/(σ²(1−|ρ|))作用于整个保留向量，给Σn_l(n_l+k)²=O(H²)。1–4个末尾实际读数的a为O(H)，它们也只贡献O(H²)，未留下O(√H)长尾。

early inactive块仅有限个，因为a_l=Θ(l²)，阈值Θ(l)，packing增量对每块uniform O(1)。prefix和这些早期块能量均O(1)，保留而不借重置忽略。

## 核对5：gap费用与渐近常数

每个gap的仿射反射恒等式包含两个保留端点；两gap中心是block中心±(n+k)/2。相加严格给β a_l²+βη²(n_l+k)²/4+η²E_k。主项为βΣa_l²，其余O(H^(3/2))，无需把单槽边界噪声视为iid。

Terminal packing预算H−1，均摊multiple-of-four padding，每块新增n为O(1)，剩下1–4槽实际读取并设u=0。于是M=√(H/ξ)+O(1)，n_l=ξl+O(1)，a_l=ηξl²+O(l+1)。两个leading sum分别η²H^(5/2)/(5√ξ)与η√ξH^(5/2)/5，其余O(H²)。U1系数为(1/10)(2βη²/√ξ+νrη√ξ)，在ξ*=2βη/(νr)给√2√(νβr)η^(3/2)/5，准确匹配T1。

## 证据与剩余工作

配套`ar1_upper_checks_v1.py/.json`报告39个全日历精确检查，其中30个逐元素保留完整C_R核对，410个局部support检查。审查没有再次运行已通过检查；代数接受依据上面的完整推导与实际源文件，有限测试只作实现支持。

下一步将下界和上界整合为同一正式定理并检查转录；继续M1物理控制桥梁、D2-a完整表、文献缺口与论文。这个数学子目标达到不意味着长期goal完成。
