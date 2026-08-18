# CERTO-FDI Paper Reset — G 盘挂载后续跑完整主提示词

> 阶段：Systematic Full-Text Literature Audit + Public Dataset Baseline Reproduction  
> 模式：**继续既有 PR #8，不重新初始化，不新增算法**  
> 远程仓库：`git@github.com:kaiwen123-yang/CERTO-FDI.git`  
> 当前分支：`stage/paper-reset-literature-public-benchmarks`  
> 当前已知远程 HEAD：`8edec2729d2ec243a584fc1fc7712a2a1046d038`  
> 当前 Draft PR：`#8`  
> 持久化根目录：`/mnt/g/CERTO-FDI`

---

## 0. 你的角色

你现在是本轮 CERTO-FDI Paper Reset 的：

1. 系统全文文献审计负责人；
2. 公共机器人异常数据集审计负责人；
3. 数据集原生基线与统一基线复现负责人；
4. 科研完整性、数据许可、Git 与 provenance 负责人；
5. 最终论文级 GO / PIVOT / NO-GO 决策执行者。

你不是新算法设计者。本轮唯一任务是回答：

\[
\boxed{
\text{当前研究是否存在可辩护的论文级空白，且当前候选是否在真实公共数据上具有外部价值？}
}
\]

本轮禁止通过新增网络、修改故障路径头、重新调内部仿真或继续细分局部问题来“救”现有方法。

---

# 1. 当前状态：必须作为不可变事实继续，而不是重新开始

## 1.1 Git 与协议状态

已完成：

- 从干净 `main` 创建分支：
  `stage/paper-reset-literature-public-benchmarks`
- 建立独立 worktree：
  `~/research/CERTO-FDI-WORKTREES/paper-reset-literature-public-benchmarks`
- Draft PR #8 已创建；
- Phase 0 协议冻结已完成；
- 文献、数据、基线与最终决策代码已在任何全量结果之前提交；
- 旧 PR #1–#7 保持 Draft、未合并、head 未移动。

当前已知提交链：

```text
0f47b9e  Phase 0 protocol freeze
814c603  L1 discovery tooling
8edec27  citation chasing + dedup + dataset grading
```

启动时必须重新核验远程状态。若远程 HEAD 仅新增 docs/tests/packaging/provenance，可记录后继续；若科学合同、决策阈值、数据拆分或基线定义发生变化，输出 `BLOCKED_PROTOCOL_HEAD_MISMATCH`，不得静默继续。

## 1.2 已完成的文献发现

Phase L1 已完成，不得重新跑一遍制造第二套发现库。

冻结事实：

```text
54 条检索式全部执行
原始记录：6299
去重记录：5303
2025–2026 记录：约1510
8/8 引文锚点完成
backward citations：325
forward citations：144
OpenAlex / Crossref / arXiv：54/54 查询成功
Semantic Scholar：UNAVAILABLE（429，无 API key）
DBLP：只用于精确标题/正式版本核验，不用于关键词召回
```

这些数字只是发现量，**不等于全文审读量**。全文门仍未完成。

## 1.3 当前阶段状态

```text
Phase 0 freeze              PASS
Phase L1 discovery          PASS
citation chaining           PASS_WITH_COVERAGE_GAPS
Phase D0 dataset audit      IN_PROGRESS
Phase L2 full-text audit    NOT_YET_PASSED
Phase B0 official smoke     NOT_STARTED
Phase B1 native baseline    NOT_STARTED
Phase B2 universal matrix   NOT_STARTED
Phase C candidate external  NOT_STARTED
paper-level decision        NOT_EVALUABLE
```

## 1.4 G 盘状态

用户已手动完成 G 盘挂载。你必须先验证：

```bash
mountpoint -q /mnt/g
findmnt -T /mnt/g -o TARGET,SOURCE,FSTYPE,OPTIONS
df -h /mnt/g
touch /mnt/g/.certo_fdi_write_test
rm /mnt/g/.certo_fdi_write_test
```

必须确认：

- `/mnt/g` 是真实 mountpoint；
- source 为 `G:` 或等价 Windows 卷；
- 文件系统为 `drvfs` / `9p`；
- 可写；
- 剩余空间足够。

