# 矩阵闭环主线的控制设计近邻补充审查 v1

2026-10-07。绑定 M2 合同 `m2_problem_contract_v1.md`，不是回填原M0矩阵已穷尽覆盖。两份primary全文已取得；本页是定向结构/定理接口核查，没有重现作者算法或逐行重证所有结果。

## Kim–Raimondo–Braatz，ECC 2013

题名 **Optimum Input Design for Fault Detection and Diagnosis: Model-based Prediction and Statistical Distance Measures**，ECC 2013，pp.1940–1945。[会议论文全文](https://skoge.folk.ntnu.no/prost/proceedings/ecc-2013/data/papers/1214.pdf)。PDF六页，SHA256 `26786822156dc8350928d7798bd5e98afe8c126007791278df07215b36c8df3e`。

本轮读取全部抽取正文，重点§III式(4)–(5)、§IV式(9)–(16)、§V式(17)–(27)及Lemma1/Remark3；没有重证全部SDP或H2条件。该文已用Gaussian距离优化closed-loop state feedback，均值和covariance共同依gain变化，并带input/state矩与semi-chance限制。因此不能把“控制改变统计距离”“同时传播均值与噪声”或“闭环统计主动诊断”写成首创。

其有限已知fault-model/Bayesian/one-step or monitoring-window优化合同不是两侧自由初值、全史rate健康paths、增长输入故障和真实缺测slots的全日历oracle亏损。没有把其local SDP解宣称为本问题全称sharp；本文若保留joint-design贡献，应精确定位在新日历极限和同一benchmark下的uniform联合asymptotic桥梁。该比较是当前模型与其所读合同不直接匹配的判断，不是对所有后续文献的排除。

## Raimondo–Marseglia–Braatz–Scott，Automatica 2016

题名 **Closed-loop input design for guaranteed fault diagnosis using set-valued observers**，Automatica74，pp.107–117，DOI `10.1016/j.automatica.2016.07.033`。[作者机构全文](https://web.mit.edu/braatzgroup/Raimondo_Automatica_2016.pdf)。PDF11页，SHA256 `cf26542d1749811684b7a77123883aa399b59c31d9f7a4f2ea199a6528a8df84`。

本轮定位§1.1、§2.2、Theorem1式(19)–(20)、§4 Lemma3/Theorem4式(24)、Algorithm1与附录对应proof接口。其set-valued observer保留既有测量/扰动历史并在线更新separating inputs；零误差保证依bounded convex polytopes，保守observer的converse条件明确区别。不能把所有既有AFD降格为open-loop，也不能独占完整历史或closed-loop horizon guarantee。

本模型Gaussian创新无bounded-noise零错误保证，scalar健康类初值无界、rate约束全inputclock，日历在noise前选定，风险目标与N固定set separation不同。新的全日历sharp损失不由该separating-input theorem直接代入；partial-state和控制约束却是该文已有的更广设计维度，不能写成本稿优于它。没有复跑其MIQP/observer数值例。

## 对稿件的具体影响

英文v1已有五条选定引用；下一个稿件版本加入这两篇，避免只引memoryless sensing而遗漏Gaussian feedback-design前史。中心贡献应是带全史健康漂移和true missing-span的matching calendar law；beta/投影/控制均值-covariance传播作为工具和解释。紧致联合设计桥梁、奇异score容量虽已/正在内审，历史覆盖仍须定向追踪，不能以17项有限查阅宣称穷尽创新。

新增primary来源及抽取文本回执为 `work/literature_control_extension/receipt.json`。原15条矩阵保持绑定其M0版本；这两项为明确M2补充，原4项全文缺口未因数量增加而关闭。
