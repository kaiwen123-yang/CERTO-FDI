# CERTO-FDI 全量执行主提示词
## 500 篇筛选 × 100 篇全文精读 × 三个真实公共数据集 × 最终论文级创新故事收敛

> 适用执行者：Claude Code / 具备终端、浏览器、Git 和长时任务执行能力的 Claude  
> 项目仓库：`git@github.com:kaiwen123-yang/CERTO-FDI.git`  
> 当前项目性质：科研方向重置、全文文献审计、公共基准复现、算法候选生成与论文故事收敛  
> 目标投稿层级：IEEE Transactions on Robotics（T-RO）优先；ICRA/RSS/RA-L/T-Mech 作为阶段性或备选  
> 本提示词优先级：高于此前任何“继续设计局部模块”的口头建议；不覆盖已经冻结的历史负结果

---

# 0. 你的角色与唯一总目标

你现在是 CERTO-FDI 项目的：

1. 系统综述负责人；
2. 主源全文审计员；
3. 机器人故障诊断与几何学习研究员；
4. 公共数据集与官方基线复现负责人；
5. 实验设计与统计审计员；
6. 论文级科学问题与故事收敛负责人；
7. Git、provenance、G 盘持久化与审查包负责人。

你的唯一总目标不是继续给现有模型打补丁，而是从最初母题重新出发：

> **神经网络如何利用李群、运动链、相对几何和机器人动力学结构，学习机械臂的健康误差/正常行为，并可靠地区分真实故障、异常接触与运行上下文变化？**

最终必须通过以下完整证据链，决定是否存在真正值得做、可执行、可投稿 T-RO/ICRA/RSS 级别的创新：

\[
\text{大规模文献发现与全文审计}
\rightarrow
\text{最近邻与 killer-paper 碰撞}
\rightarrow
\text{真实公共数据与忠实基线}
\rightarrow
\text{候选科学问题}
\rightarrow
\text{受控算法实验}
\rightarrow
\text{跨数据集证伪}
\rightarrow
\text{单一论文故事}.
\]

不要为了延续旧项目而保护任何旧模型。  
不要为了显得创新而把问题切成极小的局部补丁。  
不要因为某个构件已有先行工作就机械地放弃整个方向。  
也不要因为“没人把所有模块放在一起”就声称创新成立。

---

# 1. 当前可信状态、历史负结果与信任边界

## 1.1 GitHub 与分支

远程：

```text
git@github.com:kaiwen123-yang/CERTO-FDI.git
```

当前 Paper Reset 历史分支：

```text
stage/paper-reset-literature-public-benchmarks
```

当前 Draft PR：

```text
PR #8
base: main
head: stage/paper-reset-literature-public-benchmarks
```

在本提示词生成时，已知远程 head 为：

```text
bf8c70aacddfe050adf41e42229f0fe612ccc169
```

该 SHA 可能已在执行前变化。开始时必须重新核验，不得盲信。

PR #1–#8 都是历史审计或负面实验记录：

- 保持 Draft；
- 不得 merge；
- 不得 force-push；
- 不得改写历史；
- 不得移动其 head；
- 不得把历史 NO-GO/PIVOT 文件原位改成新结论。

## 1.2 新分支与新 PR

由于本轮把原最低门槛从 60 篇全文升级为 100 篇精读，并新增“最终创新与论文故事收敛”，这是一个新的冻结范围。必须从 PR #8 当前远程 head 派生新分支：

```text
branch:
stage/paper-reset-v2-500x100-public-story-convergence

worktree:
~/research/CERTO-FDI-WORKTREES/paper-reset-v2-500x100-public-story-convergence
```

新建 stacked Draft PR：

```text
base:
stage/paper-reset-literature-public-benchmarks

head:
stage/paper-reset-v2-500x100-public-story-convergence
```

建议标题：

```text
Paper Reset V2: 500-paper screen, 100 full-text audit, public benchmarks, and paper-story convergence
```

禁止自动 merge。

## 1.3 现有历史结论：不得重新包装

以下结论已经经过相对充分的数学或公平实验审计，除非发现明确代码错误或主源直接反证，不得为了恢复旧故事而重新开启：

### 永久删除

```text
故障破坏逐连杆 frame/gauge covariance
等变误差可以作为一般机械故障分数
frame covariance 自动推出跨构型 CFAR
健康有界变化可被无界线性子空间整体商掉
```

### 已停止作为主贡献

```text
严格逐连杆 LiGRA-v1 / LiGRA-v2 typed-equivariant 网络
全严重度区间的一阶闭环集合证书
统一 Jacobian 故障头处理全部故障族
当前自主 contact product
```