若验证失败，输出 `BLOCKED_PERSISTENT_STORAGE`，继续仅完成不依赖大文件的小型 metadata 工作，并生成失败报告，不得把大数据写入 Linux 根盘。

---

# 2. 必须先完整读取的既有合同

从当前 worktree 的 `contracts/paper_reset/` 依次完整读取：

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

冲突处理：

1. 以冻结提交中的合同为准；
2. 本续跑提示词只补充“当前进度、已发现事实和执行次序”；
3. 不得用本提示词放宽原阈值；
4. 若合同与当前事实冲突，记录 `CONTRACT_INTERPRETATION_ISSUE`，提交最小解释文档，不得私自改阈值。

---

# 3. 启动报告：先报告，再立即执行

开始时报告：

1. WSL2 或原生 Ubuntu；
2. 发行版、内核；
3. Python、NumPy、SciPy、PyTorch、CUDA；
4. CPU、GPU、RAM、当前系统负载；
5. `/mnt/g` 的 source、fstype、options、可用空间、写入测试；
6. repo 路径、当前 branch、HEAD、dirty 状态；
7. origin/main、PR #8 head、PR #1–#7 状态；
8. 当前 RUN_ID；
9. 当前 scratchpad 路径；
10. 已完成 L1 产物位置及 SHA；
11. 当前 D0 产物位置；
12. 文献访问能力；
13. 公共数据源可访问性；
14. 预计需要下载的数据大小。

随后立即进入 Phase M，不等待确认。

---

# 4. Phase M — G 盘持久化树与 scratchpad 迁移

## 4.1 建立持久化树

在 `/mnt/g/CERTO-FDI` 下创建或验证：

```text
00_inbox/
01_frozen_sources/
02_research_docs/
  paper_reset/
    literature/
    datasets/
    baselines/
    decisions/
03_data/
  public/
    voraus_ad/
    road/
    aursad/
    ur5e/
    pyscrew/
  processed/
04_runs/
  paper_reset/
05_reference_results/
  paper_reset/
06_review_exchange/
  package_staging/
  to_review/
    thin/
    full/
  from_review/
  extracted_reviews/
07_backups/
08_cache/
  downloads/
  literature/
  model_weights/
```

代码、虚拟环境和 disposable cache 仍放 Linux 本地；数据、PDF 访问记录、结果、日志、checkpoint、review ZIP 放 G 盘。

## 4.2 迁移既有 scratchpad

自动定位当前 scratchpad 和 migration manifest。不得凭猜测删除或移动。

流程：

1. 生成迁移前 inventory：
   - relative path
   - bytes
   - mtime
   - SHA256
   - artifact class
2. 按 manifest 复制到 G 盘；
3. 使用临时目标目录；
4. 逐文件重算 SHA256；
5. 验证文件数、总字节、哈希；
6. 写入：
   ```text
   storage_migration_inventory_before.csv
   storage_migration_inventory_after.csv
   storage_migration_report.md
   storage_migration_manifest.json
   ```
7. 校验通过前不得删除 scratchpad；
8. 即使通过，也先保留 scratchpad 到本轮最终 review package 验证完成；
9. 迁移失败不得用“部分成功”掩盖，记录准确路径与错误；
10. 所有大文件后续只写 G 盘。

## 4.3 原始材料只读

迁入 G 盘后：

- 原始搜索导出只读；
- 原始数据集只读；
- 下载的开放全文只读；
- 预处理和方法卡放独立目录；
- 不允许覆盖 raw export；
- 所有修改通过新文件、版本号或 diff 留痕。

---

# 5. 必须落实的书目元数据修正

数据库不得只保留单个 `year`。统一增加：

```text
publication_status
online_first_date
online_first_year
issue_publication_date
issue_year
canonical_citation_year
volume
issue
pages_or_article_number
doi
formal_version_url
open_fulltext_url
evidence_level
```

对以下条目特别处理：

## Annual Review FDI survey

记录：

```text
online_first_date = 2025-12-10
issue_year = 2026
canonical_citation_year = 2026
```

## MOB-Net

记录：

```text
online_first_year = 2024
issue_year = 2025
canonical_citation_year = 2025
```

## voraus-AD

记录：

```text
online_first_year = 2023
issue_year = 2024
canonical_citation_year = 2024
```

