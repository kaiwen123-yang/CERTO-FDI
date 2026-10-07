# PiPER H：接口核查与预备实验协议

2026-10-07；预备设计，未连接硬件、安装或运行SDK。这里没有实际机器人采集、动作、辨识或性能结果。PiPER H 实验不是当前 TAC 理论稿的前置条件。

## 已查到的官方实现

旧官方 piper_sdk 指向新 SDK pyAgxArm。本次通过已认证 gh 读取厂商仓库，固定提交 841a625f5f4920e776f20b934eb13048b747e6d0（提交时间2026-09-17）。后续硬件使用时需重新核对实际机型、固件、SDK及配置。

| 对象 | 本次源码支持的事实 | 对研究的影响 |
| --- | --- | --- |
| 机型 | ArmModel.PIPER_H 是独立配置；驱动沿用 Piper 固件分支 | 同一驱动不代表可使用普通 Piper 的力矩系数 |
| 固件 | default/v183/v188/v189 的 MIT 编码、缩放及参数随分支改变 | 固定实际固件分支；接口数值范围不是硬件额定值或实验动作许可 |
| 反馈 | get_motor_states(j) 返回缓存的position/velocity/current/torque、timestamp及hz，缺数据时可返回None | 轮询频率不是新CAN帧频率，重复缓存不是独立样本 |
| 力矩 | 解码器以电流乘配置系数得到torque | 属电流换算估计，不是独立力矩传感器 |
| MIT参考 | 概念参考为PD项加t_ff | t_ff不是总控制参考，参考也不是实际执行力矩 |
| 时间 | Parser将CAN frame.timestamp写入缓存；六关节角是多帧缓存拼合 | 时间来源取决于CAN后端；不能默认是设备采样时刻或同步全状态 |

直接来源：[固件与机型](https://github.com/agilexrobotics/pyAgxArm/blob/841a625f5f4920e776f20b934eb13048b747e6d0/docs/piper/firmware_reference.md)、[API](https://github.com/agilexrobotics/pyAgxArm/blob/841a625f5f4920e776f20b934eb13048b747e6d0/docs/piper/piper_api.md)、[驱动](https://github.com/agilexrobotics/pyAgxArm/blob/841a625f5f4920e776f20b934eb13048b747e6d0/pyAgxArm/protocols/can_protocol/drivers/piper/default/driver.py)、[解码器](https://github.com/agilexrobotics/pyAgxArm/blob/841a625f5f4920e776f20b934eb13048b747e6d0/pyAgxArm/protocols/can_protocol/drivers/piper/default/parser.py)、[接收缓存](https://github.com/agilexrobotics/pyAgxArm/blob/841a625f5f4920e776f20b934eb13048b747e6d0/pyAgxArm/protocols/can_protocol/drivers/core/table_driven.py)、[机型系数](https://github.com/agilexrobotics/pyAgxArm/blob/841a625f5f4920e776f20b934eb13048b747e6d0/pyAgxArm/api/constants.py)。文件哈希及读取范围见 piper_h_source_audit_v1.json。

源码细节：高频反馈报文类旧注释与解码后SI量描述有差异，实验须同时保存原始字节和解码版本。六关节getter按joint_12、joint_34、joint_56固定次序读取缓存，单timestamp取最后存在的那组（joint_56优先），并不是各组时间的最大值。只收到部分组时，未收到的轴仍可能保留初始0且通过通用数值validator；nonNone不证明六轴完整或同步。记录每组received/valid标志和时间，未收到轴保留missing，不把默认0当测量。这些是静态接口合同边界，不是本次复现的固件故障。

## 原始记录合同

每次会话保存manifest：实际H机型、固件字符串、SDK提交、完整配置及哈希、CAN后端/适配器、时间来源、坐标/单位、载荷、控制模式/增益、供电、环境和温度。未知字段保留unknown，不套用仿真默认值。

原始CAN层至少记录 session_id、rx_sequence、host_monotonic_ns、can_timestamp、timestamp_origin、arbitration_id、dlc、payload_hex、frame_flags。新接收事件用rx_sequence标识；两帧字节相同也可能是两个真实新帧，不能按payload去重。SDK轮询另记poll时间、缓存timestamp、消息类型及对应原始帧身份；若无法映射，标成无法确认freshness。

三组角度帧和六路电机反馈各自保留时间与received/valid标志，不先插值成同步状态。预声明最大跨关节时间差、掉帧规则和重采样方法。移动/整定期间继续采集，保存完整命令及反馈；诊断算法使用预声明mask，不在事后回填其被限制的信息集。

## 分阶段协议

1. **数据链核查。** 在未来用户允许的硬件会话中确认实际机型/固件/模式、新帧频率、缓存重复率、延迟和时间差分布。当前仅定义记录要求。验收是每个诊断读数可追溯到原始帧及真实时间。
2. **健康重复性。** 选择能执行同一任务、但对候选故障有不同敏感性的工作点，固定载荷和控制器，重复健康段。留出数据检查漂移、相关性、滞回、温度及跨段记忆。若第三姿态、其他关节或控制命令可绕过mask，重新定义实验信息合同，不能称整机信息下界。
3. **限定扰动。** 已知控制输入扰动与真实故障分开记录；后处理加信号只验证检测器。动作幅值/时长由实际设备和场地条件另定，当前不从SDK最大范围生成动作。故障/健康方向是否沿同一B须用模型及辨识核查。
4. **冻结比较。** 测试前固定点/平均索引、物理日历、移动/整定时长、方向、阈值及失败分类。健康留出段报告误报与置信界，扰动段报告功效/延迟、数据可用性和动作成功率；失败、掉帧、饱和及返回未达不能删除后重算。

## 理论对应

现实接口通常是异步部分输出，主稿则要求已知固定线性通道、完整保留状态、共同支持及确定性日历。先辨识观测算子和时钟、验证受限局部模型；不能把六关节缓存直接视为主定理的完整状态。噪声分布、稳定性、共同支持及漂移速率需要独立证据。

第一项实机目标是检验真实移动/整定时间、历史相关性和控制器/读出变化对诊断保证的影响。有限实验不能直接确认H^(5/2)渐近常数。若残差非Gaussian，应报告适用的经验结果或另证尾界。

一个独立推导的证据量例子：对预声明阈值、具有同一个固定误报概率p的独立同分布Bernoulli健康试验，N次零误报满足 (1-p)^N=0.05 的单侧95%上界是 1-0.05^(1/N)。至少2995次才使该上界小于10^-3。它是该固定条件下p的统计界，不是不同温度/载荷/姿态/路径上的最坏误报保证。相关滑窗不是独立试验，调阈值数据也不能兼作留出验证。这只说明证据量，不规定上机次数或保证实际独立同分布。

本协议完成官方接口预备核查和实验验收设计；实际固件、时钟、精度、健康数据及输入实现仍待未来会话确认。主理论、D2-a全表及论文验收继续独立推进。
