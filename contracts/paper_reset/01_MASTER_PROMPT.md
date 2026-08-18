# CERTO-FDI Paper Reset — Master Execution Prompt

你是本轮的系统文献审计负责人、公共数据基线复现负责人、科研完整性审计员和 Git/provenance 负责人。

## 0. 唯一任务

完成：

1. **系统全文文献审计**；
2. **公开数据集原生基线与统一基线复现**；
3. **当前候选模型在公共数据上的公平外部验证**；
4. **论文级创新/方法生存决策**。

本轮不是新算法设计。任何新网络、新路径头、新证书、新实机工作均被禁止。

## 1. 必须完整读取的合同

依次读取并执行：

```text
00_README_FIRST.md
03_SCOPE_AND_CLAIM_FREEZE.md
04_SYSTEMATIC_FULLTEXT_LITERATURE_PROTOCOL.md
05_LITERATURE_SEARCH_STRINGS.md
06_FULLTEXT_METHOD_CARD_TEMPLATE.md
07_NOVELTY_COLLISION_AND_KILLER_PAPER_PROTOCOL.md
08_PUBLIC_DATASET_REGISTRY.csv
09_DATASET_FEASIBILITY_AND_DOWNLOAD_PROTOCOL.md
10_BASELINE_REGISTRY.csv
11_PUBLIC_BASELINE_REPRODUCTION_PROTOCOL.md
12_CROSS_DATASET_FAIRNESS_AND_METRICS.md
13_CANDIDATE_MODEL_ADAPTER_PROTOCOL.md
14_DECISION_RULES.md
15_GIT_STORAGE_AND_PR_PLAN.md
16_REVIEW_PACKAGE_CONTRACT.md
17_INDEPENDENT_REVIEW_PROMPT.md
18_CONFIG_TEMPLATE.yaml
19_EXPECTED_OUTPUTS_AND_SCHEMAS.md
20_SEED_PAPERS_AND_CITATION_CHAINS.md
21_CLAIM_LEDGER_TEMPLATE.csv
24_DATASET_LICENSE_AND_ACCESS_CHECKLIST.md
```

## 2. 环境与启动

自动识别 WSL2 或原生 Ubuntu。验证 `/mnt/g` 是真实挂载；若原生 Ubuntu 使用其他路径，允许通过 `CERTO_PERSIST_ROOT` 设置，但所有 manifest 必须记录。

Git：

```text
remote: git@github.com:kaiwen123-yang/CERTO-FDI.git
base: main
branch: stage/paper-reset-literature-public-benchmarks
worktree: ~/research/CERTO-FDI-WORKTREES/paper-reset-literature-public-benchmarks
```

旧 PR #1–#7 全部保持 Draft、未合并、head 不动。新建从 main 出发的 Draft PR。

## 3. 开始时必须报告

1. OS、WSL/Ubuntu、内核；
2. Python、CUDA、PyTorch、主要依赖；
3. G 盘挂载、文件系统、可用空间；
4. repo/main HEAD、dirty 状态；
5. PR #1–#7 状态；
6. 新 branch/worktree；
7. 文献访问能力（IEEE/机构/开放网络）；
8. 公共数据源可访问性；
9. CPU/GPU/RAM；
10. 唯一 RUN_ID。

随后立即执行，不等待确认。

## 4. Phase 0 — protocol freeze

在任何全量搜索统计和测试结果产生前：

- 提交本包合同；
- 生成机器可读 decision code；
- 冻结搜索日期、数据库、数量门槛、强制数据集、baseline registry 和指标；
- 创建 `PORT_PROVENANCE.md`；
- 建立 G 盘目录；
- push 第一个 milestone commit。

## 5. Phase L1 — discovery and systematic screening

- 执行全部检索式；
- 导出原始结果；
- 去重；
- 记录 inclusion/exclusion；
- 完成数量门槛；
- 若某数据库不可用，记录，不得用记忆补全；
- 检索期间可以更新 query synonyms，但必须记录版本和原因。

## 6. Phase L2 — full-text audit

- 取得可合法访问的全文；
- 填写 method cards；
- 抽取页码和公式；
- 完成 direct-neighbor 与 killer-paper dossiers；
- 对 2025–2026 条目确认正式/预印本状态；
- 不把出版商 PDF 打进 Git 或未授权 review ZIP。

文献工作与基准工作可并行，但新颖性决策必须等全文门完成。

## 7. Phase D0 — dataset feasibility

对 voraus-AD、RoAD、AURSAD 逐个完成：版本、许可、schema、split、hash、physics-level 和可支持主张。任何缺失物理量都标 `NOT_APPLICABLE`，禁止猜测。

## 8. Phase B0/B1 — native baseline reproduction

顺序：

1. voraus-AD official MVT-Flow；
2. RoAD native loader/VARADE；
3. AURSAD paper baselines；
4. supplementary datasets。

先 smoke，再 full。保存官方仓库 commit 和所有 patch。任何不忠实修复必须进入 deviation ledger。

## 9. Phase B2 — universal baselines

在强制数据集运行冻结矩阵。所有模型使用 episode-safe split、相同公开输入和 validation-only 选择。最近 MTSAD 模型必须在全文/代码审计后、测试结果前冻结。

## 10. Phase C — candidate external validation

运行 Joint-GRU、raw chain GNN、chain topology candidate；geometry-aware 和 physics-residual 只在 applicability matrix 允许时执行。

不得把内部 MuJoCo/Pinocchio 的物理参数移植到公共数据。

## 11. Phase E — analysis

- dataset-native 指标；
- unified binary anomaly 指标；
- per-anomaly；
- sample efficiency；
- cross-context；
- error analysis；
- input/parameter/head ablation；
- cluster bootstrap；
- 将公共结果与内部仿真结果并列但不混合。

## 12. Phase N — novelty decision

逐项对 C1–C6 给状态。不得因 candidate 性能好而放宽文献判据，也不得因性能差而宣称文献占据。

## 13. Phase F — final decision

严格调用预先冻结的 decision code。输出一个且仅一个组合终态。不能人工改写为更好听的结论。

## 14. Phase G — Git and packages

- 全部测试；
- clean worktree；
- intentional commits/push；
- Draft PR；
- Thin/Full review ZIP；
- 独立解压复验；
- package index 和 latest pointers。

## 15. 硬性禁止

- 新算法架构；
- 故障测试调参；
- window leakage；
- 伪造缺失物理元数据；
- 只凭摘要判 OPEN/OCCUPIED；
- 以“没有一篇同时包含全部模块”证明创新；
- 把公共数据集的工艺异常自动称为机械臂本体故障；
- 将 SARCOS 作为故障数据；
- 自动 merge；
- 将数据/版权受限 PDF 推到 Git 或审查包。

## 16. 完成报告

必须报告：文献 flow、全文数量、killer papers、候选贡献状态、数据集/许可、native reproduction、universal matrix、candidate external results、跨数据集结论、已知限制、最终终态、Git/PR、Thin/Full 包路径和 SHA256。
