# CERTO-FDI Paper Reset V2-R 全量执行主提示词
## ME-AD 闭环 × AURSAD 双协议 × 统一公共基准 × 自包含证据 × 投稿成熟度判定

> 适用执行者：Claude Code / 具备 WSL、终端、浏览器、Git、GPU 与长时执行能力的 Claude  
> 项目仓库：`git@github.com:kaiwen123-yang/CERTO-FDI.git`  
> 本轮性质：投稿前实验与证据闭环，不是第三种李群网络开发，不是重新启动整个项目  
> 当前历史终态：`PIVOT_BENCHMARK_DATASET_PAPER`  
> 本轮目标：判断 benchmark 论文是否真正具备投稿价值，并用 ME-AD 判断“真实渐进机械故障 + 本体动力学残差”是否值得重新开启后续算法讨论  
> 目标 venue：RA-L / ICRA benchmark 或 evaluation 方向优先；只有证据异常强时才允许讨论 T-RO

---

# 0. 你的角色与总目标

你现在是 CERTO-FDI 的：

1. 投稿前实验负责人；
2. 机器人健康监测与渐进故障诊断专家；
3. 公共数据集与原生基线复现负责人；
4. 评估协议、泄漏和统计审计员；
5. 文献证据自包含化负责人；
6. Git、provenance、G 盘存储和审查包负责人。

你的任务不是继续修补当前 Chain/SO(3)/LiGRA 模型，而是完成一次有限、可审计、结果前冻结的 **V2-R 投稿前闭环**：

\[
\text{核验 V2 结论与证据冲突}
\rightarrow
\text{ME-AD 真实渐进机械故障基准}
\rightarrow
\text{AURSAD 原生协议 vs 诚实协议}
\rightarrow
\text{真实统一基线矩阵}
\rightarrow
\text{自包含全文证据}
\rightarrow
\text{三轴判定}
\]

最终必须分别回答：

```text
A. 当前算法路线是否仍为 NO-GO？
B. benchmark/protocol audit 是否具有独立论文价值？
C. 当前稿件是否已达到投稿状态？
```

不得再使用一个优先级枚举把三件事混成一个模糊终态。

---

# 1. 当前可信状态与历史边界

## 1.1 GitHub

远程：

```text
git@github.com:kaiwen123-yang/CERTO-FDI.git
```

当前历史 V2 分支：

```text
stage/paper-reset-v2-500x100-public-story-convergence
```

当前 Draft PR：

```text
PR #9
base: stage/paper-reset-literature-public-benchmarks
head: stage/paper-reset-v2-500x100-public-story-convergence
```

本提示词生成时的已知 head：

```text
e8ca63983d0738e7540d82200e551d20a8fca681
```

开始时必须重新核验。不得假设它仍未变化。

PR #1–#9：

```text
保持 Draft
不得 merge
不得 force-push
不得改写历史结果
不得移动旧 head
```

## 1.2 新分支

从 PR #9 当前远程 head 派生：

```text
branch:
stage/paper-reset-v2r-mead-submission-closure

worktree:
~/research/CERTO-FDI-WORKTREES/paper-reset-v2r-mead-submission-closure
```

新建 stacked Draft PR：

```text
base:
stage/paper-reset-v2-500x100-public-story-convergence

head:
stage/paper-reset-v2r-mead-submission-closure
```

PR 标题：

```text
Paper Reset V2-R: ME-AD closure, dual-protocol audits, unified benchmarks, and submission readiness
```

## 1.3 当前完整审查包

寻找：

```text
CERTO_FDI_V2_FULL_REVIEW_20260824T065812Z.zip
```

预期 SHA256：

```text
7cb14c7888e7768f6fd84120c1c2eac8cab4ce22ee2ce0af65b2a32338e5b73f
```

在以下有限范围搜索：

```text
当前目录
~/Downloads
~/Desktop
/mnt/c/Users/*/Downloads
/mnt/c/Users/*/Desktop
/mnt/g/CERTO-FDI/00_inbox
/mnt/g/CERTO-FDI/06_review_exchange
```

必须：

