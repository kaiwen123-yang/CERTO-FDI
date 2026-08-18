# Candidate Model Adapter Protocol

## 1. 目标

当前内部原型不是公共数据上的既定算法。适配的目的，是检验链结构/几何信息是否有外部增量，而不是强行把每个数据集改造成 RNEA 数据集。

## 2. 表示阶梯

在可用数据上按以下顺序比较：

1. `joint_gru_public`：按公开关节/通道输入的普通 GRU；
2. `raw_chain_gnn_public`：仅使用公开关节顺序和链拓扑；
3. `geometry_aware_chain_public`：仅在数据明确提供所需几何/动力学元数据时启用；
4. `frame_aug_chain_public`：只有能够构造物理等价 frame 版本时启用；
5. `rnea_gmo_public`：只有 P3_FULL_DYNAMICS_METADATA 时启用。

## 3. 禁止的适配

- 从机器人型号猜测未公开的 URDF/惯性并宣称 exact；
- 用测试异常数据反推控制命令或外力；
- 把电流乘任意常数称为真实力矩而无官方标定；
- 把通道顺序当作真实 kinematic chain 而未核验；
- 用自建仿真的 fault pathway dictionary 解释公共数据标签；
- 将同一模型在不同数据集上的不同输入能力混成一个平均性能。

## 4. 主要归因实验

如果数据至少为 P1：

```text
Joint-GRU
Raw joint-group GNN
Chain GNN (topology)
Chain GNN + available geometry features
```

只在同一公开输入和相同 anomaly head 下比较。

## 5. 当前候选的生存条件

在至少两个强制公共数据集上，相对最强 faithful baseline：

- 主要 AUROC 提升 >= 0.03，或 AUPRC 提升 >= 0.05；
- 且 FPR@TPR90 不恶化超过 10%；
- 至少两个异常类别/上下文、两个种子同向；
- 或在 25% 健康数据下匹配基线 100% 数据性能；
- 不能只在自建仿真成立。
