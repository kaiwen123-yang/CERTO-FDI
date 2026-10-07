# GitHub分阶段人工审查指南 v1

此批次供人工审查已有模型、证明、固定实例和复现链。先打开 [当前R8 PDF](certo_fdi_control_memory_draft_v1.pdf)，再用 [分阶段索引](STAGE_INDEX_v1.md) 追到原合同、冻结源码与独立审查；[机器可读索引](STAGE_INDEX_v1.json) 保存完整 SHA。不是TAC ready、历史首次已排除或full400科学PASS的声明。

本页位于 `outputs/`；源码与报告链接相对仓库路径。Release中较大的stage ZIP/科学payload需与main中的manifest、源码、审查记录配套阅读。实际Release链接由发布者在发布后补入索引，不能仅凭asset文件名假定已经上传。下载复现材料时保留原相对路径。

## 先区分三种证据

| 证据 | 能支持什么 | 不能据此推出什么 |
|---|---|---|
| 数学证明＋定向独立审查 | 在明示合同/量词下的主定理、逆界、构造与统一余项 | 有限脚本能替代全称证明、真实机器人满足合同或穷尽历史新颖性 |
| 有限exact checks／元数据 | 指定矩阵、日历、repair、代数反例及资产绑定；有助寻找实现/证明错误 | 全calendar最优、全部输入恢复、所有参数成立或完整科学pipeline已跑 |
| actual ZIP→fresh ROOT→完整verifier | 指定归档字节、指定有限case在新环境的完整计算重验及新receipt | full400已闭合、普遍定理再证明、真实经验power、hardware验证 |

编译/排版通过是另一层：当前R8实际12页、source `2245714e…`、PDF `e148cf86…`，有 [编译排版回执](manuscript_compile_layout_status_v4.json) 与 [R8整合独审](manuscript_revision8_integration_review_v1.md)。作者资料/bios/photos未完整；本次页数与图文布局不颁发投稿就绪结论。

## 建议阅读顺序与可质疑点

