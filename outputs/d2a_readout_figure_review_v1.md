# D2-a 读出图：有限独立证据审查 v1

2026-10-07。**当前修订图通过本次有限证据／措辞审查，可作为正文中的有限非线性证书比较；没有未解决的实质图证据问题。** 验收仅针对 prescribed terminal-balanced 日历族、预声明的7个 `H≤200` 网格点、14条分类记录和12条绘图记录。它不认证全400行完成、最优日历、真实经验功效或TAC投稿就绪。

根已检查彩色及灰度预览，在本轮术语修订后重新查看更新的彩色图并导出。本代理审查数据、代码、图注、计划、QA和已有mean-risk审查；没有重渲染、重跑科学生成器、大型伴随递推或大型科学文件hash，也没有改主稿、图文件或根状态。

## 1. 当前版本绑定

| 本次实际读过的当前文件 | SHA256 |
|---|---|
| 冻结figure data | `8022e863c9b74179f01c3452e0028ab489aa84b7111823b8bd811aab2a816e97` |
| 当前绘图脚本 | `a427d7ac369d0038fe4783ed745ff0f77b0545606aea723153ab2e1455a68263` |
| 当前修订caption | `f6c0414ef4bbd5737e2e5253caf878d6b0801d20e933718939c8832bf8cf10d5` |
| 当前修订plan | `f5998c02e58c192368b342f6f2e006987df5a044024dbc87eaa3f7ae7dd5739c` |
| 当前QA | `d5fd3fb017c077b78b5f3876f9b87cd80721db43cb2900497d1732276273bb77` |
| 当前图PDF | `999fa810669c21de84592649f8fc59325db5ca424303406c88bac5aef53b4767` |

协议为 `0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6`；冻结数据保存07:47:40 UTC时的整张原子读表hash `16f5b04e70d6246aee79a2186a6a2e197eb615fa0b5112c088302e59e6080f29`。活表仍可能推进，本轮不重新要求其当前hash等于旧快照hash；图只使用相邻的不可变14行JSON。QA中的data hash与实际冻结文件一致。详细逐行判断和当前来源hash保存在同名review JSON。

## 2. 14条分类与12条绘制

两种读出分别在 `H={40,60,80,100,120,160,200}` 各有一条记录；14个 `(H,readout)` 对无重复、无缺项。分类为：

- 2条：H40方向退化，`ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE`，数值PFA/power/V+均为空；代码从数值轴省略，caption明确说明。
- 8条：有效uniform certificate，但未达目标；含average的H60/H80，以及point的6条数值记录。
- 4条：average在H100/H120/H160/H200达到声明风险目标。

脚本筛选非空V+后，每种读出断言恰为 `H={60,80,100,120,160,200}`；共12条全部绘制，没有只保留成功行。原精确有理数保留在数据中，绘图时才转浮点。横轴严格为 `(H+4)/4` 秒，含1秒healthy prefix；H100对应26秒。连接线只引导读图，不认证网格间时域。

38个已核小元数据叶文件共659,529字节，结构是 **2个H40 direction record + 12×(direction record、current verification receipt、evidence-binding file)**，本轮均匹配冻结记录的hash。此处不是“38个科学验证重新执行”。12条风险记录的case-result／protocol／current-receipt IDs与evidence bindings一致。

其中6条current receipts为 `PASS_STDLIB_DERIVED_REBINDING`：继承原variance payload并重新绑定KKT／mean-event-risk；另外6条为 `PASS_STDLIB_NEW_CASE_VERIFIER`：原生成阶段记录完整新case检查。两类回执不能强行按同一schema解读，也不能把binding文件的“content integrity only”当成独立科学证明。本次只审其记录内容与绑定，不再执行其科学验证。

## 3. PFA、power与零方向含义

12条绘制记录全部满足精确有理比较 `PFA_upper<1/1000`、`0≤power_lower≤1`、`variance_ratio_upper≤101/100`，且 `power_lower≥9/10` 与pass分类一致。PFA约为 `0.00096712`；图显示的是冻结统计量在声明类内的证书界，不是计数频率、Monte Carlo结果、置信区间或标准误。

已有mean-risk论证对Gaussian comparator均值上下界、非线性remainder和逐假设事件预算分别支付。阈值由 `m0+b0+(25/8)√V+` 构造；positive protected gap按Gaussian tail加事件项给power下界。negative gap不允许照搬正gap的上方差代入，当前实现保守返回power下界0。两假设可以各自选择完整不同的deterministic healthy path；共享的V+和event预算是统一覆盖界，不是强制两侧共享nuisance或实际covariance。

因此point的6个零下界表示**当前充分证书没有正保证**，不能写成真实power=0、物理不可行或信息论不可检测。H40两条更弱：没有风险证书，故其缺值不能填成power=0。当前caption正确区分了两种情况。

## 4. V+的对象与尺度

V+是**fixed-path Gaussian comparator上、对应规定scalar statistic T的完整历史方差上界**。真实非线性统计量通过另列的remainder与event allowances控制；V+本身不是它的无条件方差证书。

`normalize_raw`对投影残差做有理舍入，并以向上Euclidean norm缩放physical direction，保证direction norm≤1。随后T尚未除以其标准差。因此原“raw／未归一化统计量”容易混淆方向缩放与统计量standardization；当前caption改为 **unstandardized prescribed statistics** 并说明两者区别，轴名改为 **Gaussian-comparator variance bound**，对象清楚。

physical weights同时依赖H和readout。panel(b)可显示这组规定统计量的variance bounds差异；它不能独自给出noise channel的普遍readout improvement ratio，也不能将方差作为决定panel(a)功效的唯一因素。当前plan／caption保留了这些限定。

## 5. first-H与mean scope

在每个H，两读出共享该H声明的物理日历；不同H由同一规定family生成各自日历及统计方向。这不是一条连续运行的固定日历被逐次截断，也不是数据驱动的sequential stopping test。

average的H60下界0，H80下界约0.622855；H100下界约0.999999999926且PFA达标。故 **H100是这组已列网格中该规定family的first certified grid point**。它不是所有整数H的最小值、连续停止时间、所有日历上的最优H*或全400表的first-success验收。当前caption已经逐项限定。

全部12条数值记录均绑定mean review hash `6a9cfb8009d2b424dfd29130c3d9140478531aeb74b326e917881eb35d7fe924` 与 `ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN`。该审查限固定 `H0:f=0`、`H1:f(t)=0.0003(t−1)_+`、H≤600／f≤0.045，并沿用nonlinear/event/common-contraction/segment-return条件。图子集H≤200只达到f≤0.015，处于该固定模板范围内。

没有将旧physical allowance `f≤0.75` 变成两mirror任务的已审均值范围。Gaussian comparator的确定性均值也没有被叫成真实非线性状态的无条件期望。当前图明确说该非线性comparison不实例化或验证线性sharp asymptotic theorem。

## 6. 已解决的措辞问题与结论

本轮提出的3项问题已由根改入当前caption／plan／轴：Gaussian-comparator方差对象、direction scaling与statistic standardization的区别、horizon-indexed paired calendars及first-certified-grid含义。本代理没有改图；上方hash绑定的是根修订后的文件。

**当前图证据可用于有限非线性例子的正文说明；首要边界仍是14行闭合子网格和既有条件，不能升级成full400完成或TAC-ready。** 本轮没有剩余必须改图的实质证据项，也没有扩大既有科学审查范围。
