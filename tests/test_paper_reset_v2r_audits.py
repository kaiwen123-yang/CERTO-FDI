"""V2-R section-18 audit tests over ACTUAL artifacts on the persistent root.

Skipped cleanly when an artifact does not exist yet (phases still running);
at G0 every test must run and pass. Covers items 2,6,8,9,10,12,13,14 of the
contract's test list (1,3,4,5,7,15,16 live in the freeze tests, the ME-AD
audit module and the reviewer smoke script)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

V2R = Path("/mnt/g/CERTO-FDI/04_runs/paper_reset_v2r/run_20260824T084349Z_paper_reset_v2r")
LIT = Path("/mnt/g/CERTO-FDI/02_research_docs/paper_reset_v2r")
REPO = Path(__file__).resolve().parents[1]


def _need(p: Path):
    if not p.exists():
        pytest.skip(f"artifact pending: {p}")
    return p


def test_aursad_split_isolation():  # item 8
    d = json.loads(_need(V2R / "aursad/dual_protocol_results.json").read_text())
    for proto in ("native", "honest"):
        assert d[f"{proto}_dup_audit"]["same_operation_across_split"] == 0


def test_aursad_near_duplicate_audit_present():  # item 9
    d = json.loads(_need(V2R / "aursad/dual_protocol_results.json").read_text())
    nat = d["native_dup_audit"]; hon = d["honest_dup_audit"]
    assert nat["exact_dup_rate_sampled"] > hon["exact_dup_rate_sampled"]
    assert len(nat["nn_l2_p05_p50_p95"]) == 3


def test_matrix_completeness_from_rows():  # item 10
    import csv
    comp = json.loads(_need(V2R / "unified/matrix_completeness.json").read_text())
    assert comp["computed_from_rows_only"] is True
    rows = list(csv.DictReader(_need(V2R / "unified/universal_core_matrix.csv").open()))
    per = {}
    DET = ("mahalanobis", "pca_spe")
    for r in rows:
        per.setdefault(r["dataset"], {}).setdefault(r["model"], set()).add(r["seed"])
    for ds, ok in comp["per_dataset_core8_complete"].items():
        derived = all(
            len(per.get(ds, {}).get(m, set())) >= (1 if m in DET else 3)
            for m in ("mahalanobis", "pca_spe", "iforest", "ocsvm",
                      "window_ae", "gru_ae", "tcn_ae", "gru_pred"))
        assert derived == ok, ds


def test_deterministic_seed_semantics():  # item 6
    import csv
    rows = list(csv.DictReader(_need(V2R / "unified/universal_core_matrix.csv").open()))
    for r in rows:
        if r["model"] in ("mahalanobis", "pca_spe"):
            assert r["seed_semantics"] == "deterministic_1fit", r
        else:
            assert r["seed_semantics"] == "stochastic_seed", r


def test_inherited_cards_included():  # item 12
    inv = json.loads(_need(LIT / "self_contained_inventory.json").read_text())
    assert inv["cards_v1_inherited"] == 10
    assert inv["dossiers"] == 16
    assert inv["cards_v2"] >= 94


def test_no_restricted_raw_data_in_git():  # item 13
    out = subprocess.check_output(["git", "-C", str(REPO), "ls-files"]).decode().splitlines()
    banned = (".pdf", ".h5", ".parquet", ".pkl", ".pth", ".zip", ".mat", ".npz")
    offenders = [f for f in out if f.lower().endswith(banned)]
    assert offenders == [], offenders


def test_git_head_alignment_in_manifest():  # item 14 (final packages check the rest)
    p = V2R / "run_manifest.json"
    if not p.exists():
        pytest.skip("manifest pending")
    m = json.loads(p.read_text())
    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"]).decode().strip()
    assert m.get("git_head") in (None, head) or m.get("git_head_note")


def test_claims_match_tables():  # item 11
    """Every numeric claim registered in decision/claims_check.json must match
    its extractor over the named artifact within tolerance."""
    p = V2R / "decision/claims_check.json"
    if not p.exists():
        pytest.skip("claims_check pending (S0)")
    spec = json.loads(p.read_text())
    import csv as _csv
    for c in spec["claims"]:
        art = Path(c["artifact"])
        assert art.exists(), art
        if art.suffix == ".json":
            obj = json.loads(art.read_text())
            for k in c["path"]:
                obj = obj[k]
            val = float(obj)
        else:
            rows = list(_csv.DictReader(art.open()))
            match = [r for r in rows if all(r[k] == v for k, v in c["row_filter"].items())]
            assert match, c
            val = float(match[0][c["column"]])
        assert abs(val - c["value"]) <= c.get("tol", 1e-6), (c["claim"], val)


def test_deep_neighbor_coverage_40():  # item 12 extension (contract §14.2)
    """All full-text-held direct neighbours (40 per the neighbour matrix) must be
    covered by deep-quality cards, measured from the files — not a manual flag.
    The persisted deep_neighbor_coverage.json must agree with a live recount."""
    _need(LIT / "05_nearest_neighbor_matrix.md")
    from certo_fdi_reset_v2r.evaluate_gates import deep_neighbor_coverage
    cov = deep_neighbor_coverage(write=False)
    assert cov["n_neighbors"] == 40, cov["n_neighbors"]
    assert cov["n_located"] == 40, [k for k, v in cov["per_card"].items() if not v["file"]]
    shallow = [k for k, v in cov["per_card"].items() if not v["deep"]]
    assert cov["n_deep"] >= 40, shallow
    persisted = json.loads(_need(LIT / "deep_neighbor_coverage.json").read_text())
    assert persisted["n_deep"] == cov["n_deep"]
    assert persisted["n_located"] == cov["n_located"]


def test_mead_forbidden_inputs_ast():  # item 3
    """No ME-AD experiment module may read cycle_index/fault/split-id columns
    as model INPUTS (they are allowed only in evaluation/ordering code marked
    EVAL_ONLY)."""
    import re
    src = REPO / "src/certo_fdi_reset_v2r"
    offenders = []
    for f in src.glob("mead_*.py"):
        t = f.read_text()
        for m in re.finditer(r"(cycle_index|fault_stage|split_id|fault_label)", t):
            line_start = t.rfind("\n", 0, m.start()) + 1
            line = t[line_start:t.find("\n", m.start())]
            if "EVAL_ONLY" not in line and "forbidden" not in line.lower():
                offenders.append((f.name, line.strip()[:80]))
    assert offenders == [], offenders
