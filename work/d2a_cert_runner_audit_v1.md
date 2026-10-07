# D2-a 长扫描 wrapper / 缓存 / 回执独立工程审查 v1

日期：2026-10-07。Mode：PR Review。范围：`d2a_cert_batch.py`、`d2a_cert_case.py`、`d2a_cert_verify.py`、`d2a_cert_rebind_derived.py`、`d2a_cert_sync_review_table.py`、`d2a_cert_mean_review_binding.json`；额外只读 `d2a_cert_accept_mean_review.py`、`d2a_cert_resume_probe.py` 和原 `actual_direction.py` 的生成/核验接口。

**初审结论：发现 5 类可触发工程正确性漏洞；当前抽取的 51 个已完成小 JSON 回执链没有发现不一致，不能把这些工程漏洞解释为当前数学/数值证书已失效。** 两条旧 H80 wrapper 失败的当前 full 回执均有正确的 CASE hash 和冻结模板审查字段。本轮没有干预 PID59248 或 exec session94963，没有启动 worker、读取生产 gzip jets、执行 proposal 或重跑大递推。后续补丁复审结果见第 5 节；第 2 节保留为原版问题及触发证据。

数学接受范围沿用 `outputs/d2a_mean_risk_review_v1.md`：冻结 H0/H1 模板、H≤600、实际 f≤9/200=0.045，以及明确继承的非线性/事件/收缩前提。本审查不扩展 wide f≤0.75，不重新证明 R1。

## 1. 证据与复核方式

绑定协议 SHA256：`0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6`；数学审查报告 SHA256：`6a9cfb8009d2b424dfd29130c3d9140478531aeb74b326e917881eb35d7fe924`。

脚本审查快照 SHA256：

|文件|SHA256|
|---|---|
|`work/d2a_cert_batch.py`|`60d80973b714790fa0ac17ec1efa18fd9b7ce487c74797585a69978ac2ada441`|
|`work/d2a_cert_case.py`|`b0b8309823d3d37c1a700d346a7477494d4bf7d08cd36e8e56ec16f948578453`|
|`work/d2a_cert_verify.py`|`844b3f16c7f088d8179eb3e46874378c5d0c632648f387a6615dc1b7ae688de1`|
|`work/d2a_cert_rebind_derived.py`|`193093ab2779631e879f37cc0f6abd8e9c5fd76ff397aa54cc48181a1bb32546`|
|`work/d2a_cert_sync_review_table.py`|`e037d5874ef6fb5f7f8c435f23ae2fe48267ca50b126c43bd8af2c4e1d665310`|

复核资产均在 `work/`，现有脚本/证书/根台账未修改：

- `d2a_cert_audit_fixture_v1.py` 与 `_results.json`：冻结模板、缓存和回执故障注入；约 1.96 s。所有变更仅落在 `d2a_cert_audit_fixture_v1/`。为隔离 wrapper 的状态校验，full verifier 的 `adapter.certify(True)` 被替换为其原存储方差 payload；其余 exact KKT、direction、protocol、mean、event、risk 与真实 wrapper 代码照常执行。不能据此声称重新核验了大递推。
- `d2a_cert_audit_resume_v1.py` 与 `_results.json`：`subprocess.Popen` 全部 stub，实际子进程数为零；约 0.57 s。只在 `d2a_cert_audit_resume_fixture_v1/` 写 sentinel jets、日志与 checkpoint。
- `d2a_cert_audit_live_snapshot_v1.py` 与 `_results.json`：只读已完成小 JSON；51 cases，其中 40 full、11 derived。跳过当时活 case `h160_switch_then_stay_S100_point_last_fast_read`。CASE hash、prior full→prior CASE、方差 payload、不变性、报告/mean版本、scope、目标状态一致性均未发现失败；这是当时快照，活扫描后来新增的 cases 不在该统计内。

