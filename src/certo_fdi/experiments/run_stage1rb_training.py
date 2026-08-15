"""Stage 1R-B Phase C3/D: final training + evaluation of every job (resumable, one JSON per job).

Primary models use their healthy-validation-selected configuration (stage1rb_tuning_selection.json);
diagnostics reuse the PR #2 schedule. Jobs: models x fractions {0.25, 1.00} x seeds {260815, 260816,
260817}. Each job is evaluated right after training (residual-only head, counterfactual localization,
qdd_true diagnostic, frame drift, latency)."""

from __future__ import annotations

import json
import time

from certo_fdi.experiments.stage1rb_common import DIAGNOSTIC_MODELS, PRIMARY_MODELS, Stage, common_parser, run_job


def job_list(cfg: dict, selection: dict, models: list[str]) -> list[tuple[str, float, int, float, str, str]]:
    tr = cfg["training"]
    jobs = []
    for name in models:
        sel = selection.get(name) if name in PRIMARY_MODELS else selection.get("_diagnostics", {}).get(name)
        if not sel or sel.get("status", "OK") != "OK":
            raise RuntimeError(f"no selected configuration for {name}")
        for frac in [float(f) for f in tr["fractions"]]:
            for seed in [int(s) for s in tr["final_seeds"]]:
                jobs.append((name, frac, seed, float(sel["lr"]), str(sel["scheduler"]), str(sel["tag"])))
    return jobs


def main(argv=None) -> int:
    ap = common_parser("Stage 1R-B final training + evaluation")
    ap.add_argument("--models", default=",".join(PRIMARY_MODELS + DIAGNOSTIC_MODELS))
    ap.add_argument("--reevaluate", action="store_true")
    args = ap.parse_args(argv)
    st = Stage(args, "training")
    if not st.require_provenance() or not st.require_r0():
        return 2
    sel_path = st.layout.results / "stage1rb_tuning_selection.json"
    if not sel_path.exists():
        st.log("BLOCKED: tuning selection missing")
        return 2
    selection = json.loads(sel_path.read_text())
    jobs = job_list(st.cfg, selection, args.models.split(","))
    runs_dir = st.layout.sub("c3_final") / "runs"
    runs_dir.mkdir(exist_ok=True)
    frame_manifest = json.loads((st.data_root / "frame_variant_manifest.json").read_text())
    st.log(f"{len(jobs)} final jobs: {sorted({j[0] for j in jobs})} fractions={sorted({j[1] for j in jobs})} seeds={sorted({j[2] for j in jobs})}")
    t0 = time.time()
    for k, (name, frac, seed, lr, sched, tag) in enumerate(jobs):
        out_json = runs_dir / f"{name}_frac{frac:.2f}_seed{seed}.json"
        if out_json.exists() and not args.reevaluate:
            continue
        st.log(f"[{k + 1}/{len(jobs)}] {name} frac={frac} seed={seed} ({tag})")
        run_job(st, name, frac, seed, lr, sched, tag, out_json, evaluate=True, full=(frac >= 1.0), frame_manifest=frame_manifest, reevaluate=args.reevaluate)
    st.log(f"training/evaluation phase done ({time.time() - t0:.0f}s)")
    st.finish()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
