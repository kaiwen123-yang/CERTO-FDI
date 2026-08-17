"""Stage 2B-F acceptance tests over the produced run: reproduction, leakage, statistics, decision.

These read the artifacts the run actually wrote. They skip cleanly when the run root is absent, so
the suite still passes on a machine without the storage drive, but on this machine they are the
tests that decide whether the stage's claims hold.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from certo_fdi.stage2bf import estimator_identity as EI
from certo_fdi.stage2bf.decision_stage2bf import PASS_STATE, evidence_delta

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "configs" / "stage2bf_estimator_harmonization.yaml").read_text())
RUN_GLOB = sorted(Path(CFG["paths"]["run_root"]).glob("run_*")) if Path(CFG["paths"]["run_root"]).is_dir() else []
RUN = RUN_GLOB[-1] if RUN_GLOB else None
RES = (RUN / "results") if RUN else None

requires_run = pytest.mark.skipif(
    RUN is None or not (RES / "stage2bf_reproduction_gates.json").is_file(),
    reason="no Stage 2B-F run root on this machine")


def _json(name: str):
    return json.loads((RES / name).read_text())


def _csv(name: str) -> list[dict]:
    with (RES / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------ reproduction
@requires_run
def test_stage2a_ridge_reproduces_at_every_level_on_every_seed():
    g = _json("stage2bf_reproduction_gates.json")["phase2_stage2a_ridge"]
    assert g["all_pass"] is True
    for seed, s in g["per_seed"].items():
        for gate in ("join_complete_unique", "score_within_tolerance", "candidate_index_exact",
                     "window_label_exact", "episode_votes_exact", "episode_label_exact",
                     "confusion_exact", "top1_exact", "chain_distance_exact"):
            assert s[gate] is True, f"seed {seed}: {gate}"


@requires_run
def test_ridge_scores_are_bit_identical_not_merely_within_tolerance():
    """The contract permits a tolerance; the run achieved exactness, and that is worth pinning."""
    g = _json("stage2bf_reproduction_gates.json")["phase2_stage2a_ridge"]
    for seed, s in g["per_seed"].items():
        assert s["n_bit_identical"] == s["n_score_pairs"], seed
        assert s["max_abs_diff"] == 0.0, seed


@requires_run
def test_confusion_matrices_are_identical_cell_by_cell():
    for r in _csv("stage2bf_stage2a_ridge_confusion_diff.csv"):
        assert int(r["delta"]) == 0, r


@requires_run
def test_stage2b_svd_reproduces_all_five_controls():
    g = _json("stage2bf_reproduction_gates.json")["phase3_stage2b_svd"]
    assert g["all_pass"] is True
    for seed, s in g["per_seed"].items():
        assert s["window_key_order_identical"] is True, seed
        assert set(s["methods"]) == set(CFG["loadpath_controls"]), seed
        for m, v in s["methods"].items():
            for gate in ("score_within_tolerance", "rank_exact", "published_top1_exact",
                         "published_chain_distance_exact"):
                assert v[gate] is True, f"seed {seed} {m}: {gate}"


@requires_run
def test_f4cal_selection_reproduces_exactly():
    sel = _json("stage2bf_f4cal_selection_reproduction.json")
    assert sel["reproduction_gate"]["all_pass"] is True
    for seed, s in sel["reproduction_gate"]["per_seed"].items():
        for gate in ("selected_score_exact", "calibration_top1_exact",
                     "calibration_chain_distance_exact", "acceptance_thresholds_bit_exact",
                     "reject_rule_exact"):
            assert s[gate] is True, f"seed {seed}: {gate}"
        assert s["replay_selected_canonical"] == s["historical_selected_canonical"]


@requires_run
def test_ridge_is_excluded_from_the_f4cal_candidate_set():
    sel = _json("stage2bf_f4cal_selection_reproduction.json")
    assert sel["ridge_excluded_from_selection"] is True
    assert EI.RIDGE_CANONICAL not in sel["candidates_considered"]
    assert len(sel["candidates_considered"]) == 5
    for r in _csv("stage2bf_f4cal_selection.csv"):
        if r["canonical_score"] == EI.RIDGE_CANONICAL:
            assert r["is_selection_candidate"] == "False"
            assert r["is_audit_baseline"] == "True"
            assert r["selected"] == "False"


@requires_run
def test_f4_test_is_never_read_by_the_selection_code():
    """Static check: the selection module must not mention the final test partition at all."""
    src = (ROOT / "src" / "certo_fdi" / "experiments" / "run_stage2bf_selection.py").read_text()
    body = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    body = body.split('"""', 2)[-1]        # drop the module docstring, which discusses F4_TEST
    assert "F4_TEST" not in body
    assert "test_ids" not in body


@requires_run
def test_selection_artifact_predates_any_test_metric_being_claimed():
    sel = _json("stage2bf_f4cal_selection_reproduction.json")
    assert sel["final_test_untouched_at_selection_time"] is True
    assert sel["selection_partition"] == "F4_CAL"


