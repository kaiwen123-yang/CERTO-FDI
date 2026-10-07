# D2-a 有限runner审查与修复回归 v1

2026-10-07。本页汇总独立工程审查与后续有限修复，不能替代数学审查或全表验收。

独立报告为 `work/d2a_cert_runner_audit_v1.md`。审查者读取wrapper/缓存/派生回执/合并逻辑，以小隔离fixture触发漏洞，并检查51个已完成case的小JSON链：该生产快照没有发现结果链或标签异常；没有读生产gzip、跑大递推或操纵活worker。审查范围不包括所有源数学证明、300个唯一case计算或满盘/断电试验。

发现并修复的工程问题包括：

- verifier不能信任现成通过标签：现在从实际风险、方差比重新构造状态和failure列表，拒绝`target_pass=false`配假PASS。
- mean实现版本和当前报告hash成为接受门；缺协议、方向、covariance或witness证据时拒绝cache。
- stale DERIVED不遮蔽后来的有效full回执；派生回执校验prior full→prior CASE以及variance payload未改。
- 派生重绑定采用PREPARED/COMMITTED事务；提交bytes与拟提交hash相同，明确避免Windows CRLF改写。
- 已有complete科学payload只做独立-S核验；只有jets时从saved witness推导covariance，不调用proposal重新生成。
- 每attempt独立日志，旧日志按内容hash归档；checkpoint继承并即时保存失败history，执行失败不宣称arithmetic complete。

维护者适配独立fixture后的`work/d2a_cert_audit_fixture_v3_results.json`中28项检查全部通过，包含伪PASS、错误版本、过期报告、缺文件、stale derived、提交中断/重试、日志保留、diskguard/launcher中断历史、jets-only恢复分支和失败完成标志。该回归使用tiny adapter/stub，0 worker、0生产jets读取、0大递推；不能把它表述为新科学证书或独立第三轮大审查。原v1/v2触发结果保留。

可交付回归快照为 [d2a_runner_finite_audit_v1.json](d2a_runner_finite_audit_v1.json)。独立-S实际字节核对的已完成69个唯一case快照为 [d2a_completed_artifact_integrity_v1.json](d2a_completed_artifact_integrity_v1.json)，其中失败为空、没有重新执行科学递推；这不代表全部400行完成。

后续补齐了冻结preflight方向记录SHA门、合并时统一选择实际通过接受门的full/derived回执，以及旧回执hash-only sidecar与当前回执的严格SHA一致性。28项有限fixture在这些改动后再次通过。部分H*入口只在所有前驱与当前H全部成员闭合时发布，并携带输入总表及所选证据SHA。

两个实际热更新过渡失败（H80 fixed40 point、H80 switch_then_stay S60 average）均从原jets独立-S重新核验成功。旧失败stdout保留；未更改物理参数、重新生成waveform或删除失败行。风险数值和Variance证据仍需要相应数学接受范围，当前只接受冻结f≤0.045模板。

长扫描仍由启动时的旧supervisor对象运行。新case子进程使用修复后的代码；旧supervisor的raw计数不是当前审查绑定总表。权威合并方式与恢复入口见 `d2a_recovery_index_v1.md`。
