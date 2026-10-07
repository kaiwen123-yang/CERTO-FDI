# D2-a actual-ZIP witness IO bridge v1

2026-10-07。**有限 IO 修复和真实小 ZIP fixture 通过；未构建完整科学包、未读大 jets、未执行 R1 bootstrap 或科学重放。当前 `scientific_ready=false`。** 本报告是原 `full_d2a_release_contract_v1.md/.json` 的限定补充，不改其历史状态或 SHA。

## 修复边界

原 metadata helper 在逐 case replay 清理后，无法再通过 filesystem `is_file()` 确认所有 witness。新组件 `d2a_archive_witness_view_v1.py` 提供两个 backend：默认 filesystem 保持原 contained `is_file()` 语义；actual ZIP backend 要求真实 central-directory member、实际 uncompressed size、绑定 receipt SHA 与已校验 manifest SHA 映射一致。

ZIP backend **不打开 witness body，不校验其内容 SHA 或科学算术**。它拒绝缺 member、缺 manifest mapping、错误 manifest 外部 SHA、receipt/mapping SHA 不符、member/receipt/manifest size 不符、unsafe 或 Windows 非法 namespace、case/witness 文件名不符、casefold duplicate、symlink/encrypted member、索引后文件身份变动。其 receipt 明示 `witness_payload_hash_verified=false`、`scientific_arithmetic_verified=false`。相同大小的坏 body 可以通过 presence，fixture 特意证明这个范围；完整 body hash 和算术仍必须在后续科学链实际通过。

新 `d2a_full_grid_acceptance_v2.py` 仅替换 witness availability 的 IO，加 optional ZIP 参数及范围字段；原 coverage、physical、risk、mean AST 绑定、alias 与 first-certified-grid 逻辑保留。`check_completed()` 从原 artifact entry 的 bytes 和当前 bound row 的 witness SHA 向 backend 提供绑定。没有 dummy gzip 或原 worktree fallback。

## recipe v2 的目录与调用链

新 `package_full_d2a_release_v2.py` 保留 v1，新增源清单包含 adapter 与 helper v2。`--verify-archive` 另要求调用者显式提供 `--archive-manifest-sha256`，取未来 build receipt 的真实 manifest SHA；不只依赖 ZIP 自称的 sidecar。

未来 driver 从实际 ZIP 完整读取并哈希 original small `.py/.json/.md/.csv/.sha256`（每项 ≤2 MiB），写入新 scratch 内单独的 `immutable_metadata_view`，将这些叶设只读。该 view 不含 witness gzip、原 R1 ZIP 或出版 PDF。它在任何 verifier 改写前运行 full-grid metadata gate；独立 replay root 只保留共享源码/R1 bootstrap 和每次一个 canonical case。该 case 的原始 payload 从 actual ZIP 新提取、每文件完整哈希，再执行原完整 `work/d2a_cert_verify.py --case-dir ...`，保存新 receipt/hash/log，最后沿 v1 原 Windows native guarded cleanup 只删这个新 scratch case。失败 case 不走成功 cleanup。

所有 case 清理后再次核原小 metadata hash，并以 real ZIP index 重跑 metadata gate。只有两个 metadata gate、每个必要 canonical case 的完整独立 verifier、所有 archive payload 完整 hash、完整400分类及零未接受失败均通过，未来分支才可能给 `PASS_ALL_CANONICAL_SCIENTIFIC_REPLAYS`。本轮只验 IO 小单元，**未执行或接受该全量分支**，也不将元数据 presence 等同科学证明。

重要入口：adapter `ZipWitnessView.available()`；helper `check_completed()`/`SmallReader.witness_available()`；recipe `extract_immutable_metadata_view()`/`metadata_gate()`/`verify_archive()`。paper publication bindings 仍由未来 explicit freeze 选择，不硬编码 R6/R7/R8。

## 实际小单元验收

实际执行 `python -S -B -X utf8 outputs/d2a_archive_view_bridge_fixtures_v1.py`，**30 checks、0 failures**，收据 `d2a_archive_view_bridge_fixture_results_v1.json`。fixture 建立真实 ZIP，tiny witness member 为46字节；availability 的 spy 确认没有打开 witness body。没有真实大 witness、R1 或 science执行。

包括 missing-member/missing-mapping/bad-manifest/receipt-SHA/real-size/unsafe-namespace/Windows alias/case-name 拒绝；filesystem 与 v1 一致；原 helper self-test 一致；从 actual ZIP 真实提取小 metadata、Windows readonly 属性；独立 replay receipt 改写及 tiny witness 实际移除后，original metadata bytes/hash不变，presence仍依实际ZIP成立。fixture 仅移除了自己新建目录的一份 tiny文件，没有科学 case cleanup执行。

## 冻结的本轮源 SHA256

| 文件 | SHA256 |
|---|---|
| `d2a_archive_witness_view_v1.py` | `7f566d7251ea3077b261b496d93a7469db8d502b6523be8393d3f088b760e637` |
| `d2a_full_grid_acceptance_v2.py` | `25703242972718b3a3fd6f924dacc5dd1c67b03a51518d74aa5a882412d3ab15` |
| `package_full_d2a_release_v2.py` | `1c6ecc8e5cd6323c488e3c584e74199a8a64a3c224788cd23e392b82a6ab5307` |
| `d2a_archive_view_bridge_fixtures_v1.py` | `5f262131a8d111cb233707428a695e5b3443565c46328e2965483d5f223b4961` |

fixture 收据同时绑定未变的 v1 helper `679747ac...`、v1 recipe `cae0b2d2...`、v1 contract md `d633636c...`/json `b822b2aa...`，完整 SHA 在本报告 JSON 中。root 状态、主稿、live CSV/锁/PID/core 与原 scientific payload 均不在本轮写入范围。