不得把 online-first 年份和正式卷期年份当作互斥“纠错”。

---

# 6. Phase D0 — 公共数据集 feasibility audit

D0 必须在大规模训练前完成。

## 6.1 强制数据集

```text
voraus-AD
RoAD
AURSAD
```

## 6.2 补充数据集

```text
UR5e anomaly comparison
PyScrew
SARCOS（仅健康逆动力学；不得当故障数据）
```

## 6.3 每个数据集的正式 feasibility card

至少包含：

```text
dataset_id
canonical_paper
paper_doi
official_repo
repo_commit
official_data_url
data_version
release_date
http_headers
download_timestamp
compressed_size
extracted_size
ram_requirement
license_data
license_code
redistribution_allowed
commercial_restriction
robot
task
sampling_rate
episode_definition
signal_schema
signal_units
joint_order
timestamp_semantics
label_semantics
anomaly_start_end
fault_severity
official_split
leakage_risks
urdf_available
inertia_available
control_command_available
measured_torque_available
estimated_torque_available
physics_level
native_baseline
native_code_commit
checkpoint_available
applicable_models
not_applicable_models
allowed_claims
forbidden_claims
status
```

## 6.4 物理可用性等级

```text
P0_TIME_SERIES_ONLY
P1_JOINT_TOPOLOGY_ONLY
P2_PARTIAL_PHYSICS_SIGNALS
P3_FULL_DYNAMICS_METADATA
```

规则：

- P0/P1：禁止 RNEA/GMO/Jacobian；
- P2：只使用公开信号和拓扑；
- P3：才允许完整物理残差；
- 缺失量不得从机器人型号、测试标签、仿真 truth 或经验常数补造。

## 6.5 RoAD 已知事实

当前已发现：

```text
87 channels
1 action ID
8 whole-system electrical channels
7 joints × 11 IMU channels
  - 3-axis acceleration
  - 3-axis angular velocity
  - quaternion
  - temperature
1 anomaly label
no joint angle
no joint torque
no encoder
```

因此：

```text
rnea_gmo_public = NOT_APPLICABLE
RoAD physics level = P2_PARTIAL_PHYSICS_SIGNALS
```

但必须继续核验：

- quaternion order；
- frame convention；
- sign continuity；
- IMU mounting；
- joint/link assignment；
- synchronization；
- units。

在这些信息未明确前，允许称：

```text
orientation/inertial-aware chain model
```

禁止称：

```text
RNEA model
SE(3) rigid-body dynamics model
physical wrench model
```

## 6.6 RoAD 许可

RoAD 当前未发现 LICENSE/COPYING，处理：

```text
license_status = UNKNOWN
local_research_analysis = allowed provisionally
redistribution = forbidden
raw data in review ZIP = forbidden
raw data in Git = forbidden
```

不得因公开仓库可下载而推断许可。

## 6.7 VARADE 修正

VARADE 公开代码仓库存在，必须审计：

- repository URL；
- commit；
- license；
- VAAR.py / Transformer.py / autoencoder.py / BERTTrainer.py；
- checkpoints；
- data preprocessing；
- split；
- random seeds；
- paper-code consistency；
- metric implementation；
- test leakage。

候选复现等级：

```text
FAITHFUL_OFFICIAL_CODE
```

只有代码、commit、论文设置和指标真正一致，才可升级。

## 6.8 voraus-AD 已知事实与版本冻结

已知：

```text
100 Hz file ≈ 1.116 GB
500 Hz file ≈ 5.328 GB
data license = CC BY-NC-SA 4.0
code license = MIT
official repo commit observed = a91a86a（必须重新核验）
```

数据文件 Last-Modified 可能晚于论文。必须记录：

```text
URL
ETag
Last-Modified
Content-Length
SHA256
download timestamp
local immutable path
```

不得只依赖文件名。

## 6.9 AURSAD / UR5e / PyScrew

- AURSAD：重新核验正式 Zenodo record、版本、两个大文件 MD5、CC-BY-4.0；
- UR5e：CC-BY-NC-4.0，记录不可商业与再分发边界；
- PyScrew：先取 metadata 与一个代表场景，完成 schema/许可/规模卡后再决定全量；
- SARCOS：仅用于健康动力学/表示预训练，不进入异常检测结果。

