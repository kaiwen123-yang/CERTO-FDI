# D2-a 完整网格覆盖与最终验收：独立源码审查 v1

2026-10-07。**冻结协议/runner的声明覆盖结构成立；当前不能full PASS。** 新只读验收器对当前400个tuple键、实际时间/日历、接受case小文件/receipt/alias/mean-risk绑定未发现错误，但还有206 NOT_RUN。实际进程exit2、status INCOMPLETE_VALID_METADATA、full_grid_accepted=false，不把missing/pending当数值0或失败。

本轮独立读实际源：d2a_core全文、batch全文、sync_review_table全文、partial_first_success全文、preflight全文、机器协议全文；case的actual_protocol/mean/risk/classification/review-binding与verifier的关键门；artifact-byte入口及publisher的缓存/活性逻辑。不是只重复旧summary，也不声称重证原R1/非线性/large variance proof。

仅新写本md/json及outputs/d2a_full_grid_acceptance_v1.py；小元数据验收和14个new tiny fixtures。不呼叫science、原verifier、SDK或D2生成，不改root文件，不读/大hash ADJOINT jets。

## 1. 400不是12×6×2的简单矩阵

机器protocol保持SHA0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6。
每H有5个单成员族，加floor(H/20)个switch_then_stay候选；每成员2readout。
60个常规成员+140个stage成员=200，×2=400。

|H|40|60|80|100|120|160|200|240|300|400|500|600|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|行数|14|16|18|20|22|26|30|34|40|50|60|70|

all_members实际枚举S=20,…,floor(H/20)20，S=H包含、S0不新增。Stay、零/退化direction和实际相同calendars的重复stage成员不删除。最终必须核完整tuple(H,family,S,readout)集合及唯一性，单看总400不够。

## 2. 取整、时间、physical与≥3

Core使用Fraction的ceil、terminal整块接纳和divmod左侧tie padding；fixed tail余量≤k时不做不完整move；switch stage结束后+hold至H。未事后修日历或添候选。方向nearest-even 1e−12、only exact raw moment zero才恢复零矩、sqrt-upper1e−18归一化和task→physical映射在源中明确，有限box的nonzero moment不被强行置0。

实际N=250(H+4)、终点(H+4)/4秒；point是n=250(s+1)−1的既有pre-step sample，average完整250样本，availability与sample time分开。Missing12槽含1500 move+1500 settle；首post-move窗口age1500、point1749；再移至少1750。Source/post段按是否已有arrival区分，返回+也仍post。没有noise/filter/state reset。

独立验收器从冻结protocol重建nodes/tasks/blocks并逐条对照400 frozen records的time/index/arrival/transfer字段，不调用science。其physical PASS仅是继承规则的实例检查，不是新实机返回/全6R三分量证明。

原≥3完整symmetric blocks是**主例选择标准**，不是所有candidate的physical合法性或certificate pass条件。Terminal在H40/60b1，H80/100/120b2，H160b3，H200/240b4，H300b5，H400b6，H500b7，H600b8。H100/H120 average可以certPass却不满足≥3；不能因而改其失败/成功历史。按原标准换主例的H160 pair已单独核查（d2a_three_block_example_review_v1.md/json），保留H100 firstcertgrid与原H120图/历史。

## 3. Alias和证书绑定

Batch semantic key包含protocol、full T_fast/moves/observations、readout和完整direction；不靠family名字猜复用，不仅比“看起来相似”。Cache不删除逻辑行。Full receipt与DERIVED schema区分：后者必须prior full receipt/CASE/hash链及variance payload unchanged，不能说新执行大递推。

新工具逐已接受row核：实际frozen direction hash、calendar；small CASE/current receipt/hash；CASE/covariance small payload与table一致；full科学门flags或合法derived/prior chain；selected receipt/sidecar与witness/covariance声明hash一致；witness只检查存在，不打开。同一certificate_reference下alias完整semantic必须相等。当前有14个多row alias groups、106个已接受非零unique references；逻辑400均保留。未把alias行数当独立递推次数。

Mean report及source函数digest绑定有效，actual f上界3H/40000≤.045，wide.75不自动接受。模型原盒未变，数学接受域限fixed ramp/H≤600及继承条件。

## 4. 健康、误差、event与negative gap

实际mean_certificate按真实sample times/real Δt计算whole healthy support；H0/H1各支付health+dynamic损失及各自error支持，equal uniform bounds不要求共用path。Point走pre-step C row/equilibrium/entry-rate tube，明确point_uses_average_cancellation=false；average的continuous→sampled allowance另支付。

Guarded risk用m0+b0+(25/8)sqrt_upper(Vhi)，gap=m1−b1−threshold。正gap使用Vhi；负gap诊断使用Vlo，但充分power返回0（不是actualpower0）。新工具核table/CASE/receipt这些身份、gap代数、variance choice、两侧budget字段与strict PFA<.001、power≥.9、ratio≤1.01的分类，绝不把缺数值当0。对当前frozen方法要求非正gap的保守power0，不声称一切合法lower-variance方法都只能给0。