可在仓库根目录用 `python -S -B -X utf8 work/d2a_cert_audit_fixture_v1.py` 和 `.../d2a_cert_audit_resume_v1.py` 复核隔离控制。脚本只写各自 audit fixture 和结果文件，不需要结束现有扫描。

## 2. 发现

### F1 — P1：独立 verifier 没有从已核算 payload 重建目标标签

**症状/定位：** `d2a_cert_verify.py:59–70` 重算 variance/mean/event/risk，但 `74–98` 只沿用 `result.status`、`arithmetic_risk_target_status` 和 `failure_classification`；`d2a_cert_rebind_derived.py:55–60` 同样复制旧 arithmetic status。`d2a_cert_batch.py:71–76` 直接把这些标签变成表中通过/失败。

**影响：** CASE 的数字仍正确、`protected_risk.target_pass=false`，而状态字段误写为 `CERTIFIED_TARGET_PASS` 时，独立 wrapper 会签出 `PASS_STDLIB_NEW_CASE_VERIFIER`，表中也会宣称通过。独立数值验算不能纠正 metadata 的错误判定。

**实测：** 使用真实 H80 fixed40 point 的小 JSON副本，保持风险数字与 `target_pass=false`，只把 status/arithmetic status 改为 pass、failure list 改为 `[]`。fixture 的 `false_target_label_full_wrapper_accepted`、`false_target_label_table_claims_pass` 均为 true。当前生产 51-case 快照未发现这种矛盾。

**修复：** 建唯一的判定函数：从 `variance_ratio_upper≤101/100` 和已重算 risk 的 `target_pass` 构建完整 failure list 与 arithmetic status；full verifier、derived rebinder 和缓存入口分别断言一致。另应断言 `result.calendar==pr.calendar`、`result.readout==pr.readout`、receipt.case==result.case，以避免元数据与实际核算对象脱节。数学审查状态与算术判定仍保留为两个独立字段。

### F2 — P1：已保存的审查函数版本没有成为接受门

**症状/定位：** `d2a_cert_case.py:54–66` 校验协议与报告字节、硬限制时域，却不比对 binding 的 `mean_function_after_scope_binding_sha256` 与运行中的 `mean_certificate`。`d2a_cert_batch.py:46–64` 不重新核当前报告/实现绑定；`d2a_cert_sync_review_table.py:25–46` 复用该入口并把当前 binding 另附在总回执中。

**影响：** 热更新若改变 mean 数学而保留原 binding，新 generator/verifier 会互相算出相同的新结果并继续把旧报告标成接受。缓存/同步表也能继续接受报告文件已改变或绑定已过期的旧结果。保存 hash 目前只是记录，没有 fail-closed 效果。

**实测：** 当前 mean source hash 确实匹配 binding，表明本轮没有观察到实际漂移；把 fixture 内绑定 hash 改成 64 个零后，`review_binding` 仍返回 accepted。把 fixture 报告替换为错误字节，直接缓存仍接受。`H601_scope_rejected=true`：修改 binding 的宽泛叙述不会绕过当前硬编码 H≤600/T≤151000/f≤9/200，不能把此发现描述成已允许 wide f≤0.75。

**修复：** 验证当前 mean source/规范化 AST hash，并绑定承重 helper、风险函数与源依赖 manifest；明确哪些包装改动不改变数学版本。缓存接受时核 per-case review 与对应不可变报告版本/manifest。版本不匹配时保留原算术结果，数学状态退回 pending，不冒用接受标签。同步总回执应绑定实际表字节 hash 及各行 review manifest，不能仅附一个当前全局 binding。

### F3 — P1：派生重绑定的中断窗不可直接恢复；旧 derived 会遮蔽新 full

**症状/定位：** `d2a_cert_rebind_derived.py:50–75` 已正确保留 content-addressed prior CASE/full receipt，但先提交 CASE，再 SUMMARY，再 DERIVED receipt。若最后一步前退出，CASE 已变、full 回执仍绑定旧 CASE。重试 `rebind()` 的 `22` 会因 old hash 不匹配失败；`main():87` 还会仅凭 accepted status 跳过该 case。`d2a_cert_batch.py:50` 只按文件存在优先选 DERIVED，不尝试另一条可用 full 回执。

