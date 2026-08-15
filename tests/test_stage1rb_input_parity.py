"""R0 items 13–15 (static part): the two primary models declare identical physical input fields,
neither declares a forbidden field, and the declared fields are exactly what the feature builders
consume (dimension check)."""

from __future__ import annotations

import pytest

from tests.conftest import requires_sim, requires_torch

XML = "/mnt/g/CERTO-FDI/01_frozen_sources/extracted/mujoco_menagerie_franka_emika_panda_da76818/franka_emika_panda/panda_nohand.xml"
FORBIDDEN = {"tau_meas", "tau_measured", "residual", "e_tau", "raw_residual", "fault_active", "fault_family_id", "fault_target", "severity", "family", "target", "active", "q_true", "qd_true", "qdd_true", "tau_applied", "tau_cmd", "ext_wrench_link", "region_id", "trajectory_family_id", "split", "partition"}
CONTRACT_FIELDS = {"scalars": {"q", "qd", "qdd_est", "tau_nom"}, "twists": {"V", "A", "S", "g"}, "wrenches": {"F_body", "F", "I_V", "I_A"}}


def test_manifests_match_and_contain_no_forbidden_fields():
    from certo_fdi.models.features import raw_input_field_manifest
    from certo_fdi.models.ligra_v2_typed import LiGRAv2Typed

    mb = raw_input_field_manifest()
    mv = LiGRAv2Typed.input_field_manifest()
    for key in ("scalars", "twists", "wrenches", "context", "link_descriptors"):
        assert set(mb[key]) == set(mv[key]), (key, mb[key], mv[key])
    for key, want in CONTRACT_FIELDS.items():
        assert set(mv[key]) == want
    for man in (mb, mv):
        declared = set().union(*(set(v) for k, v in man.items() if k != "processing"))
        assert not (declared & FORBIDDEN), declared & FORBIDDEN
    assert "region_id" not in mv["context"] and "trajectory_family_id" not in mv["context"]


@requires_sim
@requires_torch
def test_feature_builders_consume_exactly_the_declared_fields(rng):
    import torch

    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.rnea_torch import TorchChain, rnea_batch
    from certo_fdi.models.features import RAW_FEATURE_DIM, raw_features, raw_input_field_manifest
    from certo_fdi.models.ligra_v2_typed import typed_inputs

    chain = reference_chain(XML)
    tc = TorchChain.from_chain(chain, dtype=torch.float64)
    n = chain.n_links
    q = torch.as_tensor(rng.uniform(chain.joint_lower, chain.joint_upper, size=(3, n)))
    tb = rnea_batch(tc, q, torch.randn(3, n, dtype=torch.float64), torch.randn(3, n, dtype=torch.float64))
    tau_nom = torch.randn(3, n, dtype=torch.float64)
    mb = raw_input_field_manifest()
    raw = raw_features(tc, tb, tau_nom)
    assert raw.shape[-1] == RAW_FEATURE_DIM == 6 * (len(mb["twists"]) + len(mb["wrenches"])) + len(mb["scalars"])
    m, f, s = typed_inputs(tc, tb, tau_nom)
    assert m.shape[-2] == len(mb["twists"]) and f.shape[-2] == len(mb["wrenches"]) and s.shape[-1] == len(mb["scalars"])
    # the raw components and the typed channels are the same numbers, only arranged differently
    raw_typed = torch.cat([m.reshape(3, n, -1), f.reshape(3, n, -1), s], -1)
    assert torch.allclose(raw, raw_typed)