### 可以作为输入和基础，但不是已成立创新

```text
RNEA / GMO 物理残差
运动链或轴分组结构
Lie-group-informed / geometry-aware 非等变表示
上下文条件健康建模
多时间尺度异常检测
跨机器人、跨任务、少健康数据迁移
模块化故障路径解释
```

## 1.4 RoAD 外部结果

RoAD 冻结源：

```text
commit:
8d3366984609d952ae933e3ce6335ad29c7838be
```

RoAD 交接完整 ZIP：

```text
SHA256:
c25a01136b24f009b3d161eb1ae10ff36f8d894319e28acdd36f55346237e922
```

可能存在于：

```text
/mnt/g/CERTO-FDI/01_frozen_sources/public_baseline_repos/roaddataset
/mnt/g/CERTO-FDI/06_review_exchange/to_sandbox
Windows Downloads
```

ChatGPT 沙盒曾生成两套外部分析包，执行时若能在下载目录或 G 盘找到，必须把它们作为“外部未验证审计输入”摄取：

```text
ROAD_SANDBOX_FULL_BENCHMARK_20260820.zip
expected SHA256:
7aaef698b6fc87402d4829a496daefea8276a0df8c6b97a2c25f0f3b5953f76a

ROAD_SANDBOX_EXTENDED_AUDIT_20260821.zip
expected SHA256:
b286d44e692efcf6d3f95b5f8b3312a0f1549d89df0520e784b3751c6c1c342f
```

旧沙盒先得到 `SANDBOX_PIVOT_COLLISION_ONLY`，扩展审计又把其收紧为：

```text
SANDBOX_NO_GO_CURRENT_CHAIN_GEOMETRY_CANDIDATE_ON_ROAD
```

扩展审计声称：

- 真实关节顺序相对多个乱序控制无稳定优势；
- Chain 相对 Flat TCN 的优势依赖健康拆分；
- 当前直接 SO(3) 附加特征无稳定收益；
- SO(3) 上下文跨健康记录标定存在灾难性失效；
- RoAD 碰撞信息主要来自加速度和角速度瞬态；
- 当前事件级检测与虚警不可部署。

这些都必须独立检查，不能直接当作真值；但在未反证前，禁止继续把当前 Chain/SO(3) 模型当成默认论文候选。

## 1.5 旧文献报告的地位

阶段零、早期“组合利基开放”、对称性破缺综述、Claude 审核、Paper Reset 检索库全部是候选证据，不是当前权威。

每条旧结论必须标记：

```text
VERIFIED_BY_FULLTEXT
SUPPORTED_BY_METADATA_ONLY
SECONDARY_SOURCE_ONLY
CONTRADICTED
OUTDATED
FULLTEXT_UNAVAILABLE
```

禁止继承旧报告中的“OPEN”“FIRST”“T-RO 可投”等绝对判断。

---

# 2. WSL / G 盘 / 存储硬合同

## 2.1 环境

用户的 WSL 虚拟磁盘在 Windows E 盘，空间受限。  
G 盘是专门的持久化存储盘，WSL 挂载点：

```text
/mnt/g
```

开始时必须执行：

```bash
mountpoint -q /mnt/g
findmnt -T /mnt/g -o TARGET,SOURCE,FSTYPE,OPTIONS
df -h /
df -h /mnt/g
touch /mnt/g/.certo_write_test
rm /mnt/g/.certo_write_test
```

若 `/mnt/g` 不是真实挂载，终态为：

```text
BLOCKED_PERSISTENT_STORAGE
```

不得把大文件写入 WSL/E 盘继续执行。

## 2.2 Linux 本地只保存

```text
Git repo / worktree
src / tests / scripts / configs
当前活动虚拟环境
小型 metadata
小型临时文件
最多 5 GiB 本地 staging
```

## 2.3 G 盘必须保存

根目录：

```text
/mnt/g/CERTO-FDI
```

所有以下内容必须写 G 盘：

```text
论文 PDF / 作者版全文 / 文本提取
文献数据库导出
公共数据 raw / processed / split
官方代码归档与 Git bundle
checkpoint
训练日志
prediction
CSV / JSON / NPZ
图表
环境锁与 wheel
下载缓存
Thin / Full 审查包
```

建议本轮根目录：

```text
/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/<RUN_ID>
```

文献：

```text
/mnt/g/CERTO-FDI/02_research_docs/paper_reset_v2/literature
```

公共数据：

```text
/mnt/g/CERTO-FDI/03_data/public
```

环境与缓存：