**影响：** 本来不需要改 jets 的元数据维护，可能留下无可用回执状态，随后 batch 把它当作需要重新生成的 case。即使后来独立 full verifier 写出有效新回执，残留旧 DERIVED 也会使 `existing()` 拒绝。

**实测：** 在最后 DERIVED receipt 提交处注入 OSError，CASE 已 accepted、`existing()` 拒绝；再次 `rebind()` AssertionError。另对 fixture CASE 做无数学影响的 elapsed字段改动，生成绑定当前 CASE 的新 full 回执；仍因旧 derived 优先而拒绝。均没有重跑 jets。

**修复：** 记录可恢复的 transaction manifest，预写新 CASE/SUMMARY/receipt，commit marker 最后写；重试依据已保留 prior 文件和 transaction phase 完成事务。`main()` 仅在有效回执绑定当前 CASE 后才跳过。缓存应逐一校验候选回执，接受绑定当前版本的有效链，不以“DERIVED 文件存在”为优先级。每次更新前归档被替换的 receipt。

### F4 — P1：resume 不区分已生成 witness 与未生成；失败历史会被覆盖

**症状/定位：** `d2a_cert_batch.py:161–175` 在 cache miss 后固定构造普通生成命令，不探查已有完整 jets，未使用 `d2a_cert_case.py --verify-only`；每 case 的 generation/std-lib 日志以 `w` 打开。`119–136` 每次重建表/本次 failure list，未读取保留旧执行历史；`177–183` 与 checkpoint 只记录本轮。原 proposal 在 `actual_direction.py:49` 也直接写相同 gzip 路径。

**影响：** wrapper 后期失败且已有完整同设计 witness 的 case，resume 将再生成并覆写同名 jets/log。失败行可以转为成功，但历史失败的审计链不应因此消失；恢复也不应为纯 wrapper 修正重复生成未改 witness。

**实测：** fixture 中预置 jets sentinel、历史日志、旧 checkpoint failure，Popen 全 stub。runner仍选择不带 `--verify-only` 的生成命令；历史 per-case 日志被覆盖，旧 checkpoint failure消失。stub 没有修改 sentinel，故此实验没有执行任何生成。生产两旧失败目前已有有效 full 回执，正常精确复用会绕过生成；本发现针对后续未修/意外中断情形。

**修复：** 为完整 witness 写 identity/content manifest 和完成标记；在相同协议、日历、方向、源版本且 gzip 完整时优先从已有 witness recertify，再独立 `-S` 验证。不能盲目复用截断 gzip。日志使用 attempt编号或 content-addressed archive，执行失败采用 append-only ledger；当前表可显示 recovered，但附历史失败引用。已有 immutable旧 evidence不删除。

### F5 — P2：执行失败也可把 arithmetic complete 置为 true

**症状/定位：** `d2a_cert_batch.py:129–134` 的 `full_arithmetic_table_completed=not counts.get("NOT_RUN")` 忽略 `CERTIFICATION_EXECUTION_FAILED`。

**影响：** 所有行均尝试过、仍有无数字/无证书的失败行时，checkpoint会声明算术表完成。这会误导上层 completion检查；`full_risk_table_completed=false` 并不能修正另一个字段的错误含义。

**实测：** 一个非零行、generation stub exit1的 fixture checkpoint显示 `status_counts={"CERTIFICATION_EXECUTION_FAILED":1}` 且 `full_arithmetic_table_completed=true`。

**修复：** 将 attempted-complete 与 arithmetic-certified-complete 分开；后者只允许当前有效回执结果或明确零方向控制，不允许 execution_failed / missing mean / missing variance / NOT_RUN。总体完成应依据分类计数与回执可用性，不依据阶段名称 `RUN_COMPLETE`。