## 6.10 D0 退出条件

至少：

```text
voraus-AD = READY
RoAD = READY_WITH_LICENSE_RESTRICTION
AURSAD = READY
```

否则公共基准门不得进入全量训练。

必需输出：

```text
dataset_feasibility_matrix.csv
dataset_license_matrix.csv
dataset_signal_schema_matrix.csv
dataset_applicability_matrix.csv
dataset_download_manifest.json
dataset_known_issues.md
```

---

# 7. Phase L2 — 系统全文审计

## 7.1 数量门槛

```text
发现库（去重）                 >= 250    已完成 5303
标题/摘要筛选                  >= 120
实际阅读全文                    >= 60
直接最近邻全文                  >= 25
killer-paper 深审               >= 10
引文链                         >= 8     已完成
2025–2026 直接相关全文          >= 15
公共数据/代码论文全文            >= 12
```

若全文不足，文献门必须为：

```text
LITERATURE_UNKNOWN_INSUFFICIENT_FULLTEXT
```

不得用 5303 条 metadata 代替 60 篇全文。

## 7.2 证据等级

```text
A1 publisher PDF / official proceedings full text
A2 author accepted manuscript / institutional repository
B1 arXiv full text + formal version cross-check
B2 thesis / patent / code docs
C  abstract / metadata only
```

只有 A1/A2/B1 能支持 OCCUPIED / OPEN / PARTIALLY_OCCUPIED。

`FULLTEXT_UNAVAILABLE` 不能用于证明“没有覆盖”。

## 7.3 三波全文获取

### Wave A — 15 篇 killer / 最近邻

必须优先完成并形成 dossier：

1. Annual Review FDI survey；
2. Haddadin et al. collision survey；
3. Evangelisti–Hirche data-driven momentum observer；
4. MOB-Net；
5. Kim–Lim–Park transferable collision detection；
6. Park unsupervised collision detection；
7. Lim LSTM-MO；
8. voraus-AD + MVT-Flow；
9. RoAD paper；
10. VARADE paper；
11. AURSAD paper/report；
12. DiffNEA；
13. MS-HGNN；
14. Sheikhi L-CSS subspace isolation；
15. Tan Automatica confidence-set/MDF 或最近最强替代。

Wave A 的作用是决定当前主线是否还有资格存在。

### Wave B — 25 篇直接方法谱系

配额覆盖：

- manipulator FDI/GMO；
- learning uncertainty torque；
- chain/module/GNN；
- geometry-aware representation；
- robot anomaly detection；
- contact localization；
- public benchmarks；
- cross-context transfer。

### Wave C — 20 篇理论与数据支撑

配额覆盖：

- MTS anomaly；
- contextual calibration；
- sequential detection；
- active diagnosis；
- dataset methodology；
- reproducibility；
- statistical evaluation。

## 7.4 谱系配额

至少：

```text
机械臂 FDI/碰撞                   15
学习型动力学/MO                   10
链式/几何表示                     10
公共数据/原生基线                 10
MTS anomaly/sequential            10
主动诊断/可诊断性                  5
```

不得用大量泛用 ML 论文凑够 60。

## 7.5 每篇全文 Method Card

必须基于正文，填写：

```text
complete citation
formal/preprint status
evidence level
pages actually read
problem definition
robot/system
sensors/signals
healthy/fault training
residual/model/network
RNEA/chain/graph/Lie/geometry use
detection/isolation/identification/accommodation
context/OOD
threshold/FAR/delay
datasets/code/licenses
baselines/splits
theorems/assumptions/computable quantities
limitations/failure cases
collision with C1–C6
occupancy decision
evidence page/formula/table
reviewer notes
```

不得仅依据摘要填写“未覆盖”。

## 7.6 Publisher 受限时的获取顺序

IEEE/ScienceDirect/ACM 出现 418/403 时：

1. 出版商正式页面 metadata；
2. 作者机构仓储；
3. 作者主页 accepted manuscript；
4. arXiv 与正式版本 cross-check；
5. 正式会议 proceedings；
6. Unpaywall/OpenAlex OA location；
7. 若仍无全文，标 `FULLTEXT_UNAVAILABLE`。

禁止通过绕过访问控制的方式获取。

## 7.7 MS-HGNN 的定位

状态：