```text
/mnt/g/CERTO-FDI/08_cache
/mnt/g/CERTO-FDI/09_environment_archives
```

## 2.4 红线

```text
G 盘剩余空间最低：50 GiB
WSL 根分区剩余最低：20 GiB
本地 staging 最高：5 GiB
```

低于红线时：

- 暂停 500 Hz 数据；
- 暂停 PyScrew 全量；
- 只保留 best/final checkpoint；
- 删除已经验证的重复 staging；
- 不生成非里程碑 Full 包。

## 2.5 缓存

项目进程中设置：

```bash
export PIP_CACHE_DIR=/mnt/g/CERTO-FDI/08_cache/pip
export TORCH_HOME=/mnt/g/CERTO-FDI/08_cache/torch
export HF_HOME=/mnt/g/CERTO-FDI/08_cache/huggingface
export UV_CACHE_DIR=/mnt/g/CERTO-FDI/08_cache/uv
```

不要把活动 `.venv`、`TMPDIR`、`XDG_RUNTIME_DIR` 全局放到 G 盘。

---

# 3. 第一提交：新协议冻结

在新一轮检索排序、全文计数、模型结果产生之前，第一提交必须包含：

```text
contracts/paper_reset_v2/
configs/paper_reset_v2.yaml
src/certo_fdi_reset_v2/decision.py
docs/paper_reset_v2/PROTOCOL_FREEZE.md
docs/paper_reset_v2/PORT_PROVENANCE.md
tests/test_paper_reset_v2_freeze.py
```

第一提交信息：

```text
Paper Reset V2: freeze 500-screen, 100-fulltext, public-benchmark and story-convergence protocol
```

该提交必须早于：

- 新全文 Method Card；
- 新基线训练；
- 候选方法结果；
- 最终故事选择。

---

# 4. 文献任务：500 篇筛选与 100 篇全文精读

## 4.1 不重新制造一个低质量发现库

Paper Reset 已形成约 5,303 条去重记录。优先复用、清洗和排序现有库，不要为了满足“500 篇”而重新下载重复元数据。

本轮硬门：

```text
候选池去重记录                  >= 500
实际标题/摘要人工筛选            >= 500
全文实际阅读                     >= 100
直接最近邻全文                   >= 35
killer-paper 深度 dossier        >= 15
2025–2026 直接相关全文           >= 25
公共数据/代码/基准论文全文        >= 20
前向/后向引文链                  >= 10
```

“筛选 500 篇”必须有人类可审计的逐条结果，不是自动 relevance score 数量。

## 4.2 时间范围

主范围：

```text
2021-01-01 至当前执行日期
```

允许加入最多 20 篇不可替代经典论文，例如：

- 几何 FDI；
- 动量观测器；
- RNEA / Newton–Euler；
- 序贯检测；
- CFAR / matched subspace；
- 机器人碰撞综述；
- PCA/MSPM 故障几何。

建议结构：

```text
近五年正式/预印本全文：80 篇以上
经典基础全文：20 篇以内
```

## 4.3 文献谱系与最低配额

| 谱系 | 最少全文 |
|---|---:|
| 机械臂 FDI、碰撞检测、动量观测器 | 20 |
| 学习型动力学误差、外力矩估计、健康残差 | 15 |
| 运动链、模块化、图结构、可微动力学 | 12 |
| Lie group、geometry-aware、equivariant / approximately equivariant | 15 |
| 公共机器人异常数据与原生基线 | 12 |
| 多变量时序异常检测、OOD、domain shift | 12 |
| 条件标定、序贯报警、false alarms/hour | 8 |
| 跨机器人、跨任务、少样本迁移 | 6 |
| 主动诊断、可诊断性与传感器设计 | 5 |
| 合计 | >=105；去重后至少 100 |

如果一篇跨多个谱系，只计一次全文总数，但可在多个谱系标记。

## 4.4 Venue 优先级

### Tier S：Nature/Science 体系，必须直接相关

```text
Science Robotics
Nature Machine Intelligence
Nature Communications
Science Advances
其他直接相关 Nature/Science 专业刊
```

不得为了“Nature/Science 系列”而纳入与机械臂 FDI 关系很弱的论文。

### Tier R：机器人领域顶级

```text
IEEE Transactions on Robotics
The International Journal of Robotics Research
Robotics: Science and Systems
IEEE Robotics and Automation Letters
ICRA
IROS
CoRL
```

### Tier C：控制、机电、工业、信号与学习顶级

```text
Automatica
IEEE Transactions on Automatic Control
IEEE/ASME Transactions on Mechatronics
IEEE Transactions on Industrial Electronics
IEEE Transactions on Automation Science and Engineering
Mechanical Systems and Signal Processing
L4DC
NeurIPS
ICML
ICLR
AISTATS
```

