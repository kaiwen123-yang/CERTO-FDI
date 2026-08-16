"""Every load-path control must preserve the serial-chain prefix support (kickoff §04.3.1).

Support is defined in the **unwhitened** window residual, because the whitener ``W_0`` mixes
rows and would otherwise destroy the structure. Link ``l`` may load joints ``0..l`` only, at
every window time point.
"""

from __future__ import annotations

import numpy as np
import pytest

from certo_fdi.stage2b import loadpath_controls as LC
from tests.conftest import requires_sim

XML = "/mnt/g/CERTO-FDI/01_frozen_sources/extracted/mujoco_menagerie_franka_emika_panda_da76818/franka_emika_panda/panda_nohand.xml"
N_JOINTS, N_TIME = 7, 8
D = N_JOINTS * N_TIME


def test_support_rows_are_the_prefix_at_every_time_point():
    for l in range(N_JOINTS):
        rows = LC.support_rows(l, N_JOINTS, N_TIME)
        assert len(rows) == (l + 1) * N_TIME
        for r in rows:
            m, j = divmod(int(r), N_JOINTS)
            assert 0 <= m < N_TIME
            assert j <= l, (l, r, j)
        # every allowed (m, j) pair is present exactly once
        assert len(set(rows.tolist())) == len(rows)
        assert set(rows.tolist()) == {m * N_JOINTS + j for m in range(N_TIME) for j in range(l + 1)}


def test_support_is_nested_across_links():
    """A more distal link's support strictly contains a more proximal one's."""
    for l in range(N_JOINTS - 1):
        a = set(LC.support_rows(l, N_JOINTS, N_TIME).tolist())
        b = set(LC.support_rows(l + 1, N_JOINTS, N_TIME).tolist())
        assert a < b


def test_deterministic_and_random_bases_live_inside_the_support():
    for l in (0, 2, 4, 6):
        rows = LC.support_rows(l, N_JOINTS, N_TIME)
        mask = LC.support_mask(l, N_JOINTS, N_TIME)
        k = len(rows)
        for r in (1, 2, 3):
            for h in range(4):
                E = LC.embed(LC.dct_basis(k, r, offset=h * 3), rows, D)
                assert E.shape == (D, r)
                # link 6's support is the whole residual, so there is nothing outside it
                if (~mask).any():
                    assert np.abs(E[~mask]).max() == 0.0, (l, r, h)
                assert np.abs(E[mask]).max() > 0.0
                Er = LC.embed(LC.random_basis(k, r, seed=100 + h), rows, D)
                if (~mask).any():
                    assert np.abs(Er[~mask]).max() == 0.0


def test_bases_are_orthonormal_at_the_requested_rank():
    for k in (8, 16, 32, 56):
        for r in (1, 2, 3):
            for h in range(4):
                B = LC.dct_basis(k, r, offset=h * 5)
                assert B.shape == (k, r), (k, r, h)
                np.testing.assert_allclose(B.T @ B, np.eye(r), atol=1e-10)
                Rb = LC.random_basis(k, r, seed=17 + h)
                assert Rb.shape == (k, r)
                np.testing.assert_allclose(Rb.T @ Rb, np.eye(r), atol=1e-10)


def test_rank_zero_and_degenerate_requests_are_safe():
    assert LC.dct_basis(8, 0).shape == (8, 0)
    assert LC.random_basis(8, 0, seed=1).shape == (8, 0)
    # a rank larger than the support is clipped, never fabricated
    assert LC.dct_basis(3, 7).shape[1] == 3
    assert LC.random_basis(3, 7, seed=1).shape[1] == 3


def test_deterministic_basis_is_reproducible_and_hypotheses_differ():
    a = LC.dct_basis(32, 3, offset=2)
    b = LC.dct_basis(32, 3, offset=2)
    np.testing.assert_array_equal(a, b)                      # deterministic
    c = LC.dct_basis(32, 3, offset=9)
    assert np.abs(a - c).max() > 1e-6                        # different hypotheses really differ
    r1 = LC.random_basis(32, 3, seed=5)
    assert np.array_equal(r1, LC.random_basis(32, 3, seed=5))
    assert np.abs(r1 - LC.random_basis(32, 3, seed=6)).max() > 1e-6


@requires_sim
def test_aligned_dictionary_really_has_the_prefix_support():
    """The deployed Jacobian dictionary is what defines the support the controls must match."""
    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.pathways.dictionaries import build_episode_pathways

    ch = reference_chain(XML)
    n = ch.n_links
    T = 256
    rng = np.random.default_rng(3)
    t = np.arange(T) * 0.002
    lo, hi = ch.joint_lower + 0.15, ch.joint_upper - 0.15
    mid, amp = 0.5 * (lo + hi), 0.4 * (hi - lo)
    q = mid[None, :] + amp[None, :] * np.sin(2 * np.pi * 0.4 * t[:, None] + np.arange(n)[None, :])
    sig = {"q_meas": q, "qd_meas": rng.normal(size=(T, n)) * 0.3, "qdd_est": rng.normal(size=(T, n)) * 0.3,
           "tau_cmd": rng.normal(size=(T, n)) * 4, "tau_meas": rng.normal(size=(T, n)) * 4,
           "tau_nominal": rng.normal(size=(T, n)) * 4, "q_ref": q}
    ep = build_episode_pathways(ch, sig, np.arange(15, T, 16), episode_id="x", control_dt=0.002)
    rows = np.stack([np.arange(k, k + N_TIME) for k in range(3)])
    for l in range(n):
        for r_link in (None, np.array([0.0, 0.0, 0.06])):
            chk = LC.unwhitened_support_check(ep, rows, l, r_link)
            assert chk["support_respected"], (l, chk)
            assert chk["support_size"] == (l + 1) * N_TIME
            if l > 0:
                assert chk["max_abs_inside_support"] > 0.0


def test_support_control_reads_no_configuration():
    """The support and random controls must be functions of (link, rank, hypothesis) only."""
    import inspect

    src = inspect.getsource(LC.support_dictionaries) + inspect.getsource(LC.random_support_dictionaries)
    src += inspect.getsource(LC.dct_basis) + inspect.getsource(LC.random_basis)
    for forbidden in ("q_meas", "j_link", "r_link", "contact_columns", "forward_kinematics"):
        assert forbidden not in src, forbidden
    assert LC.NON_GEOMETRIC_METHODS == ("support_prefix_rankmatched", "random_within_support_rankmatched")
    assert set(LC.GEOMETRIC_METHODS) | set(LC.NON_GEOMETRIC_METHODS) == set(LC.METHODS)