# ------------------------------------------------------------------ naming
@requires_run
@pytest.mark.parametrize("name", [
    "stage2bf_estimator_control_matrix.csv", "stage2bf_estimator_contrast_ci.csv",
    "stage2bf_per_episode_localization.csv", "stage2bf_per_link_metrics.csv",
    "stage2bf_stage2a_ridge_reproduction.csv", "stage2bf_f4cal_selection.csv",
    "stage2bf_mechanism_robustness.csv"])
def test_new_result_tables_carry_no_renamed_legacy_name(name):
    EI.assert_no_legacy_names((RES / name).read_text())


@requires_run
def test_identity_map_is_shipped_and_complete():
    rows = _csv("stage2bf_estimator_identity_map.csv")
    assert len(rows) == 6
    for r in rows:
        assert r["historical_source_commit"] and r["canonical_name"] and r["estimator_family"]
    ridge = [r for r in rows if r["canonical_name"] == EI.RIDGE_CANONICAL]
    assert len(ridge) == 1 and ridge[0]["selection_role"] == "audit_baseline"


# ------------------------------------------------------------------ leakage / no training
def test_training_entry_points_fail_if_called(monkeypatch):
    """Stage 2B-F must not train. Prove the guard by making training explode and importing anyway."""
    import certo_fdi.experiments.pipeline as P

    def boom(*a, **k):
        raise AssertionError("training was invoked during Stage 2B-F")

    for fn in ("train_model", "fit", "train"):
        if hasattr(P, fn):
            monkeypatch.setattr(P, fn, boom)
    import certo_fdi.experiments.run_stage2bf_replay as R
    import certo_fdi.experiments.run_stage2bf_analyse as A  # noqa: F401
    assert R.METHOD_ORDER  # module imports and does no training at import time


def test_data_generation_entry_point_fails_if_called(monkeypatch):
    import certo_fdi.stage2b.contact_calibration as CC

    def boom(*a, **k):
        raise AssertionError("episode generation was invoked during Stage 2B-F")

    monkeypatch.setattr(CC, "generate_partition", boom)
    src = (ROOT / "src" / "certo_fdi" / "experiments" / "run_stage2bf_selection.py").read_text()
    assert "generate_partition" not in src.split('"""', 2)[-1], \
        "the selection replay must rebuild F4_CAL from the frozen manifest, never generate it"


@requires_run
def test_frozen_checkpoints_and_episodes_are_unchanged():
    for r in _csv("stage2bf_historical_artifact_preservation.csv"):
        assert r["unchanged"] == "True", r
        assert r["present"] == "True", r


@requires_run
def test_frozen_scientific_code_is_identical_to_the_scientific_commit():
    p = _json("stage2bf_input_provenance.json")
    assert p["scientific_code_identical"] is True
    assert p["decision_code_identical"] is True
    geom = [f for f in p["frozen_scientific_files"] if f["path"].endswith("geometry.py")][0]
    assert geom["identical_at_stage2a"] is True, "the ridge import must be Stage 2A's own code"


@requires_run
def test_input_provenance_verified_from_disk():
    p = _json("stage2bf_input_provenance.json")
    assert p["host"]["persistent_root_is_mount"] is True
    assert p["dataset"]["verified"] is True and p["dataset"]["n_missing"] == 0
    assert p["dataset"]["n_episodes"] == 590
    for pkg in p["packages"]:
        assert pkg["verdict"] == "VERIFIED", pkg["package"]
        assert pkg["sha_match"] and pkg["crc_ok"] and pkg["internal_manifest_ok"]


# ------------------------------------------------------------------ statistics
@requires_run
def test_contrasts_use_episode_cluster_bootstrap_on_paired_episodes():
    rows = _csv("stage2bf_estimator_contrast_ci.csv")
    assert rows, "no contrasts written"
    for r in rows:
        assert r["unit"] == "episode"
        assert int(r["bootstrap_resamples"]) == CFG["statistics"]["bootstrap_resamples"]
        assert float(r["alpha"]) == CFG["statistics"]["bootstrap_alpha"]
        assert int(r["n_episodes"]) == 72, "contrasts must pool the same 72 episodes"


@requires_run
def test_every_contrast_is_reported_for_both_estimators():
    rows = _csv("stage2bf_estimator_contrast_ci.csv")
    for name in CFG["mechanism_contrasts"]:
        ests = {r["estimator"] for r in rows if r["contrast"] == name}
        assert ests == {EI.RIDGE_CANONICAL, EI.SVD_CANONICAL}, name


@requires_run
def test_window_level_bootstrap_is_not_used_anywhere():
    for p in (ROOT / "src" / "certo_fdi" / "experiments").glob("run_stage2bf_*.py"):
        t = p.read_text()
        assert "window_bootstrap" not in t and "iid_bootstrap" not in t