1. 计算 SHA256；
2. `unzip -t`；
3. 全新解压；
4. 验证内部 `MANIFEST.json`；
5. 验证 Git head；
6. 将其视为“历史冻结证据”，不是待原位修改材料。

## 1.4 历史结论：不得重新包装

以下结论保持：

```text
故障破坏 frame/gauge covariance：错误
第三种 LiGRA：禁止
当前 Chain/SO(3) 公共数据主张：NO-GO
当前统一 Jacobian 故障头：NO-GO
当前自主 contact product：NO-GO
当前候选方法公共数据生存门：FAIL
```

当前算法状态的默认起点：

```text
ALGORITHM_NO_GO_CURRENT_METHOD_PUBLIC_DATA
```

只有 ME-AD 的预注册实验产生新的、跨任务稳定、相对强基线的物理残差信号，才允许把状态改为：

```text
ALGORITHM_EVIDENCE_REOPENED_FOR_FUTURE_DISCUSSION
```

该状态也不等于本轮立刻开发新算法。

## 1.5 当前 V2 包已发现的投稿缺口

必须逐项闭环：

1. `PIVOT_BENCHMARK_DATASET_PAPER` 是项目管理出口，不等于投稿成熟；
2. `8 models × 3 seeds × 3 datasets` 与实际矩阵不一致；
3. `universal_baseline_matrix_complete=True` 与 RoAD 缺行冲突；
4. AURSAD 原生 supervised baseline 未真正复现；
5. 跨数据集结果没有实际完成；
6. 10 张继承 V1 Method Card 未进入自包含 Full 包；
7. 100 张卡不等于 100 篇同深度精读；
8. `first deployment-honest audit`、`three principal benchmarks` 等措辞过强；
9. 2026-06 发布的 ME-AD 未进入原筛选与数据范围；
10. 当前 Full 包没有完整代码快照、Git bundle、逐种子预测与全部卡片。

---

# 2. 本轮绝对禁止

1. 不设计第三种 LiGRA；
2. 不恢复“故障破坏协变性”；
3. 不新增 Jacobian/pathway 网络；
4. 不在旧 590 episode MuJoCo 数据上调参；
5. 不使用 final test 选择模型、阈值、特征或协议；
6. 不把缺失 URDF、惯性或控制器信息从互联网静默补造；
7. 不用 cycle index、fault label、官方 split ID 作为模型输入；
8. 不把 benchmark onset 称为物理故障真实起点；
9. 无官方 RUL 标签时不宣称 RUL；
10. 不用 point adjustment 作为主指标；
11. 不把高度重叠窗口当独立 bootstrap 样本；
12. 不原位修改 PR #9 历史终态；
13. 不自动 merge；
14. 不 force-push；
15. 不以“下一步建议”结束，必须给出本轮终态。

---

# 3. WSL / G 盘存储合同

用户 WSL 虚拟盘在 E 盘，空间受限。所有大文件必须在 G 盘。

开始时：

```bash
mountpoint -q /mnt/g
findmnt -T /mnt/g -o TARGET,SOURCE,FSTYPE,OPTIONS
df -h /
df -h /mnt/g
touch /mnt/g/.certo_v2r_write_test
rm /mnt/g/.certo_v2r_write_test
```

若失败：

```text
BLOCKED_PERSISTENT_STORAGE
```

本轮运行根：

```text
/mnt/g/CERTO-FDI/04_runs/paper_reset_v2r/<RUN_ID>
```

数据：

```text
/mnt/g/CERTO-FDI/03_data/public/me_ad
/mnt/g/CERTO-FDI/03_data/public/aursad
/mnt/g/CERTO-FDI/03_data/public/voraus_ad
/mnt/g/CERTO-FDI/03_data/public/road
```

文献与卡片：

```text
/mnt/g/CERTO-FDI/02_research_docs/paper_reset_v2r
```

审查包：

```text
/mnt/g/CERTO-FDI/06_review_exchange/to_review/thin
/mnt/g/CERTO-FDI/06_review_exchange/to_review/full
```

缓存：

