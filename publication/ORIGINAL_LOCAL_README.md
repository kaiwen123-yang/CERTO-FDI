# CEO-FDI research workspace

目标：以理论为主，将现有 CERTO-FDI 研究推进为可评审的 IEEE TAC 投稿准备稿。项目文件夹名为 CEO-FDI；历史材料沿用 CERTO-FDI 标识，两者不构成两套模型或版本。

## 启动顺序

1. 阅读 `GOAL_PROMPT.md`：长期执行范围、授权和停止条件。
2. 阅读 `RESEARCH_PLAN.md`：阶段依赖、交付物、证明与实验标准。
3. 阅读 `CURRENT_STATE.md`：当前证据边界和第一步动作。
4. 核对 `source_index.json`，按需访问 `references/audit_20261007/`。不要每次重新通读全部 104 条历史消息。

## 文件位置

- `inputs/`：原始 R1 与 ADMISSION_REVISION ZIP，保持不可变，哈希在 `source_index.json`。大 ZIP 已忽略于 Git。
- `references/audit_20261007/`：上一阶段审查、原文、验证回执、证明接口和 TAC 路线的原样副本。
- `research/`：后续主张台账、定义版本、分支决策、进展和交接状态。
- `work/`：解压、推导草稿、临时脚本与计算中间结果。
- `outputs/`：本项目后续经检查的正式产物；对话交付的路径规则以运行时应用指令为准。

用户已启动 `/goal`。M0/M1/正定矩阵 M2 的固定范围主证明已完成内部独立审查；M2S边界、论文整合与完整 D2-a 扫描继续推进。阶段状态、活进程与证据边界见 `CURRENT_STATE.md` 和 `research/checkpoint.json`，不要重跑早期状态初始化脚本覆盖新进展。
