# D2-a actual-ZIP IO 桥与重放覆盖门独立复核 v1

2026-10-07。**当前冻结字节在限定 IO/覆盖范围内通过独审，无尚需修复项。独立合成真实 ZIP 测试 45 项、0 失败。完整科学包未构建、全量科学重放未执行，不能据此设置 `scientific_ready=true`。**

本轮只读原 V1 契约/helper/recipe、当前 adapter/helper/coverage/recipe、两版 recipe 的精确历史、三层作者 fixture/receipt/report，以及完整 verifier 的调用入口。仅在新建 `work/` 合成 fixture 中写文件和运行 `python -S -B -X utf8`。没有真实大 witness 内容/hash、R1 提取、矩阵或 D2 科学重跑，没有主稿、live CSV/lock/PID、原科学文件或作者冻结文件写入。

## 1. 最终输入与历史不可混用

| 输入 | 实际 SHA256 |
|---|---|
| `outputs/d2a_archive_witness_view_v1.py` | `7f566d7251ea3077b261b496d93a7469db8d502b6523be8393d3f088b760e637` |
| `outputs/d2a_full_grid_acceptance_v2.py` | `25703242972718b3a3fd6f924dacc5dd1c67b03a51518d74aa5a882412d3ab15` |
| `outputs/d2a_archive_coverage_gate_v1.py` | `87a4106ef35201e3562e0c5d352a4ee84b3fbec14614ae54b48ded806759cb55` |
| 当前 `outputs/package_full_d2a_release_v2.py` | `1adc2b0e1acb326e9e63c8a852fa35d3b648abe553484b63f8cdbede8b842953` |
| 首版 IO recipe 历史 | `1c6ecc8e5cd6323c488e3c584e74199a8a64a3c224788cd23e392b82a6ab5307` |
| coverage 补门 recipe 历史 | `97e36639d9291e72a93c84c822749f79eaa55d15af13c7bc5ff683916b5ee50f` |

两个历史 recipe 的实字节均存在 `references/release_recipe_history/<完整SHA>.py`，实际 hash 与文件名相同。首版 30 项作者 IO receipt 绑定 `1c6ecc…`，22 项 coverage receipt 绑定 `97e366…`，26 项 CSV cap receipt 绑定当前 `1adc2b…`；各自历史报告和 receipt 均未改。不能将早期 receipt 的 source SHA 静默换成当前版本。V1 契约/helper/recipe/guard 原 SHA 也实际核对未变；完整值见本报告 JSON。

## 2. 已解决的两项工程缺口

**重放集合遗漏（首版 `1c6ecc…`，已解决）。** 首版只迭代 manifest `cases`，而 `verified == allfiles` 只证明全部 payload 被 hash。若漏掉 science identity，其 payload 进入 shared 后可能不经过完整 case verifier。独立审查确认原代码没有等价覆盖门。当前 recipe 第 442、446、466 行分别接入 manifest inventory、actual immutable metadata、fresh replay coverage 三层门。`validate_manifest_inventory()` 要求 0..399 行索引、完整唯一逻辑 keys、science identity 集合和 canonical case keys 相等、每 case 的 science row 集合精确，以及当前 case witness 不得成为 orphan shared 文件；随后实际 CSV/direction/CASE 字节绑定身份；最后新 replay identity 集合必须精确等于 canonical 集合。缺 case、伪造 manifest-only 身份、缺/重复 replay 均由纯小反例证实拒绝。

**必需 CSV 被 small view 漏选（`97e366…`，已解决）。** 该版 `small()` 统一 4,000,000 bytes，selector 统一 2 MiB，而既有 helper/coverage 对精确表路径允许 16 MiB。这会拒绝或漏选合法完整表，属于 fail-closed 可用性缺口，不能拿表尚小作为完整归档的依据。当前版只对 `work/d2a_cert_review_bound_table.csv` 允许 16,777,216 bytes；其他小文件为 2,097,152 bytes；selected view 总量为 268,435,456 bytes。超限必需表显式拒绝且不创建 partial view，其他 CSV 无例外。对 `97e366…` → 当前版的实际 diff 只含容量常量、`small()` 的 stat/read 后检查、selector 与建目录时序，不改科学 verifier、参数、分类或覆盖门。

## 3. 三类证据及实际调用链

