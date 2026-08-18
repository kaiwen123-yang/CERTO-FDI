# Scope and Claim Freeze

## 1. 本轮不是新算法阶段

禁止：

- 第三种 LiGRA 或其他精确等变网络；
- 新的 GNN/Transformer/normalizing-flow 结构搜索；
- 新的 Jacobian 定位器、严格证书或故障路径头；
- 在自建 590-episode 仿真上继续微调 1–2% 指标；
- 进入真实机械臂实验；
- 合并任何旧 Draft PR。

允许：

- 系统全文文献检索、全文获取、方法卡、引文链与新颖性碰撞；
- 公共数据下载、校验、schema/split/许可冻结；
- 数据集官方或论文原生基线忠实复现；
- 统一通用基线公平复现；
- 将当前内部候选模型以**不伪造缺失物理量**的方式适配公共数据；
- 形成论文级 GO/PIVOT/NO-GO 决策。

## 2. 待审计的总体科学假设

> 解析机器人动力学残差、运动链拓扑与空间几何表示能否作为健康时序建模的归纳偏置，在真实公开机器人异常数据上提升跨任务、跨速度、跨负载、跨上下文与有限健康样本条件下的异常检测性能，并提供比纯黑箱时序模型更稳定的物理归因？

## 3. 候选贡献（全部初始为 UNKNOWN）

- C1：`physics residual + chain representation` 在真实公共数据上的跨上下文异常检测价值；
- C2：geometry-aware、非精确等变的链式表示相对纯 joint-space 与普通 chain GNN 的增量价值；
- C3：有限健康样本下的样本效率与跨数据集/跨机器人迁移；
- C4：只在公开信号允许时的模块化物理归因，且不伪造不可观物理量；
- C5：episode-blocked 上下文标定与持续运行虚警/延迟评价；
- C6：公开、可复现的多数据集机器人异常基准与适配层。

每项最终只能标记：

```text
OCCUPIED
PARTIALLY_OCCUPIED
PLAUSIBLY_OPEN
UNKNOWN
FALSELY_FRAMED
```

## 4. 不可恢复的历史结论

- 故障不会普遍破坏逐连杆 frame/gauge covariance；
- gauge-equivariance error 不得作为一般机械故障分数；
- 当前 LiGRA-v1/v2 不再作为主要性能贡献；
- 旧严格闭环集合证书在冻结合同下 NO-GO；
- Stage 2B-F 的接触产品 `NO_GO_CONTACT_PRODUCT` 保持不变。

这些结论不得因公共基准结果不理想而回滚。
