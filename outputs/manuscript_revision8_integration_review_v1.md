# Manuscript R8 局部集成独立审查 v1

2026-10-07。结论：**ACCEPTED FOR THE DECLARED LOCAL INTEGRATION**。未发现必须修复的公式、量词、引用或 scope 缺口。此结论接受已审固定终点推论的 R8 集成，不表示编译/布局验收、full400 验收或整体投稿准备完成。

## 冻结输入

| 输入 | SHA256 |
|---|---|
| R8：outputs/certo_fdi_control_memory_draft_v1.tex | 2245714e5b92c5e36039a688f453b477256aa57df15f97a783442ea2bacbfdc1 |
| 历史 R7：references/manuscript_working_history/a26c945e35a8da9c598a5b94fe34f528a19025a652b335a457c4f9fa65626eca.tex | a26c945e35a8da9c598a5b94fe34f528a19025a652b335a457c4f9fa65626eca |
| 已接受 final fragment：outputs/fixed_endpoint_horizon_corollary_v1.tex | d60b75fb81d3bb1da1e2e507588d41cd8442cb4531b222b8cf13a24fae853287 |
| final companion JSON | 9b20b8c19ff51aa1402fb93cbaba43a29252f4712c88e98c29cc8a9abce3a088 |
| candidate MD | 47e9f15a41e90ce71c262dce4c725ec3cc7bda41760fc865bb8d5302ce5ade0e |
| 既有独审 MD，含最终 bytes 补绑定 | de520083bc5ea064cbb9aa0abe4139dad4dadd7db9565e9274ba9e318d9bc290 |
| 既有独审 JSON，含最终 bytes 补绑定 | e274b6fe172ff918aad6d9652ee4b46c6f52ddaeb103da6f52f24c6385aa803f |

实际读完整 R7→R8 unified diff 以及插入文本；以既有完整推论独审为基础，只复核本次集成。原先 1992ab48…/a3d814e8… 输入仍在既有报告保留，不把它们静默当作当前 d60b75fb…/9b20b8c1…。

## 1. 实际改动范围

实测源码 diff 仅有两个 insert，无 delete/replace：

- R8 行 432–501：正文 Risk meaning subsection、完整 corollary、scalar settling 解释。
- R8 行 1275–1457：第六个 appendix section，即附录 F Fixed-endpoint risk cost。

删去两处新增行后，R7 原文精确恢复；无旧段落删改。正文 corollary 从 begin 到 end 与最终 d60b75fb… fragment 相同；附录从 begin proof 到 rounding-example 结尾，与该 fragment 的 proof/risk-scale/example 全部相同。因此没有仅保留结论却遗漏承重证明或反加强例。

既有模型、two-regime/score/capacity/SPD/compact-uniform/bounded-even 定理及附录 A–E 未变。R7 的有限非线性实验、H160 three-block 实例、H100 firstcertgrid、H120 历史、封闭子网格图与 caption、variance/mean/event 域及 13 条 bibliography 原文均未变。这是源码保全证明，不是重新计算或升级这些实验的统计验收。

## 2. 正文风险意义

正文保留 fixed-controller theorem 和 fixed-calendar Gaussian risk 接口为明确依赖；miss tolerance 固定，0<α<1−miss，α↓0。Hdiag 仍按存在真实 legal calendar/test 定义，uniform PFA/power 作用于完整两侧健康路径类；不是假定信息 sup 取到。已知控制器、终点、日历和检验事先确定，原因果反馈模型未改变。

Oracle 仍明确是 ideal healthy-subtracted complete white record，非 composite full-record experiment。正分支系数

\[
\frac{2C}{F\eta^2}=\frac{2\sqrt2}{5}\sqrt{\frac{\beta_k r}{F\eta}}
\]

完整保留。零分支仅 0≤Hdiag−Hor=O(1)，明确不主张正下界或 Θ(1)。Joint 分支依然限定 common-positive-definite-noise compact family，用 Cinf 而非最小值，不假 k 连续或 optimizer attained。

新增 settling 解释：同 physical force/noise 保持 F 和 Hor 不变，故既有 coefficient minimum c=81/100 同时最小化该 leading endpoint excess。该文字只组合既有结论；明确排除 finite-risk global optimizer 和 full forced-return guarantee，未声称任意有限风险目标的最早整数 endpoint 在该 gain 取到。

## 3. 附录 F 承重内容

附录 F 和已接受 fragment 的数学文本相同，以下内容全部保留：

1. 每个实际日历风险可行 iff Gπ≥Λ；Gπ≤O_H 排除全部 H<Hor；不以未取到的 sup equality 断言存在。
2. 精确 cubic oracle 与整数 overshoot O(n²)，h≤M√n 的一致 increment remainder O_M(n²)，固定 L 的 O_L(n) remainder。
3. 同一收敛 tail error 覆盖全部较早整数 H，不假 G*_H monotonic。
4. 显式 ξ*=2βη/(Fr) calendar 在稍晚 endpoint 严格超阈值，产生真实检验和非空可行集合。
5. β=0 用实际 profile-aware calendar 的 M₀H² 界，再选固定整数 L，保留 rounding 与 oracle overshoot 的同阶影响。
6. Common-SPD uniform tail 的 all-controller lower；固定 near-inf Kδ 的显式上界，先风险极限再 δ↓0，不换成未知控制器 robust test。
7. 固定 miss 下 Mills risk-scale 推导；same-model copy-plant 例以及 Λ_H=H³/6+H/12、H≥226 的严格 dual bound，反驳普遍 Θ(1) 增量。

正文与附录均指明这是 deterministic fixed-endpoint 风险代价，不是 sequential stopping、ARL 或 expected stopping time。附录明确禁止把渐近移到 bounded-time nonlinear certificate 域；正文新增解释也强调有限 nonlinear comparison 仍受独立 mean/variance/remainder/event gates 约束。

## 4. 标签、引文与静态源码

65 个 label 全部唯一；ref/eqref 均有目标，无 unresolved。附录 section 顺序为 geometry、positive、zero、control、even、endpoint，故新 proof 是第六附录 F；正文 sf:endpoint-proof 引用解析正确。

13 个 bibitem key 全部唯一，cite key 全解析。旧 bibliography 和引文原文未变，本次不新增文献或隐去既有四处 fulltext gaps。begin/end environment 栈闭合；非法低控制字节为 0、tab 为 0、孤立 CR 为 0。

以上只是静态源码和已审语义集成检查。未编译、未打开新编辑器、未重审全篇旧证明、未运行旧 math checks/D2、未读写动态实时文件、未编辑主稿或根 claims。R8 编译/版面应由独立正常流程验收。

必须修复项：无。该冻结 R8 可作为已接受推论的集成版本。
