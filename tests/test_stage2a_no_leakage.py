"""Stage 2A contract §7.3: automatic no-leakage scan of every model and fuser input.

Forbidden anywhere in an encoder or a fuser input:

    tau_meas, the raw residual, a fault label, a fault severity, a fault link id,
    truth-only acceleration or state.

``tau_meas`` is allowed in exactly two places: the training **target** ``tau_meas - tau_nom``
and the final residual ``e_tau = tau_meas - tau_nom - d_chain``. ``tau_cmd`` (the controller's
own command) is a deployment-available signal used by the F1 and F6 dictionaries; it is
asserted here never to reach an encoder.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import numpy as np
import pytest

from tests.conftest import requires_sim, requires_torch

XML = "/mnt/g/CERTO-FDI/01_frozen_sources/extracted/mujoco_menagerie_franka_emika_panda_da76818/franka_emika_panda/panda_nohand.xml"
FORBIDDEN_ENCODER_FIELDS = ("tau_meas", "tau_cmd", "active", "target", "family", "severity", "qdd_true", "q_true", "qd_true", "tau_applied", "ext_wrench_link", "r_gmo")


def test_chain_gnn_input_manifest_excludes_torque_measurements():
    from certo_fdi.models.chain_gnn import ChainGNN
    from certo_fdi.models.features import RAW_FEATURE_DIM

    man = ChainGNN.input_field_manifest()
    flat = " ".join(str(v) for v in man.values())
    for bad in ("tau_meas", "tau_cmd", "tau_applied", "qdd_true", "q_true", "qd_true", "fault", "severity", "ext_wrench"):
        assert bad not in flat, (bad, man)
    assert "tau_nom" in flat                       # the nominal RNEA torque IS an input
    assert RAW_FEATURE_DIM == 52


def test_encoder_source_never_reads_a_forbidden_batch_field():
    """Static scan: no ``batch["<forbidden>"]`` inside any model's feature/forward path."""
    import certo_fdi.models.chain_gnn as mod
    import certo_fdi.models.features as feat

    for m in (mod, feat):
        tree = ast.parse(inspect.getsource(m))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript) or not isinstance(node.value, ast.Name) or node.value.id != "batch":
                continue
            key = node.slice.value if isinstance(node.slice, ast.Constant) else None
            if key is None:
                continue
            # tau_meas is allowed ONLY where the residual/target is formed; those two call sites
            # are inside typed_link_features / the loss target, never inside features().
            if key == "tau_meas":
                continue
            assert key not in FORBIDDEN_ENCODER_FIELDS, f"{m.__name__} reads batch[{key!r}] "


@requires_sim
@requires_torch
def test_tau_meas_only_enters_the_residual_not_the_features(rng):
    """Perturbing ``tau_meas`` must not change the encoder features or ``delta_tau``."""
    import torch

    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.models.chain_gnn import build_model
    from tests.test_models_and_heads import _synthetic_batch

    ch = reference_chain(XML)
    tc = TorchChain.from_chain(ch, dtype=torch.float64)
    batch = _synthetic_batch(ch, rng, B=3, T=8, dtype=torch.float64)
    batch["inertia"] = tc.inertia[None].expand(3, -1, -1, -1)
    for name in ("chain_gnn_aug", "rnea_gru"):
        m = build_model(name, tc, 6, {"scalar_hidden_dim": 16, "scalar_layers": 1, "baseline_gru_hidden": 16}).to(torch.float64)
        m.fit_normalizers(tc, [batch])
        b2 = dict(batch)
        b2["tau_meas"] = batch["tau_meas"] + 7.0
        with torch.no_grad():
            o1, o2 = m(batch, tc), m(b2, tc)
        assert torch.allclose(o1.delta_tau, o2.delta_tau, atol=1e-12), name
        # the post-correction residual DOES move, by exactly the perturbation
        i = o1.link_feature_names.index("post_residual")
        assert torch.allclose(o2.link_features[..., i] - o1.link_features[..., i], torch.full_like(o1.link_features[..., i], 7.0), atol=1e-9)


