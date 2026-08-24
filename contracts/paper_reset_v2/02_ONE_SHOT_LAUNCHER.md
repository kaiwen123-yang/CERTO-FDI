你现在是 CERTO-FDI 全量文献—公共基准—创新故事收敛阶段的执行负责人。

不要重新从零创建仓库，也不要改写 PR #1–#8。请先完整读取本启动包中的：

`01_MASTER_PROMPT.md`

随后将其视为本轮唯一执行合同，立即执行到最终终态，不要只给计划。

已知远程：

```text
git@github.com:kaiwen123-yang/CERTO-FDI.git
```

现有基础分支：

```text
stage/paper-reset-literature-public-benchmarks
```

新分支：

```text
stage/paper-reset-v2-500x100-public-story-convergence
```

新 worktree：

```text
~/research/CERTO-FDI-WORKTREES/paper-reset-v2-500x100-public-story-convergence
```

新 Draft PR 必须 stacked on：

```text
stage/paper-reset-literature-public-benchmarks
```

第一步必须重新核验 PR #8 的当前远程 head。提示词生成时已知是：

```text
bf8c70aacddfe050adf41e42229f0fe612ccc169
```

但不得假设它仍然不变。

所有大文件、数据、PDF、checkpoint、结果和审查包写入：

```text
/mnt/g/CERTO-FDI
```

WSL 本地只保留代码、测试、配置和活动环境。

本轮硬目标：

```text
500 篇实际筛选
100 篇全文精读
35 篇直接最近邻
15 个 killer-paper dossier
voraus-AD + RoAD + AURSAD
native baselines + unified baselines
最多 2 个候选故事
1 个最终论文级故事或明确 NO-GO
```

历史边界：

```text
不要设计第三种 LiGRA
不要恢复“故障破坏 gauge covariance”
不要继续在内部 590 episode 上调参
不要把 RoAD 当前 Chain/SO(3) 当成已成立候选
不要使用测试异常调参
不要补造公共数据缺失的物理量
不要自动 merge
不要 force-push
```

找到以下 RoAD 外部包时，先验证后摄取，不能盲信：

```text
ROAD_SANDBOX_FULL_BENCHMARK_20260820.zip
SHA256 7aaef698b6fc87402d4829a496daefea8276a0df8c6b97a2c25f0f3b5953f76a

ROAD_SANDBOX_EXTENDED_AUDIT_20260821.zip
SHA256 b286d44e692efcf6d3f95b5f8b3312a0f1549d89df0520e784b3751c6c1c342f
```

开始时报告环境、G 盘、Git、PR #8、已有文献数量、已有全文数量、公共数据与 baseline 状态、RUN_ID；随后立即冻结 V2 合同并执行，不等待确认。
