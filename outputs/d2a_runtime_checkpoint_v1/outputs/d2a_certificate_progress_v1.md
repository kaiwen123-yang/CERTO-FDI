# D2-a 新参数统一证书进展 v1

2026-10-07。承接冻结协议 SHA256 `0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6`。原模型、物理盒、噪声、日历、读数和方向规则均不改。新入口为 `work/d2a_cert_case.py`；独立标准库核验入口为 `work/d2a_cert_verify.py`，使用 `python -S`。

## 可复用的证明与适配边界

从 R1 原包继承：degree-8 β/0.02 analytic A/B jets 与 Cauchy/slow-path 余项；共同正 M-matrix convolution supersolutions；ρ=197/200 的 P 度量收缩；affine equilibrium 半径和变化率；source/post entry 的 deterministic mean 管；三分量 source-return；source/post nonlinear remainder 和日历事件含义。这里新做的是给定 D2-a 方向和读数的全历史 certificate 实例化，以及点读数独立均值代数。

原 `actual_direction.py` 的全局 CASE/ROOT/PROTOCOL 绑定为新工作目录和实际方向，科学函数源码不改。原脚本要求 `WS % WDEN=0`；有理近单位方向引入非十进制分母，因此 adapter 取 `WS=lcm(10^24,WDEN)`，保证整数 lattice 的所有输出权重仍精确。scale只是存储/残差核验精度，不改变物理创新或信号。每新case保留协议、exact KKT、direction、gzip jets、polynomial/Abel certificate、mean/event/risk和失败原因。

## 点均值传递的独立推导

以下 μ 是相同 Gaussian comparator 的 deterministic mean，不是真实非线性期望。真实与比较输出之差另由冻结 remainder 支撑支付。对 hold 的 pre-step 输出，

`Y^g_(4,n)=C4 X^g_n + D4 ν_n + ζ_n`, `C4=−M0,4:[ωI,2ωI,2ωI]`。

固定任一允许完整确定性物理路径，Gaussian 创新均值为0，包括此前 move/hold/filter 记忆，故 `μ_(4,n)=C4 m_n`。在当前 task 的坐标中令

`d_n=task·gp β_n+e4 f_n`, `Lβ=M0ω²+β_nKp`, `q*_n=−Lβ^-1 d_n`，

`X*_n=(ωq*_n,0,0)`。

该 equilibrium 恒等式来自原 frozen-inertia/no-C tangent comparator，原 hold 证书已经逐参数单元验证 Lβ 的逆及 `|q*_n|≤Es`。其输出满足

`C4 X*_n=d_(4,n)+β_n(Kp q*_n)_4`。

因此，在同一 mean tube `|m_n−X*_n|≤mbar(n)` 下，

`|μ_(4,n)−(task·gp4β_n+f_n)| ≤ 0.02 |Kp,4:| Es + |C4| mbar(n)`。

这是逐点代数与确定性支撑，**没有平均窗口的 momentum 端点消去**。source initial 相对 equilibrium 的半径可取 `(ωEs,0,0)`；post initial 再加原 entry.mean_radius。原 rate-only 与 P contraction 给

`mbar(n)=b_rate+ρ^n H(initial)`，

`H_i(b)=sqrt((P^-1)_ii) sqrt(bᵀ|P|b)`。

所有逆/平方根/乘积采用原 verified interval或向上有理取整。source/post 分组取实际非零方向读数的最小 **point age**，随后以 `Σ|a_i|` 支撑；首post point age1749。上界在继承时间域内单调，因此对该组所有实际点成立。不同假设可以选择不同 β 路径，均分别支付此同一有效最坏管。该新推导仍须独立数学审查；数值/标准库重算不能代替这项审查。

平均 mean 继续用原 momentum/gradient 支撑并单列 `κh/2` 的 continuous-slot 与 discrete-ramp reference 差，不拿它代替点公式。

## 健康支持与两侧预算

设计投影的 difference class 为 K(B,r)。实际静态健康 difference class使用真正的 gp4 interval，令 `Btrue=2 gpmax·0.02`、`rtrue=2 gpmax·0.001·δ`，`γ=max(Btrue/B,rtrue/r)`，则 `Ktrue⊆γK(B,r)`。精确投影 KKT 给 raw residual v 的支撑

`hK(v)=Σ|q_i|rΔj_i+BΣ|eta_i|=vᵀp`。

对舍入残差 vr、有理normalizer d，真实单假设静态均值支持不超过

`[γ hK(v)+Btrue ||vr−v||_1]/(2d)`。