### Tier Q1

记录 2025 年中科院一区 Top / 一区标签，但必须：

- 保存评级来源；
- 保存查询日期；
- 不以期刊分区替代直接相关性；
- 不把低相关 Nature 子刊排在直接相关 T-RO/IJRR 之前。

MDPI 可作为排除项或背景，不能作为主创新锚点、主要竞品和推荐投稿 venue。

## 4.5 检索数据库

至少使用：

```text
OpenAlex
Crossref
DBLP（精确题名/正式版本核验）
arXiv
Google Scholar（若可）
Semantic Scholar（若有 API/不被限流）
IEEE Xplore
ACM DL
ScienceDirect
SpringerLink
PMLR
RSS Proceedings
作者机构仓储
Unpaywall
出版社正式页面
```

如果 IEEE/Elsevier/ACM 被阻断：

1. 查作者主页；
2. 查机构仓储；
3. 查 accepted manuscript；
4. 查 arXiv；
5. 用 DOI/卷页交叉核验正式版；
6. 仍不可得则 `FULLTEXT_UNAVAILABLE`。

`FULLTEXT_UNAVAILABLE` 不得支持 `OPEN` 或 `OCCUPIED`。

## 4.6 检索词簇

必须同时覆盖：

```text
robot manipulator fault detection
robot collision detection momentum observer learning
model uncertainty learning manipulator
proprioceptive anomaly detection robot
robot anomaly detection public dataset
kinematic chain graph neural network dynamics
modular neural network robot collision
Lie group robot dynamics learning
geometry-aware time series robot anomaly
equivariant fault detection
approximately equivariant dynamics anomaly
symmetry breaking fault detection robot
cross-robot anomaly detection
cross-task robot anomaly detection
healthy-only robot anomaly detection
context-conditioned robot anomaly
robot anomaly calibration false alarm
sequential robot fault monitoring
multiscale time-series anomaly robot
domain adaptation robot anomaly
few-shot healthy adaptation anomaly detection
robot foundation model anomaly detection
multimodal proprioceptive anomaly detection
```

并对 killer papers 做前向/后向追踪。

## 4.7 全文证据等级

允许支撑新颖性：

```text
A1 出版商或正式 proceedings 全文
A2 作者接受稿或机构仓储
B1 arXiv 全文 + 正式版本交叉核验
```

不允许支撑新颖性：

```text
摘要
搜索摘要
博客
二手综述单独陈述
ResearchGate 页面
标题推断
```

## 4.8 Method Card

每篇精读至少记录：

```text
paper_id
完整引用
DOI / 正式 URL
online-first / issue year
正式或预印本
venue / tier / 中科院标签
机器人/系统对象
输入信号
是否需要 q / qdot / torque / current / IMU / URDF
训练数据
是否 healthy-only
异常/故障定义
算法结构
物理模型与几何结构
是否 equivariant
是否 geometry-aware 但非 equivariant
损失
阈值与校准
序贯机制
数据拆分
跨构型/跨负载/跨机器人
基线
指标
代码/数据/license
理论
限制
与本项目重叠
击穿哪个候选贡献
未覆盖什么
证据页码/公式/图
最终标签
```

最终标签：

```text
OCCUPIED
PARTIALLY_OCCUPIED
PLAUSIBLY_OPEN
UNKNOWN
FALSELY_FRAMED
NOT_DIRECTLY_RELEVANT
```

## 4.9 Killer-paper dossier

至少 15 个 dossier。每个必须回答：

1. 是否同一科学问题；
2. 是否同一输入与训练范式；
3. 是否同一机器人对象；
4. 是否同一几何/物理结构；
5. 是否已有跨机器人/跨任务；
6. 是否已有公共数据与实机；
7. 是否已有事件级虚警与延迟；
8. 若网络名字不同，论文故事是否实质相同；
9. 是否让候选故事 NO-GO。

重点审读但不限于：

```text
Evangelisti & Hirche 2024
MOB-Net
Kim–Lim–Park transferable collision detection
Park unsupervised collision detection
voraus-AD / MVT-Flow
RoAD
VARADE
MS-HGNN
DiffNEA
structured rigid-body dynamics survey
Lie-group Hamiltonian / port-Hamiltonian learning
recent cross-robot anomaly detection
recent robot MTSAD
recent multi-timescale anomaly detection
recent foundation-model anomaly methods
```

---

# 5. 公共数据任务

## 5.1 强制数据集

必须完成：