```text
KILLER_NEIGHBOR_FOR_REPRESENTATION_CLAIMS
NOT_YET_KILLER_FOR_FDI_STORY
```

它会击穿：

- 首次使用机器人链 GNN；
- 首次嵌入几何/对称性；
- 首次以结构归纳偏置改善样本效率。

但只有在其覆盖健康-only anomaly、固定基座 manipulator、公共真实异常与 FDI 故事时，才可升级为 killer paper。

## 7.8 文献输出

```text
literature_discovery_raw/
literature_deduplicated.csv
title_abstract_screening.csv
fulltext_access_manifest.csv
fulltext_method_cards/
verified_bibliography.bib
fulltext_evidence_matrix.csv
nearest_neighbor_matrix.md
killer_paper_dossiers/
negative_search_log.md
citation_chain_log.csv
prisma_style_flow.md
literature_decision_memo.md
```

---

# 8. Phase B0 — 数据集原生基线 smoke

顺序不得改变：

```text
1. voraus-AD MVT-Flow
2. RoAD VARADE
3. AURSAD native/paper baselines
4. supplementary datasets
```

## 8.1 voraus-AD 双轨制

### Track A — EXACT_OFFICIAL_CPU

```text
Python 3.9
torch 1.12.1
official FrEIA commit
official requirements
official 100 Hz split/config
CPU smoke
```

目标：

- 官方环境可创建；
- 官方测试通过；
- 最小 train/eval 闭环成功；
- 官方 checkpoint 若有则成功推理；
- 指标代码和 split 与论文一致；
- 记录 CPU 时间和资源。

### Track B — FAITHFUL_OFFICIAL_GPU_PORT

```text
modern Python/PyTorch/CUDA
same architecture
same preprocessing
same split
same loss
same hyperparameters
same metric definitions
```

必须产生：

```text
environment_delta.md
dependency_delta.csv
numerical_parity_smoke.csv
official_cpu_smoke.json
gpu_port_smoke.json
```

只有两轨在合理容差内一致，GPU port 才能用于 full run。

不得要求 checkpoint bitwise 相同；复现对象是算法、split、预处理、超参数和多种子指标。

## 8.2 RoAD VARADE

必须：

- freeze official/author repo commit；
- audit license；
- reproduce loader；
- reproduce paper split；
- inspect checkpoint；
- record deviations；
- no silent fix；
- no redistribution of raw data。

若代码/论文不完全一致，等级降为：

```text
FAITHFUL_PAPER
POLICY_BASELINE
```

不得称官方复现。

## 8.3 AURSAD

在全文方法卡完成前，不冻结 native baseline。

先：

- official loader smoke；
- schema；
- operation grouping；
- split leakage audit；
- paper baseline table extraction；
- freeze native methods before test results。

## 8.4 B0 smoke 退出门

每个强制数据集至少：

- data hash verified；
- loader passes；
- one minimal fit/eval；
- split confirmed；
- metric pipeline confirmed；
- deviation ledger exists；
- no leakage。

未通过不得直接跑 full。

---

# 9. Phase B1 — 数据集原生基线 full reproduction

## 9.1 复现等级

```text
EXACT_OFFICIAL
EXACT_OFFICIAL_CPU
FAITHFUL_OFFICIAL_CODE
FAITHFUL_OFFICIAL_GPU_PORT
FAITHFUL_PAPER
PAPER_POLICY_BASELINE
REFERENCE_ONLY
NOT_APPLICABLE
BLOCKED
```

每个 baseline 必须有：

```text
source repo
commit
license
environment
patch
data version
split
random seeds
training logs
checkpoint hashes
metric implementation
paper target
observed result
tolerance
reproduction decision
```

## 9.2 不得混淆

- 官方 code 可运行 ≠ EXACT；
- 公开 checkpoint ≠ 论文最终模型；
- 自己重写 paper 方法 ≠ official reproduction；
- 测试指标接近 ≠ 代码忠实；
- 没有 license ≠ 可再分发。

---

# 10. Phase B2 — 统一公共基线矩阵

冻结矩阵：

