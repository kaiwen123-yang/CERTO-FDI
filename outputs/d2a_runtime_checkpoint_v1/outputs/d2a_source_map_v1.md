# D2-a 恢复来源与可复用边界 v1

2026-10-07。原 ZIP 在 `inputs/` 保持不变，安全提取在 `work/r1_extract/`。提取检查 463 个文件、139638206 字节，所有 resolved target 均留在目标目录，禁止绝对路径、父目录跳转、符号链接、大小写冲突与重复路径。完整流读取校验各 ZIP CRC；462/462 根 manifest 匹配。原 ZIP 前后 SHA256 为 `f703091ace28d9017d0400e07984f4c34f03d5efdba14742f5a3a9f4ea94a60b`。逐文件哈希见 `work/d2a_extraction_receipt.json`。

本轮不再次运行完整 verifier；已有同哈希 WSL 成功证据见 `references/audit_20261007/r1_verification.md`。安全提取/来源读取不等于新的数学认证。协议哈希与恢复脚本见 `work/d2a_PROTOCOL_v1.*`、`work/d2a_extract_r1.py`。

## 唯一源别名

以下均相对 `work/r1_extract/CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919/`：

```
R = ./
C = R/input/CERTO_FDI_STAGE_D1_CALENDAR_RISK_20260919/
N = C/input/CERTO_FDI_STAGE_D1_NONLINEAR_ADMISSION_20260919/
E = N/input/CERTO_FDI_STAGE_D1_ENTRY_LTV_20260913/
H = E/input/CERTO_FDI_STAGE_D1_HOLD_REDESIGN_20260912/
B = H/input/CERTO_FDI_STAGE_D1_ROBUST_HOLD_20260912/
O = B/input/CERTO_FDI_STAGE_D1_READOUT_20260911/
D = R/input/CERTO_FDI_STAGE_D1_COVARIANCE_DERIVATIVE_20260918/
DH = D/input/CERTO_FDI_STAGE_D1_HOLD_REDESIGN_20260912/
```

R 的 `stage_context`/`derivative_certificate` 用 D→DH 链；C 的 `context`/`certify_admission` 用 C→N→E→H 链。读取时记录实际路径，不混称为一个唯一物理文件；提取回执保存二者分别的身份。

## 模型和调用链

| 来源入口 | 实际用途 | 可复用范围/必须扩展 |
|---|---|---|
| `O/frozen/robot6r.py`, `O/frozen/sampled_model.py`, `O/frozen/robot_input.json` | 原机械几何、采样/滤波模型、任务姿态 | 原 plant/controller 参数不改；sample order 仍需 E 的真实顺序 |
| `E/src/sample_sequence.py` | 实际控制采样：读编码器、旧滤波速度、command、ZOH plant、滤波更新 | 顺序可复用；不得在窗边界 reset |
| `D/src/parametric_model.py:49 build`，`D/audit/PARAMETRIC_MODEL.json` | β/0.02 的 degree-8 A/B analytic jets、C/D 行、slow-path 与余项 | 参数模型可原样复用；不是 nonlinear 噪声同伦三阶证书 |
| `R/src/stage_context.py:moving_matrices` | 原 18 状态/6 创新 command/discrepancy move comparator | 原样复用；参考强迫须按转移方向和真实时刻传播 |
| `C/src/calendar_model.py:hold/move/reference_forcing` | 浮点评估同一 hold/move mean/covariance 模型 | 只作 numerical QA；常 β 三点不证明参数统一极值 |
| `C/src/calendar_model.py:block_noise/cov_forward/cov_all_block_innovations` | 两种完整创新协方差实现，保留直接/状态共享创新交叉项 | average 原实现可复用；point 需新 observation lift 与末样本权重 |
| `R/src/numeric_multiblock.py:all_calculations` | fast adjoint、block covariance、fast/block mean 一致性核对 | 只有固定 M 日历；需日历作为参数，禁写入提取源树 |

## 日历、方向、支撑与风险