```text
voraus-AD 100 Hz
RoAD
AURSAD
```

补充至少一个：

```text
UR5e anomaly comparison
PyScrew representative subset
SARCOS（只用于健康动力学，不算异常数据）
```

## 5.2 物理可用性等级

每个数据集标记：

```text
P0_TIME_SERIES_ONLY
P1_JOINT_OR_AXIS_TOPOLOGY
P2_PARTIAL_PHYSICS_SIGNALS
P3_FULL_DYNAMICS_METADATA
```

禁止：

- 缺 URDF 时从型号补造；
- 电流乘经验常数称为真实关节力矩；
- 无 q 时运行 RNEA；
- 无接触点时声称精确 Jacobian 定位；
- 用异常标签构造输入；
- 用测试集估计归一化。

不适用必须写：

```text
NOT_APPLICABLE
```

## 5.3 RoAD

RoAD 当前应作为外部负面证据和通用时序碰撞数据。

必须独立复核 ChatGPT 沙盒结果：

- 检查两个结果 ZIP；
- 重算关键 CSV；
- 选择至少 E1、E2、E4、E5 做本机复算；
- 比较真实顺序与多个乱序；
- 检查健康拆分敏感性；
- 检查通道来源。

不要再在 RoAD 上设计第三种 Chain/SO(3) 网络。  
RoAD 主要用于：

```text
否定不稳健的链拓扑/几何主张
建立碰撞时序基线
测试事件级虚警与阈值迁移
```

## 5.4 voraus-AD

必须完成：

### Track A：官方 CPU 环境

```text
Python 3.9
torch 1.12.1
官方 FrEIA commit
官方 requirements
100 Hz
官方 split
官方参数
```

先 smoke，再尽可能完成官方全日程。若 CPU 3 seeds 过慢，可至少做：

- 官方 tests；
- 官方一个完整 seed；
- 官方 checkpoint 或 70 epoch；
- 数据与评估逐值检查。

### Track B：现代 GPU faithful port

```text
RTX 5080
现代 PyTorch/CUDA
模型、split、预处理、loss、超参数不变
70 epoch
3 seeds
```

输出：

```text
best AUROC
final AUROC
AUPRC
FPR@TPR90
per anomaly type
training curve
runtime
checkpoint hash
CPU/GPU parity
```

不能把短 10 epoch 结果作为最终。

## 5.5 RoAD 原生基线

先读 RoAD 正文。不要把 VARADE误称为 RoAD 原生 baseline。

确认正文实际比较的：

```text
kNN
Isolation Forest
AE
VAE
VQ-VAE
OmniAnomaly
MAD-GAN
GDN
其他原生方法
```

VARADE 作为后续使用 RoAD 的 policy baseline，单独审计：

- 代码；
- checkpoint；
- license；
- 数据重复；
- seed；
- training script；
- evaluator bug。

## 5.6 AURSAD

完成：

- 官方数据与 loader；
- 许可；
- 原生拆分；
- 工件/操作重复泄漏；
- 类不平衡；
- 原生论文基线；
- 统一基线；
- 当前候选合法适配。

不要同时保留 HDF5 和 Pickle 两套完整副本，选一个主格式，另一套只保留 hash 和 provenance。

---

# 6. 基线矩阵

## 6.1 数据集原生基线

```text
voraus-AD: MVT-Flow
RoAD: 论文原生 baselines
AURSAD: 正文原生 baselines
```

## 6.2 统一传统基线

```text
Robust Mahalanobis
PCA-SPE / Hotelling T²
Isolation Forest
One-Class SVM
```

## 6.3 统一神经基线

```text
Window Autoencoder
GRU Autoencoder
TCN Autoencoder
Flat GRU / TCN predictive or density model
```

## 6.4 近期强 MTSAD

在任何结果产生前，由全文和官方代码审计冻结：

- 一个 reconstruction/density 类；
- 一个 attention/transformer 或 convolution 类；
- 一个近期强、代码可复现、无明显泄漏的方法。

选择条件：

```text
2021–当前
公开代码
可运行
支持多变量时序
训练/测试定义明确
不是仅在 point-adjusted 指标下显得强
```

必须记录是否使用 point adjustment。主结果禁止使用有争议的 point adjustment；可作为补充。

## 6.5 结构与几何候选阶梯

不是继续造模型，而是公平回答信息来源：

| 模型 | 链/轴分组 | 几何特征 | frame/rotation augmentation | 精确等变 |
|---|---:|---:|---:|---:|
| Flat TCN/GRU | 否 | 否 | 否 | 否 |
| Grouped chain/axis model | 是 | 否 | 否 | 否 |
| Geometry-aware non-equivariant | 是 | 是 | 否 | 否 |
| Geometry-aware + augmentation | 是 | 是 | 是 | 否 |
| 旧 LiGRA | 历史审计 | 历史审计 | — | 是 |

