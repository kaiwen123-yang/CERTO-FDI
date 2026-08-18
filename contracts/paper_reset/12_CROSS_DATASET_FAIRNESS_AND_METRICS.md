# Cross-Dataset Fairness and Metrics

## 1. 三种评价层级

### Dataset-native
按原论文指标与 split 复现，用于证明忠实性。

### Unified binary anomaly
统一报告：

- window/sample AUROC、AUPRC；
- episode/event AUROC、AUPRC、F1；
- FPR@TPR90；
- false alarms/hour（有真实时间轴时）；
- detection delay（有异常起点时）；
- per-anomaly/family metrics；
- healthy ID/OOD 分层；
- episode-cluster bootstrap CI。

### Transfer/sample efficiency

- 10/25/50/100% healthy training；
- train context A → test context B；
- leave-one-task/condition-out；
- 若跨数据集特征不兼容，不做伪跨数据集零样本迁移，而做共享接口/重新训练对比。

## 2. 公平性

- 不同模型使用完全相同的公开输入字段；
- 不把 dataset ID、fault label 或 test-only metadata 作为输入；
- 参数预算分组报告，不要求所有模型完全相等；
- 超参数搜索预算相同；
- 选择指标只用 normal validation 或数据集官方 validation；
- 不因候选方法需要而删除不利异常类；
- 异常极少类（如 AURSAD damaged thread）单独报告，不纳入不稳定 macro 结论或使用明确规则。

## 3. 统计

- 置信区间按 episode/operation cluster bootstrap；
- 多数据集比较报告平均排名、每数据集效应量和方向一致性；
- 禁止将窗口数当作独立样本扩大显著性；
- 预注册主要指标与 secondary 指标。