| 来源入口 | 实际用途 | 可复用范围/必须扩展 |
|---|---|---|
| `R/frozen/STAGE_A_PROTOCOL.json` | 原 B/r/η/k/前缀的节点参考类 | 模型参考，不代表真实平均类完全相同 |
| `R/frozen/validate_sharp.py:schedule/fixed` | terminal-balanced 和固定停留的原取整/尾规则 | 原规则复用，D2-a 新 wrapper 用 Fraction ceil 固定边界 |
| `R/frozen/projection.py:solve/rational_certificate` | scalar bounded-Lipschitz projection proposal + exact KKT | 各新方向可用，raw gap 为平方距离；不得强迫有限盒非零矩归零 |
| `R/src/prepare_multiblock.py` | H300 原节点 direction 舍入、move、readout 索引恢复 | 只恢复 M，一条方向；每个新族/H/readout 都需独立定义 |
| `R/src/actual_direction.py:proposal/verify_recursions/energy_bounds/certify` | 全史 polynomial adjoint、exact recursion、Abel、supersolutions、V± | 算法结构复用；全局 CASE 只容许 ACTUAL/MULTIBLOCK且写 ROOT/audit，必须隔离适配任意协议/输出目录 |
| `R/src/risk_and_control.py:mean_dynamic_per_slot` | 平均读数 mean momentum/gradient 支撑，source/post 管分开 | 不能复用为点的窗口消去；点 mean transfer 是独立扩展义务 |
| `R/src/risk_and_control.py:risk/mills` | 阈值 25/8、Mills tail、分符号保护、两側误差 | 函数结构复用；未来支持 V0/V1、δ0/δ1分别输入 |
| `R/src/event_accounting.py:budget` | 按 N/M 的原日历事件预算，统计完整创新仍不重置 | 数学可复用；必须先有每段 component return 合同，δ分别用于两假设 |
| `R/src/segment_interface.py:certify`，`R/audit/SEGMENT_COMPONENT_RETURN.json` | mean/Gaussian/discrepancy 三分量返回，最低 1750 步；总≤250s | 原 physical/mirror/路径域内重用；source-box return 单独不够 |
| `C/audit/DIRECTIONAL_RISK_CERTIFICATE.json` | 原 gp4 区间、average εsource/εpost 与均值管输入 | 数值字段可追溯；42.5s固定风险结果不能当新行 |
| `DH/audit/POINT_READOUT_CERTIFICATE.json` | source point ε 与 linear C 行 | 同 local hold event 与初始化；不能替代 post point |
| `references/audit_20261007/post_move_point_bound.md`及support.py/json | 新 post point age≥1500 的条件支撑；age1750更紧值 | D2-a最后快读数age1749使用保守age≥1500值；不是point风险 |
| `references/audit_20261007/next_proofs.tex:228–338` | 两側风险、投影尺度、平移不变regime、first success语义 | 一般接口证据；不是新增6R全表 |

## 已定位的实现差异和开放项

1. R1 的 ACTUAL/MULTIBLOCK 协议、gzip jets 和证书都是固定实例，不是 D2-a 任意日历入口。直接改全局 CASE/PROTOCOL 并复用证书会越界。新 wrapper 需绑定 protocol SHA256、实际方向与读出。
2. average 源码实际 `Y_n` 索引为槽内前 250 个 pre-step 读数；point 固定用同槽最后样本，采样/可用时刻分列。原 brief 的 ηj 与 η(j−1/2)只用于设计，真实均值另核。
3. average 的 momentum 端点消去、εavg 和噪声缩减不可移给 point。source εpoint 和 post εpoint 已有条件输入；**point mean transfer 与每个新方向的统一方差证书仍需扩展**。
4. nodal average class 是连续/采样平均路径类的外包络，最近点只提出方向。方向健康支持要保留真实 gaps；若由 KKT dual 支撑向实际健康类迁移，必须检查真实 gp 区间、两假设盒/速率及舍入剩余量。
5. `V+/Vnom≤1.01` 是该认证流程的验收阈值；失败、缺失和 physical-contract failure 分列，不删行。stay 的零 nodal residual仅使该方向失效；载荷相关协方差/动态信号可能另带信息。

## 当前恢复入口

`python -B -X utf8 work/d2a_freeze.py` 重建同一机器协议并检查根 manifest；`work/d2a_core.py` 提供所有固定族成员、真实时间索引和有理方向尺度。随后运行 `work/d2a_smoke.py` 做最小 numerical/精确KKT/索引核对，结果写 `work/d2a_smoke_results.json` 和完整结构候选表 `work/d2a_calendar_inventory.csv`。这些是恢复 QA，不能称完整 FIRST_SUCCESS_TABLE 或认证 H*。

下一步先把 `actual_direction.py` 的读数协议和输出目录参数化，保存所有新方向的 jets、supersolutions 和 exact recursion 结果；随后实例化点均值支撑，独立 review 后再启动完整风险全表。无需为了建立这些接口再跑一次未变的 R1 全 verifier。

## 本轮实际核对与失败记录

`work/d2a_smoke_results.json` 是新运行结果。200 个 calendar 成员 × 2 个 readouts 共 400 个结构行，包含 switch-then-stay 的全部 S 候选和重复成员。Fraction calendar 与原 schedule/fixed 的节点和任务符号逐项一致；本清单的原继承时长/再移动/准入规则没有失败，最早 post 点 age=1749，总物理时域最大151 s。这是使用继承证明检查合同实例，未独立重证所有物理管。

6 个小例均保留：H40 stay 的两个 exact nodal residual 为0；H120/H300 terminal 的两个 readouts，共4个非零方向，exact rational KKT、raw squared-gap identity 和合理方向尺度通过。4个非零方向的 forward-vs-all-innovation covariance 最大差 `3.47e-18`，direction fast-adjoint 方差最大差 `4.17e-16`，fast-vs-block mean 最大差 `4.86e-17`。实际 direction 的 mean transfer 与静态 sampled ramp 确有约 `0.78e-6` 至 `1.64e-6 Nm` 的差，不能把静态模板直接当真实 comparator mean。名义方差仅在 β=0 核对，不称参数统一方差界或风险证书。

本轮恢复有3个执行失败，均在 wrapper 层留下记录（`work/d2a_recovery_notes.md`）：Python默认GBK输出原brief时不能编码组合字符；Windows普通深层路径的importlib找不到继承模块；两个继承包的裸 `input_setup` 模块名在同一进程冲突。分别用 `-X utf8`、Windows extended path、数值 calendar module 的隔离三路径 context 绑定恢复；**没有更改归档科学源码、降低断言或将失败算成成功**。完成后逐个核对全部463份已提取文件字节未变。完整R1 verifier未复跑。
