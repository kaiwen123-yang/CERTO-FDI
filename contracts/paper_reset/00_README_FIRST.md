# CERTO-FDI Paper Reset — Read Me First

本包用于执行一次**论文级重置**，而不是继续扩展内部仿真算法。

本轮名称：

> **CERTO-FDI Paper Reset — Systematic Full-Text Literature Audit and Public Benchmark Reproduction**

唯一目标：

1. 用系统、可追溯的全文审计判断当前候选问题是否具有可辩护的新颖性；
2. 在真实公开机器人异常数据上忠实复现数据集原生基线和统一通用基线；
3. 判断当前 `chain_gnn_aug` / geometry-aware chain residual 思路是否在外部数据上具有可重复价值，还是只对自建 MuJoCo–Pinocchio 仿真有效；
4. 在这两个门通过前，**禁止设计新网络、新 Jacobian 模块、新证书或实机实验**。

## 当前 Git 边界

- 仓库：`git@github.com:kaiwen123-yang/CERTO-FDI.git`
- 新分支：`stage/paper-reset-literature-public-benchmarks`
- 新 worktree：`~/research/CERTO-FDI-WORKTREES/paper-reset-literature-public-benchmarks`
- 从 `main` 创建干净分支；旧 PR #1–#7 全部保持 Draft、未合并、不得改写。

## 存储边界

- Linux 本地：代码、测试、配置、虚拟环境、Git worktree；
- G 盘：论文全文索引、允许保存的开放全文、数据、checkpoint、运行结果、日志、图、manifest 与审查包；
- 默认持久化根：`/mnt/g/CERTO-FDI`，可通过环境变量 `CERTO_PERSIST_ROOT` 覆盖。

## 使用

最省事方式：把整个 ZIP 放进 Windows 下载目录，将 `02_ONE_SHOT_LAUNCHER_PROMPT.md` 的内容粘贴给 Codex 或 Claude Code。

## 信任规则

- 历史报告、早期“开放/首次”判断、旧 PR 结果均为**待核验输入**；
- 搜索摘要不能支持新颖性判断；
- “未发现”不能写成“不存在”；
- 数据集官方 split、标签、许可和 native baseline 必须从主源冻结；
- 公共数据缺少 URDF/惯性/控制器信息时，禁止伪造 RNEA、Jacobian 或物理路径输入；
- 公共测试异常不得用于模型、阈值或超参数选择。