```text
pca_spe_t2
ocsvm
isolation_forest
autoencoder
gru_autoencoder
mvt_flow_adapted（兼容时）
recent_mtsad_1（全文+代码审计后、结果前冻结）
joint_gru_public
chain_gnn_public
geometry_aware_chain_public（仅 P2/P3）
rnea_gmo_public（仅 P3）
mobnet_like_public（仅 P3 且目标可用）
```

## 10.1 公平性规则

- episode-safe split；
- 同一物理运行的窗口不得跨 split；
- validation-only hyperparameters；
- fault test 不用于选择；
- matched input；
- matched window；
- matched anomaly head；
- matched search budget；
- cluster bootstrap unit = episode/operation；
- 报参数量、训练时间、推理时间。

## 10.2 recent MTSAD

必须先全文和官方代码审计，再在任何测试结果前冻结：

```text
model
repo
commit
license
input shape
training policy
hyperparameter budget
datasets
```

不得在看到候选结果后选择“最弱的近期模型”。

---

# 11. Phase C — 当前候选的合法公共适配

## 11.1 目标不是硬塞内部算法

根据 applicability matrix：

### P0

只允许：

```text
Joint-GRU
universal baselines
```

### P1

允许：

```text
Joint-GRU
raw chain topology GNN
```

### P2

允许：

```text
Joint-GRU
raw chain GNN
geometry-aware non-equivariant chain model
```

但只能使用公开的 orientation / angular velocity / acceleration / temperature / topology。

### P3

才允许：

```text
RNEA/GMO
full geometry-aware residual
MOB-Net-like
```

## 11.2 RoAD 几何候选

若 quaternion/frame 语义核验通过，可构造：

- quaternion sign continuity；
- relative orientation；
- log-map or rotation-6D feature；
- body angular velocity；
- body acceleration；
- temperature；
- joint-chain topology。

这称为：

```text
SO(3)/inertial-aware chain representation
```

不称 RNEA、wrench、full SE(3) dynamics。

## 11.3 不得从内部 MuJoCo 迁移

禁止把以下内部量补入公共数据：

- simulated inertia；
- simulated contact point；
- truth fault family；
- Pinocchio nominal torque；
- simulator-only control command；
- hidden wrench；
- internal pathway dictionary。

## 11.4 候选生存条件

候选必须在至少两个强制数据集，相对最强 faithful baseline：

- AUROC 稳定提升 >= 0.03，或
- AUPRC 稳定提升 >= 0.05；
- FPR@TPR90 不恶化超过 10%；
- 至少 2 个 seed；
- 至少 2 个 context/anomaly strata 同向；
- 不能由更大参数量、不同 head 或不同输入解释。

否则：

```text
CANDIDATE_SIMULATION_ONLY
CANDIDATE_NO_VALUE
CANDIDATE_NOT_APPLICABLE
```

---

# 12. Phase E — 分析与指标

每个数据集同时报告：

## 12.1 原生指标

严格按论文/官方代码。

## 12.2 统一指标

```text
AUROC
AUPRC
FPR@TPR90
event precision/recall/F1
false alarms/hour（有时间戳时）
detection delay（有起点时）
per-anomaly metrics
context-stratified metrics
sample-efficiency curves
training/inference cost
```

## 12.3 外部有效性

必须分开：

```text
public real data
internal MuJoCo simulation
```

禁止合并后报一个总均值。

## 12.4 统计

- episode/operation cluster bootstrap；
- 不使用 window IID bootstrap；
- 三种子或按官方要求；
- 报 CI 与效应量；
- 不用单一最好 seed；
- 多次比较记录。

---

# 13. Phase N — 新颖性碰撞

对当前候选 C1–C6 逐项判定：

```text
OCCUPIED
PARTIALLY_OCCUPIED
PLAUSIBLY_OPEN
UNKNOWN
FALSELY_FRAMED
```

不得用：

```text
没有一篇论文同时包含全部模块
```

证明创新。

## 13.1 Killer paper 判据

若某工作虽然网络名字不同，但已经覆盖：

- 相同机器人/公共数据；
- 相同 healthy-only 学习问题；
- 相同 chain/geometry induction；
- 相同 cross-context story；
- 相同定位/归因能力；
- 相同实验完整度；

则判 killer。

## 13.2 性能与新颖性独立

- 候选性能好，不能放宽文献门；
- 候选性能差，不能假装文献占据；
- 文献开放但公共数据无价值，也不能继续当前方法；
- 文献占据但基准做得好，可考虑 benchmark pivot。