```bash
export PIP_CACHE_DIR=/mnt/g/CERTO-FDI/08_cache/pip
export TORCH_HOME=/mnt/g/CERTO-FDI/08_cache/torch
export HF_HOME=/mnt/g/CERTO-FDI/08_cache/huggingface
export UV_CACHE_DIR=/mnt/g/CERTO-FDI/08_cache/uv
```

红线：

```text
G 盘可用空间 >= 50 GiB
WSL 根可用空间 >= 20 GiB
本地 staging <= 5 GiB
```

ME-AD 原 ZIP 约 10.8 GB，解压后约 10 GB。优先：

- 保留原 ZIP；
- 首轮仅选择性解压 `README / Tasks / Pandas / scripts`；
- 暂不解压全部 `CSV/`，除非 Pandas 数据或官方任务脚本不足；
- checkpoint 只保留 best/final；
- 不重复保存 raw 与 processed 的多个副本。

---

# 4. Phase R0 — 结果前冻结与三轴决策

任何 ME-AD/AURSAD 新结果产生前，第一提交必须包含：

```text
contracts/paper_reset_v2r/
configs/paper_reset_v2r.yaml
src/certo_fdi_reset_v2r/decision.py
docs/paper_reset_v2r/PROTOCOL_FREEZE.md
docs/paper_reset_v2r/PORT_PROVENANCE.md
tests/test_paper_reset_v2r_freeze.py
```

第一提交：

```text
Paper Reset V2-R: freeze ME-AD, dual-protocol, unified-benchmark and submission-readiness contract
```

## 4.1 三轴状态

### AlgorithmState

```text
ALGORITHM_NO_GO_CURRENT_METHOD_PUBLIC_DATA
ALGORITHM_EVIDENCE_REOPENED_MEAD_PHYSICS_RESIDUAL
ALGORITHM_EVIDENCE_REOPENED_CONTEXT_CALIBRATION
ALGORITHM_INCONCLUSIVE
```

### BenchmarkArtifactState

```text
BENCHMARK_ARTIFACT_SUBMISSION_READY
BENCHMARK_ARTIFACT_MAJOR_REVISION
BENCHMARK_ARTIFACT_NO_GO
BENCHMARK_ARTIFACT_BLOCKED
```

### SubmissionReadiness

```text
READY_RAL_ICRA_BENCHMARK
READY_TRO_EVALUATION_PAPER
NOT_READY
BLOCKED
```

## 4.2 CombinedState

只允许：

```text
V2R_READY_BENCHMARK_PAPER
V2R_MAJOR_REVISION_REQUIRED
V2R_NO_GO_BENCHMARK_PAPER
V2R_REOPEN_METHOD_DISCUSSION
V2R_BLOCKED
```

Combined state 不得掩盖三轴结果。

---

# 5. Phase R1 — V2 证据冲突与包自包含闭环

## 5.1 重算历史终态

直接导入 PR #9 冻结的：

```python
certo_fdi_reset_v2.decision.resolve_final_state
```

用上传包的 `24_decision_evidence.json` 重算，结果必须仍为：

```text
PIVOT_BENCHMARK_DATASET_PAPER
```

若不一致，先 BLOCKED。

## 5.2 修复“矩阵完整”语义

必须明确选择：

### 方案 A：真正补齐

对 RoAD、voraus、AURSAD、ME-AD 执行同一 `CORE-8` 矩阵。

### 方案 B：停止笛卡尔积主张

分别报告：

```text
voraus unified matrix
RoAD controlled audit
AURSAD native-vs-honest matrix
ME-AD progressive-fault matrix
```

不得继续写：

```text
8 models × 3 seeds × 3 datasets
```

除非真实存在。

机器可读字段必须从实际文件自动计算，不允许手工设：

```text
universal_baseline_matrix_complete
```

## 5.3 自包含全文证据

新 Full 包必须包含：

- 94 张 V2 新卡；
- 10 张继承 V1 卡；
- 所有 16 个 killer dossier；
- 更新后的 ME-AD 卡；
- 至少 40 篇直接最近邻深度卡。

“深度卡”必须至少有：

```text
问题与系统对象
输入信号
完整算法/公式
训练与损失
数据与 split
基线
指标
关键结果
限制
与本项目重叠
页码/公式/图表证据
```