| 层级 | 当前代码保证的范围 | 不能从该层推出的结论 |
|---|---|---|
| `ZipWitnessView` / helper `witness_available()` | 独立外部 manifest SHA、实际 central member、规范 namespace、receipt/manifest SHA 字符串绑定、实际 uncompressed size；缺成员/mapping、错 manifest、unsafe/casefold/symlink/encrypted/size/name 均拒绝 | witness body SHA 或数学算术通过 |
| recipe `extract_members()` | 从实际 ZIP 逐字节提取，比较实际 bytes 与完整 payload SHA；small metadata 单独提取到全新只读 view | full Gaussian/nonlinear/variance 证明通过 |
| future full replay + coverage | 新 scratch 中每个 canonical case 的完整 `-S` verifier、fresh receipt/log，全部 payload hash，清理后 metadata gate 与完整 replay 集合门 | 本轮已经实际完成上述全量分支 |

同尺寸坏 body 通过 presence 是其明确范围，不是科学接受。独立真实 ZIP 反例同时验证：该坏 body 在 presence 层可用，但 `extract_members()` 随后以 `ACTUAL_ZIP_PAYLOAD_HASH_MISMATCH` 拒绝。scope 字段继续写明 payload hash/arithmetic 未验。

默认 filesystem backend 保留 V1 的 contained `Path.resolve()`/`is_file()` 可用性语义，不以 expected SHA/size 验 body。V1→V2 实际文本 diff 显示其余 physical/risk/mean AST/alias/first-grid 逻辑未改。V2 完成行从已绑定 artifact entry 传 witness bytes，ZIP backend 才实际核其大小。

**独立元数据来源在 recipe 接线中成立。** 单独调用 helper 的 `--witness-archive` 只改变 witness backend；其余小 metadata 仍由 `--root` 读取。当前 `metadata_gate()` 第 383 行明确将 root 指向实际 ZIP 已提取、hash 并设只读的 `immutable_metadata_view`，脚本本身来自新 scratch，前后两次运行均不读原 worktree。该 view 没有 dummy gzip；科学 verifier 可改写 replay root 的 CASE/receipt，而独立 original view 保持原字节并在最后再次 hash。

**完整 verifier 没有被 presence 或旧 receipt 代替。** 当前 recipe 第 456–462 行顺序为 exact alias scope → 新 scratch 下完整 `work/d2a_cert_verify.py --case-dir <新case>` → 复制其新 receipt/hash → append replay record → 仅清理成功的新 case。`run_logged()` 非零退出抛错，失败不会经过成功 cleanup。只读入口追踪确认 verifier 的 `core.ROOT` 来自其新副本的 `__file__`，R1 source 来自该 ROOT 下新 bootstrap，case 必须在该 ROOT/work 内；无代码中的原工作树 fallback。全 witness `certify(True)`、均值/event/risk 重算仍在完整 verifier 中。这个调用链已静态核验，但本轮未启动该 verifier/R1。

`record_case_replays()` 是集合覆盖门，synthetic PASS 文本不能单独证明 verifier 执行。实际 recipe 仅在上述 subprocess 成功并保存 fresh receipt 后产生记录，因此不能将纯 coverage fixture 的合成 receipt 当真实 science replay。

## 4. 实际有限验证与结论边界

独立执行 `work/review_archive_io_bridge_v1.py`：33 项通过，实际合成 coverage ZIP 450,561 bytes；执行 `work/review_archive_csv_cap_v1.py`：12 项通过，实际 compressed synthetic ZIP 与超过 2 MiB 的 CSV 真实提取/hash/binding，并核 TABLE/other/total 边界拒绝。两份独立 receipt 的路径、SHA、全部项与脚本 SHA 在本报告 JSON。测试只写自己的新 fixture，实际移除的也是其中一份 tiny witness；未调用科学 case cleanup。作者冻结的 30/22/26 项 receipt 另逐字节绑定，不混成当前版科学验收。

本轮接受的是**限定 IO 桥、覆盖门与容量合同的工程实现**。未来仍须按原契约在完整 400 行闭合、明确 freeze/OS quiescence 后，对实际完整 ZIP 执行全部 payload hash、R1 fresh bootstrap、每个 canonical science case 完整 verifier、前后 metadata gate 和最终覆盖门。ZERO/target-not-met/显式失败的既有科学含义与有限 H/fault 范围保持，不以 fixture 预测最终点会通过，也不把未来分支已连接解释成 `scientific_ready` 已成立。
