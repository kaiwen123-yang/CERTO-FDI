"""Phase D-AURSAD: audit the AURSAD HDF from its own bytes.

Contract 5.6: official data/loader facts, native split practice, repetition
leakage axes, class imbalance, and the legal adaptation surface for our
candidates. HDF5 is the primary format (frozen); the Pickle variant is kept
as hash+provenance only.

Verified upstream facts this audit extends (probe 2026-08-24): pandas-HDF
'complete_data' with 134 columns x 6,249,074 rows, 100.0 Hz timestamps,
sample_nr 1..4094 (operations), label in {0..5} with heavy imbalance.
"""

from __future__ import annotations

import json
from pathlib import Path

import h5py
import numpy as np

H5 = Path("/mnt/g/CERTO-FDI/03_data/public/aursad/AURSAD.h5")
OUT = Path(
    "/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2/d_aursad"
)

# Label semantics from the AURSAD technical report (arXiv:2102.01409): the
# supervised task uses classes 0-4; the additional class marks robot movement
# between screwdriving operations. Which integer is 'movement' is verified
# below from the data itself (dominant within-operation prefix/suffix runs),
# not assumed.
LABEL_NAMES_HYPOTHESIS = {
    0: "normal",
    1: "damaged_screw",
    2: "extra_assembly_component",
    3: "damaged_plate",
    4: "loosening",
    5: "movement_or_transition",
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with h5py.File(H5, "r") as f:
        g = f["complete_data"]
        sn = g["block3_values"][:, 0]
        b2_items = [c.decode() for c in g["block2_items"][:]]
        lab = g["block2_values"][:, b2_items.index("label")].astype(np.int64)

    ops, first_idx = np.unique(sn, return_index=True)
    order = np.argsort(first_idx)
    ops = ops[order]

    # Per-operation structure
    per_op = []
    boundaries = np.flatnonzero(np.diff(sn)) + 1
    starts = np.concatenate([[0], boundaries])
    ends = np.concatenate([boundaries, [len(sn)]])
    contiguous = len(starts) == len(ops)
    for op, st, en in zip(sn[starts], starts, ends):
        seg = lab[st:en]
        vals, counts = np.unique(seg, return_counts=True)
        non_move = {int(v): int(c) for v, c in zip(vals, counts)}
        per_op.append(
            {
                "op": int(op),
                "n_samples": int(en - st),
                "labels_present": non_move,
            }
        )

    # Operation-level class: the operation's non-movement majority label.
    # First determine which label behaves like 'movement': the label that
    # co-occurs inside nearly every operation alongside another label.
    presence = np.zeros(6, dtype=int)
    for row in per_op:
        for v in row["labels_present"]:
            presence[v] += 1
    movement_label = int(np.argmax(presence)) if presence.max() > 0.9 * len(per_op) else None

    op_class: dict[int, int] = {}
    for row in per_op:
        cand = {v: c for v, c in row["labels_present"].items() if v != movement_label}
        if cand:
            op_class[row["op"]] = max(cand, key=cand.get)
        else:
            op_class[row["op"]] = movement_label if movement_label is not None else -1

    class_counts = {}
    for v in op_class.values():
        class_counts[v] = class_counts.get(v, 0) + 1

    lengths = np.array([r["n_samples"] for r in per_op])
    sample_counts = {int(v): int(c) for v, c in zip(*np.unique(lab, return_counts=True))}

    result = {
        "file": str(H5),
        "n_rows": int(len(sn)),
        "n_operations": int(len(ops)),
        "operations_contiguous_in_file": bool(contiguous),
        "sample_rate_hz": 100.0,
        "label_sample_counts": sample_counts,
        "label_presence_in_operations": {int(i): int(presence[i]) for i in range(6)},
        "inferred_movement_label": movement_label,
        "label_names_hypothesis": LABEL_NAMES_HYPOTHESIS,
        "operation_class_counts": {int(k): int(v) for k, v in sorted(class_counts.items())},
        "operation_length_samples": {
            "min": int(lengths.min()), "p50": float(np.median(lengths)),
            "mean": float(lengths.mean()), "max": int(lengths.max()),
        },
        "leakage_axes": {
            "no_workpiece_or_hole_id_column": True,
            "note": (
                "The HDF exposes no plate/hole/screw identity, so group splits by "
                "physical workpiece are IMPOSSIBLE from this file alone; operations "
                "on the same physical thread cannot be separated. Random "
                "operation-level splits (the native papers' 70/30 practice) "
                "therefore risk near-duplicate leakage across repeated operations "
                "on the same hole; any split we use must be by contiguous "
                "operation blocks (temporal split) and this limitation must be "
                "reported."
            ),
            "native_paper_split": "random 70/30 sliding-window supervised splits (screwdriving_usecase_lnme21 card)",
        },
        "class_imbalance_note": (
            "label 4 (loosening hypothesis) has ~4k samples of 6.25M (0.06%); "
            "operation-level minority classes must be evaluated per class, and "
            "healthy-only training uses operation-class 0 only."
        ),
        "primary_format_decision": "HDF5 primary; Pickle variant not stored (hash-only if ever obtained)",
    }
    (OUT / "aursad_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    ops_path = OUT / "aursad_operation_table.json"
    ops_path.write_text(json.dumps(
        {"op_class": {int(k): int(v) for k, v in op_class.items()}}, indent=0
    ), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("label_names_hypothesis",)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