@requires_run
def test_random_control_is_carried_per_replicate_then_aggregated():
    rows = _csv("stage2bf_estimator_control_matrix.csv")
    rep = [r for r in rows if r["control"] == "random_within_support_rankmatched"
           and r["is_replicate_row"] == "True"]
    agg = [r for r in rows if r["control"] == "random_within_support_rankmatched"
           and r["is_replicate_row"] == "False"]
    assert len(rep) == 3 * 2 * 16, "16 replicates per seed per estimator must be reported"
    assert len(agg) == 3 * 2
    for a in agg:
        mine = [float(r["episode_top1"]) for r in rep
                if r["seed"] == a["seed"] and r["estimator"] == a["estimator"]]
        assert float(a["episode_top1"]) == pytest.approx(float(np.mean(mine)), rel=1e-12)


# ------------------------------------------------------------------ the 2x5 matrix
@requires_run
def test_matrix_covers_two_estimators_by_five_controls_by_three_seeds():
    rows = [r for r in _csv("stage2bf_estimator_control_matrix.csv") if r["is_replicate_row"] == "False"]
    assert len(rows) == 2 * 5 * 3
    assert {r["estimator"] for r in rows} == {EI.RIDGE_CANONICAL, EI.SVD_CANONICAL}
    assert {r["control"] for r in rows} == set(CFG["loadpath_controls"])


@requires_run
def test_orthonormalised_controls_are_flagged_and_the_two_estimators_agree_there():
    """The declared caveat, checked against the numbers rather than left as prose."""
    rows = [r for r in _csv("stage2bf_estimator_control_matrix.csv") if r["is_replicate_row"] == "False"]
    for control in CFG["orthonormalised_controls"]:
        for seed in {r["seed"] for r in rows}:
            vals = {r["estimator"]: float(r["episode_top1"]) for r in rows
                    if r["control"] == control and r["seed"] == seed}
            assert vals[EI.RIDGE_CANONICAL] == pytest.approx(vals[EI.SVD_CANONICAL], abs=1e-9), \
                f"{control}/{seed}: orthonormalised control should collapse the estimator contrast"
    for r in rows:
        assert (r["orthonormalised_control"] == "True") == (r["control"] in CFG["orthonormalised_controls"])


@requires_run
def test_robustness_labels_come_from_the_frozen_vocabulary():
    for r in _csv("stage2bf_mechanism_robustness.csv"):
        assert r["robustness"] in CFG["robustness_labels"], r


# ------------------------------------------------------------------ decision
@requires_run
def test_integrity_passed_and_the_scientific_decision_used_the_frozen_function():
    d = _json("stage2bf_integrity_decision.json")
    assert d["stage2bf_integrity_decision"] == PASS_STATE
    assert d["decision_function"]["module"] == "certo_fdi.stage2b.decision_stage2b"
    assert d["decision_function"]["name"] == "decide"
    assert d["decision_function"]["manual_override"] is False
    assert d["stage2bf_scientific_decision"] in CFG["scientific_decision"]["vocabulary"]
    assert d["stage2bf_combined_terminal"] == \
        f"{d['stage2bf_integrity_decision']}__{d['stage2bf_scientific_decision']}"


@requires_run
def test_evidence_delta_touched_only_the_reproduction_gate():
    d = _json("stage2bf_evidence_delta.json")
    assert d["clean"] is True and not d["violations"]
    paths = {c["path"] for c in d["allowed"]}
    for p in paths:
        assert p.startswith(("contact_reproduction", "reproduction_gate",
                             "evidence.integrity.baseline_reproduction_outside_tolerance")), p
    forbidden = ("detection", "localization", "selective", "loadpath", "sequential",
                 "healthy_expansion", "thresholds")
    for p in paths:
        assert not any(f".{x}." in f".{p}." for x in forbidden), p


@requires_run
def test_a_moved_scientific_metric_would_have_blocked():
    """The guard is only worth having if it fires: prove it on the real historical evidence."""
    hist = json.loads((Path(CFG["paths"]["stage2b_run_root"]) / "results"
                       / "stage2b_decision_evidence.json").read_text())
    import copy
    tampered = copy.deepcopy(hist)
    tampered["evidence"]["localization"]["episode_top1"] = 0.99
    out = evidence_delta(hist, tampered,
                         ("contact_reproduction", "reproduction_gate",
                          "evidence.integrity.baseline_reproduction_outside_tolerance"))
    assert out["clean"] is False
    assert any("episode_top1" in v["path"] for v in out["violations"])


@requires_run
def test_historical_stage2b_decision_is_still_blocked_and_untouched():
    d = _json("stage2bf_integrity_decision.json")
    assert d["historical_stage2b_decision"] == "BLOCKED"
    hist = json.loads((Path(CFG["paths"]["stage2b_run_root"]) / "results"
                       / "stage2b_decision_evidence.json").read_text())
    assert hist["decision"] == "BLOCKED"
    assert hist["reproduction_gate"]["contact_localizer"] == "FAIL"


@requires_run
def test_scientific_decision_evidence_records_the_function_hash():
    d = _json("stage2bf_scientific_decision_evidence.json")
    assert d["produced_by"].startswith("certo_fdi.stage2b.decision_stage2b.decide")
    assert len(d["decision_function_sha256"]) == 64
    assert d["historical_stage2b_decision"] == "BLOCKED"
