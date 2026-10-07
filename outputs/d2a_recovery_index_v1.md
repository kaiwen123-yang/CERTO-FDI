# D2-a 统一恢复入口索引 v1

2026-10-07。本页覆盖正在运行的完整有限表，不宣称完成。

## 运行所有权与存活判断

当前唯一serial science为 **PID62844**，metadata伴随为 **PID10032**。2026-10-07 06:36 UTC由WMI broker创建独立隐藏launcher71048，再以 `Start-Process -WindowStyle Hidden` 启动；launcher已退出，两实际进程仍存活并继续H200/S140计算。**没有unified exec session句柄**。当前receipt为 `work/d2a_cert_detached_launch_receipt.json`，用户快照为 [d2a_detached_launch_receipt_v1.json](d2a_detached_launch_receipt_v1.json)。仍需每次以真实OS/CIM和最新日志判断存活，不能只信旧checkpoint。

历史59248/63968以及94963/1590已失效：本代理句柄也返回Unknown process id，OS枚举没有这些进程，日志没有Traceback或正常结束，锁残留。这符合外部强制清理，亦与代理final清理一致，但不可取得退出码，**不把该推断写成确证原因**。中断H200/S140 average gzip65,755,445字节缺EOF marker，完整原字节保留为 `audit/INTERRUPTED_5711395f5a81e7f2e6b53f80f2eba89bcc62c4ab8ec7802a4f2d02760c6145f8_...gz`；仅该未完成case需重新生成，原ZIP与已完成科学witness未改。

机器可读的所有权快照为 `work/d2a_cert_owner_session.json`，记录代码owner代理、detached/no unified session模式、OS PID、UTC快照时间及权威表入口。它仅是当时存活证据；后续恢复仍须检查真实OS状态。

metadata每45秒检查小回执/checkpoint变更，串行刷新review-bound总表及部分H*；不读取witness、不生成case、不运行科学verifier、不控制science。其入口为 `work/d2a_cert_live_publisher_checkpoint.json`、同名前缀`.log`和独占`.lock`。它观察科学supervisor停止后只作最后一次视图刷新，不能把停止当完成。发布器活着时由它负责视图刷新，避免旁边同时手动写同一总表。

首次脱离启动50664在纯cache恢复中遇到真实Windows WinError5：publisher短读raw CSV时阻止atomic replace；stderr/stdout新attempt均保留。现batch/core/publisher的replace对Windows5/32/33作最多20秒短重试，超时保留失败与临时文件。真实Windows短读锁回归三个入口均等待约0.25秒后成功，见 [d2a_windows_atomic_retry_v1.json](d2a_windows_atomic_retry_v1.json)；28项tiny工程fixture也再次通过，没有科学递推。该失败不冒称数学证书失败。

旧锁/checkpoint/raw/overlay/完整logs逐SHA保存在 `work/d2a_cert_recovery_20261007T063228Z`；首次后台attempt及下一份恢复快照保存在 `work/d2a_cert_recovery_20261007T063527Z`。新stdout/stderr四个独立文件名由current launch receipt给出，旧日志不覆盖。

## 权威状态与入口

| 文件/入口 | 含义 |
|---|---|
| `work/d2a_cert_batch_stdout.log` | 唯一batch总stdout，含phase/heartbeat/历史失败 |
| `work/d2a_cert_batch_checkpoint.json` | 当前supervisor进度、命令、execution_failures与interruption_history；历史旧runtime快照另保存在恢复目录 |
| `work/d2a_cert_checkpoint.json` | 当前case阶段、实际recursion/proposal可观察进度 |
| `work/d2a_cert_partial_table.csv` | 活worker原始400行表；不把旧pending标签当当前数学否决，不把历史已恢复错误当当前无证据 |
| `work/d2a_cert_review_bound_table.csv` | **当前权威审查绑定总表**：严格重新核case/回执/当前review/目标状态，与raw表分开 |
| `work/d2a_cert_review_bound_table_receipt.json` | 当前overlay分类计数与接受范围；全表完成仍单独判定 |
| `work/d2a_cert_mean_review_binding.json` | accepted review report SHA、mean实现版本、H≤600/实际f≤0.045限制 |
| `outputs/d2a_partial_first_success_v1.json` | 仅已经闭合前驱和当前成员的部分H*；其他族不作全网格失败判断 |

刷新权威表及部分H*（不运行大递推）：

`python -B -X utf8 work/d2a_cert_sync_review_table.py`

`python -B -X utf8 outputs/d2a_partial_first_success_v1.py`

需要为旧回执补内容哈希时，先运行 `python -B -X utf8 work/d2a_cert_bind_artifact_hashes.py`，再刷新上述两个入口。它读取已完成witness字节并生成hash-only sidecar，不重执行科学递推。