1. **S00：先核贡献与出处。** Gaussian closest-means/凸分离、滤波、controlled/Markov sensing、switching cost以及反馈主动诊断均有前史。当前论点需要依靠固定合同下all-calendar同首系数、beta两regime、同物理输入下control loss和共同SPD uniform设计，而非这些工具的首创。核 [来源预检](citation_preflight_v1.md)、[来源支持矩阵](citation_support_matrix_v1.json) 和 [贡献/限制对照](tac_contribution_argument_v1.md)；后者绑定当时R6，不冒称对R8历史优先权的新认证。
2. **S01→S02：先读合同，再读主证明。** R1是继承的固定物理/比较系统证据。新主稿要求known fixed stable plant、共同Gaussian input support、retained完整状态、预先确定calendar、完整scalar nuisance路径与free level，missing期间状态/噪声继续演化。检验 `sf:two-regime` 和附录 `sf:geometry`/`sf:positive-proof`/`sf:zero-proof`：逆界是否覆盖任意calendar；构造是否只用真实可观测rowspace；双向exact-k是否可重复；1/2 gap偏移、singleton、跨macro与零总质量repair是否正确。score恢复只保一个constant-force方向，不能换成全部latent input恢复。
3. **S03：核control含义和uniform量词。** 共同force/noise/input/观测合同下比较beta，equal poles不能代替rowspace。共同固定Q正定的compact controller族必须有共同tail、packing和余项才能取joint inf；不能假设k连续、inf达到或finite-H optimizer存在。齐次settling结论不自动保证noisy/forced return，不能推广到rank-changing singular族。
4. **S04：把端点推论当风险解释。** 固定miss、alpha趋零时，相对ideal healthy-subtracted oracle的最小确定性整数endpoint代价：正beta为sqrt(H_or)首项，zero beta仅非负O(1)。核actual calendar/test存在、sup阈值的slack、全部更早H排除与整数overshoot；不能默许G-star(H)单调，不能写成sequential/ARL/E[tau]，不能外推到有限非线性D2或硬件。
5. **S05：查看有限检查，不把它当证明。** V2理论checkpoint实际封存的是R6/11页：source `8eaa707d…`、PDF `c8e02b02…`；212成员/210payload，11个有限exact checks和图metadata已有实际新目录验收。它不含R8 endpoint增量，也没有大型D2科学replay。检查哪些cases真正触发非零repair/不对称边界，比PASS数量更有意义。
6. **S06：核冻结子网格的科学范围。** Figure2仅terminal-balanced的7个H、两readout共14分类/12数值行，38小叶绑定。H40没有风险证书，不能填power=0；point下界0仅说明该充分证书未给正保证。V-plus是规定Gaussian-comparator统计量的完整历史方差上界；真实非线性误差与两侧事件预算另付。H100/26s是该列网格first certified；H160/41s、3完整块是代表例准则，H120历史保留；均不是全calendar最短时域。
7. **S07：看actualpipeline如何成功及曾在哪里失败。** 两个H160 distinct readout从296443279-byte实际ZIP、新ROOT和一次R1bootstrap各full-S一次，avg目标PASS、point有效证书未达目标。核新的receipt/日志、CASE与五项artifact绑定、全部48payload/47原输入/R1463文件记录。首轮PowerShell-File清理失败及第二普通长路径后置hash失败都保留；修复用新的native-inline cleanup与长路径只读finalizer。恢复源码在原ZIP外，需同main交付材料一起保留。原case非OS ReadOnly，只接受本轮字节稳定，不能把旧wrapper改记为原样全程PASS。
8. **S08：明确没有完成的部分。** 此批次冻结状态full400未闭合，正式完整科学包/未来V3full driver未执行。最终仍需400唯一keys、closed分类、CSV/direction/canonical实际身份、新full verifier集合精确覆盖、全部payload hash、独立original metadata view和清理后再验，以及explicit freeze/OS quiescence。presence/string-SHA映射不是body hash，更不是数学重验；任何unfinished前驱、缺证书或失败不得删除后宣称first success。
9. **S09：PiPER只是官方静态准备。** 固定官方SDKcommit的定向接口核查与记录协议已审。缓存非新RX、torque是电流换算、aggregate可部分/default0且timestamp非max；没有SDK运行、CAN连接、机器人动作或实测Gaussian/stability/commonB验证。异步部分输出不能直接成为主稿full-state合同。IID binomial证据量例也不是变化上下文的worst-case保证。

## 四项全文比较缺口

- Esna Ashari／Nikoukhah／Campbell，*Effects of feedback on active fault detection*（2012）。
- 同作者，*Active Robust Fault Detection in Closed-Loop Systems: Quadratic Optimization Approach*（2012）。
- Cheng／Steinberg，*Trend robust two-level factorial designs*（1991）。
- Coster／Cheng，*Minimum Cost Trend-Free Run Orders of Fractional Factorial Designs*（1988）。

它们已有身份/metadata记录，承重模型/定理比较尚未关闭。获取失败、摘要或本地未命中不能作为“不覆盖本文”的证明。原15项M0 matrix、17项后续对照、13条当前书目与四缺口有各自范围，不能互相替换成穷尽novelty审查。

## 留下可复核的审查记录

建议写明stage ID、所读文件/完整SHA、具体合同/定理/源码位置，再给出疑点及最小反例或缺失依赖。数学疑点应说明calendar、path预算、rowspace或量词；有限证书疑点应给case/readout/方向/receipt；IO疑点应给实际archive member/manifest/newROOT来源。仅“脚本PASS”或“图看起来合理”不足以关闭承重质疑。

后续全网格闭合或新发布应新增stage snapshot及实际验收记录，并保留旧R6/R8、frozen子网格和失败历史。本导航编写只读取既有材料及小文件hash，不重跑测试、不改科学/稿件/claims、不做remote动作。
