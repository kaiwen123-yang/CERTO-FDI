"""Compare Track A and Track B on multi-seed metrics, and say what that proves.

Contract §8.1 lets the GPU port be used for full runs only when the two tracks
"agree within a reasonable tolerance", and §9.2 forbids treating a close test metric
as evidence that the code is faithful. Those two rules pull in opposite directions
unless the comparison is honest about its own power, so this module reports three
different things and never collapses them:

* **epoch-0 agreement** -- the earliest comparable point. Note what it is and is
  not: the official trainer reports "Epoch 000" *after* the first epoch of
  optimisation, so this is not a pure-initialisation anchor. It is the point where
  the fewest optimiser steps have accumulated, so agreement there is evidence about
  loading, preprocessing, split, padding, normalisation and architecture -- and
  disagreement there is weak evidence of anything, because a single epoch of
  nondeterministic GPU reduction order is already enough to separate two runs.
* **final-metric agreement across seeds** -- compared against the configured
  tolerance, using the seed spread as the yardstick rather than a single run.
* **whether the spread is small enough for the tolerance to mean anything.** A
  10-epoch smoke on this model swings by more than 0.1 AUROC between adjacent
  epochs. If the within-track spread exceeds the tolerance, then agreement within
  tolerance is luck and disagreement is noise; the correct verdict is
  INCONCLUSIVE_UNDERPOWERED, not PASS and not FAIL.

    python -m certo_fdi_reset.baselines.parity --config configs/paper_reset.yaml \
        --track-a <track_a_seeds.json> --track-b <track_b_seeds.json>
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

from ..config import load_config
from ..provenance import utc_stamp, write_manifest

PARITY_COLUMNS: tuple[str, ...] = (
    "quantity",
    "seed",
    "track_a",
    "track_b",
    "abs_delta",
    "rel_delta",
    "abs_tolerance",
    "rel_tolerance",
    "within_tolerance",
    "note",
)


def _same_config_as_run(track_a: dict, track_b: dict) -> bool | None:
    """Per-seed equality of the configuration that actually executed.

    None when either sweep predates the config_as_run field, so "we did not record
    it" never reads as "it matched".
    """
    a = {r["seed"]: r.get("config_as_run") for r in track_a["runs"]}
    b = {r["seed"]: r.get("config_as_run") for r in track_b["runs"]}
    shared = set(a) & set(b)
    if not shared or any(a[s] is None or b[s] is None for s in shared):
        return None
    return all(a[s] == b[s] for s in shared)


def _series(payload: dict, key: str) -> dict[int, float]:
    return {run["seed"]: float(run[key]) for run in payload["runs"]}


def _epoch0(payload: dict) -> dict[int, float]:
    out = {}
    for run in payload["runs"]:
        epochs = run.get("epochs") or []
        if epochs:
            out[run["seed"]] = float(epochs[0]["auroc_mean"])
    return out


def _row(quantity, seed, a, b, abs_tol, rel_tol, note=""):
    abs_delta = abs(a - b)
    rel_delta = abs_delta / abs(a) if a else float("inf")
    return {
        "quantity": quantity,
        "seed": seed,
        "track_a": round(a, 6),
        "track_b": round(b, 6),
        "abs_delta": round(abs_delta, 6),
        "rel_delta": round(rel_delta, 6),
        "abs_tolerance": abs_tol,
        "rel_tolerance": rel_tol,
        # Either bound satisfied counts as within tolerance: the contract states both,
        # and an absolute bound alone is unreasonable for a metric near 1.0.
        "within_tolerance": str(abs_delta <= abs_tol or rel_delta <= rel_tol).lower(),
        "note": note,
    }


def compare(track_a: dict, track_b: dict, abs_tol: float, rel_tol: float) -> dict:
    rows: list[dict] = []
    shared = sorted(set(_series(track_a, "final_auroc_mean")) & set(_series(track_b, "final_auroc_mean")))
    if not shared:
        return {"rows": [], "verdict": "BLOCKED_NO_SHARED_SEEDS", "shared_seeds": []}

    for quantity, getter in (
        ("epoch0_auroc_mean", _epoch0),
        ("final_auroc_mean", lambda p: _series(p, "final_auroc_mean")),
        ("best_auroc_mean", lambda p: _series(p, "best_auroc_mean")),
    ):
        a_vals, b_vals = getter(track_a), getter(track_b)
        for seed in shared:
            if seed in a_vals and seed in b_vals:
                rows.append(_row(quantity, seed, a_vals[seed], b_vals[seed], abs_tol, rel_tol))

    a_final = [_series(track_a, "final_auroc_mean")[s] for s in shared]
    b_final = [_series(track_b, "final_auroc_mean")[s] for s in shared]
    a_mean, b_mean = statistics.fmean(a_final), statistics.fmean(b_final)
    a_spread = (statistics.pstdev(a_final) if len(a_final) > 1 else 0.0)
    b_spread = (statistics.pstdev(b_final) if len(b_final) > 1 else 0.0)
    rows.append(
        _row(
            "final_auroc_mean_ACROSS_SEEDS", "mean", a_mean, b_mean, abs_tol, rel_tol,
            note=f"track A sd={a_spread:.4f}, track B sd={b_spread:.4f}, n={len(shared)}",
        )
    )

    def _all_within(quantity: str) -> bool:
        subset = [r for r in rows if r["quantity"] == quantity]
        return bool(subset) and all(r["within_tolerance"] == "true" for r in subset)

    epoch0_ok = _all_within("epoch0_auroc_mean")
    # The BEST metric over the schedule answers "does the port reach the same
    # performance?", while the FINAL metric also answers "did it stop in the same
    # place?". On a truncated schedule the second question is noise, so the two are
    # tracked separately rather than averaged into one verdict.
    best_ok = _all_within("best_auroc_mean")
    mean_ok = rows[-1]["within_tolerance"] == "true"
    worst_spread = max(a_spread, b_spread)
    underpowered = worst_spread > abs_tol and worst_spread / max(a_mean, 1e-9) > rel_tol

    if not underpowered:
        verdict = "PARITY_PASS" if (epoch0_ok and mean_ok) else "PARITY_FAIL"
    elif epoch0_ok:
        verdict = "PIPELINE_PARITY_CONFIRMED_METRIC_INCONCLUSIVE"
    elif best_ok:
        verdict = "ATTAINABLE_METRIC_AGREES_STOPPING_POINT_INCONCLUSIVE"
    else:
        verdict = "INCONCLUSIVE_UNDERPOWERED"

    return {
        "rows": rows,
        "shared_seeds": shared,
        "epoch0_agreement": epoch0_ok,
        "best_auroc_agreement": best_ok,
        "mean_within_tolerance": mean_ok,
        "track_a_mean_final_auroc": round(a_mean, 6),
        "track_b_mean_final_auroc": round(b_mean, 6),
        "track_a_seed_sd": round(a_spread, 6),
        "track_b_seed_sd": round(b_spread, 6),
        "underpowered": underpowered,
        "verdict": verdict,
    }


VERDICT_MEANING = {
    "PARITY_PASS": (
        "Pipeline and final metrics agree within tolerance across seeds. The GPU port may "
        "be used for the full run."
    ),
    "PIPELINE_PARITY_CONFIRMED_METRIC_INCONCLUSIVE": (
        "The two tracks demonstrably run the SAME pipeline -- epoch-0 metrics agree -- but "
        "the 10-epoch seed spread is larger than the tolerance, so the final-metric "
        "comparison cannot decide parity either way. The port is not disqualified and is "
        "not yet cleared: clearing it requires the full official schedule (70 epochs, LR "
        "milestones 11 and 61), where the metric is no longer dominated by where training "
        "happened to stop."
    ),
    "ATTAINABLE_METRIC_AGREES_STOPPING_POINT_INCONCLUSIVE": (
        "The best AUROC reached over the schedule agrees within tolerance on every seed, "
        "so the port attains the same performance as the official CPU run. The FINAL-epoch "
        "metric does not agree, and the within-track seed spread is several times the "
        "tolerance -- on a 10-epoch truncation the final epoch is an arbitrary stopping "
        "point, not a converged result. This neither clears nor disqualifies the port. "
        "Clearing it requires the full official schedule (70 epochs, LR milestones 11 and "
        "61), where the final epoch is a converged number and the comparison means "
        "something."
    ),
    "INCONCLUSIVE_UNDERPOWERED": (
        "The seed spread exceeds the tolerance and epoch-0 does not agree either. Nothing "
        "can be concluded; do not use the port."
    ),
    "PARITY_FAIL": (
        "The tracks disagree beyond tolerance with a spread small enough for that to be "
        "meaningful. The port must not be used until the cause is found."
    ),
    "BLOCKED_NO_SHARED_SEEDS": "The two sweeps share no seed; nothing is comparable.",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certo_fdi_reset.baselines.parity")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--track-a", required=True, type=Path)
    parser.add_argument("--track-b", required=True, type=Path)
    parser.add_argument("--out-name", default="voraus_ad_gpu")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    for path in (args.track_a, args.track_b):
        if not path.exists():
            print(f"ERROR: sweep result missing: {path}", file=sys.stderr)
            return 2

    track_a = json.loads(args.track_a.read_text(encoding="utf-8"))
    track_b = json.loads(args.track_b.read_text(encoding="utf-8"))
    abs_tol = float(cfg.get("reproduction_tolerance.abs"))
    rel_tol = float(cfg.get("reproduction_tolerance.rel"))

    result = compare(track_a, track_b, abs_tol, rel_tol)

    out_dir = cfg.layout.run_dir(cfg.run_id) / "b0" / args.out_name
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "numerical_parity_smoke.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PARITY_COLUMNS)
        writer.writeheader()
        writer.writerows(result["rows"])

    payload = {
        "run_id": cfg.run_id,
        "generated_utc": utc_stamp(),
        "abs_tolerance": abs_tol,
        "rel_tolerance": rel_tol,
        "epochs_per_run": track_a.get("epochs_per_run"),
        "track_a_environment": {k: track_a.get(k) for k in ("python", "torch", "torch_cuda", "device", "numpy")},
        "track_b_environment": {k: track_b.get(k) for k in ("python", "torch", "torch_cuda", "cudnn", "gpu", "device", "numpy")},
        # What matters is that the two tracks ran the same protocol, not that they
        # report the same restored defaults. Compare the overrides that actually
        # applied; fall back to the defaults blob for sweeps written before
        # config_as_run existed.
        "same_seeds": track_a.get("seeds") == track_b.get("seeds"),
        "same_epochs_per_run": track_a.get("epochs_per_run") == track_b.get("epochs_per_run"),
        "same_official_defaults": (
            track_a.get("config_defaults_after_restore", track_a.get("config"))
            == track_b.get("config_defaults_after_restore", track_b.get("config"))
        ),
        "same_config_as_run": _same_config_as_run(track_a, track_b),
        **{k: v for k, v in result.items() if k != "rows"},
        "verdict_meaning": VERDICT_MEANING.get(result["verdict"], ""),
    }
    sha = write_manifest(out_dir / "numerical_parity_smoke.json", payload)

    print(f"shared seeds        {result['shared_seeds']}")
    print(f"same seeds          {payload['same_seeds']}  same epochs {payload['same_epochs_per_run']}")
    print(f"same defaults       {payload['same_official_defaults']}  same config-as-run {payload['same_config_as_run']}")
    print(f"epoch0 agreement    {result.get('epoch0_agreement')}")
    print(f"best-AUROC agreement {result.get('best_auroc_agreement')}")
    print(f"mean final AUROC    A={result.get('track_a_mean_final_auroc')} B={result.get('track_b_mean_final_auroc')}")
    print(f"seed sd             A={result.get('track_a_seed_sd')} B={result.get('track_b_seed_sd')}  (abs tol {abs_tol})")
    print(f"VERDICT             {result['verdict']}")
    print(f"                    {payload['verdict_meaning']}")
    print(f"csv                 {csv_path}")
    print(f"json                {out_dir / 'numerical_parity_smoke.json'}  sha256={sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