所有真实点/平均sample-time gaps均等于 δΔj，包括move/settle gaps；没有压缩时间。均值上/下界为 `mu0_upper=health+dynamic`、`mu1_lower=sampled_fault_signal−health−dynamic`。两侧 remainder分别为 `Σ|a_i|ε_segment`，两侧方差/event分别保守支付，不在同一均值差中抵消未知误差。

## 运行状态

首批目标是 H120 terminal_balanced 的 average250 和 point_last_fast_read。活运行及phase记录在 `work/d2a_cert_checkpoint.json`；每case结果和独立验证回执保存在各 `work/d2a_cert_h120_terminal_balanced_*` 目录。完成数字将在此文件追加。风险目标、1%流程目标与证书有效性分别报告；不把失败行删除，也不因获得这两行就报告完整D2-a或H*。

### 新结果的条件算术核验

两行均完成degree-8 full-history lattice recurrences、signed Abel及supersolutions，随后分别在新的 `python -S` 进程复算 exact KKT、方向/协议、完整方差、均值/event/risk；没有加载NumPy/SciPy。每行逻辑scalar recursions为6696000；源scientific code与原ZIP未改。

| H120 terminal | V− | V+ | V+/Vnominal | 每侧动态均值损失 | 每侧remainder | 保护间隔 | 功效下界（条件） |
|---|---:|---:|---:|---:|---:|---:|---:|
| average250 | 6.66906e−7 | 6.70739e−7 | 1.00289100 | 0.000653168 | 0.000874611 | 0.0111325 | 0.9999999999793 |
| point_last_fast_read | 0.0181101 | 0.0181313 | 1.00058712 | 0.00695240 | 0.0177802 | −0.453312 | 0 |

两行PFA算术上界同为约0.000967122591927；每假设事件预算约2.06634262233e−11。point的负间隔保留为 `RISK_TARGET_NOT_MET`，未使用上方差作错误同方向功效替换。这些不是完整时域结果，也不是H*。

**共同均值数学审查已接受冻结模板范围。** 报告 `outputs/d2a_mean_risk_review_v1.md` 的SHA256为 `6a9cfb8009d2b424dfd29130c3d9140478531aeb74b326e917881eb35d7fe924`，binding在 `work/d2a_cert_mean_review_binding.json`。独立审查按16个原β cells确认实际 `f≤0.045` 的两任务equilibrium被原Es包含，最大比值约0.303724/0.303739；H120 `f≤0.009` 更紧。原wide `f≤.75` 的task− enclosure曾略超旧Es（约1.00008373），这不是实际反例，也没有自动关闭wide范围。因此这里只接受固定κ/onset/H≤600模板；原物理盒和Es都未改，不扩展为全部f≤.75的mirror证明。继承nonlinear/event/contraction仍是条件。

11个先前已完成case只重新核对KKT/方向、均值/event/risk派生并在独立 `python -S` 进程绑定审查，**未重跑两H120的大递推**。旧CASE与旧full回执按内容hash保存在audit历史路径，新 `DERIVED_VERIFICATION_RECEIPT.json` 明确大递推未重执行、variance payload未改。tiny-positive Mills score在1e−8 grid截零时保守返回1；零分数、正微小gap和常用25/8边界小检通过，继承风险源码不改。

热更新审查metadata时有两条旧生成/新verifier的均值JSON比较失败：H80 fixed40 point、H80 switch_then_stay S60 average。大variance步骤此前均通过；旧失败日志保留。两行均从已有jets运行修复后的独立-S verifier成功，没有重新生成waveform。它们是已恢复的wrapper失败，不是数学方差失败或删行。

### 全表预检、resume与长期计算

400行exact nodal direction预检已完成：74退化、326非零KKT方向，108个非零矩方向，没有投影证书失败；326行中有300个逐字段完全相同实验去重后的唯一非零设计。重复成员仍有各自表行和source reference，不因去重减少申明范围。

`work/d2a_cert_batch.py`按H升序、原family顺序、S升序、readout的协议顺序串行生成。它仅跳过已有相同protocol、direction、CASE_RESULT字节hash和独立stdlib回执的结果；相同设计复用须逐字段相等，不能按近似矩阵/近似方向或大小相近缓存。`d2a_cert_partial_table.csv`始终包含所有400行，未运行值为NA；checkpoint和表用同目录临时文件后atomic rename。每新case单独跑 `python -S` verifier，并保存生成/核验日志。runner有exclusive lock，避免盲目启动多个大jobs。

小resume测试没有启动新case，正确保留74退化、复用H120两行及其重复成员共4行，其余322行未算。隔离fixture的3个negative controls分别改CASE hash、direction和protocol hash，cache均拒绝，原有效case文件未改。完整运行前已通过此测试。

