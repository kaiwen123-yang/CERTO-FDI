"""Stage 1R-B Phase C2: healthy-only fair tuning of the two primary models (contract 06 §4).

Same 8 configurations for both models (learning rate x scheduler), single tuning seed, fraction 1.0,
otherwise frozen. Selection criterion: healthy validation torque-correction RMSE (N m); if two
configurations differ by < 1 % the smaller learning rate (more stable) wins. Fault data is never
read here (only healthy train/val windows are touched)."""

from __future__ import annotations

import itertools
import json
import time

from certo_fdi.experiments.common import write_csv, write_json
from certo_fdi.experiments.stage1rb_common import PRIMARY_MODELS, Stage, common_parser, run_job


def select_config(rows: list[dict], tie_rel: float) -> dict:
    """Pick the configuration with the smallest val RMSE; within ``tie_rel`` prefer smaller lr, then cosine."""
    ok = [r for r in rows if r.get("status") == "OK" and r.get("val_healthy_rmse_nm") == r.get("val_healthy_rmse_nm")]
    if not ok:
        return {"status": "NO_VALID_CONFIG"}
    best = min(ok, key=lambda r: r["val_healthy_rmse_nm"])
    cands = [r for r in ok if r["val_healthy_rmse_nm"] <= best["val_healthy_rmse_nm"] * (1.0 + tie_rel)]
    chosen = sorted(cands, key=lambda r: (r["lr"], 0 if r["scheduler"] == "cosine" else 1))[0]
    return {"status": "OK", "lr": chosen["lr"], "scheduler": chosen["scheduler"], "tag": chosen["config_tag"], "val_healthy_rmse_nm": chosen["val_healthy_rmse_nm"], "best_val_rmse_nm": best["val_healthy_rmse_nm"], "n_candidates_within_tie": len(cands), "criterion": "healthy VAL torque-correction RMSE; ties (<1%) -> smaller lr, then cosine"}


def main(argv=None) -> int:
    ap = common_parser("Stage 1R-B healthy-only fair tuning")
    ap.add_argument("--models", default=",".join(PRIMARY_MODELS))
    args = ap.parse_args(argv)
    st = Stage(args, "tuning")
    if not st.require_provenance() or not st.require_r0():
        return 2
    tr = st.cfg["training"]
    grid = list(itertools.product([float(x) for x in tr["tuning_grid"]["learning_rate"]], list(tr["tuning_grid"]["scheduler"])))
    seed = int(tr["tuning_seed"])
    runs_dir = st.layout.sub("c2_tuning") / "runs"
    runs_dir.mkdir(exist_ok=True)
    rows = []
    t0 = time.time()
    models = args.models.split(",")
    st.log(f"tuning grid: {len(grid)} configs x {models} (seed {seed}, fraction 1.0, epochs {tr['epochs']})")
    for name in models:
        for lr, sched in grid:
            tag = f"lr{lr:g}_{sched}"
            out_json = runs_dir / f"{name}_{tag}_seed{seed}.json"
            if out_json.exists():
                res = json.loads(out_json.read_text())
            else:
                res = run_job(st, name, 1.0, seed, lr, sched, tag, out_json, evaluate=False)
            info = (res or {}).get("train_info", [{}])[0]
            rows.append({**st.base_row(model=name, seed=seed, checkpoint_sha256=info.get("checkpoint_sha256", ""), status="OK" if res else "FAILED"), "config_tag": tag, "lr": lr, "scheduler": sched, "training_fraction": 1.0, "n_train_episodes": info.get("n_train_episodes"), "epochs_run": info.get("epochs_run"), "best_val_loss": info.get("best_val_loss"), "val_healthy_rmse_nm": info.get("val_healthy_rmse_nm"), "train_seconds": info.get("train_seconds"), "n_params": info.get("n_params"), "selection_metric": "val_healthy_rmse_nm", "uses_fault_data": False})
        write_csv(st.layout.results / "stage1rb_tuning_runs.csv", rows)
    selection = {name: select_config([r for r in rows if r["model"] == name], float(tr.get("selection_tie_relative", 0.01))) for name in models}
    # diagnostics reuse the PR #2 schedule (OneCycle, lr 2e-3), documented here
    selection["_diagnostics"] = {"rnea_gru": {"lr": 2e-3, "scheduler": "onecycle", "tag": "pr2sched", "note": "reused PR #2 protocol (contract 06 §4: auxiliary models may reuse the old best configuration)"}, "ligra_free_output": {"lr": 2e-3, "scheduler": "onecycle", "tag": "pr2sched", "note": "reused PR #2 protocol"}}
    write_json(st.layout.results / "stage1rb_tuning_selection.json", selection)
    st.log(f"tuning done ({time.time() - t0:.0f}s): " + json.dumps({k: (v.get("tag"), v.get("val_healthy_rmse_nm")) for k, v in selection.items()}))
    st.finish({"selection": selection})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
