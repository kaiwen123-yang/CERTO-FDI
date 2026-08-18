# Git, Storage, and PR Plan

## Git

```text
remote: git@github.com:kaiwen123-yang/CERTO-FDI.git
base: main
branch: stage/paper-reset-literature-public-benchmarks
worktree: ~/research/CERTO-FDI-WORKTREES/paper-reset-literature-public-benchmarks
```

- PR #1–#7 保持 Draft、未合并、不得改写；
- 新建 Draft PR #8（实际编号以 GitHub 为准），base=`main`；
- 不自动 merge；
- 不把旧实验分支整体 merge；
- 只选择性迁移必要的数据接口、评价和模型代码，并建立 `PORT_PROVENANCE.md`；
- 文献 PDFs、数据、checkpoint 和结果不提交 Git。

## G 盘结构

```text
/mnt/g/CERTO-FDI/
├── 01_frozen_sources/
│   ├── literature_reset/
│   │   ├── metadata/
│   │   ├── open_fulltexts/
│   │   └── access_manifest/
│   └── public_baseline_repos/
├── 02_research_docs/paper_reset/
│   ├── literature/
│   ├── novelty/
│   ├── datasets/
│   └── decisions/
├── 03_data/public/
│   ├── voraus_ad/
│   ├── road/
│   ├── aursad/
│   ├── ur5e_graabaek/
│   └── pyscrew/
├── 04_runs/paper_reset_public_benchmarks/<RUN_ID>/
├── 05_reference_results/paper_reset/
└── 06_review_exchange/to_review/{thin,full}/
```

## 里程碑 commits

1. protocol/decision freeze；
2. literature search and evidence tooling；
3. dataset registry/loaders/checks；
4. native baseline reproductions；
5. universal baselines；
6. candidate adapters；
7. combined decision and packaging。