不以词数单独判定，但不得仅为摘要复述。

## 5.4 Delta literature search

仅做投稿前增量检索：

```text
2026-06-01 至执行日期
```

至少覆盖：

```text
ME-AD
progressive robot degradation anomaly detection
robot benchmark validity audit
deployment-honest anomaly detection
industrial robot early fault detection
robot RUL anomaly dataset
context-calibrated robot anomaly
```

补入：

- ME-AD 官方数据记录与论文/预印本状态；
- 2026 benchmark validity/audit 工作；
- 原 unavailable killer papers 的最后获取尝试；
- RAS-2；
- CASPER 或其他本轮发现资源。

若全文不可得，记录 `FULLTEXT_UNAVAILABLE`。

---

# 6. Phase M0 — ME-AD 获取与数据审计

## 6.1 官方来源

官方数据记录：

```text
ME-AD: Progressive Robotics Anomaly Detection Dataset
Zenodo DOI: 10.5281/zenodo.20817531
Version: v1
Published: 2026-06-23
License: CC BY-SA 4.0
Archive: ME-AD.zip
Official MD5: c74dedb954931034d1870db8cd13e33b
```

数据描述：

```text
6-DoF Mitsubishi RV-7FM-D1-S15
joint 3 gearbox lubricant removed
progressive mechanical wear
~17,000 cycles
7 tasks
3 motion families
~280 Hz
6 q + 6 qdot + 6 qddot + 6 torque
raw CSV + cleaned Pandas + Tasks
```

这些是待文件内 README 复核的官方元数据，不得只凭网页使用。

## 6.2 下载

直接下载到 G：

```text
/mnt/g/CERTO-FDI/03_data/public/me_ad/source_v1/ME-AD.zip
```

保存：

```text
URL
HTTP headers
Content-Length
ETag/Last-Modified
download UTC
MD5
SHA256
Zenodo metadata JSON
```

验证：

```text
MD5 == c74dedb954931034d1870db8cd13e33b
ZIP CRC PASS
```

## 6.3 选择性解压

首轮只解压：

```text
README*
Tasks/
Pandas/
*.py
requirements*
LICENSE*
```

记录未解压的 `CSV/` 清单和大小。

## 6.4 数据审计

必须生成：

```text
mead_dataset_manifest.json
mead_file_inventory.csv
mead_schema_audit.md
mead_task_split_audit.csv
mead_cycle_order_audit.csv
mead_duplicate_hash_audit.csv
mead_label_semantics.md
mead_leakage_audit.md
mead_physics_applicability.md
```

必须回答：

1. 17,000 是近似还是精确；
2. 每个 task 的 train/healthy/faulty 数量；
3. 三个 motion family 的映射；
4. cycle 顺序是否跨文件连续；
5. 官方 healthy/faulty 边界；
6. “故障起点”是物理测量、人工边界还是 benchmark 定义；
7. 是否存在同一 cycle/文件跨 split；
8. raw 与 filtered 是否被当作独立样本；
9. task、motion、cycle index 是否会泄漏故障阶段；
10. q/qdot/qddot/torque 单位、列顺序和关节顺序；
11. 是否提供 URDF、惯性、控制器命令或电流；
12. 是否足以运行 RNEA；
13. 是否只支持 data-driven inverse-dynamics residual；
14. 是否有 RUL label；
15. 是否可定义 early detection lead time。

若没有官方 RUL 标签：

```text
RUL = NOT_APPLICABLE
```

若只有官方 split boundary：

```text
benchmark_onset
```

不得称为物理故障真实发生时刻。

---

# 7. Phase M1 — ME-AD 预注册任务与拆分

## 7.1 官方任务

首先逐值复现 `Tasks/` 中 7 个官方 AD 任务。

任何自定义 split 均为补充，不得替代官方结果。

## 7.2 样本单位

主单位：

```text
cycle
```

不得把同一 cycle 的窗口随机拆到 train/test。

若在 cycle 内切窗：

- 所有窗口继承 cycle ID；
- bootstrap 以 cycle 为单位；
- 阈值在健康 validation cycles 上选择。

## 7.3 特征层

### L0：原始时序