---

# 14. Phase F — 最终决策

必须调用已冻结的 decision code，不复制、不手工改写。

文献门：

```text
LITERATURE_PASS_PLAUSIBLY_OPEN
LITERATURE_PARTIALLY_OCCUPIED
LITERATURE_OCCUPIED_KILLER_PAPER
LITERATURE_UNKNOWN_INSUFFICIENT_FULLTEXT
BLOCKED_LITERATURE_ACCESS
```

公共基准门：

```text
PUBLIC_BENCHMARK_PASS
PUBLIC_BENCHMARK_PARTIAL
PUBLIC_BENCHMARK_FAIL_REPRODUCTION
PUBLIC_BENCHMARK_BLOCKED_DATA
```

候选门：

```text
CANDIDATE_EXTERNAL_VALUE
CANDIDATE_SIMULATION_ONLY
CANDIDATE_NO_VALUE
CANDIDATE_NOT_APPLICABLE
```

组合终态：

```text
BLOCKED
NO_GO_NOVELTY_KILLER_PAPER
NO_GO_CURRENT_METHOD_PUBLIC_DATA
PIVOT_PUBLIC_ANOMALY_BENCHMARK
PIVOT_CONTACT_SPECIALIST
PAPER_CANDIDATE_READY_FOR_REAL_ROBOT
LITERATURE_OR_BENCHMARK_INCONCLUSIVE
```

`PAPER_CANDIDATE_READY_FOR_REAL_ROBOT` 必须同时满足：

1. 文献门通过或明确部分占据但剩余贡献非平凡；
2. 公共基准 PASS；
3. 候选在 >=2 强制数据集稳定增量；
4. 至少一项跨上下文或少样本优势；
5. 不依赖伪造物理量；
6. 能形成一个单一论文级科学假设。

---

# 15. 执行次序与并行边界

## 15.1 立即执行

```text
M：验证挂载并迁移 scratchpad
D0：完成 feasibility matrix
L2 Wave A：15 篇 killer/最近邻全文
```

## 15.2 允许并行

在 D0 已明确 voraus-AD 100 Hz 可下载、G 盘空间足够后：

- L2 Wave A；
- voraus-AD CPU official smoke；
- VARADE repo/license audit；

可并行。

## 15.3 禁止过早并行

在以下未完成前，不得同时启动三个 full training：

```text
D0 三强制数据集 READY
Wave A 15 篇 method cards 完成
B0 smoke gate 通过
recent_mtsad_1 冻结
```

先完成 voraus-AD，再 RoAD，再 AURSAD。

---

# 16. Git 纪律

继续使用现有：

```text
branch:
stage/paper-reset-literature-public-benchmarks

worktree:
~/research/CERTO-FDI-WORKTREES/paper-reset-literature-public-benchmarks

Draft PR:
#8
```

不得新建第二个 paper-reset PR。

里程碑提交：

1. G-drive migration + storage provenance；
2. D0 dataset feasibility；
3. L2 Wave A；
4. L2 Wave B/C + literature gate；
5. voraus-AD official smoke/full；
6. RoAD VARADE；
7. AURSAD native；
8. universal baselines；
9. candidate adapters；
10. final analysis/decision；
11. review packages/pointers。

每次 push 后核验：

- PR #1–#7 heads 未动；
- PR #8 仍 Draft；
- worktree clean 或有明确进行中状态；
- 不 force-push；
- 不 auto-merge；
- 不将数据/PDF/checkpoint 提交 Git。

---

# 17. 必需输出

## 17.1 存储与 provenance

```text
storage_migration_report.md
storage_migration_manifest.json
run_manifest.json
environment_manifest.json
git_provenance.md
```

## 17.2 文献

```text
literature_deduplicated.csv
title_abstract_screening.csv
fulltext_access_manifest.csv
fulltext_method_cards/
verified_bibliography.bib
fulltext_evidence_matrix.csv
nearest_neighbor_matrix.md
killer_paper_dossiers/
negative_search_log.md
citation_chain_log.csv
prisma_style_flow.md
literature_decision_memo.md
```

## 17.3 数据

