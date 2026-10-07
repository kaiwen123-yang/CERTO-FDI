# Full D2-a 科学复现包契约 v1

2026-10-07。**契约、正式可执行 recipe 和轻量预检已交付；完整科学复现包未构建、未做大型科学重放，当前 `scientific_ready=false`。** 本契约执行原计划P5/P7：全400行须有结果或明确失败分类，发布的实际ZIP须在新副本中验收，不能只检工作树，也不能用V2阶段包的11项有限理论检查或38个metadata叶替代全D2科学证据。

正式可恢复源为 `outputs/package_full_d2a_release_v1.py`，SHA256 `cae0b2d25804bdb7dc9f76f86bffb82733220883156a9c46121c4e0b275ce920`；工作recipe与其逐字节相同。C1/C2 helper另保存为 `outputs/full_d2a_release_metadata_guard_v1.py`，与active `work/d2a_metadata_guard.py`相同，SHA256 `b2bedb201eaafb5e59f40b55d96040e1895503643210e92b51bdb132b3114122`。最终显式清单同时含active guard、新 `outputs/d2a_full_grid_acceptance_v1.py`及guard修订证据，不从旧runtimeV1还原过时guard。

## 当前验收范围

正式recipe实际执行：

```text
python -S -B -X utf8 outputs/package_full_d2a_release_v1.py --plan
python -S -B -X utf8 outputs/package_full_d2a_release_v1.py --preflight
```

`--preflight`只读单次捕获CSV、方向/CASE/receipt等小元数据和文件大小，不导入science runner、不读大jets内容、不碰live锁、不写原CSV或科学目录。09:31:22 UTC快照：400行中74条ZERO、85条有效但未达目标、45条目标通过、**196条NOT_RUN**；114个已有canonical科学case，metadata错误0。这是当时快照，不是持续“当前”状态。完整表尚未闭合，因此预检按设计以非零退出拒绝ready。

另完成语法与一个必要的小门禁测试：在400行未闭合时，build在读取freeze/创建ZIP前拒绝。收据为 `full_d2a_release_recipe_precheck_v1.json`。没有执行R1新提取、big hash、science、新包构建或完整replay；未来build/replay分支不属于本次已验收范围。

## 每一逻辑行必须闭合的科学链

1. 固定协议 `0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6` → 完整唯一400个 `(H,family,S,readout)` keys → 方向record及精确projection。
2. 原时钟、4槽前缀、pre-step读数、move/settle及≥1750再移动、三分量返回条件 → physical/risk分类；不得在窗口或块间reset。
3. exact experiment identity → canonical `CASE_RESULT.json`／`SUMMARY.json`、`ACTUAL_PROTOCOL.json`、`PROJECTION_CERTIFICATE.json`、`DIRECTION.json`。
4. 实际大witness **`audit/<CASE>_ADJOINT_JET.json.gz`** → `audit/<CASE>_DIRECTION_CERTIFICATE.json`：完整历史整数/区间递推、Abel及supersolutions、covariance上下界；没有一个小“WITNESS metadata”能替代该gzip。
5. Gaussian-comparator均值/方差 → 真实非线性remainder → 每假设event budget → guarded双侧风险；与CASE、表格数字、current full/derived receipt和artifact hashes一致。
6. DERIVED链须保留引用的PRIOR_CASE、PRIOR_STDLIB和unchanged covariance payload；所有失败/中断/旧attempt/恢复记录保留，不将失效的旧receipt伪装成current。

PASS与TARGET_NOT_MET都要完整科学材料；后者不是物理不可行或真实power低。ZERO须精确KKT/舍入退化与physical实例可复核，保留缺风险证书，不填power=0，不称全实验无信息。physical/projection/mean/variance/execution失败须有原因和现有证据；明确失败包可以另经root授权归档，但不得变成最终科学PASS。

aliases保留所有逻辑行，以protocol、完整fast clock/moves/observations、readout、实际direction的指纹证明等价；名字、H或“看起来同一日历”不足以复用。每个unique实验完整验一次，而非为相同实验重复存大jets。固定family/grid的earliest certificate须关闭全部前驱及当前S成员；不是连续停止时间、信息论最短时域或所有日历全局最优。≥3完整块为原代表实例筛选标准，不删掉其他记录或强造成功。

## R1与环境

采用self-contained **exact R1 bootstrap**：最终ZIP包含原输入ZIP，SHA256 `f703091ace28d9017d0400e07984f4c34f03d5efdba14742f5a3a9f4ea94a60b`，实际114,986,329字节；在新验证root中一次安全展开463文件、139,638,206字节。无需现在再复制active R1树。C→N→E→H和D→DH来源分别保留，不能混成一个唯一物理文件。

离线独立verifier用64-bit Python≥3.11、`-S -B -X utf8`，不加载NumPy/SciPy。原generation/preflight已测环境为Python3.12.10、NumPy2.4.5、SciPy1.17.1/Windows，仅作版本说明；本任务不安装或下载。科学replay不是重新证明全部普遍定理，旧R1固定实例PASS也不自动覆盖D2新case。

mean接受范围仍是固定H0/H1模板、H≤600、实际f≤0.045及原nonlinear/event/contraction/segment-return前提；不扩大到mirror全f≤0.75。V+属于Gaussian comparator；真实NL统计量另付remainder/events，不把它写成真实无条件方差或经验频率。

## 磁盘可执行方案

最终build直接从冻结原文件流式写一个Zip64，不建整套science staging copy；已经gzip的jets及原R1ZIP用ZIP_STORED。actual-ZIP验收共享一次小源码/R1 bootstrap，每次只新解压一个canonical case，完整独立`-S`验证并保存新log/receipt/hash，然后**仅清理该成功的新scratchcase**；失败scratch保留。Windows cleanup先校resolved绝对路径及exact intended root、禁止reparse point，再用native PowerShell `Remove-Item -LiteralPath`；原science始终不删、不移。

验收后另一份用户路径可选同C卷immutable ZIP hardlink，目标存在即拒绝，避免第二份物理大ZIP。这个方案减小磁盘峰值，**不**改变原verifier整块解析单case gzip JSON的RAM开销。

09:31快照free157,315,153,920字节、既有witness7,728,329,143字节、最大已有case scratch189,287,596字节；reserve26,843,545,600字节。原fulljets估计54,879,354,838字节的方案可落入当时预算；82,319,032,258字节headroom方案不能保证落入。两者都是规划估计，不预测最后大小或全面PASS。最终build须根据完成后的实际文件清单、free及maxcase重新拒绝不足空间，不能靠删原witness救预算。

## 门禁与精确下一步

没有全400闭合、完整材料、review/receipt bindings、root explicit freeze与actual OS quiescence，build拒绝；当前不会构建或重包V2。最终freeze显式选择届时paper revision、source/PDF、compile-layout与review/figure hashes，**不硬编码R6、R7或status_v2**；physics协议保持0d8b。

当前future replay driver另留一条fail-closed门：新full-grid metadata helper要求所有witness paths同时`is_file()`，而逐case scratch清理会移走它们。**下一条具体工程动作是为该helper提供已验证actual-ZIP member presence与小metadata view的IO适配**，随后做小fixture验收；不能伪造空witness，不能回读原worktree，也不能因此持有全部55GB scratch。该门未完成前，recipe即使case replays都成功仍输出`scientific_ready=false`，不颁发final-PASS。

完整契约、版本hash、预算公式和freeze schema见 `full_d2a_release_contract_v1.json`。根可据此保存checkpoint；本轮没有改变main稿、root状态、live生产者或任何原科学产物。
