# Public Dataset Feasibility and Download Protocol

## 1. 下载前必须做 feasibility card

每个数据集先填写：

- 正式论文、官方数据 URL、版本、发布日期；
- 许可、非商业限制、再分发限制；
- 文件大小、解压大小、RAM 需求；
- 机器人、任务、采样率、episode 单位；
- 信号名称、单位、关节顺序、时间戳；
- 标签语义、异常起止、故障严重度；
- 官方 train/val/test split；
- 是否有重复主体/工件/轨迹导致泄漏；
- 是否提供 URDF、惯性、控制命令、实际/估计力矩；
- 能支持的主张和不能支持的主张。

## 2. 物理可用性分级

```text
P0_TIME_SERIES_ONLY
P1_JOINT_TOPOLOGY_ONLY
P2_PARTIAL_PHYSICS_SIGNALS
P3_FULL_DYNAMICS_METADATA
```

- P0/P1 数据不得运行或声称 RNEA、GMO、Jacobian 物理头；
- P2 只允许使用明确公开的信号和关节拓扑；
- P3 才允许完整 physics-residual 适配；
- 缺失量不得从测试标签、仿真 truth 或手工猜测补齐。

## 3. 下载顺序

1. voraus-AD 100 Hz；
2. RoAD；
3. AURSAD HDF5 单一版本；
4. UR5e 补充数据；
5. PyScrew 先下载 metadata/一个代表场景，再决定全量。

每次下载：

- 保存 source URL、HTTP headers/版本、文件大小、原始 checksum；
- 下载到临时目录；
- 校验并移动到 G 盘；
- 原始数据只读；
- 预处理输出独立目录，含代码 SHA 和配置 SHA；
- 禁止把数据提交 Git 或打进 review ZIP。

## 4. 数据拆分硬规则

- 以 episode/operation/physical run 为最小独立单位；
- 窗口不得跨 split；
- 同一工件/轨迹/运行的窗口不得分散到 train/test；
- 阈值和超参数只用正常 train/validation；
- 测试异常不得参与架构、特征、窗口、阈值和 sequential rule 选择；
- 官方 split 优先；若无官方 split，先冻结分组策略并提交后再看测试结果。