独立标准库字节验收入口为 `python -S -B -X utf8 work/d2a_cert_verify_artifact_bindings.py --all-completed`。它从冻结preflight和当前接受回执重新读取每个已完成唯一case的五类artifact实际字节，对比回执或有效sidecar的SHA/大小，写入 `work/d2a_cert_artifact_integrity_receipt.json`；不能代替未完成case计算或科学proof。

## 每行证据绑定

非零case目录在 `work/d2a_cert_h...`，包含ACTUAL_PROTOCOL、PROJECTION_CERTIFICATE、DIRECTION、saved jets、DIRECTION_CERTIFICATE、CASE_RESULT、SUMMARY及full或DERIVED标准库回执。缓存要求同protocol SHA、完整物理experiment字段、同direction和CASE字节hash；不是近似数值或RMSE缓存。

冻结preflight的 `direction_record_sha256` 现在在读入时逐行核验，改动方向记录字节会停止合并。总表每个非零已完成行绑定 `case_result_sha256`、真正通过接受门的 `current_receipt_path/sha256`、`witness_sha256`、`covariance_certificate_sha256`、mean review report SHA；使用旧回执补哈希时另绑定 `EVIDENCE_ARTIFACT_HASHES.json` 的路径和SHA。该sidecar还列当时CASE及有效回执SHA，必须与当前接受回执相同。总表回执绑定总表SHA；部分H* JSON绑定其输入总表SHA与所选行完整证据hash。

新full/derived回执自带artifact哈希。旧回执缺少witness哈希时，sidecar是事后的当前字节绑定，不冒充旧核验时已经生成的哈希承诺。原full算术核验及未改方差的派生链保留；最终打包必须再次核所有artifact实际字节。

full回执绑定CASE hash，CASE的uniform_variance必须与保存的covariance证书一致；exact KKT、actual protocol和direction须相等，witness必须存在。派生回执另绑定prior full receipt hash、prior CASE hash及variance payload hash，注明未重复大递推。审查范围与当前report/mean版本也必须一致。重复family/S成员仍各有表行和证书source，不删除。

既有科学jets未因数学review注记改变而重新生成；所有旧CASE/回执及失败logs保留。若重新full核验了已有case，则使用当前有效full回执，不让过期DERIVED遮蔽它。

overlay额外保留raw与checkpoint execution_failures的历史失败列。已恢复行采用有效回执的当前分类；尚未恢复的真实失败行保留 `CERTIFICATION_EXECUTION_FAILED`，不能只变成空白或声称完成。两个早期wrapper失败的resolved回执SHA及本次外部中断均保存在历史链。

## 进程结束后的最终合并

先确认PID结束和锁状态，再用修复后代码严格重建overlay，校验每行回执与当前metadata；不得仅看旧supervisor的RUN_COMPLETE或旧计数。

对完整科学payload但回执缺失/失效的行，只从saved witness执行独立-S verifier；只有jets时先 `--derive-from-witness` 推导covariance，再独立-S核验；只有必要证据不完整时才重新proposal，保留失败和attempt历史。不重跑原R1完整verifier来代替新case核验。

确认400行均有有效结果或明确的方向退化/流程失败分类，且没有NOT_RUN、缺均值/方差、未恢复execution failure、过期review接受后，才输出最终全表。每族H*还需所有更早网格与当前H成员闭合；point/avg各自判断。最终release仍需要实际新ZIP的干净解压验收，不因现工作树通过宣布全D2-a或长期TAC goal完成。

结束后先运行上述 `--all-completed` 字节入口，再刷新overlay和部分H*。不要在字节不匹配时重新生成sidecar来掩盖差异；保留失败，定位所改artifact并从已有回执链恢复或重新核验必要部分。

## 安全续接命令

当前进程活着时不重启。若它确已停止，先保存/核实锁的PID、旧checkpoint与日志，再处理stale lock并运行：

恢复时先以真实旧PID运行 `work/d2a_cert_prepare_detached_recovery.py --old-science-pid <已确认停止的PID> --old-publisher-pid <已确认停止的PID> --cause <实际原因>`；若正常finally已经清锁才可加 `--allow-missing-locks`。它校验协议、锁owner及绝对路径、保留快照和未完成witness；CRC不完整的witness原字节保留并移出正式输入名。随后用PowerShell运行 `work/d2a_cert_launch_via_wmi.ps1`。该入口由WMI创建脱离unified-exec后代树的hidden launcher；内部再次检查旧PID死、协议/锁SHA和没有其他science/metadata进程，才删除仅已确认stale的锁，并使用 `Start-Process -WindowStyle Hidden`、独立新stdout/stderr恢复。

runner默认串行、按H/family/S/readout固定顺序resume，磁盘保留25GiB及下一case缓冲。不足时先checkpoint，不删除需要保留的证据。执行失败history、attempt logs与未计算行都保留。
