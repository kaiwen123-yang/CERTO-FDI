# Systematic Full-Text Literature Audit Protocol

## A. 目标与审计范围

文献审计必须先于最终算法定义。目标不是证明当前想法新，而是寻找 killer papers、占据项、失败先例、真实公开基线和可验证空白。

覆盖时间：经典文献不限年份；重点监控 2020-08-18 至 2026-08-18，特别是 2025–2026。

数据库/主源：

1. IEEE Xplore；
2. Scopus / Web of Science（可访问时）；
3. ACM DL、ScienceDirect、SpringerLink、Wiley、SAGE、Annual Reviews；
4. RSS/PMLR/CoRL/ICRA/IROS 正式论文集；
5. arXiv 仅作为公开全文或预印本状态；
6. 作者机构仓储/作者主页；
7. Crossref、DBLP、Google Scholar 仅用于发现和引文追踪。

禁止用博客、论文解读、ResearchGate 摘要或搜索摘要作为占据结论的最终证据。

## B. 最低数量门槛

```text
发现库（去重后）              >= 250
标题/摘要筛选                >= 120
取得并实际阅读全文            >= 60
直接最近邻全文                >= 25
killer-paper 深审             >= 10
向前/向后引文链               >= 8 条
2025–2026 直接相关全文         >= 15
公开数据/代码论文全文          >= 12
```

如果因付费墙无法取得全文，记录为 `FULLTEXT_UNAVAILABLE`，不得用摘要判定 OCCUPIED/OPEN。

## C. 八条谱系

1. 经典几何、结构、未知输入与 behavioral FDI；
2. 机械臂执行器/传感器故障与广义动量观测器；
3. 学习型动量观测器、模型不确定性与碰撞检测；
4. 结构化、模块化、图/运动链与可微刚体动力学学习；
5. Lie-group / geometry-aware / equivariant robot learning（含负结果）；
6. 接触检测、链节/接触体定位、virtual-power、kinetostatic/Jacobian projection；
7. 多变量时序异常检测、上下文/OOD 标定与序贯报警；
8. 机器人异常公共数据、基准、跨机器人/跨任务迁移。

## D. 检索流程

1. 执行 `05_LITERATURE_SEARCH_STRINGS.md` 中全部查询；
2. 导出原始结果和检索日期、数据库、结果数；
3. DOI/标题/作者去重；
4. 双层筛选：标题摘要 → 全文；
5. 对核心综述和最近邻做 backward/forward citation chasing；
6. 对每项候选贡献单独做否定性检索；
7. 建立 killer-paper 队列；
8. 每篇全文填写统一 method card；
9. 每条结论链接到具体页码、公式、图表或实验段落；
10. 输出 PRISMA 风格流转表，但不冒充医学系统综述。

## E. 证据等级

```text
A1 publisher PDF / official proceedings full text
A2 author accepted manuscript / institutional repository
B1 arXiv full text with formal version cross-check
B2 thesis/patent/source code documentation
C  abstract/metadata only (discovery only)
```

只有 A1/A2/B1 能支持贡献碰撞；C 不能支持“未覆盖/开放”判断。

## F. 方法卡字段

必须使用 `06_FULLTEXT_METHOD_CARD_TEMPLATE.md`，至少抽取：

- 问题定义与系统对象；
- 传感器和信号；
- 健康/故障训练数据；
- 残差/模型/网络；
- 几何、Lie、chain、graph、RNEA 使用方式；
- 检测/隔离/辨识/容错层级；
- 上下文与 OOD；
- 统计阈值、虚警、延迟；
- 数据集、代码、许可证；
- 对比基线和拆分；
- 理论定理、假设与可计算量；
- 局限和失败场景；
- 与 C1–C6 的具体碰撞；
- 占据结论与证据等级。

## G. 文献门终态

```text
LITERATURE_PASS_PLAUSIBLY_OPEN
LITERATURE_PARTIALLY_OCCUPIED
LITERATURE_OCCUPIED_KILLER_PAPER
LITERATURE_UNKNOWN_INSUFFICIENT_FULLTEXT
BLOCKED_LITERATURE_ACCESS
```

文献门不通过时仍可完成公共基准，但不得定义论文算法贡献。