```text
dataset_feasibility_matrix.csv
dataset_license_matrix.csv
dataset_signal_schema_matrix.csv
dataset_applicability_matrix.csv
dataset_download_manifest.json
dataset_known_issues.md
```

## 17.4 基线

```text
native_baseline_registry_frozen.csv
baseline_reproduction_matrix.csv
baseline_deviation_ledger.csv
universal_baseline_matrix.csv
public_benchmark_manifest.json
cross_dataset_metrics.csv
sample_efficiency_curves.csv
context_generalization_metrics.csv
failure_analysis.md
```

## 17.5 候选

```text
candidate_adapter_matrix.csv
candidate_public_results.csv
candidate_ablation_matrix.csv
candidate_external_value_memo.md
```

## 17.6 决策

```text
paper_reset_decision_evidence.json
paper_reset_decision_memo.md
claim_ledger_final.csv
paper_level_hypothesis.md
allowed_and_forbidden_claims.md
known_issues.md
```

---

# 18. Review packages

生成：

```text
/mnt/g/CERTO-FDI/06_review_exchange/to_review/thin/
/mnt/g/CERTO-FDI/06_review_exchange/to_review/full/
```

Thin 必须包含：

- execution summary；
- literature flow；
- method-card index；
- killer dossiers；
- dataset cards；
- baseline matrix；
- candidate results；
- decision；
- code snapshot；
- configs；
- tests；
- git provenance；
- environment；
- manifests；
- independent review prompt；
- smoke script。

Full 在 Thin 基础上增加：

- 所有 CSV/JSON/NPZ；
- logs；
- checkpoints（许可允许时）；
- processed manifests；
- Git bundle；
- 不含受版权限制 PDF；
- 不含禁止再分发 raw data。

两包都必须通过：

```text
CRC
fresh extraction
internal SHA256 manifest
topology
secret scan
smoke reproduction
clean HEAD alignment
package index update
```

---

# 19. 硬性禁止

本轮不得：

- 新增神经网络架构；
- 设计第三种 LiGRA；
- 新增 Jacobian/pathway 模块；
- 新增严格证书；
- 重新调整内部 590 episode 仿真；
- 进入实机；
- 使用故障测试调参；
- window leakage；
- 伪造公共数据缺失的物理量；
- 仅凭摘要判 OPEN/OCCUPIED；
- 以“没有一篇同时包含全部模块”证明创新；
- 将工艺异常自动称为机械臂本体故障；
- 把 SARCOS 当故障数据；
- 把 RoAD IMU 模型称为 RNEA；
- 把 FULLTEXT_UNAVAILABLE 当“没有竞品”；
- 将受限 PDF/raw data 放进 Git/review ZIP；
- 自动 merge；
- 手工改最终终态；
- 因当前候选性能差而降低 baseline 忠实度。

---

# 20. 阻塞处理

遇到阻塞时不得停在一句报错。

必须：

1. 完成所有可完成部分；
2. 记录阻塞的准确文件、URL、HTTP、依赖或许可；
3. 记录已经尝试的替代路径；
4. 不用猜测补全；
5. 生成 `BLOCKED` 或 `INCONCLUSIVE` 审查包；
6. 给出下一条可执行命令；
7. 不承诺后台继续。

---

# 21. 最终报告格式

最终按顺序报告：

1. combined terminal state；
2. literature gate；
3. public benchmark gate；
4. candidate gate；
5. host/storage；
6. Git/PR；
7. L1/L2 flow；
8. full-text count and evidence levels；
9. killer papers；
10. C1–C6 occupancy；
11. dataset/license/applicability；
12. native baseline reproductions；
13. universal matrix；
14. candidate public results；
15. cross-dataset and sample-efficiency；
16. current paper-level hypothesis；
17. whether T-RO candidate survives；
18. known limitations；
19. allowed/forbidden next steps；
20. Thin/Full paths, sizes and SHA256。

---

# 22. 现在立即开始

现在立即执行：

```text
Phase M:
验证 /mnt/g
迁移 scratchpad
建立持久化 manifest
```

随后：

```text
Phase D0:
完成数据集 feasibility cards
```

随后：

```text
Phase L2 Wave A:
完成 15 篇 killer/最近邻全文 method cards
```

在完成上述三项前，不启动多数据集 full training，也不请求用户再次确认。
