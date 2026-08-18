# Resume contract — provenance

This directory freezes the **resume** contract received after the operator mounted
`G:` by hand. It is subordinate to `contracts/paper_reset/`, which stays the
authority.

## Source

| field | value |
| --- | --- |
| archive | `CERTO_FDI_PAPER_RESET_RESUME_AFTER_G_MOUNT_20260818.zip` |
| archive sha256 | `770514d1dce3f44e7347501049f4b4d5b12ae4ab85fcf3098768b795db2ddab0` |
| archive size | 16,352 B |
| found at | `/mnt/c/Users/ykw/Downloads/` (searched: cwd, `~/Downloads`, `~/Desktop`, `/mnt/c/Users/*/{Downloads,Desktop}`, `/mnt/g/CERTO-FDI/00_inbox`) |
| `unzip -t` | `No errors detected in compressed data` |
| inner `SHA256SUMS.txt` | 3/3 OK (`sha256sum -c`) |
| extracted to | `/tmp/certo_paper_reset_resume_20260818T163916Z/` |
| loose master prompt beside the ZIP | byte-identical, sha256 `8d96270980fab93bb5a4ac36632d7a2f6e1742c1c68dd080884fd0354f8121a6` |

## Renaming

Files are stored under stable ordinals so the tree hash is order-stable. The
shipped names and hashes are kept verbatim in `SHA256SUMS_AS_SHIPPED.txt`:

| in-repo | as shipped |
| --- | --- |
| `00_README.md` | `README.md` |
| `01_RESUME_MASTER_PROMPT.md` | `CERTO_FDI_PAPER_RESET_RESUME_AFTER_G_MOUNT_MASTER_PROMPT_20260818.md` |
| `02_ONE_SHOT_LAUNCHER.md` | `ONE_SHOT_LAUNCHER.md` |

## Precedence (resume prompt §2)

1. The frozen `contracts/paper_reset/` documents win on any conflict.
2. This resume prompt only adds *current progress, discovered facts, and
   execution order*.
3. It may **not** relax an original threshold. None of the thresholds in
   `configs/paper_reset.yaml` changed, and `src/certo_fdi_reset/decision.py`
   stays at v1.0.0, blob `b9364975aa80efcf3d77e32ccd6a165c3ae66909`.

## Head-mismatch gate (resume prompt §1.1)

The resume prompt cites remote HEAD `8edec2729d2ec243a584fc1fc7712a2a1046d038`.
The actual head at resume time was `87bf3e4aa0f80f609e737ee0349b452c3d9fff7a`.
§1.1 requires `BLOCKED_PROTOCOL_HEAD_MISMATCH` only when the scientific contract,
decision thresholds, data splits, or baseline definitions moved. Checked:

```text
git diff --stat 8edec27..87bf3e4 -- contracts/ src/certo_fdi_reset/decision.py \
    configs/ docs/paper_reset/PROTOCOL_FREEZE.md
(empty)
```

`decision.py` is the same blob at both commits. The 13 files that did change are
tooling, tests and new-phase code (`storage_migration.py`, `datasets/d0.py`,
`datasets/probe.py`, `literature/fulltext.py`, `literature/cards.py`,
`baselines/smoke_record.py`, `provenance_report.py`, their tests, the Makefile).

**Verdict: gate PASSES, recorded, not blocked.**