旧 LiGRA 不进入新候选搜索，只作为负结果。

几何候选必须有同维随机特征和乱序控制。

---

# 7. 实验公平性

## 7.1 数据拆分

- 以 episode / recording / workpiece 为独立单位；
- 禁止窗口随机拆分导致同一记录泄漏；
- PyScrew 工件重复必须 group split；
- AURSAD 动作和工件重复必须审计；
- RoAD 不允许用异常 test 调阈值；
- voraus 使用官方 split。

## 7.2 超参数

- 只用健康 train/validation；
- 测试异常不参与模型选择；
- 每个主模型相同调参预算；
- 参数量报告；
- 训练时长报告；
- 三随机种子；
- 保存 best/final checkpoint。

## 7.3 指标

必须报告：

```text
AUROC
AUPRC
FPR@TPR90
precision / recall / F1
false alarms/hour（可定义时）
detection delay
event recall
event F1
OOD/ID healthy alarm ratio
calibration error
sample-efficiency curve
per anomaly type
per dataset macro
```

Bootstrap 单位：

```text
episode / recording / workpiece
```

禁止把高度重叠窗口当独立样本。

## 7.4 点异常与整体工况异常

必须显式区分：

```text
fast transient anomaly
collective regime anomaly
context shift / healthy OOD
```

不能用一个重构误差的单向“大即异常”假设覆盖所有异常。

---

# 8. 候选创新生成：必须晚于全文与第一轮公共基准

在至少完成：

```text
40 篇决定方向的全文
voraus-AD 官方基线
RoAD 独立复核
AURSAD 数据审计
```

之前，禁止开始新算法设计。

然后必须生成 3–5 个候选，每个使用统一 Candidate Card：

```text
候选名称
一句话科学问题
为何是机器人问题而非通用 MTSAD
现有方法为何失败
最接近 5 篇全文
占据/部分占据/开放
输入与传感器
核心数学对象
方法模块
非装饰性的 Lie/geometry 价值
理论命题
公开数据适用性
最小实现
强基线
关键消融
失败条件
预计图表
T-RO 故事
风险与 NO-GO
```

优先考虑但不预设成立：

1. 跨机器人、上下文解耦的健康建模；
2. 快/慢双时间尺度机器人异常；
3. 模态缺失下的分级物理—几何表示；
4. 健康-only 少样本目标机器人适配；
5. 事件级低虚警 robot anomaly monitoring；
6. 接触/碰撞专项跨机器人迁移。

禁止候选：

```text
第三种精确李群等变网络
故障破坏 gauge covariance
只为 link 1 设计的局部补丁
只在内部 MuJoCo 上有效
没有公共数据适用性的“漂亮数学”
```

---

# 9. 候选实验：探索与确认分离

## 9.1 探索阶段

使用：

- training；
- healthy validation；
- development anomaly split（若数据协议允许）。

最多保留 2 个候选故事。

## 9.2 确认阶段

冻结：

- 架构；
- 输入；
- 超参数；
-阈值；
-主要指标；
-决策门。

再打开 final test。

不得在 final test 后增加新模块救结果。

## 9.3 跨数据集与跨机器人

至少执行一种：

### 零样本

```text
在数据集 A/B 的 healthy 上训练
直接测试数据集 C
```

### 少健康样本适配

```text
1 / 5 / 10 / 20 条健康 episode
```

### 多数据集健康预训练

```text
RoAD + voraus healthy
→ AURSAD/UR5e anomaly
```

公共数据通道不一致时，必须使用合法共享模态或 missing-modality adapter，不得补造信号。

---

# 10. 论文级决策门

## 10.1 文献门 PASS

必须同时满足：

```text
500 篇实际筛选
100 篇实际全文
35 篇直接最近邻
15 个 killer dossier
25 篇 2025–2026 直接相关
20 篇数据/代码论文
10 条引文链
所有最终贡献有最近邻
无未解决 DOI/状态冲突
```

否则：

```text
LITERATURE_INCONCLUSIVE
```

## 10.2 公共基准门 PASS

必须：

```text
voraus-AD 完成
RoAD 完成
AURSAD 完成
每个强制集至少一个 native baseline
统一基线矩阵完成
主模型三种子
无测试调参
无伪造物理量
```

## 10.3 方法生存门

候选相对最强 faithful baseline，在至少两个强制数据集满足：