```text
q, qdot, qddot, tau
```

### L1：任务/运动上下文

```text
task ID
motion family
cycle phase（只可由当前 cycle 信号因果计算或官方合法元数据给出）
```

### L2：动力学残差可行性

若无官方 URDF/惯性：

```text
RNEA = NOT_APPLICABLE
```

允许的替代是：

```text
healthy inverse-dynamics prediction residual:
(q, qdot, qddot, context) -> tau
```

该模型是普通 data-driven healthy torque residual，不得称为解析 RNEA。

cycle index、fault progression index、split ID 不得作为输入。

---

# 8. Phase M2 — ME-AD 基线矩阵

## 8.1 CORE-8

在所有 7 个官方任务上运行：

```text
B1 Robust Mahalanobis
B2 PCA-SPE
B3 Isolation Forest
B4 One-Class SVM
B5 Window Autoencoder
B6 GRU predictor or GRU Autoencoder
B7 TCN predictor or TCN Autoencoder
B8 MVT-Flow or frozen recent MTSAD anchor
```

要求：

- deterministic 模型运行一次并做 cycle bootstrap；
- stochastic 模型 seeds = 260824, 260825, 260826；
- 同一健康 train/validation；
- 同一官方 final test；
- 不用 faulty test 调参；
- 保存参数量、训练时间、best/final checkpoint；
- 不做 point adjustment。

## 8.2 Progressive baselines

额外运行：

```text
EWMA on anomaly scores
one-sided CUSUM
cycle-level PCA health index
cycle-summary Mahalanobis
```

这些是序贯/趋势基线，不计入 CORE-8。

## 8.3 Healthy torque-residual feasibility

仅使用既有标准架构，不设计新网络：

```text
Ridge inverse dynamics:
(q,qdot,qddot,context) -> tau

MLP inverse dynamics

GRU/TCN inverse dynamics
```

主异常分数：

```text
per-joint standardized torque residual
joint-3 residual
all-joint residual energy
```

`joint-3 residual` 只作为 diagnostic，因为故障位置已知；主结论必须使用全关节盲检测。

必须包含：

```text
same-capacity direct anomaly model
permuted-joint control
context-permuted calibration control
```

不得把该可行性实验直接写成新方法。

---

# 9. Phase M3 — ME-AD 评价

每个 task 分别报告：

```text
AUROC
AUPRC
FPR@TPR90
precision/recall/F1 at healthy-val threshold
false alarms per 1000 healthy cycles
false alarms/hour（若 cycle duration 可计算）
cycle-level detection delay
earliest detection cycle at fixed FPR
event/cycle recall
```

Progressive metrics：

```text
Kendall tau(score, cycle order)
Spearman rho(score, cycle order)
monotonicity
trendability across tasks
time-dependent AUROC
detection lead time relative to benchmark onset
```

只有官方 RUL label 才报告：

```text
RUL MAE/RMSE/C-index
```

否则禁止。

## 9.1 Cross-task / motion-family

若官方数据语义允许，执行：

```text
leave-one-task-out healthy generalization
leave-one-motion-family-out
train on early healthy tasks -> test on held-out task
```

不得破坏官方主结果；作为 supplement。

## 9.2 Sample efficiency

健康训练比例：

```text
5%, 10%, 25%, 50%, 100%
```

必须按 cycle 抽样，3 seeds。

## 9.3 Context calibration

比较：

```text
marginal
task-conditioned
motion-family-conditioned
task+motion-conditioned
context-permuted control
```

小 cell 回退规则在结果前冻结。

---

# 10. ME-AD 结果门

## 10.1 Physics residual signal

只有满足全部条件，才将算法轴从 NO-GO 改为：

```text
ALGORITHM_EVIDENCE_REOPENED_MEAD_PHYSICS_RESIDUAL
```

条件：

1. data-driven torque residual 相对最强 CORE-8 baseline：
   - 在至少 4/7 tasks，AUROC +0.03 或 AUPRC +0.05；
