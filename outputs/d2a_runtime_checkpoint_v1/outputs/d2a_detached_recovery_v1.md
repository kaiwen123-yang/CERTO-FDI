# D2-a 隐藏后台恢复证据 v1

2026-10-07 06:36 UTC。当前唯一science PID62844、metadata PID10032，均由WMI broker创建的独立隐藏launcher71048再经 `Start-Process -WindowStyle Hidden` 启动；launcher已退出，进程不依赖unified exec会话。当前实际OS/CIM、stdout/stderr与最新checkpoint仍是存活判断依据。launch快照见 [d2a_detached_launch_receipt_v1.json](d2a_detached_launch_receipt_v1.json)，续接入口见 [d2a_recovery_index_v1.md](d2a_recovery_index_v1.md)。

旧science59248、metadata63968及会话94963/1590均已失效。日志没有正常结束或Traceback、锁仍在，符合外部强制终止；与代理final清理一致，但没有直接取得退出码，因此不把猜测写成确证原因。旧锁/checkpoint/raw/overlay/完整logs逐SHA保存在 `work/d2a_cert_recovery_20261007T063228Z`。

唯一科学中断是H200/S140 average：遗留gzip65,755,445字节缺end-of-stream marker，SHA256为 `5711395f5a81e7f2e6b53f80f2eba89bcc62c4ab8ec7802a4f2d02760c6145f8`。全部原字节保存在该case的audit/INTERRUPTED文件，只有此未完成case重新生成；已完成case仍按同协议、同完整方向/物理实验、有效CASE/回执cache复用。旧两条wrapper失败的已恢复回执SHA保留于checkpoint执行历史和overlay历史列。

首次脱离启动science50664在纯cache恢复中因Windows WinError5退出：metadata短读raw CSV阻止atomic replace。它没有重做科学计算；新attempt stdout/stderr及下一份恢复快照保存在 `work/d2a_cert_recovery_20261007T063527Z`。三个atomic入口现对Windows5/32/33作最多20秒短重试，超时仍保留失败及临时文件。真实Windows短读锁回归均约0.25秒后成功，见 [d2a_windows_atomic_retry_v1.json](d2a_windows_atomic_retry_v1.json)；28项tiny工程fixture再次全部通过，0科学递推。

新stdout/stderr四个独立attempt文件名由launch receipt列出，旧日志不覆盖。两次中断分别保存在 `interruption_history`；恢复代码不改物理盒、模板、方向、原模型或原ZIP。完整400行表仍未完成，固定模板数学接受范围仍为H≤600、实际f≤0.045及继承条件。
