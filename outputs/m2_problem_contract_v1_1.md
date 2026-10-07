# M2 合同 v1.1：固定阶矩阵植物、完整状态读数与共同标量输入

冻结日期 2026-10-07。这是 M1 scalar proof之后单独声明的扩展合同，M1文件不作覆盖。它不涉及任意向量nuisance或一般partial-state observation；只有一个完整 scalar健康路径，通过固定非零向量B进入已知矩阵植物。

## 1. 同一物理植物与固定已知反馈

\[
x_j=A x_{j-1}+B_u u_j+B(\mathbf1_{h=1}a_j+g_j b_j^h)+w_j,\qquad
u_j=-Kx_{j-1},\qquad A_K=A-B_uK.
\tag{M2.1}
\]

维数d固定，A∈R^{d×d}、B_u∈R^{d×p}、K∈R^{p×d}已知，B∈R^d固定非零。每个h下w_j独立N(0,Q)，Q≻0已知固定，创新与nature预先选择的健康路径独立。固定A_K严格离散稳定，即spectral radius(A_K)<1；不要求normal，也不把||A_K||<1当成必要条件。

初始x_{−n₀}=0已知，n₀≥1固定。所有slots，包括missing，都持续执行同一反馈和植物递推；状态/噪声/健康路径都不reset。不同已知K的比较保留A、B_u、B、Q、a、健康类及读数协议；fault、health和noise均通过同一个F_{A_K}动态映射。这里没有state measurement noise、饱和、tracking/actuation预算或unknown plant。

严格稳定保证存在依赖该固定K的C<∞、α<1使||A_K^j||≤Cα^j。任何未来controller族下的uniform claim都须另外给出统一稳定和非退化常数；本合同不许可pole随H靠近unit circle或nonnormal transient无界后沿用fixed-K余项。

## 2. 同一时钟与完整状态受限协议

Prefix j=−n₀+1,…,0任务g=+1，state vector全部读取，fault a_j=0。之后post-onset H槽在开始前已知，a_j=ρ₀+ηj，ρ₀≥0、η>0，已知scalar故障template。

Holding时g=±1、每槽读一次完整x_j。改变任务至少k≥1个连续slots不给诊断器state vector；其中g_j预先已知、|g_j|≤1，输入B(a+gb)与innovation仍作用。固定k长移动有允许的known profile，matching calendar只需要它，对gap profile不作事后调优。

诊断器读取retained full states、known calendar/g、A,B_u,K,B,Q、初始state和template；不读取fast internal states/control commands或其他旁路。控制器可以内部获得反馈所需full state。完整状态读数是假定的解析通道，不等于完整机器人的所有传感器；partial observation须另建模型。

允许较长moves、consecutive moves、empty round trips；无terminal task obligation，最后无后续read的moves可由原任务继续full-state readings支配。Calendar及g在噪声产生前固定，nature随后选两条完整健康路径，再产生innovations。所有H和parameters都固定于实验规划时。

## 3. 只有一个scalar nuisance，保留两侧量词

每个h有独立可选的完整scalar b^h，幅值无界、自由初始level、slot差分rate≤r/2，r>0。差分z=b^0−b^1的实际类为

\[
\mathcal Z_H=\{z\in\mathbb R^{H+n_0}:|\Delta z_j|\le r\}.
\]

z/2与−z/2分别实现原两侧paths，piecewise-linear interpolation实现时间域健康路径。已知初始state不固定健康level。未知健康输入只能为B g_j b_j；不允许每个坐标/方向独立nuisance、不改变B、不逐block重挑起点。

缺测期完整scalar z影响后续vector state，所以不能把所有unread input健康nodes删除。最坏case和profiling必须作用于同一完整z。

## 4. 完整输入白化与真实保留创新

取固定square factorL使Q=LLᵀ，f=L⁻¹B，F=||f||²=BᵀQ⁻¹B>0。完整创新noise L⁻¹w_j独立N(0,I_d)，完整fault/health mean在每槽都沿同一f。