实测H120压缩jets：average 60190348字节，point 60740809字节；原生成/同进程复核分别129.47/125.31秒。300个唯一方向共28120000快步，按此线性估算仅生成约32.5小时，含单独stdlib核验规划40–50小时，不能当保证ETA。压缩jets线性估算约54.9GB，1.5倍头间约82.3GB；起跑前C盘空闲约167.4GB。runner保留25GiB磁盘余量及下一case的额外缓冲；不足时先atomic checkpoint并退出，不删需要保留的证据。后续runner已移除同一进程的重复复验，仍每case保留独立-S核验，因此上述时间估计保守。

真实活session、总日志与下一步恢复位置由根checkpoint记录。runner自身文件为 `work/d2a_cert_batch_checkpoint.json`、`work/d2a_cert_batch_stdout.log`、`work/d2a_cert_checkpoint.json`。如果进程意外终止，先检查lock内PID和活会话；确认已停止后恢复，不能在未知活进程旁再启动同一个serial扫描。

活worker在启动时加载了旧supervisor对象，其raw table仍保守pending和历史失败标签；每case的新子进程已经使用接受门与修复verifier。**当前可信绑定总表为 `work/d2a_cert_review_bound_table.csv`**，由 `d2a_cert_sync_review_table.py` 逐字段检查当前case/full或derived回执、canonical目标状态和当前数学审查绑定。sync不覆盖worker的raw表，不据旧pending标签否定已完成审查，也不据阶段名宣布全表完成。历史unified exec句柄94963已失效，历史OS batch PID59248已确认停止；当前detached science62844/metadata10032仅按真实CIM与新日志判断，不再轮询旧会话。

### 工程审查与恢复回归

有限独立审核在 `work/d2a_cert_runner_audit_v1.md`，51个完成case的小JSON/回执链快照没有异常；没有读取生产gzip、重跑大计算或操纵活PID。隔离负控找出并推动修复：canonical目标/failure重建、mean版本接受门、当前报告与所需artifact检查、过期derived不遮蔽有效full、可恢复PREPARED/COMMITTED派生事务、精确UTF-8 bytes原子写（避免Windows CRLF改变拟提交hash）、已有complete science只-S重验、jets-only `--derive-from-witness`产生covariance而不proposal、attempt日志/旧日志hash归档、每次checkpoint保留失败历史、执行失败禁止arithmetic complete。

维护者对独立fixture作有限适配后，`work/d2a_cert_audit_fixture_v3_results.json` 全部负控与恢复检查通过；用的是隔离小fixture、tiny adapter/stub，0 worker、0生产jets读取、0大递推。它验证wrapper/事务分支，不冒称重新数学核验全部科学证书。旧v1/v2失败证据保留；没有通过删除输入、失败行或改变冻结物理参数得到通过。

### 当前证据交付与自动视图

部分首成功网格证据、可执行入口及JSON分别为 `outputs/d2a_partial_first_success_v1.md/.py/.json`。已闭合的average族为fixed20 H100、fixed40 H120、fixed76 H100、terminal_balanced H100、switch_then_stay H100；所有更早网格及当前H全部成员均闭合。stay及全部point尚未完成，不声称全网格失败。JSON绑定输入总表与所选CASE/有效receipt/covariance/witness/review SHA。

用户可读有限工程审查在 `outputs/d2a_runner_finite_audit_v1.md/.json`；实际字节验收快照在 `outputs/d2a_completed_artifact_integrity_v1.json`，69个已完成唯一case对五类artifact SHA/大小核对通过，0科学递推。冻结preflight方向记录SHA成为接受门；旧回执的事后hash-only sidecar与实际通过门的当前receipt严格绑定，补绑定入口拒绝用新hash覆盖旧hash差异。

统一续接文档为 `outputs/d2a_recovery_index_v1.md`。旧科学PID59248/session94963已停止并不可访问。当前science PID62844由独立WMI隐藏launcher启动，无unified session，科学串行扫描已恢复。当前轻量metadata伴随PID10032（无unified session）仅每45s在小回执/checkpoint变更时刷新严格overlay和部分H*，0 case生成、0科学verifier、0witness读取；当前两进程为脱离unified-exec进程树的隐藏OS进程；历史句柄94963/1590失效。根无需访问句柄即可读 `work/d2a_cert_live_publisher_checkpoint.json/log`；该发布器在科学PID停止后只最终刷新，不能把进程停止当全表完成。原supervisor启动时的raw/pending计数仍不是当前权威结果。