2. 至少 2/3 seeds 同方向；
3. FPR@TPR90 不恶化超过 10%；
4. fixed-FPR earliest detection 至少在 4/7 tasks 更早；
5. all-joint blind score 成立，不只 joint-3 oracle；
6. permuted-joint control 不复现增益；
7. 不是参数量或 context ID 泄漏；
8. task/motion OOD 不灾难性失效。

这只允许“未来讨论重新开启”，不自动构成新论文方法。

## 10.2 Context calibration generalization

只有满足：

1. 在 ME-AD + 至少一个旧数据集均减少 healthy-context false alarms ≥30%；
2. detection AUROC/AUPRC 不明显下降；
3. permutation control 干净；
4. 至少 3 个 front-end；
5. 2/3 seeds 同方向；

才允许：

```text
ALGORITHM_EVIDENCE_REOPENED_CONTEXT_CALIBRATION
```

否则保持算法 NO-GO。

---

# 11. Phase A0 — AURSAD 双协议实验

## 11.1 目标

定量回答：

```text
原论文/原生随机拆分性能
vs.
泄漏安全、部署诚实协议性能
```

不能只说原协议“可能泄漏”。

## 11.2 Protocol N：Native/Faithful

先获取：

- 论文全文；
- 官方 loader；
- 代码；
- split 逻辑；
- seed；
- 归一化；
- 操作/窗口定义。

若 exact split 不可恢复：

```text
FAITHFUL_NATIVE_POLICY
```

不得称 EXACT。

至少复现原生论文中的主要 supervised baselines 或最接近官方实现。

输出：

```text
aursad_native_reproduction.csv
aursad_native_deviation_ledger.md
```

## 11.3 Protocol H：Honest

健康-only：

- class 0 healthy screwdriving；
- class 5 benign movement context；
- fault classes 1/2/3；
- class 4 n=3 单独报告，不进入宏平均；
- split 按 operation/file/session group；
- 若无 workpiece ID，使用最保守可用 group；
- 不允许同一 operation 窗口跨 split；
- normalization 只来自 train。

统一 CORE-8 与 3 seeds。

## 11.4 Leakage quantification

必须计算：

```text
exact duplicate hashes
near-duplicate nearest-neighbor similarity
same operation across split
window overlap
random split vs grouped split performance inflation
```

核心输出：

```text
aursad_dual_protocol_comparison.csv
aursad_inflation_effect_sizes.csv
aursad_duplicate_audit.csv
aursad_movement_context_false_alarms.csv
```

## 11.5 双协议论文门

benchmark 论文要保留 AURSAD 主张，至少满足：

1. native/faithful 结果可复算；
2. honest 结果可复算；
3. performance inflation 有置信区间；
4. 泄漏机制由字节/ID/相似度证据支持；
5. 不把缺 workpiece ID 夸大为已证明同工件泄漏；
6. 明确只说“随机划分无法证明新工件泛化”。

---

# 12. Phase U0 — 真正统一的公共矩阵

## 12.1 数据集

```text
voraus-AD
RoAD
AURSAD
ME-AD
```

## 12.2 两层矩阵

### Universal-core matrix

只包含在四集均合法的模型与模态：

```text
Mahalanobis
PCA-SPE
Isolation Forest
OCSVM
Window AE
GRU
TCN
one frozen strong MTSAD
```

### Dataset-native matrix

分别记录：

```text
voraus MVT-Flow
RoAD paper-native baselines / protocol forensics
AURSAD native/faithful supervised baselines
ME-AD official/native benchmark if available
```

## 12.3 Seed 语义

不得再写：

```text
8 models × 3 seeds × N datasets
```

除非每个格子真实存在。

正确规则：

- deterministic 模型：1 次 fit + bootstrap CI；
- stochastic 模型：3 seeds；
- 表中显式 `seed_count`；
- `NOT_APPLICABLE` 与 `NOT_RUN` 分开；
- completeness 由程序从实际表计算。

## 12.4 RoAD

允许复用已经独立复核的 R1–R5 和旧统一基线，但：

- 若模型定义与 CORE-8 不同，必须重新跑；
- 不为 Chain/SO(3) 设计新版本；
- RoAD 仍报告 event-level failure 与 split sensitivity。

---

# 13. Phase X0 — 跨数据集适用性

不再强迫非法模板。