\[
\Delta AUROC \ge 0.03
\]

或：

\[
\Delta AUPRC \ge 0.05
\]

并且：

```text
FPR@TPR90 不恶化超过 10%
至少 2/3 seeds 同方向
至少两个异常类型/上下文同方向
少样本或跨数据集至少一项成立
几何特征优于同维随机控制
链/轴结构优于多乱序控制
不是参数量优势
```

## 10.4 论文故事门

最终故事必须：

1. 是一个机器人科学问题；
2. 不是通用 MTSAD 换数据集；
3. 不是多个已有模块的无机拼接；
4. 有一个明确的失败机制；
5. 方法直接针对失败机制；
6. 至少三个真实公共数据集；
7. 一个内部机制数据集；
8. 强基线与官方 baseline；
9. 事件级结果；
10. 至少一个真实机器人/后续实机可执行计划；
11. 文献无 killer paper 直接占据；
12. 可以用一张总图讲清楚。

---

# 11. 允许的终态

完整性优先于科学结论。

```text
PAPER_GO_TRO_CANDIDATE
PAPER_GO_ICRA_RSS_CANDIDATE
PIVOT_PUBLIC_ROBOT_ANOMALY
PIVOT_COLLISION_CONTACT_SPECIALIST
PIVOT_BENCHMARK_DATASET_PAPER
NO_GO_CURRENT_METHOD_PUBLIC_DATA
NO_GO_NOVELTY_OCCUPIED
NO_GO_NO_COHERENT_ROBOT_SCIENCE
LITERATURE_OR_BENCHMARK_INCONCLUSIVE
BLOCKED
```

### PAPER_GO_TRO_CANDIDATE

要求：

- 文献门 PASS；
- 三数据集 PASS；
- 方法生存门 PASS；
- 一个统一故事；
- 预期可做实机；
- 无 killer paper。

### PAPER_GO_ICRA_RSS_CANDIDATE

有强机器人方法和实验，但理论/系统完整度尚不足 T-RO。

### PIVOT_PUBLIC_ROBOT_ANOMALY

故障物理归因失败，但跨上下文异常检测和低虚警成立。

### PIVOT_COLLISION_CONTACT_SPECIALIST

只有碰撞/接触跨机器人任务成立。

### PIVOT_BENCHMARK_DATASET_PAPER

方法无稳定优势，但公共基准、泄漏审计、统一协议和 negative results 具有独立价值。

### NO_GO_CURRENT_METHOD_PUBLIC_DATA

当前候选只在内部仿真有效，公共数据不优于强基线。

### NO_GO_NOVELTY_OCCUPIED

killer paper 覆盖同一问题、能力和故事。

### NO_GO_NO_COHERENT_ROBOT_SCIENCE

即使有局部数值提升，也无法形成机器人级统一问题。

---

# 12. 最终必须交付的论文级故事包

无论终态如何，必须生成：

```text
00_executive_decision_memo.md
01_prisma_style_flow.md
02_verified_bibliography.bib
03_500_paper_screening.csv
04_100_fulltext_evidence_matrix.csv
05_nearest_neighbor_matrix.md
06_killer_paper_dossiers/
07_negative_search_log.md
08_dataset_feasibility_matrix.csv
09_public_dataset_manifests/
10_baseline_reproduction_matrix.csv
11_universal_baseline_matrix.csv
12_cross_dataset_metrics.csv
13_sample_efficiency_curves.csv
14_event_and_false_alarm_metrics.csv
15_candidate_cards/
16_candidate_collision_matrix.md
17_final_method_contract.md
18_final_experiment_contract.md
19_final_story_memo.md
20_paper_title_abstract_contributions.md
21_paper_figure_table_plan.md
22_limitations_and_no_go_boundaries.md
23_claims_ledger.csv
24_decision_evidence.json
25_run_manifest.json
```

如果 GO，再额外生成：

```text
26_stage_next_codex_handoff.md
27_real_robot_validation_plan.md
28_preliminary_paper_outline.md
```

## 12.1 最终故事 memo 必须回答

1. 真正的新科学问题是什么；
2. 为什么不是一个细分补丁；
3. 为什么必须使用机器人几何/拓扑/动力学；
4. 李群在方法中是主贡献、辅助表示还是仅正确性语言；
5. 已有方法为什么失败；
6. 新方法哪个机制对应哪个失败；
7. 哪三组公共结果支撑故事；
8. 哪些结果是否定性的；
9. 何时必须拒绝输出；
10. 为什么够 T-RO/ICRA/RSS；
11. 最大风险是什么；
12. 实机最小验证是什么。

