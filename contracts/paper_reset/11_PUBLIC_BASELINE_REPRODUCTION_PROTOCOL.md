# Public Baseline Reproduction Protocol

## A. 复现等级

```text
EXACT_OFFICIAL          官方代码、版本、数据、配置、split 和指标
FAITHFUL_OFFICIAL       官方代码可运行，但环境/版本修复有记录
FAITHFUL_PAPER          按正文与附录重实现，方法卡完整
POLICY_BASELINE         论文只给策略，无法严格复现
REFERENCE_IMPLEMENTATION 通用基线
NOT_APPLICABLE          信号/标签/元数据不支持
BLOCKED                 数据/代码/许可/环境阻塞
```

禁止把 `POLICY_BASELINE` 写成官方复现。

## B. 阶段顺序

### Phase B0 — smoke

- 每个数据集读取少量 episode；
- schema、单位、标签、split、窗口与 hash 测试；
- 每个 baseline 单 epoch/小样本运行；
- 无泄漏测试；
- 估算全量时间和空间。

### Phase B1 — dataset-native reproduction

1. voraus-AD：官方 MVT-Flow 100 Hz；
2. RoAD：官方 loader 与 VARADE/native paper baseline；
3. AURSAD：官方 loader + 论文原生 benchmark；
4. 补充数据按可用性执行。

必须保存：

- repo commit、环境、patch；
- 原始/预处理数据 hash；
- split；
- 训练日志/checkpoint；
- 论文报告值与复现值；
- 任何偏差解释。

### Phase B2 — universal baseline matrix

统一运行：PCA-SPE/T2、OC-SVM、Isolation Forest、AE、GRU-AE、MVT-Flow-adapted、冻结的一种 recent MTSAD。

公平约束：

- 同一数据 split；
- 相同可用输入；
- 相同 normal validation；
- 相同窗口与 episode 聚合协议，或明确模型原生协议并双报；
- 相同超参数预算；
- 三个随机种子（无随机性的模型标 `DETERMINISTIC`）；
- test anomaly 从未参与选择。

### Phase B3 — current candidate adapters

只运行 `13_CANDIDATE_MODEL_ADAPTER_PROTOCOL.md` 允许的模型。任何物理量缺失都必须输出 `NOT_APPLICABLE`，不能用常数、测试标签或仿真参数填补。

## C. 复现容差

若官方论文/代码给出确定性 split 和单值指标：

- AUROC/AUPRC 绝对差 <= 0.01 或相对差 <= 2%，取较宽者；
- 样本/episode 计数必须精确；
- 指标定义和聚合必须一致。

若论文仅报告均值/随机 split：

- 三种子均值应落在报告均值 ± 报告标准差；
- 无标准差时只标 `FAITHFUL_NOT_NUMERICALLY_VERIFIED`，不得强行 2% gate。

## D. 输出

- `dataset_schema_matrix.csv`
- `dataset_split_manifest.csv`
- `native_baseline_reproduction.csv`
- `universal_baseline_matrix.csv`
- `baseline_deviation_ledger.csv`
- `training_run_manifest.json`
- `baseline_reproduction_memo.md`