先建立合法共享模态矩阵：

```text
dataset_pair
shared signals
units
joint/axis count
sampling
episode definition
legal adapter
```

只有共享模态足够且 adapter 在结果前冻结，才运行：

```text
zero-shot healthy transfer
few-shot healthy adaptation
multi-dataset healthy pretraining
```

否则：

```text
NOT_APPLICABLE_PHYSICAL_MODALITY_MISMATCH
```

该结果不影响 benchmark 论文 readiness，但禁止在摘要中写跨机器人泛化。

---

# 14. Phase L0 — 投稿前文献证据闭环

## 14.1 自包含

Full 包必须包含：

```text
全部 104+ Method Cards
全部 killer dossiers
verified bibliography
screening decisions
evidence matrix
negative search log
ME-AD card
benchmark-validity audit cards
```

## 14.2 40 篇深度直接近邻

至少 40 篇真正深度卡，必须含：

```text
公式/算法
输入
split
baseline
结果
限制
页码
与本论文碰撞
```

不能用 17 篇 NOT_DIRECTLY_RELEVANT 充当近邻配额。

## 14.3 主张修订

必须删除或替换：

```text
first deployment-honest audit
three principal public benchmarks
8 models × 3 seeds × 3 datasets
field's newest surveys cite none
deployable calibration
```

除非新证据严格支持。

安全标题候选：

```text
A Deployment-Oriented Audit of Public Robot-Manipulator Anomaly-Detection Benchmarks
```

ME-AD 加入后可改成：

```text
A Deployment-Oriented Audit of Public Robot-Manipulator Anomaly Detection: Reproducibility, Leakage, Context Shift, and Progressive Faults
```

---

# 15. Benchmark artifact readiness 门

## 15.1 SUBMISSION_READY

必须全部满足：

1. voraus、RoAD、AURSAD、ME-AD 完成；
2. native/faithful baseline 状态明确；
3. universal-core matrix 完成；
4. AURSAD 双协议完成；
5. ME-AD progressive metrics 完成；
6. 所有摘要主张与实际表一致；
7. self-contained evidence package；
8. code snapshot/Git bundle/config/environment lock；
9. per-seed predictions/metrics 可复算；
10. 不存在机器可读 flag 与 CSV 冲突；
11. 至少两项跨数据集可复现的 benchmark finding；
12. 相关工作不使用 “first”；
13. 论文故事可以用一张图讲清楚；
14. 独立 reviewer smoke PASS。

达到则：

```text
BENCHMARK_ARTIFACT_SUBMISSION_READY
```

否则：

```text
BENCHMARK_ARTIFACT_MAJOR_REVISION
```

若主要结论无法复现或 standalone value 不成立：

```text
BENCHMARK_ARTIFACT_NO_GO
```

## 15.2 允许的投稿状态

### READY_RAL_ICRA_BENCHMARK

要求 artifact ready + 明确独立贡献 + 四数据集 + 自包含复现包。

### READY_TRO_EVALUATION_PAPER

仅当额外满足：

- 机制层结论显著超出数据集整理；
- ME-AD 真实渐进故障带来新的系统性发现；
- 统一协议改变领域结论；
- 强统计与实际部署分析；
- 无直接 benchmark-audit killer paper；
- 至少一个可验证 constructive component 跨两集成立。

否则不得标 T-RO ready。

---

# 16. 独立三轴最终决策

最终必须输出：

```json
{
  "algorithm_state": "...",
  "benchmark_artifact_state": "...",
  "submission_readiness": "...",
  "combined_state": "..."
}
```

优先级：

1. integrity/provenance blocked；
2. benchmark no-go；
3. submission ready；
4. major revision；
5. method evidence reopened。

历史 PR #9 仍保持：

```text
PIVOT_BENCHMARK_DATASET_PAPER
```

本轮不得改写。

---

# 17. 必需输出

## 决策与故事

```text
00_v2r_executive_decision_memo.md
01_three_axis_decision.json
02_submission_readiness_memo.md
03_revised_title_abstract_contributions.md
04_revised_story_memo.md
05_claims_ledger_v2r.csv
06_limitations.md
```

## ME-AD

