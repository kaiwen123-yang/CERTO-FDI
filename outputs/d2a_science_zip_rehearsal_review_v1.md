# H160 actual-ZIP 科学预演限定独审 v1

2026-10-07。**限定预演 ACCEPTED，无尚需修复项：两种 distinct readout 在同一实际 ZIP、新 ROOT 和一次 fresh R1 bootstrap 下，各执行一次完整标准库 verifier，分类与输入字节保持；两个真实工程失败及有限恢复均保留。** 这不接受首版 wrapper 原样全程成功，也不接受未来 full400 分支。`scientific_ready=false`、`full400=false`。

审查只读新方案/precheck、冻结源码、实际 ZIP 的小 metadata/central directory、两份 fresh receipt/stdout/stderr、bootstrap/失败/诊断/cleanup/final receipt，以及 V2→V3 实际 diff。审查者未重跑科学、R1、旧 fixtures、真实大 hash 或删除任何文件。完整大 payload/ZIP/R1 输入哈希来自作者实际执行的、已绑定 final receipt；本审查另从实际 ZIP 独立读取/hash 45 个小成员共 762,868 bytes，并核新 ROOT 中六份小 shared source/mean 文件。

## 实际绑定与结果

| 项目 | 最终实际字节绑定 |
|---|---|
| 专用 ZIP | 296,443,279 bytes；SHA `c5dfadbb4c914299fa502b4549158f8b2d0adae0d1f690cd06066d45b4c39f4f` |
| actual manifest | SHA `3039e08106e41653dc0b0406623bad17bc674a3948137ab4c9f5849f553cbc90`；50 members，48 payload |
| final execution receipt | SHA `7b80a9f530f40e6c89767dd6d75bb6ebd0c01b5912e29b41fd703adfda9a8832` |
| 首版 wrapper | SHA `2d324aefaa33cb869b79c94bd57aaeb7be6c4b05ec38056118e061e07edb8186` |
| cleanup-recovery resume | SHA `eaa7875ca115baf464ae3e544545e3d297a9a3869869c08ab79d66d002d37fcf` |
| long-path finalizer | SHA `15bd463094278a4f90ba9cd87fa9aa2407fc883562d7d87031895618465693d5` |
| 新 native cleanup | SHA `f8f4bde50b121f7be975ade18d2988c66428d5463effde29a8889167efa7d070` |

作者冻结报告 MD SHA `caab4817569539c9bd704e1d3bc6d424183a43d768cfd4405f7a94862720e997`、JSON SHA `9939355fce37d2edb5a75a056d5be0e2194385b39d90ac107f79e7f79769d6e0` 均已实际读取/hash，并与 final receipt 和历史记录核对。

| Readout | fresh receipt SHA | 完整 verifier 秒数 | 保留的风险分类 |
|---|---|---|---|
| `average250` | `2ae7eadea94432484964ecc4cdafaae5e4f3efec863dbd53fb1b158e0a6bf019` | 77.6346846 | `CERTIFIED_TARGET_PASS` |
| `point_last_fast_read` | `a1d8712a0d7ebe6ec3688ba757bc6d92e315946696e3c894a2ed56bf748deada` | 78.9168846 | `VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET` |

两份 fresh receipt 各与 stdout **最后一个 JSON** 逐值相同，stderr 均 0 bytes，且 hash 与 ZIP 中旧 receipt 不同。stdout 前有 adapter 文本，不能将整个 stdout 直接作为单个 JSON。projection KKT、actual protocol、完整 integer/interval recursion、Abel/supersolution、mean/event/risk 重算标志均真，NumPy/SciPy 均 false。每份新 receipt 的五项 artifact SHA/bytes 对应实际 archive 清单，CASE SHA 保持原值，mean review 仍绑定 `6a9cfb8009d2b424dfd29130c3d9140478531aeb74b326e917881eb35d7fe924`。

## 输入、身份与新 ROOT 调用

实际包含两个 case 各全部 12 文件，原 sidecar、receipt/log、CASE/SUMMARY、projection/protocol/direction、真实大 witness 与 covariance certificate；没有 dummy witness 或伪400表。对应 preflight direction 与实际 CASE+DIRECTION 的 semantic identity 严格相同：平均读出 `dfcb45fa…`，末点 `9ccd02f0…`，二者 distinct；均 H160/terminal_balanced/S=null、41,000 fast steps、6 moves、92 observations。不能按同 calendar 合并验证。两案原链均为直接完整 receipt，不存在本次需追随的 DERIVED 或外部 PRIOR path；旧 full receipt 的 artifact 绑定位于 sidecar，已实际收录并核其 CASE/receipt SHA。

科学命令使用实际新目录 `work/d2a_pair_replay_30573e7b/work/d2a_cert_verify.py --case-dir <该新ROOT中的case>`，`-S -B -X utf8`；子 process 清除 PYTHONPATH/PYTHONHOME。共享 science 源码均由实际 ZIP 提取/hash，verifier 的 `core.ROOT` 根据新副本 `__file__` 派生，其 R1 source 位于该 ROOT 的新 bootstrap，未将旧工作树用作科学源。审查者独立 hash 新 ROOT 的 core/case/verifier/extractor/mean binding/report 小文件，与 actual manifest 对应项相同。