def test_pathway_dictionaries_use_no_truth_only_signal():
    """The deployed dictionary builder reads only measured signals and the nominal model."""
    import certo_fdi.pathways.dictionaries as dic

    src = inspect.getsource(dic)
    tree = ast.parse(src)
    read = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "signals":
            if isinstance(node.slice, ast.Constant):
                read.add(node.slice.value)
    assert read <= {"q_meas", "qd_meas", "qdd_est", "tau_cmd", "q_ref"}, read
    for bad in ("qdd_true", "q_true", "qd_true", "tau_applied", "ext_wrench_link", "fault_active", "fault_target", "severity"):
        assert f'signals["{bad}"]' not in src, bad


def test_oracle_sensitivities_are_isolated_from_the_deployed_path():
    """Nothing in the deployed pathway/fusion code may import the oracle replay module."""
    import certo_fdi.pathways.dictionaries as dic
    import certo_fdi.pathways.fusion as fus
    import certo_fdi.pathways.geometry as geo
    import certo_fdi.pathways.localization as loc
    import certo_fdi.pathways.whitening as whi
    import certo_fdi.pathways.window_features as wf

    for m in (dic, geo, whi, wf, loc, fus):
        tree = ast.parse(inspect.getsource(m))
        for node in ast.walk(tree):
            # AST only: a docstring may *describe* the oracle module, but nothing may import it
            if isinstance(node, ast.ImportFrom):
                assert "sensitivity" not in (node.module or ""), (m.__name__, node.module)
            if isinstance(node, ast.Import):
                assert all("sensitivity" not in a.name for a in node.names), m.__name__
            if isinstance(node, ast.Name):
                assert "closed_loop_sensitivity" not in node.id, m.__name__


def test_whitener_is_fitted_on_healthy_partitions_only():
    import certo_fdi.experiments.stage2a_pathway_pipeline as pp

    src = inspect.getsource(pp.fit_whiteners) + inspect.getsource(pp.fit_whiteners_pre)
    assert "healthy" in src
    import yaml

    cfg = yaml.safe_load((Path(__file__).resolve().parents[1] / "configs" / "stage2a_pathway_audit.yaml").read_text())
    assert cfg["pathway"]["whitening"]["fit_partitions"] == ["train", "val"]
    # the frozen splits put every fault episode in test or calib, so train+val is healthy-only
    from certo_fdi.data.splits import build_plan, leakage_report

    frozen = yaml.safe_load((Path(__file__).resolve().parents[1] / "configs" / "frozen_dataset_protocol.yaml").read_text())
    rep = leakage_report(build_plan(frozen, "pilot", 260815))
    assert rep["checks"]["train_val_healthy_only"] and rep["checks"]["all_faults_in_test_or_calib"]
    assert rep["all_pass"]


def test_context_vector_excludes_region_and_trajectory_family():
    """Configuration-region id and trajectory-family id are never model or head inputs."""
    from certo_fdi.data.schema import CONTEXT_FIELDS
    from certo_fdi.data.windows import MODEL_CONTEXT_INDICES, MODEL_CONTEXT_NAMES

    assert set(MODEL_CONTEXT_NAMES) == {"controller_id", "speed_scale", "tool_mass_kg", "tool_com_z_m", "temperature_proxy", "noise_level"}
    used = {CONTEXT_FIELDS[i] for i in MODEL_CONTEXT_INDICES}
    assert used == set(MODEL_CONTEXT_NAMES)
    assert "region_id" not in used and "trajectory_family_id" not in used


def test_ablation_blocks_never_mix_the_oracle_into_a_deployed_head():
    from certo_fdi.pathways.fusion import ABLATION_BLOCKS

    for name, blocks in ABLATION_BLOCKS.items():
        if "contact_oracle" in blocks:
            assert "oracle" in name, name          # oracle blocks only in explicitly named ablations
    deployed = [n for n in ABLATION_BLOCKS if "oracle" not in n]
    for n in deployed:
        assert "contact_oracle" not in ABLATION_BLOCKS[n], n