对前一真实retained state（首项为已知初始化）和下一retained state之间span m，conditional innovation为

\[
x_{t_i}-A_K^m x_{t_{i-1}}
=\sum_{r=0}^{m-1}A_K^rB(a_{t_i-r}^h+g_{t_i-r}b_{t_i-r}^h)
+\sum_{r=0}^{m-1}A_K^r w_{t_i-r}.
\]

协方差

\[
W_m=\sum_{r=0}^{m-1}A_K^rQ(A_K^r)^\top\succeq Q\succ0.
\]

设H_m=[A_K^{m−1}L,…,L]，T_m=W_m⁻¹/²H_m，则T_mT_mᵀ=I_d，span projection P_m=H_mᵀW_m⁻¹H_m。不同span使用不相交的真实innovation blocks，全局T row-orthonormal、P=TᵀT是完整白化input空间的orthogonal projection。人工proof block joins若前后state都实际观测，下一span仅长度1；这不reset state输出covariance。

定义完整白化fault vector a_f=(f a_j)_j和health映射 H_g z=(f g_j z_j)_j，真实信息为

\[
G_H(\pi)=\frac12\inf_{z\in\mathcal Z_H}\|P_\pi(a_f-H_gz)\|^2.
\tag{M2.2}
\]

完整state联合covariance仍是共同F_{A_K}传播Q的covariance，跨block项保留。未被末次read覆盖的terminal input columns在P中为0；不能人为给它们一个conditional innovation。

## 5. Oracle和候选gap系数

完整记录的共同可逆whitening把整个composite experiment还原为同一独立vector创新实验，oracle

\[
O_H=\frac F2\sum_{j=1}^H a_j^2,\qquad
D_H^*=O_H-\sup_\pi G_H(\pi)
\]

对固定已知controller中性。保留states后的projection随实际A_K变化，所有signal/health/noise同步变化。

m=k+1，令

\[
M_m=\sum_{r=0}^{m-1}A_K^rB,\qquad
\beta_K(k)=mF-M_m^\top W_m^{-1}M_m.
\tag{M2.3}
\]

候选fixed-K leading sharp系数为

\[
\frac{\sqrt2}{5}\sqrt{F\beta_K(k)r}\,\eta^{3/2},\qquad
\xi_*=\frac{2\beta_K(k)\eta}{Fr}.
\tag{M2.4}
\]

合同冻结不预设该候选成立。承重任务：严格β>0/monotonic/asymptotic、nonreflection affine cross全日历O(H²)、合法scalar完整对手、vector innovation-range对偶的单个scalar weighted-zero约束、matrix方向修复energy/support、actualjoin与½因子。未知vector nuisance、partial outputs、singularQ、unknownA_K、controller无uniform稳定的H-dependent比较、finite幅值盒与硬件风险均不在本版结论内。


## v1.1 编辑澄清与版本边界

本版是独立文件，原 v1 合同与绑定它的审查快照保持不变。Sharp 首项、完整 nuisance 类及物理信号/噪声模型不变。达到性明确需要 +→− 与 −→+ 两个方向各有预先已知的 exact-k bounded profile，并能在任意预定起点与 holds 重复串接。允许 profile 随该预定起点变化，证明只用长度 k 与 |g|≤1；若缺少双向可串接操作，converse 仍成立，上界不能自动引用。

日历动作集合未假定 closed，因此最优信息写 sup，不要求某个有限-H 日历达到该上确界。Scalar 表达式 gz、gv 均指逐节点乘积 diag(g)z、diag(g)v；M2 的 H_gz=(fg_jz_j)_j 与 scalar dual weights (g_jf)ᵀv_j 不变。半个 held run 在 proof 中记 h=n/2，真实 gap input span 仍记 m=k+1。

原 v1 合同 SHA256 794c245d0fdb672021cb36566382d68834b2abe20331dde0bc01a0bc71671eae。
