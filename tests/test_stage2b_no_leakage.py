"""Nothing may be selected on the final F4 test set, and no partition may overlap another."""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import numpy as np
import yaml

from certo_fdi.experiments import stage2b_common as SC
from certo_fdi.stage2b import contact_calibration as CC
from certo_fdi.stage2b import healthy_expansion as HE

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "configs" / "stage2b_contact_loadpath.yaml").read_text())
RUNNERS = sorted((ROOT / "src" / "certo_fdi" / "experiments").glob("run_stage2b_*.py"))


def test_the_final_test_partition_is_never_a_selection_partition():
    assert SC.FINAL_TEST_PARTITION == "F4_TEST"
    assert SC.FINAL_TEST_PARTITION not in SC.SELECTION_PARTITIONS
    assert set(SC.SELECTION_PARTITIONS) == {"healthy_train", "healthy_val", "F4_CAL"}
    assert CFG["localization"]["selection_partition"] in SC.SELECTION_PARTITIONS
    assert CFG["localization"]["rejection_selection_partition"] in SC.SELECTION_PARTITIONS
    assert CFG["calibration"]["tune_on_healthy_only"] is True


def test_f4_cal_seeds_cannot_collide_with_frozen_or_expansion_seeds():
    cal = {s.seed for s in CC.design_table(CFG)}
    exp = {s.seed for s in HE.design_table(CFG)}
    assert cal.isdisjoint(exp), sorted(cal & exp)[:10]
    # and the guard itself reports a collision rather than passing silently
    specs = CC.design_table(CFG)
    bad = CC.seeds_are_disjoint(specs, {specs[0].seed})
    assert bad["disjoint"] is False and bad["n_overlap"] == 1
    good = CC.seeds_are_disjoint(specs, {-1})
    assert good["disjoint"] is True


def test_f4_cal_episode_ids_cannot_be_frozen_episode_ids():
    ids = {s.episode_id for s in CC.design_table(CFG)}
    assert all(i.startswith("F4CAL_") for i in ids)
    assert len(ids) == len(CC.design_table(CFG))               # no duplicates
    exp_ids = {s.episode_id for s in HE.design_table(CFG)}
    assert ids.isdisjoint(exp_ids)
    assert all(i.startswith("H_EXT_") for i in exp_ids)


def test_healthy_expansion_adds_only_to_train_and_keeps_the_sets_nested():
    specs = HE.design_table(CFG)
    totals = [int(t) for t in CFG["healthy_expansion"]["totals"]]
    frozen_train = [f"TRAIN_{i:03d}" for i in range(totals[0])]
    sets = HE.nested_ids(frozen_train, specs, totals)
    chk = HE.check_nested(sets, totals)
    assert chk["nested"] and chk["sizes_correct"]
    for t in totals:                                            # every scale still contains all of H40
        assert set(frozen_train) <= set(sets[f"H{t}"])
    # every added episode is a *healthy train* episode, never a val/test or fault one
    for r in (s.row() for s in specs):
        assert r["kind"] == "healthy" and r["partition"] == "train" and r["split"] == "S0"


def test_no_runner_fits_a_calibrator_or_selector_on_the_final_test_partition():
    """Static check: `F4_TEST` / `test_eps` never flow into a fit/selection call."""
    fit_calls = re.compile(r"(CAL\.fit|select_feature_and_threshold|_tune_on_grid|healthy_acceptance_thresholds)\s*\(")
    for p in RUNNERS:
        src = p.read_text()
        for m in fit_calls.finditer(src):
            # take the balanced argument list of the call
            i = src.index("(", m.start())
            depth, j = 0, i
            while j < len(src):
                depth += (src[j] == "(") - (src[j] == ")")
                if depth == 0:
                    break
                j += 1
            args = src[i:j + 1]
            for banned in ("test_eps", "F4_TEST", "test_ids", "f4_test", "test_conf"):
                assert banned not in args, f"{p.name}: {banned} reaches {m.group(1)}"


def test_no_runner_imports_a_truth_label_into_a_calibrator():
    """The four calibrators take (scores, ctx, episode) only -- there is nowhere to put a label."""
    from certo_fdi.stage2b import context_calibration as CALMOD

    params = list(inspect.signature(CALMOD.fit).parameters)
    assert params == ["method", "scores", "ctx", "episode", "quantile", "context_names", "cfg"]
    for banned in ("label", "y", "target", "fault", "truth", "severity"):
        assert banned not in params


def test_every_runner_declares_the_partition_on_every_result_row():
    """`base_row` always emits a partition column, and it is one of the declared values."""
    assert "partition" in SC.REQUIRED_COLUMNS

    class _Layout:
        run_id = "r"
    class _Fake:
        layout = _Layout(); repo_root = ROOT; cfg_sha = "c"; manifest_sha = "m"
    row = SC.Stage.base_row(_Fake(), method="m", partition="F4_CAL")
    for c in SC.REQUIRED_COLUMNS:
        assert c in row, c
    assert row["partition"] == "F4_CAL"


def test_committed_result_tables_never_select_on_the_final_test_partition():
    """Selection tables are F4_CAL / healthy_val; only reported metrics may be F4_TEST."""
    import csv

    run = Path(CFG["paths"]["run_root"])
    runs = sorted(run.glob("run_*")) if run.exists() else []
    if not runs:
        return                                                  # nothing produced yet in this checkout
    res = runs[-1] / "results"
    selection_tables = {"stage2b_localizer_selection.csv": SC.SELECTION_PARTITIONS,
                        "stage2b_contact_calibration_manifest.csv": ("F4_CAL",)}
    for name, allowed in selection_tables.items():
        f = res / name
        if not f.exists():
            continue
        with f.open(encoding="utf-8") as fh:
            parts = {r["partition"] for r in csv.DictReader(fh)}
        assert parts <= set(allowed), (name, parts)
    # the calibration tuning table must be tuned on healthy validation, never on faults
    f = res / "stage2b_sequential_metrics.csv"
    if f.exists():
        with f.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        tuned = {r["partition"] for r in rows if r.get("status") in ("OK", "TARGET_NOT_REACHED")
                 and r.get("tuned_quantile", "") not in ("", "nan")}
        assert tuned <= {"healthy_val"}, tuned


def test_the_frozen_config_records_the_prohibition_explicitly():
    forbidden = " ".join(str(x) for x in CFG["claims"]["forbidden"]).lower()
    assert "exact conditional cfar" in forbidden
    assert "network-internal messages" in forbidden
    raw = (ROOT / "configs" / "stage2b_contact_loadpath.yaml").read_text().lower()
    assert "hard: selection never touches the final f4 test set" in raw
    assert "hard: window-level iid bootstrap is forbidden" in raw
    assert CFG["statistics"]["independent_unit"] == "episode"


def test_module_sources_parse_and_declare_no_hidden_test_time_fitting():
    """Every stage2b module compiles and none calls `.fit(` on data named like a test set."""
    for p in sorted((ROOT / "src" / "certo_fdi" / "stage2b").glob("*.py")) + RUNNERS:
        tree = ast.parse(p.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "fit":
                names = [a.id for a in node.args if isinstance(a, ast.Name)]
                assert not any("test" in n for n in names), (p.name, names)
