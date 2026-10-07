# 共同输入记忆模型的非零质量修复补充 v1

2026-10-07。仅补充计算覆盖，M1/M2/M2S 的 frozen v1 合同、证明、审查绑定及原 checks 不变。原 M1 的129个、M2 的68个、M2S 的186个完整 calendar records 的 repair energy 全为零（镜面对称 gap profiles）。这些记录及其局部代数证书验证了恒等式和上界，但不能声称实际覆盖 α≠0 的修复分支。

新正式脚本 outputs/memory_asymmetric_repair_checks_v1.py（SHA256 0411fba7daac9948bb6d3a1a3687f657f0bb9e21f8779cf04ced9852dcb96db1），报告 outputs/memory_asymmetric_repair_checks_v1.json（SHA256 ba6e9936cccf6c32685298af971904217a6d1e88615d1ada47078c5bc3496576）。Standalone，仅标准库 Fraction，无外部 helper import；执行只跑六个新例，没有重跑原大表。

所有例有一个真实 prefix reading、已知 x_{−1}=0、post horizon H=10、k=1、n=4、halfhold h=2、真实 gap input span m=2、r=1、η=1/7、ρ₀=129/14、block center A=10。完整 task/auxiliary/baseline：
\[
g=(1;\,1,1,\tfrac13,-1,-1,-1,-1,-\tfrac23,1,1),
\]
\[
U=(0;\,8,9,10,9,8,8,9,10,9,8),\quad
\lambda^0=(0;\,8,9,0,-9,-8,-8,-9,0,9,8).
\]
矩阵例将 U 乘固定 whitened input f、baseline 乘 F。真实 spans 为 prefix singleton、post singleton 1,2,5,6,7,10 和 gaps [3,4],[8,9]。局部 repair h_block 在 prefix为0，保留实际 full健康 coefficient h=(g_jf)_j；最终 v_prefix=0，所以实际完整零质量与局部约束一致，没有免费删 prefix nuisance。

|新例|修复前 N|D|α=N/D|N²/D|
|---|---:|---:|---:|---:|
|M1 c=−1/2|8/15|383/45|24/383|64/1915|
|M1 c=1/2|−28/15|311/45|−84/311|784/1555|
|M2 nonnormal SPD|−22863/1307|628321/10456|−182904/628321|4181734152/821215547|
|M2 scaled-copy SPD|−125/39|1997/234|−750/1997|31250/25961|
|M2S scaled-copy singular|−10/3|77/9|−30/77|100/77|
|M2S partial constant mode|−13/2|89/6|−39/89|507/178|

M2 nonnormal 使用 frozen M2 的 A_K=[[1/2,2],[0,1/4]]，B=(1,2)，Q=[[1,1/3],[1/3,5/9]]。Scaled-copy A_K=[[0,1/2],[0,0]]、B=e₂，SPD Q=diag(1/100,1)、singular G=e₂。Partial-constant 使用3D shift A_K=[[0,1,0],[0,0,1],[0,0,0]]、G=[e₂,e₃]、B=e₂+e₃，只保留 constant force mode而非全部 inputs。

六个例全部精确验证：
- N≠0、α≠0、repair energy>0；修复后 full scalar mass精确0、Pv=v。
- D lower bound、N/energy/support upper bounds、repair energy精确 N²/D。
- 无幅值盒健康类：未修复 scalar mass非零，所以 support为无穷；修复后的完整 input support有限。
- 将 latent v 真实拉回 retained-state statistic，再通过整个 initialized plant做 backward adjoint；产生的每个独立 process-noise coefficient 精确等 v，variance精确 ||v||²。Prefix noise已包含，不能以独立 block reset代替。
- Exact affine oracle norm loss和完整 Fenchel deficit平方分解，包括 gap right retained input。
- Scalar negative例重现审查者见证：baseline support100、correction support10251/383、repaired support35773/383、oracle norm loss178309/490。

实际报告 status PASS、nonzero_repairs=6。有限算例支持 proof的 general |g|≤1 修复分支，但不替代所有日历和完整 nuisance 量词的解析证明；不增加新的物理观测、不拟合渐近常数、不跑历史 MC 或硬件。

