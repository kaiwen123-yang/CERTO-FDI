# D2-a archive replay coverage gate 限定补充 v1

2026-10-07。**新增 pure coverage gate 与真实小 ZIP fixture 验收通过；仍未构建完整科学包、未执行科学 replay/R1、大 witness hash，`scientific_ready=false`。** 此补充修正首版 IO driver 的独立覆盖缺口，首版 IO 30 项结果不充当新增覆盖门的验收。

## 已确认缺口与修复

首版 `package_full_d2a_release_v2.py` 的 full replay 只迭代 manifest `cases`。`verified == allfiles` 只证明 archive 文件被 hash，original full-grid helper 只核 CSV/原 receipt。因此 manifest 若遗漏某个 science identity，该 case payload 可能落入 shared 而只 hash、未完整 `-S` 验算；原 working-tree snapshot 的 alias 检查不足以证明 actual-ZIP replay 集合完整。首版确实没有等价门。

新 `d2a_archive_coverage_gate_v1.py` 不导入 science、不开 witness body、不写文件，提供三层门：

1. `validate_manifest_inventory()` 在任何 shared/payload提取前，要求 row索引恰为0..399且唯一、完整400逻辑key、closed status、science canonical identity与case keys全集相等、每case的row集合完整唯一、dir与CASE名绑定、必需payload及artifact的manifest绑定。当前case namespace中未列canonical的witness拒绝，不能静默进入shared。历史recovery namespace保持历史payload范围，不提升为当前canonical replay。
2. `validate_immutable_metadata()` 从actual ZIP已真实提取并hash的immutable小view读取CSV/direction/CASE，核 table SHA、逐row key/status/direction路径和SHA、完整physical calendar/readout/direction的exact identity，以及actual CSV certificate reference→canonical dir、CASE bytes/hash/name/identity。该门在 shared提取、R1 bootstrap和case replay之前完成，没有原worktree fallback。
3. `record_case_replays()` 要求fresh完整verifier result identity全集与全部science canonical case全集完全相等，零遗漏、重复、额外case，且每个CASE/dir、PASS状态、fresh receipt SHA绑定正确。recipe在该门之后才能形成未来 `scientific_ready`；此门与原全部ZIP payload hash、前后metadata gate、零未接受失败一起成立。

future driver原完整per-case `work/d2a_cert_verify.py --case-dir ...`、日志/新receipt、native guarded scratch cleanup保持；覆盖门不会把presence或旧receipt当新科学验算。

## 本轮实际验收

运行 `python -S -B -X utf8 outputs/d2a_archive_coverage_gate_fixtures_v1.py`：**22 checks、0 failures**，真实小ZIP450,561字节、synthetic400行/3 science row/2 canonical case。另一个真实小ZIP验证actual CSV错误canonical directory拒绝。

检查包括缺science case、缺/重复row索引、缺/重复逻辑key、extra case、错/重复case rows、wrong dir/name、wrong canonical identity、orphan current witness、manifest status与actualCSV不符、coherent forged identity仍与actual direction不符、direction路径/hash绑定、actual CSV→dir绑定、missing/duplicate/wrongdir fresh replay集合拒绝。通过的synthetic receipt records只是coverage contract fixture，**不是实际科学replay**。两个realZIP仅小metadata/witness fixture，无真实大科学输入。

## 历史与当前源绑定

首版 IO adapter/helper/fixture/results/report未改；其30checks仍只说明首版IO单位。首版 recipe精确字节已保存于 `references/release_recipe_history/1c6ecc8e5cd6323c488e3c584e74199a8a64a3c224788cd23e392b82a6ab5307.py`，实际SHA与文件名完整相同，使历史报告仍有可读取原source。

| 当前文件 | SHA256 |
|---|---|
| `d2a_archive_coverage_gate_v1.py` | `87a4106ef35201e3562e0c5d352a4ee84b3fbec14614ae54b48ded806759cb55` |
| `package_full_d2a_release_v2.py` | `97e36639d9291e72a93c84c822749f79eaa55d15af13c7bc5ff683916b5ee50f` |
| `d2a_archive_coverage_gate_fixtures_v1.py` | `314030b67dac31624f74cd014d7332d4b67fd1a2e250ea28e90037061903793c` |

当前source接点为recipe `verify_archive()` 中提取前inventory门、immutable小view实际绑定门、末尾complete fresh-replay门。初版历史SHA、两层fixture/receipt/report SHA和当前SHA汇于同名JSON。V1 contract/helper/recipe、root状态/main/live CSV/locks/PID/core与原science均未改。本轮不作最终full400或publication-ready声明；独审应分别绑定首版IO与本轮覆盖补充。
