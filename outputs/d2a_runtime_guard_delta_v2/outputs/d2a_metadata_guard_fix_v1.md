# D2-a C1/C2 元数据守门实际修复 v1

2026-10-07。C1/C2已实际写代码并完成有限验证，待root独审后启用一次正常metadata CLI。**没有恢复/重跑science，没有执行preflight、覆盖400冻结records或改physical protocol。**

## 文件与精确版本

|文件|before SHA256|after SHA256|
|---|---|---|
|work/d2a_cert_partial_first_success.py|7c83403d97418d38e290762d6b6141fe21b4916c8465e706f64b9eafbce03bdc|fe0b6f7935106fbb81b586cbd453631fdeced85af7e09d681bda210debf9a41c|
|outputs/d2a_partial_first_success_v1.py|同上|同上|
|work/d2a_cert_preflight.py|d60ca87a6d6f7329f2e82e268cfbe1a17e64975e895f7494c97a3b20a64c5c13|aba4de0223251574a8227062487684ca43b1c33aa3ae52bda1fed9749ae32ad4|
|新work/d2a_metadata_guard.py|无|b2bedb201eaafb5e59f40b55d96040e1895503643210e92b51bdb132b3114122|

work/outputs两partial入口内容与hash完全相同。纯guard只依标准库，不import core/case/batch或science。原d2a_core.py、主case、verifier及protocol hash均保持前审版本，具体after核值在JSON。

## C1：一次CSV快照与完整成员门

两入口现在只读取一次CSV bytes，把该相同bytes传给build_report作DictReader和SHA。不会解析A版本却在末尾再次读B版本绑定hash。

从byte冻结protocol构造每个(H,family,S,readout)期望键；必须正好400 unique，当前表无missing/unexpected/duplicate。每个族/H的期望组必须非空且所有期望成员存在，才可能closed。已处理的closed状态集合不变；NOT_RUN/pending/未知未处理成员不变成成功。

Selector仍仅选certified rows，按**exact Fraction power最大、相同power取最小S**；selected power/PFA及evidence binding原字符串原样复制，不重新计算或舍入任何numeric payload。所有stage aliases仍是各自逻辑行，不删除。

异常/缺键/重复/坏certified数字时normal CLI返回3、stdout FAIL_CLOSED_METADATA_GUARD、metadata_written=false；不覆盖旧live报告。--dry-run有完整守门但只stdout、不atomic写。Normal metadata路径保持Windows5/32/33有界20秒atomic重试，不新增science subprocess。

## C2：physical与projection分开

preflight初始physical_rule_status=NOT_CHECKED。
在design前调用纯guard，要求core提供显式validation pass、无validation_errors，并核原prefix/total clock、1500 move/1500 settle、1750 source/re-move、readout index与postarrival读数时钟。成功后才PASS_INHERITED_RULE_INSTANCE_CHECK；这是继承规则clock实例核，不重证全6R返回/硬件。

错误分stage：
- physical/clock错误：PHYSICAL_CONTRACT_FAILED，同时direction不执行、风险失败分类明确。
- design/projection失败：PROJECTION_CERTIFICATE_FAILED，已过的physical PASS保留；不冒称physically impossible。
- 输出metadata/IO异常：CERTIFICATION_EXECUTION_FAILED/PREFLIGHT_METADATA_FAILURE，不能改称合同或数学投影失败。

preflight原来的numeric/scientific算法和protocol未改。本轮只对其新source作AST语法解析，没有import或调用preflight.main。

## 实际有限验证

新work/d2a_metadata_guard_fixtures_v1.py（SHAf286d6a5684118def4084ce767a3a1fca51e601a4357e38e9c921056a22c1109）共15项纯内存adversarial fixtures全部通过：缺前驱、同总数重复+missing、stage alias丢失、非法S0、pending、certified数字缺失/short CSV None、exact tie、同一次bytes hash、physical失败不保PASS、伪造valid flag但1750时钟错、projection/metadata分项等。仅读取一个已有H40 calendar作为小fixture基准，无文件写入或science。

新work/d2a_metadata_guard_selector_equivalence_v1.py（SHAdffb28d83926e7f6f2beda1f4797b55d56cff9e90e46e929d5b3297a4945823a）从readonly runtime里SHA7c83403d…的旧script提取**仅纯selector AST循环**，未执行旧main/import/atomic。在一个相同的实际CSV bytes快照（SHA4139e7c0a8026173797804f7faee44baa3140f94b51d6dbea4900c51d3f47834、400行）上，新旧pairs、selected numeric strings和bindings精确相等。不是旧science/checks重跑，是本次所要求数值payload保全的有限比较。

实际outputs入口--dry-run通过，rows400、full_table_complete=false、metadata_written=false。五个既有average first grid及switch S100不变，point/stay尚无first-success不被填0。stdout具体快照/选择记录在JSON。现有science/publisher自己持续变化，报告不声称暂停它们或封住live输出。

## 最终recipe与启用

最终恢复/发布recipe必须同时包含：
- work/d2a_metadata_guard.py
- work/d2a_cert_partial_first_success.py
- outputs/d2a_partial_first_success_v1.py

建议验收命令仅：
python -S -B -X utf8 work/d2a_metadata_guard_fixtures_v1.py；
python -S -B -X utf8 work/d2a_metadata_guard_selector_equivalence_v1.py；
python -S -B -X utf8 outputs/d2a_partial_first_success_v1.py --dry-run。

Root独审之后可按约定运行一次**不带dry-run的metadata CLI**；我没有运行它，避免和唯一publisher同时写live reports。Publisher后续child自然载入新outputs入口，不需重启science或重生成任何frozen方向。

C3只留final derived diagnostics的event-exhaustion规则，不改live case.numeric/classification/mean source digest；C4仍须full400 gate结合actual artifact/ZIP验收，不能用subset PASS代替。此修复不宣布全表或TAC准备完成，也未改根状态/claims/主稿。