## 3. 当前工作机制中通过的检查与限制

- **精确缓存 identity：** key含 protocol SHA、T、moves、完整 observations、readout、完整 direction；复用前再做解码结构的严格 equality，没有近似数值或 RMSE选择。case字节 hash变化、direction变化会拒绝，fixture已确认。它是物理实验字段的精确同一，不是全部JSON文件字节完全相同；family/S标签作为重复表行仍保留。
- **冻结 preflight hash：** batch/sync读取 `direction_record_path`，但没有核 CSV 的 `direction_record_sha256`。建议补该 immutable inventory核对；当前 semantic同一检查不能替代预检文件被冻结的证据。
- **CASE / full / derived链：** 生产快照中 prior full 确实绑定 prior CASE，且 covariance相同。缓存 reader自身只哈希 prior文件，没有解析/assert prior full→prior CASE 的内部关系；直接 full分支也不要求 protocol/projection/covariance/jets这些证据文件存在。fixture缺失 ACTUAL_PROTOCOL 与 covariance artifact仍被缓存接受。若缓存契约仅是“已签回执保存其摘要”，数值可信性可继承；若声称证据包完整可复核，应补manifest及artifact存在/hash校验。无需每次读取巨型jets，可在生成/核验时保存内容hash并区分证据完整性与数值接受。
- **原子写：** `os.replace` 保证每个小文件替换；case heartbeat有同进程thread锁。但它不保证 table/checkpoint或CASE/SUMMARY/receipt的一组更新原子，文件也未 fsync；不能宣称断电级持久事务。sync总回执未绑定表hash，可能表/summary不同代。
- **单worker：** batch入口使用 O_CREAT|O_EXCL；存在锁会停止新runner，finally清锁。这正确阻止另一普通batch重入，但 case CLI、rebind、sync未共享同一进程锁；`.next`名固定，维护脚本并发仍靠调用方避免。当前活worker继续使用启动时旧模块，磁盘上文件新版本不会改变其已有Python对象；raw保守pending/历史失败与review_bound表不同是已知版本差异，不应将raw状态当当前审查否决。
- **diskguard：** 新case前预留25GiB以及 max(2GiB,3×压缩估计)，不足先checkpoint后return，未观察到删证据行为。估计是规划值而非配额保证，且guard只在case起跑前检查；没有负载/满盘/断电故障试验。本轮未证明长任务全部运行资源上界。

## 4. 推荐修复顺序与边界

先补 F1 的 canonical判定与 F2 的版本接受门，再补 F3的事务恢复/回执择优，随后修 F4的 witness恢复与历史ledger，最后修 F5的完成标志及表hash/预检hash。这些改动可在新隔离测试完成后供后续worker使用；修改磁盘源码不会修正仍在运行的旧supervisor内存状态。

本轮交付是独立工程审核及隔离触发证据；**没有替用户修改生产实现，也没有完整重跑300个唯一case、400行扫描、R1原 verifier、所有 inherited证书或做数学范围扩展。** 51-case快照不等于全表完成，审查覆盖仅是指定wrapper链及小JSON一致性。Brooks技能的 shared参考文件在本机缺失，本轮采用已读review-guide的“症状→定位→影响→修复”框架，没有声称完成书目级全覆盖。

## 5. 第一轮工程补丁复审

根代理已补目标状态 canonical判定、mean函数hash接受门、完整小JSON/已有witness存在检查、full/derived候选择优、derived事务记录、分阶段resume、attempt日志与正常结束的失败历史继承，以及执行失败completion条件。本节绑定的第一轮补丁快照为：

|文件|SHA256|
|---|---|
|`d2a_cert_batch.py`|`5f66cb34302a43c3d7b3fe678f0c83ebb100e6e4063aed7f40a73893b83c5e6a`|
|`d2a_cert_case.py`|`d727fd778919ca4ae31459c072cf7e471c713e37b6b180ea8ce9a6cd4fe97017`|
|`d2a_cert_verify.py`|`9ba6559c3228c1fd2e153d56e7806af56cc0d86aba2da952e1f44e8c26f85167`|
|`d2a_cert_rebind_derived.py`|`c908fd28f8faa375af50bcd7531a1384a71e16829340152cbf6101b25f0761ce`|