---

# 13. Git 里程碑

推荐提交：

```text
1. freeze V2 protocol
2. ingest prior evidence and provenance
3. complete 500-paper screening
4. complete first 40 fulltexts and killer dossiers
5. complete 100 fulltexts and literature decision
6. complete voraus official reproduction
7. complete RoAD independent replication
8. complete AURSAD benchmark
9. freeze candidate shortlist
10. complete exploratory candidate experiments
11. freeze final candidate
12. complete confirmatory cross-dataset tests
13. finalize paper story and decision
14. build review packages
```

每次 push 后验证 PR #1–#8 heads 未移动。

不得把以下内容提交 Git：

```text
PDF
raw data
checkpoint
大结果 CSV/NPZ
review ZIP
secret
```

Git 只保存：

```text
代码
配置
小型表
文档
provenance pointer
hash
```

---

# 14. 审查包

每个重大里程碑生成 Thin：

```text
/mnt/g/CERTO-FDI/06_review_exchange/to_review/thin
```

Full 仅在：

```text
100 篇全文完成
三个公共数据集完成
最终决策
```

生成到：

```text
/mnt/g/CERTO-FDI/06_review_exchange/to_review/full
```

审查包必须：

- CRC；
- fresh extraction；
- 内部 SHA256；
- topology；
- smoke；
- secret scan；
- Git HEAD 对齐；
- raw PDF/data 不再分发；
- RoAD license 限制遵守。

---

# 15. 执行纪律

1. 不要只列计划，立即执行。
2. 不要等待用户决定每一个模型。
3. 只有 sudo、账号、付费墙、数据许可或物理硬件需要用户时才报告阻塞。
4. 每个里程碑报告实际数字，不报告“正在努力”。
5. 发现 killer paper 立即报告。
6. 发现数据泄漏立即停止该结果。
7. 发现候选不优于强基线立即降级，不继续打补丁。
8. 不允许把摘要当全文。
9. 不允许用 test anomaly 选择模型。
10. 不允许把公共数据缺失信号补造出来。
11. 不允许因为结果负面而缩小问题直到“看起来可发表”。
12. 不允许因为构件已有而放弃一个仍可能有新系统问题的整体故事。
13. 所有新算法必须来自文献和公共数据共同暴露的失败机制。
14. 用户没有中止时，按合同持续推进到最终终态。

---

# 16. 开始时必须报告

开始后先报告：

```text
OS / WSL / kernel
Python / CUDA / PyTorch
CPU / GPU / RAM
/mnt/g mount and free space
repo / base / head / dirty
PR #8 state and current head
new worktree / branch
old result packages found and hashes
existing literature counts
existing fulltext counts
existing dataset status
existing official baseline status
RUN_ID
```

随后：

1. 创建 V2 branch/worktree；
2. 第一提交冻结合同；
3. 摄取 PR #8 与 RoAD 外部包；
4. 继续全文与公共基准；
5. 不等待确认。

---

# 17. 第一批执行顺序

严格顺序：

```text
Phase V0
验证 Git、G 盘、旧包和当前 Paper Reset 产物

Phase V1
冻结本提示词与 V2 决策规则，建立新 Draft PR

Phase L500
从现有 5303 库中完成 500 篇人工筛选

Phase L40
先完成 40 篇决定方向的全文：
25 killer/最近邻 + 15 cross-robot/context/MTSAD

Phase B-voraus
完成 voraus-AD 官方 MVT-Flow 和统一基线

Phase B-RoAD
独立复核 RoAD 扩展负结果，不再造新 RoAD 网络

Phase D-AURSAD
完成数据、split 和泄漏审计

Phase L100
补齐 100 篇全文和 15 个 killer dossier

Phase CANDIDATES
生成 3–5 个候选，只保留最多 2 个

Phase B-AURSAD
完成 AURSAD 原生和统一基线

Phase EXPLORE
候选探索实验

Phase FREEZE
冻结唯一候选和 final test

Phase CONFIRM
跨数据集、少样本、事件级确认

Phase STORY
论文故事、标题、摘要、贡献和图表

Phase DECISION
唯一终态、Draft PR、Thin/Full review packages
```

---

# 18. 退出标准

任务只在以下全部满足时结束：

```text
500 篇筛选完成
100 篇全文完成
三个强制数据集完成
官方/native baselines 完成
统一基线完成
候选生成与碰撞完成
最终候选确认或 NO-GO
论文级故事完成
最终决策完成
Git clean
远程同步
Draft PR 更新
Thin/Full 包验证
```

不能以“下一步建议”为结束。必须完成一个终态。
