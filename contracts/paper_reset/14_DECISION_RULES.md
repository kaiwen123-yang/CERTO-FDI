# Paper-Reset Decision Rules

决策代码必须在任何全量公共测试结果产生前提交。

## 1. 文献门

- `LITERATURE_PASS_PLAUSIBLY_OPEN`
- `LITERATURE_PARTIALLY_OCCUPIED`
- `LITERATURE_OCCUPIED_KILLER_PAPER`
- `LITERATURE_UNKNOWN_INSUFFICIENT_FULLTEXT`
- `BLOCKED_LITERATURE_ACCESS`

## 2. 公共基准门

- `PUBLIC_BENCHMARK_PASS`
- `PUBLIC_BENCHMARK_PARTIAL`
- `PUBLIC_BENCHMARK_FAIL_REPRODUCTION`
- `PUBLIC_BENCHMARK_BLOCKED_DATA`

`PASS` 至少要求 voraus-AD、RoAD、AURSAD 三个强制数据集完成数据校验；至少两个 dataset-native baseline 达到相应复现等级；统一基线矩阵完整且无泄漏。

## 3. 候选方法门

### `CANDIDATE_EXTERNAL_VALUE`

当前 chain/geometry candidate 在至少两个强制数据集达到 `13` 中生存条件，并且增量不能由更大模型/不同 anomaly head 解释。

### `CANDIDATE_SIMULATION_ONLY`

只在自建仿真有效，公共数据无稳定收益。

### `CANDIDATE_NO_VALUE`

公平比较后在三个强制数据集均不优于强基线，或仅随机单点收益。

### `CANDIDATE_NOT_APPLICABLE`

公共数据不足以实现该物理模型；此时不能据此宣称方法失败，但也不能支撑公共外部验证。

## 4. 组合终态

按优先级：

```text
BLOCKED
NO_GO_NOVELTY_KILLER_PAPER
NO_GO_CURRENT_METHOD_PUBLIC_DATA
PIVOT_PUBLIC_ANOMALY_BENCHMARK
PIVOT_CONTACT_SPECIALIST
PAPER_CANDIDATE_READY_FOR_REAL_ROBOT
LITERATURE_OR_BENCHMARK_INCONCLUSIVE
```

### PAPER_CANDIDATE_READY_FOR_REAL_ROBOT

同时满足：

1. 文献门为 `PASS_PLAUSIBLY_OPEN` 或明确的 `PARTIALLY_OCCUPIED` 且剩余贡献非平凡；
2. 公共基准 `PASS`；
3. 候选在 >=2 强制数据集有稳定增量；
4. 至少一项跨上下文或少样本优势；
5. 所有主张不依赖伪造物理量；
6. 结果足以定义一个单一论文级算法假设。

### PIVOT_PUBLIC_ANOMALY_BENCHMARK

候选算法没有稳定增量，但形成高质量、多数据集、忠实基线和可复现适配基准；是否作为 benchmark 论文另审。

### PIVOT_CONTACT_SPECIALIST

只有接触/碰撞专项具备外部证据，广义 FDI 不成立。

### NO_GO_CURRENT_METHOD_PUBLIC_DATA

候选在公共数据上无价值，且新增几何/链结构不优于强基线。禁止继续为当前方法添加新模块。