Event按N+1 encoder cap、N−1500M+(M+1) hold及M entry逐假设计账；event可依同noise，不能条件Gaussian或假独立事件。完整innovation方差/共同covariance proof来自既有独立full verifier或其合法derived链，本新工具不重算。

## 5. 新发现的有限守门缺口

### C1：空集合可假闭合（当前数据未触发）

partial_first_success第24–25行的completed=all(...)没有期望成员非空/完整检查；all(empty)=True。若删掉某前驱行或某stage，仍可能报告前驱“全部已处理”；若另重复一行，总数仍400。Sync completeness也只看现有rows statuses。

最小fix：在输出前以frozen protocol构造完整keyset，断言每键唯一且无缺项；每H族闭合必须every expected member存在且closed。新工具采用这一守门，tiny缺前驱/同总数duplicate/alias-drop fixtures确实拒绝。当前actual键集完整，未发现旧报告实际firstcert错误。

### C2：preflight提前写physical PASS（当前全部合法）

preflight第25–33行在检查validation_errors前就写PASS_INHERITED_RULE_INSTANCE_CHECK，异常分支第50–53仅改direction/contract failure。故真实timing失败也可能保留physical PASS。

最小fix：初始NOT_CHECKED，通过timing/admission后才PASS；合同失败单独PHYSICAL_CONTRACT_FAILED，projection失败另分。不能改变冻结物理参数或修candidate覆盖失败。当前全部冻结calendars通过独立时钟核查，潜在分类缺口未造成当前错误PASS。

### C3：event不足分项未独立输出

target_classification第102–108行只append variance ratio/RISK_TARGET_NOT_MET，没有单列protocol的EVENT_BUDGET_EXHAUSTED。当前event很小未触发，risk未达仍如实保留，不是数学false PASS。

可在final derived diagnostics单列delta0≥alpha/delta1≥beta原因，而不改旧CASE numeric payload或偷偷重写旧分类。Physical_status、certificate_validity和risk_target三层要分开。

### C4：all-completed artifact PASS不是full400

现artifact-byte入口只核已有accepted cases，未完成成员会跳过；其自身scope已经说明这点。它可能在一个真子集上合法PASS，不能单独用来关闭P5。最终必须先完整400 gate，再把实际artifact check的unique reference数与最终table expected scientific identity范围对齐。

## 6. 新验收器及tiny fixtures

执行python -S -B -X utf8 outputs/d2a_full_grid_acceptance_v1.py；默认纯只读/stdout，零subprocess/science imports。每small file≤2MiB，总≤256MiB；gz/zip/pdf类型在读取前禁止，路径必须留在root。当前共读89478573字节小metadata（含400方向records/已接受CASE等），large witness字节0。

Exit/status：
- 0：PASS_FULL_GRID_METADATA，仅小metadata全表，不等于science/大payload/ZIP/TAC PASS。
- 2：INCOMPLETE_VALID_METADATA或changing paired view；当前未算不得填0。
- 3：FAIL_CLOSED_INVALID_METADATA/INPUT：缺键/重复、坏绑定、contradictory status等。
- 4：明确但仍待审/恢复的classified failures，不冒充全接受。

--self-test的14个纯内存fixtures通过：缺前驱、同总数缺键+duplicate、pending阻断、certified exact-power/min-S tie、alias标签保留/错readout不可复用、negative-gap假positive power、missing-power非0、PFA equality非strict、原400 cardinality、禁止读科学witness及root外路径。没有filesystem写入、旧科学测试或镜像重跑。实际运行当前exit2，不作为异常去重启job。

## 7. 当前结果和最终必要checks

本轮最后实际CSV SHA0d01edca0fe3fe49f6e19c19e976de95b9356578a3e88aef0246578a00306f54与receipt配对；41 pass、79目标未达、74方向退化、206 NOT_RUN。400keys无missing/duplicate/unexpected，小绑定errors0，full_grid_accepted=false。晚于任务给的08:13状态，已有scan仍在自然推进。本代理未启动/控制它。

最终P5至少要：
1. 冻结original input/protocol/current source，完整400 keys和全部分类；不把pending、无mean/variance、未恢复execution failure隐藏为PASS。
2. 核真实clock/admission/继承return条件、physical与cert/risk区别、alias equality和历史失败链；≥3主例标准单列。
3. 每已接受case有full/合法derived receipt、current mean/function/source/CASE/KKT/protocol/direction/covariance/witness绑定；风险两侧budget/variance与target分类一致。
4. Firstcertgrid须expected更早/当前全族完整；用exact certified power再min S，不用nominal或只挑已成功成员掩盖未算。
5. Science停止/结果冻结后，运行原**大artifact字节**核验与必要saved-witness独立验证，并从实际final ZIP新解压验收；比较unique scientific references而非只报partial checker PASS数。此次工具明确没有执行这一层。

没有新理论/物理protocol改写。Source具体hash、actual validator JSON、14fixture结果及最终gate列表都在同名review JSON。P5仍incomplete；root/goal/主稿未改。

