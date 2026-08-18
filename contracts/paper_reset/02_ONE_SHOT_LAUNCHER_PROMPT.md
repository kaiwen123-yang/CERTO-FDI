你现在是 CERTO-FDI Paper Reset 的执行负责人。不要让我创建目录、worktree、下载目录或手动运行初始化命令；全部由你完成。

在以下有限位置搜索：

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
CERTO_FDI_LITERATURE_PUBLIC_BENCHMARK_RESET_KICKOFF_20260818.zip
01_MASTER_PROMPT.md
```

找到 ZIP 后：

1. 计算 SHA256；
2. `unzip -t` 验证；
3. 解压到 `/tmp/certo_paper_reset_<UTC>`；
4. 完整读取 `01_MASTER_PROMPT.md` 和它列出的全部合同；
5. 将其作为本轮唯一执行合同；
6. 立即执行，不要只复述计划。

已知 Git：

```text
remote: git@github.com:kaiwen123-yang/CERTO-FDI.git
base: main
branch: stage/paper-reset-literature-public-benchmarks
worktree: ~/research/CERTO-FDI-WORKTREES/paper-reset-literature-public-benchmarks
```

PR #1–#7 均为历史 Draft：不得 merge、force-push、移动 head 或改写结果。

本轮只允许：系统全文文献审计、公开数据/许可/schema 审计、官方/忠实公共基线复现、统一通用基线、当前候选的合法公共数据适配、论文级决策。

禁止新增网络、Jacobain/路径模块、严格证书、仿真故障注入或实机实验。

开始时报告系统、挂载、Git、PR、文献访问、数据访问、资源、RUN_ID；随后直接进入 protocol freeze。
