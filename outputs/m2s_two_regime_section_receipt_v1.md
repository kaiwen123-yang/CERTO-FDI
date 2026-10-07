# M2S two-regime section v1 — integration receipt

2026-10-07。交付文件 outputs/m2s_two_regime_section_v1.tex，SHA256 9e7bb4513007c9226f315e5e58ee661f556a7097d26fb31030aefc136fb03b7f。单一英文 section fragment，无 documentclass、preamble 或 document environment，不改根当前主稿或旧 proof。

依赖既有 amsmath/amssymb/amsthm 及 theorem、proposition environments；唯一外部数学交叉引用是主稿 thm:main，其余22个新 labels 全使用 m2sreg: 前缀且互不重复。没有引用或扩展 thm:uniform 的正定 controller-family 结论。

本片段明确保留 fixed known A_K/G、B∈range(G) 非零、full-column G、同一完整 scalar healthy difference class、free initial level、r,η>0、known horizon、held g=±1、任意 known bounded missing g、诊断器只能读 retained full states、真实初始化与无 reset。达到性需要双向 exact-k profiles 可重复与 holds 串接。没有声称 actuator saturation、partial observations、额外传感或任意 vector nuisance。

内容：
- 所有均值都在 noise image，common Gaussian support，reduced SVD 与真正 likelihood。
- Predictor 可逆左乘保留 rowspace；不使用 Moore–Penrose inverse 的错误 congruence，也不把冗余 d 行称为 I_d covariance。
- Fixed reached-space stabilization 给 sup_m||W_m†||<∞；strict stability 给 S_B，calendar-uniform affine cross O(H²)。
- β几何、单调性、tail、score 保留的充要条件及 k≤d−p 容量；不等同所有 latent inputs 恢复。SPD 是 strictly positive 特例。
- Positive β 分支说明主 M2 proof 的承重替换，写出 global gap-budget split 与真实 observable scalar mass repair、匹配上界系数。
- Zero β 分支完整上下界：真实全输入 profile-aware cumulative balance calendar、global zero-mass repair、free-level support；所有日历的 late positive-gap/late all-zero-gap 两分与 ε coefficient。
- 没有引入新的理论方向或模型。

冻结的已独立接受数学来源：
|来源|SHA256|
|---|---|
|m2s_problem_contract_v1.md|80a5a5d643432f54f1a2d9f3dc7a9e374528358c18e10beb6b0e1ac1d5b9e7d5|
|m2s_singular_memory_theorem_v1.md|8ff2de70274973e4a9e104b26a5bf4be14e0e742998f2c562f6023e6316ab431|
|m2s_recoverable_order_v1.md|5b04f87f23fbfe1d2bc1fb1fbb791e783a47e029c7cdf130e1c000dd22d0f4f1|
|m2s_recoverable_order_review_v1.md|c32efb758b39e3b3f1d11e8219ee365f50fb33f84eb44857739620d8e99571c8|

本次只做 section 转录/数学整合，不重跑旧表。已有新小型证据及独审：
- outputs/m2s_recoverable_order_checks_v1.py/.json：六个新日历、十九个 ε identities，独审已运行并确认 stdout=保存JSON PASS。
- outputs/memory_asymmetric_repair_checks_v1.py/.json：六个 genuinely nonzero local repairs，独审已运行并确认 PASS。
- 原 v1 及 M1/M2 的独立 v1.1 均保持不变。

Source 静态核验：472行、22 unique labels、均 m2sreg:；TAB=0、孤立CR=0、其他低控制字节=0；无 documentclass。它是插入既有主稿的 section fragment，不作为 standalone 发起编译。根主稿内置 compiler 的平台错误与数学接受状态分开，片段本身尚无编译成功证据。根将其内联到已打开主稿后管理编译与整稿版本绑定。

