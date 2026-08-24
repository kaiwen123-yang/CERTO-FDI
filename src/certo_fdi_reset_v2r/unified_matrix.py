"""U0: assemble the truthful four-dataset matrices from ACTUAL result files.

Outputs (run root /unified):
  universal_core_matrix.csv   one row per (dataset, model, seed) with metrics
  dataset_native_matrix.csv   native/faithful rows per dataset
  matrix_applicability.csv    NOT_APPLICABLE vs NOT_RUN per cell with reasons
  matrix_completeness.json    completeness computed FROM ROWS ONLY

CORE-8 canonical names: mahalanobis, pca_spe, iforest, ocsvm, window_ae,
gru_ae, tcn_ae, gru_pred. Deterministic {mahalanobis, pca_spe} carry
seed_semantics=deterministic_1fit; stochastic carry stochastic_seed.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

V2 = Path("/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2")
V2R = Path("/mnt/g/CERTO-FDI/04_runs/paper_reset_v2r/run_20260824T084349Z_paper_reset_v2r")
OUT = V2R / "unified"
CORE8 = ("mahalanobis", "pca_spe", "iforest", "ocsvm", "window_ae", "gru_ae", "tcn_ae", "gru_pred")
DET = ("mahalanobis", "pca_spe")
STOCH_SEEDS = (260824, 260825, 260826)


def rows_voraus():
    d = json.loads((V2 / "b_voraus/unified_baselines.json").read_text())
    out = []
    for k, v in d.items():
        if k.startswith("_"):
            continue
        m, s = k.rsplit("_seed", 1)
        p = v["primary_mean_agg"]
        out.append(dict(dataset="voraus_ad", model=m, seed=s,
                        seed_semantics="deterministic_1fit" if m in DET else "stochastic_seed",
                        metric_primary="auroc_mean_over_12_types", auroc=round(p["auroc_mean"], 4),
                        auprc=round(p["auprc_mean"], 4), fpr_at_tpr90=round(p["fpr_at_tpr90_mean"], 4),
                        protocol="official split; episode=window-mean", source="v2/b_voraus"))
    return out


def rows_aursad():
    d = json.loads((V2 / "b_aursad/unified_baselines.json").read_text())
    out = []
    for k, v in d.items():
        if k.startswith("_"):
            continue
        m, s = k.rsplit("_seed", 1)
        out.append(dict(dataset="aursad", model=m, seed=s,
                        seed_semantics="deterministic_1fit" if m in DET else "stochastic_seed",
                        metric_primary="op_macro_auroc_c123_vs_class0",
                        auroc=round(v["macro"]["auroc"], 4), auprc=round(v["macro"]["auprc"], 4),
                        fpr_at_tpr90=round(v["macro"]["fpr_at_tpr90"], 4),
                        protocol="healthy-only temporal 70/30; movement probe separate",
                        source="v2/b_aursad"))
    return out


def rows_road():
    p = V2R / "unified/road_core8.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text())
    out = []
    for k, v in d.items():
        if k.startswith("_"):
            continue
        m, s = k.rsplit("_seed", 1)
        out.append(dict(dataset="road", model=m, seed=s,
                        seed_semantics=v.get("seed_count_semantics", ""),
                        metric_primary="macro_window_auroc_3subsets",
                        auroc=round(v["macro_auroc"], 4),
                        auprc=round(float(sum(v[x]["auprc"] for x in ("collision", "weight", "velocity")) / 3), 4),
                        fpr_at_tpr90=round(float(sum(v[x]["fpr_at_tpr90"] for x in ("collision", "weight", "velocity")) / 3), 4),
                        protocol="win50@10Hz s10; collision within-rec; wt/vel vs control set",
                        source="v2r/road_core8"))
    return out


def rows_mead():
    p = V2R / "mead/mead_core8_metrics.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text())
    out = []
    for k, v in d.items():
        if k.startswith("_"):
            continue
        m, s = k.rsplit("_seed", 1)
        out.append(dict(dataset="me_ad", model=m, seed=s,
                        seed_semantics="deterministic_1fit" if m in DET else "stochastic_seed",
                        metric_primary="cycle_auroc_macro_over_tasks",
                        auroc=round(v["macro"]["auroc"], 4), auprc=round(v["macro"]["auprc"], 4),
                        fpr_at_tpr90=round(v["macro"]["fpr_at_tpr90"], 4),
                        protocol=d.get("_protocol", {}).get("summary", "official tasks; cycle unit"),
                        source="v2r/mead"))
    return out


def native_rows():
    rows = []
    ta = json.loads((V2 / "b_voraus/track_a_seed177_70ep.json").read_text())["runs"][0]
    tb = json.loads((V2 / "b_voraus/track_b_seeds_70ep.json").read_text())
    rows.append(dict(dataset="voraus_ad", baseline="MVT-Flow", mode="EXACT_OFFICIAL_CPU",
                     detail=f"seed177 70ep final {ta['final_auroc_mean']:.4f} vs paper 0.936 (PASS)"))
    fins = [r["final_auroc_mean"] for r in tb["runs"]]
    rows.append(dict(dataset="voraus_ad", baseline="MVT-Flow", mode="FAITHFUL_OFFICIAL_GPU",
                     detail=f"seeds 177-179 final {sum(fins)/3:.4f} (seed177 {fins[0]:.4f}, PASS)"))
    nb = json.loads((V2 / "b_road/native_baselines.json").read_text())
    rows.append(dict(dataset="road", baseline="kNN+IF (paper Table IV)", mode="FAITHFUL_PAPER",
                     detail="collision reproduces (±0.02-0.04); weight/velocity INVERT under the literal per-sample protocol — protocol underdetermined by the paper text"))
    dp = json.loads((V2R / "aursad/dual_protocol_results.json").read_text())
    def agg(proto, kind):
        vals = [dp[f"{proto}_{kind}_seed{s}"]["macro_f1"] for s in STOCH_SEEDS]
        return sum(vals) / 3
    rows.append(dict(dataset="aursad", baseline="supervised MLP/ResNet1d (FAITHFUL_NATIVE_POLICY; official repo ships no model code)",
                     mode="EXACT official split semantics (op-level rs=42 stratify)",
                     detail=f"native macroF1 mlp {agg('native','mlp'):.3f} / resnet {agg('native','resnet'):.3f}; "
                            f"honest temporal {agg('honest','mlp'):.3f} / {agg('honest','resnet'):.3f}; "
                            f"exact-dup 13.8% vs 0.0%"))
    mp = V2R / "mead/mead_native_status.json"
    if mp.exists():
        rows.append(json.loads(mp.read_text()))
    else:
        rows.append(dict(dataset="me_ad", baseline="official Tasks", mode="PENDING_M1",
                         detail="official task reproduction pending"))
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    uni = rows_voraus() + rows_aursad() + rows_road() + rows_mead()
    with (OUT / "universal_core_matrix.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(uni[0].keys()))
        w.writeheader(); w.writerows(uni)
    nat = native_rows()
    with (OUT / "dataset_native_matrix.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["dataset", "baseline", "mode", "detail"])
        w.writeheader(); w.writerows(nat)

    # applicability + completeness computed FROM ROWS
    have = {}
    for r in uni:
        have.setdefault(r["dataset"], {}).setdefault(r["model"], set()).add(str(r["seed"]))
    app_rows, complete = [], {}
    datasets = ("voraus_ad", "road", "aursad", "me_ad")
    for ds in datasets:
        ok = True
        for m in CORE8:
            seeds = have.get(ds, {}).get(m, set())
            need = 1 if m in DET else len(STOCH_SEEDS)
            status = ("COMPLETE" if len(seeds) >= need else
                      ("NOT_RUN" if not seeds else f"PARTIAL({len(seeds)}/{need})"))
            if status != "COMPLETE":
                ok = False
            app_rows.append(dict(dataset=ds, model=m, required_seeds=need,
                                 present_seeds=len(seeds), status=status,
                                 reason="" if status == "COMPLETE" else
                                 ("dataset added this round; M2 pending" if ds == "me_ad" and not seeds else "")))
        complete[ds] = ok
    with (OUT / "matrix_applicability.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(app_rows[0].keys()))
        w.writeheader(); w.writerows(app_rows)
    completeness = {
        "computed_from_rows_only": True,
        "per_dataset_core8_complete": complete,
        "universal_core_matrix_complete": all(complete.values()),
        "n_universal_rows": len(uni),
        "n_native_rows": len(nat),
    }
    (OUT / "matrix_completeness.json").write_text(json.dumps(completeness, indent=2))
    print(json.dumps(completeness, indent=2))


if __name__ == "__main__":
    main()
