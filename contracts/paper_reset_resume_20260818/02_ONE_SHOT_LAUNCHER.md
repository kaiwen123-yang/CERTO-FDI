# CERTO-FDI Paper Reset — G 盘挂载后续跑一键提示词

你现在是 CERTO-FDI Paper Reset 的续跑负责人。G 盘已由用户手动挂载完成。

不要重新创建 Paper Reset 分支，不要重新执行 Phase 0 或 L1 discovery，不要新建第二个 PR。继续当前：

```text
remote: git@github.com:kaiwen123-yang/CERTO-FDI.git
branch: stage/paper-reset-literature-public-benchmarks
worktree: ~/research/CERTO-FDI-WORKTREES/paper-reset-literature-public-benchmarks
Draft PR: #8
known head: 8edec2729d2ec243a584fc1fc7712a2a1046d038
```

先在以下位置寻找完整续跑提示词：

```text
当前目录
~/Downloads
~/Desktop
/mnt/c/Users/*/Downloads
/mnt/c/Users/*/Desktop
/mnt/g/CERTO-FDI/00_inbox
```

寻找：

```text
CERTO_FDI_PAPER_RESET_RESUME_AFTER_G_MOUNT_MASTER_PROMPT_20260818.md
01_MASTER_PROMPT.md
```

找到后完整读取并作为唯一续跑合同。

立即执行，不只列计划：

1. 验证 `/mnt/g` 是真实 G: mountpoint，并做写入测试；
2. 按既有 migration manifest 将 scratchpad 全量迁移到 `/mnt/g/CERTO-FDI`；
3. 逐文件 SHA256 验证，验证前不删除 scratchpad；
4. 完成 D0 dataset feasibility；
5. 完成 L2 Wave A 15 篇 killer/最近邻全文 method cards；
6. 修正 online-first/issue-year 双字段；
7. 将 VARADE 公开仓库纳入 RoAD 原生基线审计；
8. 对 RoAD 只使用公开 IMU/四元数/温度/拓扑，不伪造 q、tau、URDF 或 RNEA；
9. 对 voraus-AD 执行 EXACT_OFFICIAL_CPU + FAITHFUL_OFFICIAL_GPU_PORT 双轨 smoke；
10. 不新增算法，不启动三个数据集的 full training，直到 D0 READY、Wave A 完成、B0 smoke 通过。

开始先报告环境、挂载、Git/PR、scratchpad、L1 产物、D0 状态、RUN_ID；随后直接进入迁移，不等待确认。
