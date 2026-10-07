# CERTO-FDI：控制理论与冻结仿真审查版

面向 IEEE TAC 的研究工作记录。研究问题是：健康解释可以随时间漂移、任务变化占用真实时间、闭环状态保留记忆时，诊断信息损失有什么极限，什么任务日历与受限控制设计能达到它？

**当前状态：研究已按作者最新要求停止；goal 为 paused，后台 400 行计算也已停止。这里是 2026-10-07 的审查快照，尚未完成全表和最终科学包验收，尚不具备投稿就绪声明。**

先读 [人工审查路线](outputs/GITHUB_REVIEW_GUIDE_v1.md) 与 [10 阶段索引](outputs/STAGE_INDEX_v1.md)，再看 [当前 R8 稿件（12 页）](outputs/certo_fdi_control_memory_draft_v1.pdf) 和 [源码](outputs/certo_fdi_control_memory_draft_v1.tex)。

| 阶段 | 重点 | 当前证据范围 |
|---|---|---|
| S00 | 当前稿、贡献与文献边界 | R8 源/PDF、编译与整合独审；4 项文献全文缺口保留 |
| S01 | 原 R1 来源与物理证书 | 继承的实际归档固定实例验证，范围见 source scope |
| S02 | 两种信息亏损与 score 容量 | 固定 common-support 模型的完整数学证明与反例 |
| S03 | 控制器与闭环记忆 | 同物理输入/噪声的控制比较、common-SPD 一致设计 |
| S04 | 固定终点风险代价 | 正分支平方根额外时域；零分支有界代价及反加强例 |
| S05 | 有限理论计算与历史阶段包 | V2 包含 R6/11 页；不能当作当前 R8 或完整 D2 |
| S06 | 冻结 D2 子网格 | 点/平均读出、真实时钟、两侧预算与全创新史 |
| S07 | H160 实际科学 ZIP 预演 | 两个读出各一次 fresh-root full stdlib 验证；失败与恢复保留 |
| S08 | 400 行扫描 | 发布时点快照未完成；完整大证据与后续验收分开 |
| S09 | PiPER H 准备 | 官方接口静态核查与协议，没有硬件操作 |

[长期目标](RESEARCH_PLAN.md)、[逐项主张台账](research/claims.json)、[暂停及恢复状态](research/checkpoint.json)、[决策记录](research/decisions.md) 均保留。

## 如何审查证据

数学证明、有限精确计算、科学执行回执是不同层级。一个有限程序 PASS 不证明全称定理，一个归档 hash 通过也不证明科学算术。H160 average 达到既定目标；point 是有效证书未达目标，功效下界 0 不代表真实功效 0。[余项优先级评估](outputs/d2a_remainder_priority_assessment_v1.md) 只说明这六个固定 point 行不能仅靠收紧同一风险接口的误差预算获救。

当前单文件稿包含完整附录。12 页尚不含真实作者信息/bios/photos。四项全文比较未取得，未宣称穷尽或历史首次；未把确定性固定终点写成序贯/ARL 最优；非线性例有自己的有限 mean/variance/remainder/event 条件。

## 代码与数据

`outputs/` 保存稿件、图、证明、可运行检查与版本回执；`references/` 保存用户研究来源及历史；`work/` 只提交冻结的可运行源、方向与已完成小 CASE 元数据。原 ROOT 相对路径保留，生成代码与标准库 verifier 没有为了发布改动数学或物理参数。

`PUBLICATION_SNAPSHOT_STATUS.json` 和 `publication_snapshots/` 标明同一次捕获的 UTC、400 行分类和源 SHA。仓库内 `work/d2a_cert_review_bound_table.csv` 是这个审查快照，不是持续更新的本机活表。

大文件在 [分阶段 Releases](https://github.com/kaiwen123-yang/CERTO-FDI/releases) 中提供：原始用户输入、R1 ZIP、V1/V2 阶段包、H160 实际预演包，以及截至最终停止时已完成算例的全部 witness/历史。每个资产有 manifest/hash；未完成算例未复制成已完成结果。下载与恢复说明见 `publication/RELEASE_ASSETS.md`。

论文全文副本保留在原本地研究环境；仓库公开可核对的引用、主来源 URL、DOI、审查定位和范围，不镜像未获分发许可的第三方全文。

## 旧仓库与许可

原无关研究已从当前默认分支树移除，原提交与 10 条旧研究分支保存于 `legacy-pre-theory-20261007/*` 标签；本地另有完整 Git bundle。新的 `review-20261007-*` 标签是本次发布的审查分类，不伪造原研发时间线。

未指定新的开源许可。公开可读不构成对第三方材料的再许可；原材料的声明与来源保持。
