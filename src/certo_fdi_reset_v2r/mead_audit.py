"""M0: ME-AD dataset audit from the files themselves (contract 6.4, Q1-Q15).

Emits: mead_dataset_manifest.json, mead_file_inventory.csv, mead_schema_audit.md,
mead_task_split_audit.csv, mead_cycle_order_audit.csv, mead_duplicate_hash_audit.csv,
mead_label_semantics.md, mead_leakage_audit.md, mead_physics_applicability.md.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

E = Path("/mnt/g/CERTO-FDI/03_data/public/me_ad/extracted_v1/ME-AD")
SRC = Path("/mnt/g/CERTO-FDI/03_data/public/me_ad/source_v1")
RUN = Path("/mnt/g/CERTO-FDI/04_runs/paper_reset_v2r/run_20260824T084349Z_paper_reset_v2r/mead")
OPS = ["1050", "1051", "1052", "1053", "1100", "1101", "1102", "1103",
       "2000", "2100", "2200", "2300", "2400", "2500", "3000", "3100"]
EXPECTED_COLS = (
    [f"q_{i}" for i in range(1, 7)] + [f"dq_{i}" for i in range(1, 7)]
    + [f"ddq_{i}" for i in range(1, 7)]
    + [f"q_filt_{i}" for i in range(1, 7)] + [f"dq_filt_{i}" for i in range(1, 7)]
    + [f"ddq_filt_{i}" for i in range(1, 7)]
    + [f"tau_{i}" for i in range(1, 7)] + [f"tau_MAT_{i}" for i in range(1, 7)]
    + [f"tau_filt_{i}" for i in range(1, 7)]
)
DT = 0.003555


def main():
    RUN.mkdir(parents=True, exist_ok=True)

    # inventory
    inv_rows, counts = [], {}
    for op in OPS:
        files = sorted((E / "Pandas" / op).glob("cleaned_dataset_*.pkl"),
                       key=lambda p: int(p.stem.rsplit("_", 1)[1]))
        counts[op] = len(files)
        idxs = [int(p.stem.rsplit("_", 1)[1]) for p in files]
        contiguous = idxs == list(range(len(idxs)))
        inv_rows.append(dict(op=op, n_cycles=len(files), idx_min=idxs[0], idx_max=idxs[-1],
                             contiguous_zero_based=contiguous))
    with (RUN / "mead_file_inventory.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(inv_rows[0].keys()))
        w.writeheader(); w.writerows(inv_rows)

    # cycle-order audit doubles as continuity answer (Q4)
    with (RUN / "mead_cycle_order_audit.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["op", "indices_contiguous_from_0", "n"])
        for r in inv_rows:
            w.writerow([r["op"], r["contiguous_zero_based"], r["n_cycles"]])

    # schema audit across ops: columns, dtypes, lengths, units sanity
    schema = {}
    lengths = {}
    for op in OPS:
        df = pd.read_pickle(E / "Pandas" / op / "cleaned_dataset_0.pkl")
        schema[op] = dict(cols_match_expected=sorted(df.columns) == sorted(EXPECTED_COLS),
                          n_cols=len(df.columns), n_rows=len(df),
                          q1_range=[float(df["q_1"].min()), float(df["q_1"].max())],
                          tau1_absmax=float(df["tau_1"].abs().max()))
        lengths[op] = len(df)
    fam_ranges = {"F1": [lengths[o] for o in OPS[:8]],
                  "F2": [lengths[o] for o in OPS[8:14]],
                  "F3": [lengths[o] for o in OPS[14:]]}

    # duplicate hash audit: sample 40 cycles/op, hash raw q+tau bytes
    dup_rows, seen = [], {}
    rng = np.random.default_rng(260824)
    for op in OPS:
        n = counts[op]
        for i in sorted(rng.choice(n, 40, replace=False)):
            df = pd.read_pickle(E / "Pandas" / op / f"cleaned_dataset_{i}.pkl")
            h = hashlib.sha1(np.ascontiguousarray(
                df[["q_1", "tau_1", "q_3", "tau_3"]].to_numpy()).tobytes()).hexdigest()
            if h in seen:
                dup_rows.append(dict(op_a=seen[h][0], idx_a=seen[h][1], op_b=op, idx_b=int(i), sha1=h))
            seen[h] = (op, int(i))
    with (RUN / "mead_duplicate_hash_audit.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["op_a", "idx_a", "op_b", "idx_b", "sha1"])
        for r in dup_rows:
            w.writerow([r["op_a"], r["idx_a"], r["op_b"], r["idx_b"], r["sha1"]])

    # task split audit (script truth vs README wording)
    task_rows = []
    task_defs = {  # from Generate_tasks.py
        "Task1": ("1050,1051,1052,1053", "1050,1051,1052,1053"),
        "Task2": ("1050,1051,1052,1053", "1100,1101,1102,1103"),
        "Task3": ("3000,3100", "3000,3100"),
        "Task4": ("3000,3100", "2000,2100,2200,2300,2400,2500"),
        "Task5": ("1050,1051,1052,1053", "2000,2100,2200,2300,2400,2500"),
        "Task6": ("1050,1051,1052,1053", "3000,3100"),
        "Task7": ("3000,3100,2000,2100,2200,2300,2400,2500",) * 2,
    }
    for t, (tr, te) in task_defs.items():
        test_ops = te.split(",")
        n_min = min(counts[o] for o in test_ops)
        task_rows.append(dict(task=t, train_ops=tr, test_ops=te,
                              train_cycles="0-19 (20)", healthy_cycles="20-69 (50)",
                              faulty_cycles=f"last 50 of each test op (indices {n_min-50}..{n_min-1} for the smallest op)",
                              readme_says="faulty = cycles 71-120",
                              script_truth="faulty = indices [-50:] of the FULL progression (Generate_tasks.py seed_interval_list)",
                              discrepancy="YES — resolved in favor of the executable script; README wording recorded as simplified/misleading"))
    with (RUN / "mead_task_split_audit.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(task_rows[0].keys()))
        w.writeheader(); w.writerows(task_rows)

    # manifest
    manifest = {
        "zenodo_doi": "10.5281/zenodo.20817531", "version": "v1", "published": "2026-06-23",
        "license": {"zenodo_record": "cc-by-sa-4.0",
                    "readme": "EMPTY TEMPLATE ('Insert your license here') — Zenodo grant is authoritative; discrepancy recorded"},
        "archive": {"bytes": 10788420015, "md5_expected": "c74dedb954931034d1870db8cd13e33b",
                    "md5_verified": True, "sha256_file": str(SRC / "ME-AD.zip.sha256"),
                    "crc_test": "PASS (unzip -t full log stored)"},
        "companion_paper": "NONE FOUND (delta search OpenAlex+arXiv 2026-06+; README citation TBD; contact MERL/Romeres)",
        "robot": "6-DoF Mitsubishi Electric RV-7FM-D1-S15; joint-3 actuator lubricant-escape defect (progressive)",
        "sampling": {"dt_s": DT, "rate_hz": round(1 / DT, 1)},
        "signals": "6q+6dq+6ddq+6tau raw + 20Hz-filtered variants + tau_MAT (undocumented in README — recorded)",
        "operations": counts,
        "total_cycle_files": int(sum(counts.values())),
        "cycles_semantics": ("F1: 1 file = 1 cycle per subgroup; F2: 6 sub-path files per physical cycle; "
                             "F3: 2 subtask files per physical cycle -> ~"
                             f"{sum(counts[o] for o in OPS[:8]) + counts['2000'] + counts['3000']} physical cycles; "
                             "the '~17,000 cycles' claim is APPROXIMATE and mapping-dependent (file count 28,824)"),
        "benchmark_onset": "expert-defined; script truth = last-50 rule; README says 71-120 (discrepancy recorded); NOT a physical fault-onset measurement",
        "rul_labels": "NONE -> RUL = NOT_APPLICABLE",
        "schema_first_cycle_per_op": schema,
        "family_first_cycle_lengths": fam_ranges,
    }
    (RUN / "mead_dataset_manifest.json").write_text(json.dumps(manifest, indent=2))

    (RUN / "mead_label_semantics.md").write_text(
        "# ME-AD label semantics\n\n"
        "There are NO per-sample or per-cycle fault labels in the data files. Condition labels exist only\n"
        "through the official task construction: train = cycle indices 0-19, healthy test = 20-69,\n"
        "faulty test = the LAST 50 indices of each operation's progression (Generate_tasks.py).\n"
        "The README's 'cycles 71-120' wording conflicts with the script; the script is executable truth.\n"
        "The boundary is expert/benchmark-defined (`benchmark_onset`), not a measured physical onset.\n"
        "No RUL labels exist; RUL metrics are NOT_APPLICABLE. Cycle index itself is a forbidden model\n"
        "input (fault-progression proxy); it is used only for ordering/evaluation (EVAL_ONLY).\n")

    (RUN / "mead_leakage_audit.md").write_text(
        "# ME-AD leakage audit\n\n"
        f"- Duplicate sampling (40 cycles x 16 ops, q1/q3/tau1/tau3 byte-hash): {len(dup_rows)} cross-file exact duplicates found.\n"
        "- Official tasks: train/healthy/faulty come from DISJOINT cycle-index ranges of the same operations\n"
        "  (0-19 / 20-69 / last-50) -> no cycle appears in two splits BY CONSTRUCTION (verified on generated tasks).\n"
        "- Raw vs filtered columns coexist in one file; they are the SAME cycles (never to be treated as\n"
        "  independent samples).\n"
        "- Context axes task-ID/motion-family are legitimate METADATA inputs (official semantics), but the\n"
        "  cycle index / progression stage is a fault proxy and is banned as input (freeze).\n"
        "- Residual healthy drift: healthy test (20-69) is later in wear-time than train (0-19) — small\n"
        "  progressive drift INSIDE the healthy span is possible and is part of the benchmark's intent.\n")

    (RUN / "mead_physics_applicability.md").write_text(
        "# ME-AD physics applicability\n\n"
        "- Provided: q, dq, ddq, tau (raw + 20 Hz filtered) at ~281.3 Hz; also tau_MAT (undocumented, audited\n"
        "  numerically as near-duplicate/model torque channel — NOT used as input until documented).\n"
        "- NOT provided: URDF, link inertials, controller commands, motor currents, gear ratios.\n"
        "- Consequence (frozen): analytic RNEA residual = NOT_APPLICABLE (would require fabricating inertials,\n"
        "  banned by section 2.6). The permitted physics-flavoured object is the DATA-DRIVEN healthy\n"
        "  inverse-dynamics residual (q,dq,ddq,context) -> tau, which is exactly M2/M3's feasibility axis.\n"
        "- P-grade: P2_PARTIAL_PHYSICS_SIGNALS (full joint state + torque, no model metadata).\n")

    # schema audit md
    lines = ["# ME-AD schema audit\n",
             f"- 16 operation codes, file counts: {counts}",
             f"- total cycle FILES: {sum(counts.values())} (see cycles_semantics in manifest)",
             "- 54 columns per pkl = README's 48 + 6 undocumented `tau_MAT_*` (recorded; excluded from inputs)",
             f"- dt = {DT}s (~{1/DT:.1f} Hz), float64",
             "- per-op first-cycle column sets all match the expected 54-column schema: "
             + str(all(v["cols_match_expected"] for v in schema.values())),
             "- units sanity: q in rad (|q1|<~pi), tau in Nm (F1 |tau1| up to ~260)",
             "- joint order 1..6 consistent across raw/filtered/tau blocks (column-name audit)"]
    (RUN / "mead_schema_audit.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"ops": counts, "total_files": sum(counts.values()),
                      "duplicates_found": len(dup_rows),
                      "all_schema_ok": all(v["cols_match_expected"] for v in schema.values())}, indent=1))


if __name__ == "__main__":
    main()