适配脚本：`work/d2a_cert_audit_fixture_v2.py`；结果：`work/d2a_cert_audit_fixture_v2_patch1_results.json`（保留本轮快照），以及可继续复跑的 `...v2_results.json`。本轮约2.18s；没有worker进程，未读生产jets，未执行大递推。为检查 inherited verifier缺少参考证书的具体失败位置，只在audit fixture写了一个含 `{}` 的 tiny gzip，并stub所有recursion，不能把这称为科学witness核验。

### 5.1 已通过的修复控制

|场景|复审结果|
|---|---|
|真实不达标payload配错误pass标签|full wrapper、apply_result和cache均拒绝|
|绑定mean hash改为64个零|review_binding与cache均拒绝|
|ACTUAL_PROTOCOL / DIRECTION / covariance缺失|cache拒绝|
|报告字节与绑定hash不符|cache拒绝|
|旧DERIVED残留、新full绑定当前CASE|cache正确接受新full|
|complete科学payload但无有效回执|只选择独立 `-S` verifier，不重新生成|
|历史legacy日志与新失败attempt|旧内容留在content-addressed archive；新attempt存在|
|正常终止保存旧execution_failures|旧marker保留|
|单非零行仍execution_failed|full_arithmetic_table_completed=false|

### 5.2 仍需处理的三类恢复问题

**R1 — P1：Windows换行导致PREPARED事务的proposed hash不是实际CASE字节hash。** `rebind:76–82` 对LF `proposed_text.encode('utf-8')` 求hash；`core.atomic_text`的 `Path.write_text` 在Windows默认将LF写为CRLF。注入最后receipt前中断后，retry在`rebind:28`的current_hash检查失败。fixture实际CASE hash为 `890db18fe5fad9f812f711b6629e6c4a91ed6f29965d3b5ead8cccdb54ce5f19`，transaction proposed hash为 `5758b71b3dbcaee453e9bc1df0e670698ab82502c228602746c0a504d884628f`；CASE经read_text换行正规化后再encode得到后者，直接确认原因。建议将待提交bytes作为唯一对象，使用atomic bytes写入并对同一bytes求hash，或明确 `newline=''`。prior既有证据字节无需修改。

**R2 — P1：witness-only分支仍缺它需要的covariance reference。** batch有jets且缺CASE/covariance时选择 `--verify-only`；case调用 `adapter.certify(True)`，但原 inherited `actual_direction.py:134–137` 的True模式需要已有 `DIRECTION_CERTIFICATE.json` 的supersolutions。tiny fixture加stubrecursions直接复现FileNotFoundError；真实长case会先验算大recursions再碰到缺reference。建议明确两个状态：有完整covariance reference时执行True重验；仅jets且无reference时调用 `certify(False)` 从已生成jets产生supersolutions/covariance，不调用proposal。必须验证已有jets完整且精确匹配当前protocol/direction，失败时保留证据并明确分类。

**R3 — P1：failure history只在最终save持久化，提前退出仍丢失。** patched batch将prior failures读入内存，但 `save(STARTED/GENERATING_CASE/ROW/DISK_GUARD)` 默认不附 `execution_failures`。fixture正常结束旧marker保留；diskguard提前return及launcher注入中断后，checkpoint均丢失旧marker。建议所有checkpoint统一包含累计history，并在新失败append后立即持久化；初始化history应先于第一次save。最好另有append-only ledger，避免一个覆盖式checkpoint承载唯一历史。

这些是恢复流程中的实测失败；F1/F2与正常resume的修复已经有独立通过证据。当前长扫描与既有科学结果未被本轮测试修改。