```text
mead_dataset_manifest.json
mead_schema_audit.md
mead_task_split_audit.csv
mead_leakage_audit.md
mead_physics_applicability.md
mead_core8_metrics.csv
mead_progressive_metrics.csv
mead_torque_residual_metrics.csv
mead_context_calibration_metrics.csv
mead_sample_efficiency.csv
mead_cross_task_metrics.csv
mead_decision_memo.md
```

## AURSAD

```text
aursad_native_reproduction.csv
aursad_honest_protocol_metrics.csv
aursad_dual_protocol_comparison.csv
aursad_inflation_effect_sizes.csv
aursad_duplicate_audit.csv
aursad_protocol_memo.md
```

## 统一矩阵

```text
universal_core_matrix.csv
dataset_native_matrix.csv
matrix_applicability.csv
matrix_completeness.json
event_false_alarm_matrix.csv
sample_efficiency_matrix.csv
```

## 文献

```text
self_contained_method_cards/
deep_40_neighbor_cards/
mead_method_card.md
benchmark_audit_delta_search.csv
updated_verified_bibliography.bib
updated_negative_search_log.md
```

## Provenance / review

```text
run_manifest.json
git_status.txt
git_log.txt
environment_locks/
dataset_hashes.json
code_snapshot_or_git_bundle
reproduce_key_results.sh
THIN.zip
FULL.zip
```

---

# 18. 测试要求

至少包括：

1. ME-AD ZIP MD5/SHA/CRC；
2. cycle-level split leakage；
3. cycle index/label 输入泄漏 AST 检查；
4. official task count；
5. unit/column order；
6. deterministic/stochastic seed semantics；
7. no test tuning；
8. AURSAD native vs honest split isolation；
9. near-duplicate audit；
10. universal matrix completeness from rows, not manual flag；
11. summary claim vs CSV consistency；
12. inherited Method Cards included；
13. no raw restricted data in Git/review package；
14. Git head/package head alignment；
15. final decision purity test；
16. smoke recomputation of key tables。

---

# 19. Git 里程碑

建议：

```text
1. freeze V2-R protocol
2. ingest V2 review and close evidence contradictions
3. add ME-AD dataset audit
4. complete ME-AD baseline matrix
5. complete ME-AD progressive/physics residual audit
6. complete AURSAD native reproduction
7. complete AURSAD honest protocol
8. complete unified matrix
9. complete self-contained literature package
10. finalize three-axis decision and paper text
11. build review packages
```

每次 push 后核验 PR #1–#9 heads 未移动。

---

# 20. 启动时必须报告

1. WSL / kernel；
2. Python / CUDA / PyTorch；
3. CPU / GPU / RAM；
4. G 盘 mount 与空间；
5. repo / base / head / dirty；
6. PR #9 当前状态与 head；
7. V2 Full 包 SHA；
8. 数据集状态；
9. ME-AD 是否已下载；
10. 当前文献卡数量与继承卡位置；
11. RUN_ID；
12. 新 branch / worktree / G 盘 run root。

随后立即冻结 V2-R 合同并执行，不等待确认。

---

# 21. 执行顺序

严格依次：

```text
R0  冻结协议与三轴 decision code
R1  验证 V2 包、重算历史决策、关闭 flag/CSV 冲突
M0  下载并审计 ME-AD
M1  复现官方 tasks 与 split
M2  CORE-8 + progressive baselines
M3  torque-residual feasibility + controls
M4  context/sample-efficiency/cross-task
A0  AURSAD native/faithful reproduction
A1  AURSAD honest protocol
A2  双协议 effect-size audit
U0  四数据集 universal-core matrix
L0  自包含 104+ 卡 + 40 深度近邻 + delta search
S0  重写标题、摘要、贡献与故事
D0  三轴决策
G0  push、Draft PR、Thin/Full 包
```

任务只有在以下全部完成时结束：

```text
ME-AD complete
AURSAD dual protocol complete
universal matrix truthful and complete
self-contained literature evidence complete
three-axis decision complete
submission readiness decided
Git clean and pushed
Draft PR updated
Thin/Full packages independently verified
```

不得以“建议下一步”结束。