原 R1 ZIP 的 `f703091a…` 在该新 ROOT 只 bootstrap 一次。其实际 receipt 绑定前后原 input SHA、463 文件、139,638,206 uncompressed file bytes及新 destination。finalizer 以长路径读取在 pair 后完整核 463 个文件，另核全部 fresh shared source；审查按 receipt/manifest/root 路径与小 source 实字节绑定接受，不自行再次解压或重算大文件。此前完整 verifier 内的 `certify(True)` 和均值/event/guarded risk 重算在两案各真实执行一次，finalizer 不调用任何科学 verifier。

final receipt 的 48 条 actual ZIP payload hash 记录精确覆盖 actual manifest，size/SHA 逐项一致；47 条原输入前后记录精确覆盖 frozen precheck 输入，前期实际 streaming SHA、结束 SHA/stat 及两原 case 文件树均一致。原 case 并非 OS ReadOnly；这里只接受本轮采集和执行期间字节稳定，不声称永久不可变。审查者未重复这三个大成员或整个 ZIP 的 hash；其完整 SHA 依据已核作者实际执行 receipt，独立 central directory/stat 与小 metadata 另行核对。

## 两次失败与恢复完整保留

1. `2d324a…` 首轮 avg 已实际验算成功，但旧 V2 helper 的 PowerShell `-File` 因 scripts disabled 返回 1；point 尚未执行。真实 failure SHA `7658cafde1de4a8f100509282eb2d2ca21a68b3fc1c245ac82176b63e57e75b3` 与实际 stderr 诊断保留，没有将首版 wrapper 改记为 PASS。
2. 新 native component 以明确 System32 WinPS、inline `-Command`、process-only native Modules 环境执行相同 root/parent/name/reparse/LiteralPath guards；不改机器/用户 execution policy 或全局环境。实际 tiny cleanup/outside-root 拒绝已有 receipt，随后 avg 新 case 清理成功。resume 保留 avg fresh receipt，仅首次执行 point 完整 verifier并清理；两次实际 cleanup receipt 均 exit0，审查确认两个新 case 目录已不存在。此恢复不删原 science，不重算 avg。
3. resume 在后置 R1 hash 遇 264 字符普通 Windows 路径读取失败，真实 failure SHA `97560868ad04d5ede27b1a4c527852bfd3ea28ff9395221aae5be6fea6251492` 保留。诊断的 extended-path 读取命中同一真实文件及 bootstrap SHA。`15bd463…` finalizer 只读 `\\?\` 长路径补齐 actual ZIP、fresh R1 tree、原输入及 source hashes；没有重提取 R1、科学重跑或新的 cleanup。

恢复/cleanup/finalizer 源码在原 ZIP **之外**，是额外交付并分别绑定的新源；旧 ZIP 仍含原 `2d324a…` wrapper。重现恢复需同时保留这些源和两次失败记录，不能称原 ZIP 内 wrapper 在本机原样全程 PASS。

## 资源、未来 driver 与范围结论

precheck 实际 RAM free 13,404,569,600 bytes、C free 181,244,502,016 bytes；门为 RAM≥8 GiB、C free≥6 GiB且每 case 前再查 selected pair writer。只顺序保留一个新 case payload，成功后清理；结束 RAM free 14,745,460,736 bytes、C free 180,172,361,728 bytes，原 live batch/publisher PID 仍在资源快照。预估 scratch 347,992,083 bytes只是规划量，不是实测 RAM 峰值保证；没有停止、重启或改动 live jobs。

V2 `1adc2b…` 实字节保留；新增 V3 `6c5512c180046c7916f8294626eef6af748d4385346442a54088572c59490dd0` 的实际 diff 仅 native cleanup、源清单及自身/default archive/scratch 版本名。独立 AST 比较的变化函数恰为 build/cleanup_case/verify_archive；精确归一自身文件/default ZIP/scratch 三个版本名后，27 个非 cleanup 函数 AST 全同。explicit GO、quiescence、small/caps、metadata gate、offline identity/alias及交付门保持。新 cleanup 明确针对 Windows native 环境。本预演只接受这项有限兼容接线，没有运行 V3 full400 driver。

接受范围为**固定 H160 两种读出从真实 ZIP 到新 ROOT 的完整计算重验及有记录的 Windows 工程恢复**。风险仍属已有固定模板、H160 实际 fault `3/250`、既有 mean/nonlinear/event/physical 条件；不扩为 wide fault 0.75、全日历最优、理论重新证明、full400 或 TAC ready。最终完整包仍须所有 400 行闭合、explicit freeze、actual OS quiescence、全部 canonical full replay、前后 metadata 与覆盖门，不能用本 pair 代替。
