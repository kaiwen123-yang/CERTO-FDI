"""F1-F6 joint-Cartesian fault-pathway dictionaries in the window-residual coordinates.

Definitions
-----------
The window residual is the stacked chain-corrected joint residual

    E_W = vec( e_tau(t_1), ..., e_tau(t_M) )   in R^{n*M},
    e_tau(t) = tau_meas(t) - tau_nom(t) - d_chain(t).

Every dictionary column is the derivative of ``E_W`` with respect to one **physical** fault
parameter, evaluated on the *observed* trajectory with the *nominal* model:

    D_j,W[:, k] = d E_W / d theta_j,k       (columns stacked over the same t_1..t_M)

Sign convention (declared once, used everywhere): ``theta`` is the physical fault parameter
itself, so a fitted coefficient is directly readable in physical units -- contact force in N,
payload mass in kg, actuator efficiency *loss* as a fraction, friction increment in N m s/rad
or N m, encoder bias in rad, command delay in s. The Stage 2A contract writes several of the
same columns with the opposite sign (``-Diag(tau_cmd)``, ``-Diag(qdot)``, ``-Y_load``,
``+J^T``); those span the identical subspace and differ only by ``theta -> -theta``, which
changes no principal angle, projection residual or explained energy.

Derivations (all from ``M(q) qdd + h(q,qdot) + friction = tau_applied + J^T f_ext`` with
``tau_meas ~ tau_cmd`` and ``tau_nom = RNEA_nom + friction_nom``):

* **F1 actuator efficiency loss s_j**: ``tau_applied = (1-s) tau_cmd`` so
  ``e_tau += s_j * tau_cmd,j``  ->  ``D_gain(t) = Diag(tau_cmd(t))``.
* **F2 friction increments**: viscous ``Diag(qdot)``, Coulomb ``Diag(tanh(qdot/eps))``,
  Stribeck ``Diag(exp(-(qdot/v_s)^2) tanh(qdot/eps))`` -- three *separate* column groups, so
  the audit never assumes viscous+Coulomb span all friction anomalies.
* **F3 payload**: ``D_load(t) = Y_load(q,qdot,qdd)``, the exact 10-parameter body regressor of a
  rigid payload attached to the last link, obtained from the frozen typed RNEA (the joint
  torque is linear in the payload's spatial inertia).
* **F4 contact**: ``D_contact(l,p,t) = -J_{l,p}(q(t))^T`` (3 columns, point force in N) and the
  point-agnostic ``-J_l(q(t))^T`` (6 columns, body wrench). The frozen simulator injects a pure
  force at a point, so the 3-D form is the matched one; the two are never mixed in one
  dictionary.
* **F5 encoder**: symmetric finite differences of the *deployed* residual computation through
  the controller feedback path, the RNEA nominal path and the acceleration-estimator path --
  never a static Jacobian. Separate q-bias and qdot-bias column groups.
* **F6 command delay**: ``D_delay(t) = d tau_cmd/dt`` (the local analytic form) plus the
  closed-loop finite-difference form; the analytic one is used only as a control.

Deployment vs oracle: everything above is a function of measured signals and the nominal
model. The *oracle* validation (symmetric finite differences through the frozen truth
simulator) lives in :mod:`certo_fdi.pathways.sensitivity` and is used for correctness tests
and upper bounds only, never inside a deployed head.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from certo_fdi.dynamics.chain_model import ChainModel
from certo_fdi.pathways.jacobians import ChainKinematics, candidate_points, forward_kinematics, link_spatial_jacobians, point_jacobian

PAYLOAD_PARAM_NAMES = ("m", "h_x", "h_y", "h_z", "I_xx", "I_xy", "I_xz", "I_yy", "I_yz", "I_zz")
PAYLOAD_PARAM_UNITS = ("kg", "kg m", "kg m", "kg m", "kg m^2", "kg m^2", "kg m^2", "kg m^2", "kg m^2", "kg m^2")
WRENCH_COMPONENT_NAMES = ("n_x", "n_y", "n_z", "f_x", "f_y", "f_z")
FORCE_COMPONENT_NAMES = ("f_x", "f_y", "f_z")

FAMILY_OF_KEY = {
    "F1_actuator": "F1_actuator",
    "F2_viscous": "F2_friction",
    "F2_coulomb": "F2_friction",
    "F2_stribeck": "F2_friction",
    "F2_friction_all": "F2_friction",
    "F3_payload": "F3_payload",
    "F5_encoder_q": "F5_encoder",
    "F5_encoder_qd": "F5_encoder",
    "F5_encoder_all": "F5_encoder",
    "F6_delay": "F6_command",
}


def payload_inertia_basis() -> np.ndarray:
    """(10, 6, 6) basis of the payload spatial inertia in ``[omega; v]`` coordinates.

    ``I_p(phi) = sum_k phi_k B_k`` with ``phi = [m, h(3), I_o(6)]``, ``h = m c`` the first
    moment and ``I_o`` the rotational inertia about the **link-frame origin**. Matches
    ``geometry.spatial_types.spatial_inertia`` exactly (parallel-axis identity
    ``I_o = I_c + m skew(c) skew(c)^T``).
    """
    from certo_fdi.geometry.se3 import skew

    B = np.zeros((10, 6, 6))
    B[0, 3:, 3:] = np.eye(3)  # mass
    for j in range(3):
        e = np.zeros(3)
        e[j] = 1.0
        s = skew(e)
        B[1 + j, :3, 3:] = s
        B[1 + j, 3:, :3] = s.T
    idx = [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 2)]
    for k, (a, b) in enumerate(idx):
        E = np.zeros((3, 3))
        E[a, b] = 1.0
        E[b, a] = 1.0
        B[4 + k, :3, :3] = E
    return B


def payload_regressor(chain: ChainModel, q: np.ndarray, qd: np.ndarray, qdd: np.ndarray, link: int | None = None) -> np.ndarray:
    """(T, n, 10) exact payload regressor ``Y_load`` from the frozen typed RNEA.

    The joint torque induced by a rigid payload with spatial inertia ``I_p`` attached to
    ``link`` (default: the last link) is ``S_i^T`` of the backward-transported body wrench
    ``I_p A + ad*(V) I_p V``, which is linear in ``I_p`` and hence in ``phi``.
    """
    import torch

    from certo_fdi.dynamics.rnea_torch import TorchChain, rnea_batch
    from certo_fdi.geometry import torch_ops as T
    from certo_fdi.models.chain_gnn import backward_recursion

    tc = TorchChain.from_chain(chain, dtype=torch.float64)
    n = tc.n
    L = tc.n - 1 if link is None else int(link)
    qt = torch.as_tensor(np.asarray(q, dtype=float))
    tb = rnea_batch(tc, qt, torch.as_tensor(np.asarray(qd, dtype=float)), torch.as_tensor(np.asarray(qdd, dtype=float)))
    V = tb.V[:, L]  # (T,6)
    A = tb.A[:, L]
    ad_star = T.ad_star(V)  # (T,6,6)
    B = torch.as_tensor(payload_inertia_basis())  # (10,6,6)
    cols = []
    for k in range(B.shape[0]):
        Bk = B[k][None]
        f = (Bk @ A[..., None])[..., 0] + (ad_star @ (Bk @ V[..., None]))[..., 0]
        local = torch.zeros(V.shape[0], n, 6, dtype=V.dtype)
        local[:, L] = f
        dF = backward_recursion(tc, tb.X, local, None)
        cols.append((tb.S * dF).sum(-1))
    return torch.stack(cols, -1).numpy()


# --------------------------------------------------------------------------- per-episode cache
@dataclass
class EpisodePathways:
    """All per-sample dictionary columns of one episode, on a fixed time sub-grid."""

    episode_id: str
    t_index: np.ndarray  # (Tg,) sample indices on the episode's own time axis
    n_links: int
    d_gain: np.ndarray  # (Tg, n) diagonal of D_gain
    d_viscous: np.ndarray  # (Tg, n)
    d_coulomb: np.ndarray  # (Tg, n)
    d_stribeck: np.ndarray  # (Tg, n)
    y_load: np.ndarray  # (Tg, n, 10)
    j_link: np.ndarray  # (Tg, n_links, 6, n) spatial Jacobians at the body origins (float64:
    #   the whitened dictionaries reach condition numbers ~1e6, where float32 storage would
    #   dominate the projection error)
    r_link: np.ndarray  # (Tg, n_links, 3, 3) link orientations (for point Jacobians)
    d_sensor_q: np.ndarray  # (Tg, n, n) d e_tau / d q_bias
    d_sensor_qd: np.ndarray  # (Tg, n, n) d e_tau / d qd_bias
    d_delay: np.ndarray  # (Tg, n) d e_tau / d Delta (analytic dtau_cmd/dt)
    d_delay_buffer: np.ndarray  # (Tg, n) d e_tau / d Delta (explicit command-buffer finite difference)
    meta: dict = field(default_factory=dict)


def _finite_difference_sensitivities(
    controller, nominal,
    q_now: np.ndarray, qd_now: np.ndarray, qdd_now: np.ndarray,
    q_prev: np.ndarray, qd_prev: np.ndarray,
    q_ref_prev: np.ndarray, qd_ref_prev: np.ndarray, qdd_ref_prev: np.ndarray,
    torque_limit: np.ndarray, *, delta_q: float, delta_qd: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Symmetric finite differences of ``e_tau = tau_cmd - tau_nom`` w.r.t. encoder biases.

    Both paths a deployed detector can evaluate are propagated:

    (i)  the **controller feedback path** ``tau_cmd = clip(controller(q_meas, qd_meas, refs))``;
    (ii) the **RNEA nominal path** ``tau_nom = RNEA_nom(q_meas, qd_meas, qdd_est) + friction_nom``.

    **Timing.** The frozen generator logs ``tau_cmd[k] = tau_cmd(k-1)`` (the command held over
    the interval ending at ``t_k``) while ``tau_nominal[k]`` uses the measurements at ``k``.
    The sensitivity therefore differentiates the controller at ``k-1`` and the nominal model at
    ``k``; getting this off by one is one of the injected mutations
    (``tests/test_stage2a_mutations.py``).

    **Acceleration-estimator path.** ``qdd_est`` is a causal Savitzky-Golay derivative of
    ``qd_meas``: a constant position bias leaves it unchanged, and a constant velocity bias
    also leaves it unchanged (the SG derivative weights sum to zero). Both are *measured*
    here rather than assumed -- the qd-bias columns include the estimator term via the
    explicit ``qdd`` argument, which is held at its observed value exactly because the
    analytic derivative of the estimator w.r.t. a constant bias is zero.
    """
    Tg, n = q_now.shape
    dq = np.zeros((Tg, n, n))
    dqd = np.zeros((Tg, n, n))

    def cmd(qm: np.ndarray, qdm: np.ndarray) -> np.ndarray:
        out = np.empty((Tg, n))
        for t in range(Tg):
            out[t] = np.clip(controller(qm[t], qdm[t], q_ref_prev[t], qd_ref_prev[t], qdd_ref_prev[t]), -torque_limit, torque_limit)
        return out

    def nom(qm: np.ndarray, qdm: np.ndarray, qddm: np.ndarray) -> np.ndarray:
        out = np.empty((Tg, n))
        for t in range(Tg):
            out[t] = nominal.torque(qm[t], qdm[t], qddm[t])
        return out

    for j in range(n):
        ep = np.zeros(n)
        ep[j] = delta_q
        d_cmd = (cmd(q_prev + ep, qd_prev) - cmd(q_prev - ep, qd_prev)) / (2 * delta_q)
        d_nom = (nom(q_now + ep, qd_now, qdd_now) - nom(q_now - ep, qd_now, qdd_now)) / (2 * delta_q)
        dq[:, :, j] = d_cmd - d_nom
        ev = np.zeros(n)
        ev[j] = delta_qd
        d_cmd_v = (cmd(q_prev, qd_prev + ev) - cmd(q_prev, qd_prev - ev)) / (2 * delta_qd)
        d_nom_v = (nom(q_now, qd_now + ev, qdd_now) - nom(q_now, qd_now - ev, qdd_now)) / (2 * delta_qd)
        dqd[:, :, j] = d_cmd_v - d_nom_v
    return dq, dqd


def build_episode_pathways(
    chain: ChainModel,
    signals: dict[str, np.ndarray],
    t_index: np.ndarray,
    *,
    episode_id: str,
    trajectory: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None,
    controller=None,
    nominal=None,
    torque_limit: np.ndarray | None = None,
    control_dt: float = 0.002,
    coulomb_eps: float = 0.05,
    stribeck_velocity: float = 0.15,
    delta_q: float = 1e-4,
    delta_qd: float = 1e-3,
    delta_delay: float | None = None,
) -> EpisodePathways:
    """Compute every deployment dictionary column of one episode on ``t_index``.

    ``trajectory`` is the exact ``(q_ref, qd_ref, qdd_ref)`` of the frozen episode
    (reconstructed deterministically from its seed); when omitted the reference derivatives
    are taken numerically from the logged ``q_ref`` column.
    """
    t_index = np.asarray(t_index, dtype=int)
    t_prev = np.maximum(t_index - 1, 0)
    q_full = np.asarray(signals["q_meas"], dtype=float)
    qd_full = np.asarray(signals["qd_meas"], dtype=float)
    q = q_full[t_index]
    qd = qd_full[t_index]
    qdd = np.asarray(signals["qdd_est"], dtype=float)[t_index]
    tau_cmd_full = np.asarray(signals["tau_cmd"], dtype=float)
    tau_cmd = tau_cmd_full[t_index]
    n = chain.n_links

    kin = forward_kinematics(chain, q)
    j_link = link_spatial_jacobians(kin)

    d_gain = tau_cmd.copy()
    d_viscous = qd.copy()
    d_coulomb = np.tanh(qd / coulomb_eps)
    d_stribeck = np.exp(-((qd / stribeck_velocity) ** 2)) * np.tanh(qd / coulomb_eps)
    y_load = payload_regressor(chain, q, qd, qdd)

    # F6: analytic local control  d e_tau / d Delta = d tau_cmd / dt (central difference)
    d_delay = np.gradient(tau_cmd_full, control_dt, axis=0)[t_index]
    # F6: explicit command-buffer finite difference over a *fractional* delay (linear
    #     interpolation between taps). It is deliberately **causal** (backward): a deployed
    #     detector only holds past commands, and a centred difference is undefined exactly at
    #     the window's last sample -- the sample the detector acts on.
    dd = float(delta_delay if delta_delay is not None else 2.0 * control_dt)
    d_delay_buffer = (tau_cmd - _delayed_command(tau_cmd_full, dd, control_dt)[t_index]) / dd

    if controller is not None and nominal is not None:
        if trajectory is not None:
            q_ref_f, qd_ref_f, qdd_ref_f = (np.asarray(a, dtype=float) for a in trajectory)
        else:
            q_ref_f = np.asarray(signals["q_ref"], dtype=float)
            qd_ref_f = np.gradient(q_ref_f, control_dt, axis=0)
            qdd_ref_f = np.gradient(qd_ref_f, control_dt, axis=0)
        tl = np.asarray(chain.torque_limit if torque_limit is None else torque_limit, dtype=float)
        d_sensor_q, d_sensor_qd = _finite_difference_sensitivities(
            controller, nominal, q, qd, qdd, q_full[t_prev], qd_full[t_prev],
            q_ref_f[t_prev], qd_ref_f[t_prev], qdd_ref_f[t_prev], tl,
            delta_q=delta_q, delta_qd=delta_qd,
        )
    else:
        d_sensor_q = np.zeros((len(t_index), n, n))
        d_sensor_qd = np.zeros((len(t_index), n, n))

    return EpisodePathways(
        episode_id=episode_id, t_index=t_index, n_links=n,
        d_gain=d_gain, d_viscous=d_viscous, d_coulomb=d_coulomb, d_stribeck=d_stribeck,
        y_load=y_load, j_link=j_link, r_link=kin.R_link,
        d_sensor_q=d_sensor_q, d_sensor_qd=d_sensor_qd, d_delay=d_delay, d_delay_buffer=d_delay_buffer,
        meta={"coulomb_eps": coulomb_eps, "stribeck_velocity": stribeck_velocity, "delta_q_rad": delta_q,
              "delta_qd_rad_s": delta_qd, "delta_delay_s": dd, "control_dt_s": control_dt,
              "trajectory_source": "reconstructed_from_seed" if trajectory is not None else "numerical_from_q_ref"},
    )


def _delayed_command(tau: np.ndarray, delay_s: float, dt: float) -> np.ndarray:
    """Fractional-delay resample of a command history (linear interpolation between taps).

    ``delay_s`` may be negative (advance); samples before the start are held at the first value.
    """
    T = tau.shape[0]
    idx = np.arange(T, dtype=float) - delay_s / dt
    idx = np.clip(idx, 0.0, T - 1.0)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, T - 1)
    w = (idx - lo)[:, None]
    return (1.0 - w) * tau[lo] + w * tau[hi]


# --------------------------------------------------------------------------- window assembly
def _stack_diag(diag: np.ndarray) -> np.ndarray:
    """(M, n) diagonals -> (n*M, n) block-stacked diagonal dictionary."""
    M, n = diag.shape
    D = np.zeros((n * M, n))
    for m in range(M):
        D[m * n : (m + 1) * n, :] = np.diag(diag[m])
    return D


def _stack_dense(cols: np.ndarray) -> np.ndarray:
    """(M, n, p) -> (n*M, p)."""
    M, n, p = cols.shape
    return cols.reshape(M * n, p)


def contact_columns(ep: EpisodePathways, rows: np.ndarray, link: int, r_link: np.ndarray | None) -> np.ndarray:
    """(n*M, 3 or 6) contact dictionary of one link on the window rows ``rows``.

    ``r_link is None`` -> the point-agnostic 6-column body-wrench form ``-J_l^T``;
    otherwise the 3-column point-force form ``-J_{l,p}^T`` at the link-frame offset.
    """
    J = ep.j_link[rows, link]  # (M,6,n)
    if r_link is None:
        return -np.concatenate([J[m].T for m in range(J.shape[0])], axis=0)
    R = ep.r_link[rows, link]  # (M,3,3)
    r_world = (R @ np.asarray(r_link, dtype=float)[None, :, None])[..., 0]  # (M,3)
    from certo_fdi.pathways.jacobians import skew

    Jp = J[:, 3:, :] - skew(r_world) @ J[:, :3, :]  # (M,3,n)
    return -np.concatenate([Jp[m].T for m in range(Jp.shape[0])], axis=0)


def family_dictionaries(ep: EpisodePathways, rows: np.ndarray) -> dict[str, np.ndarray]:
    """Non-contact family dictionaries on the window rows ``rows`` -> ``{key: (n*M, p)}``."""
    return {
        "F1_actuator": _stack_diag(ep.d_gain[rows]),
        "F2_viscous": _stack_diag(ep.d_viscous[rows]),
        "F2_coulomb": _stack_diag(ep.d_coulomb[rows]),
        "F2_stribeck": _stack_diag(ep.d_stribeck[rows]),
        "F3_payload": _stack_dense(ep.y_load[rows]),
        "F5_encoder_q": _stack_dense(ep.d_sensor_q[rows]),
        "F5_encoder_qd": _stack_dense(ep.d_sensor_qd[rows]),
        "F6_delay": _stack_dense(ep.d_delay_buffer[rows][:, :, None]),
    }


def dictionary_column_units() -> dict[str, list[str]]:
    """Units of every dictionary's parameter vector (recorded in the audit table)."""
    joint = [f"j{j + 1}" for j in range(7)]
    return {
        "F1_actuator": [f"efficiency_loss_fraction[{j}]" for j in joint],
        "F2_viscous": [f"N m s/rad[{j}]" for j in joint],
        "F2_coulomb": [f"N m[{j}]" for j in joint],
        "F2_stribeck": [f"N m[{j}]" for j in joint],
        "F3_payload": [f"{n} [{u}]" for n, u in zip(PAYLOAD_PARAM_NAMES, PAYLOAD_PARAM_UNITS)],
        "F4_contact_point": ["N", "N", "N"],
        "F4_contact_wrench": ["N m", "N m", "N m", "N", "N", "N"],
        "F5_encoder_q": [f"rad[{j}]" for j in joint],
        "F5_encoder_qd": [f"rad/s[{j}]" for j in joint],
        "F6_delay": ["s"],
    }


# --------------------------------------------------------------------------- batched builders
# The per-window Python loop over (link, candidate point) dominated the runtime; these build the
# whole (Nw, n*M, p) stack in one vectorised step. They are checked against the single-window
# builders above in tests/test_stage2a_dictionaries.py.
def contact_columns_batched(ep: EpisodePathways, rows: np.ndarray, link: int, r_link: np.ndarray | None) -> np.ndarray:
    """(Nw, n*M, 3 or 6) contact dictionaries for every window in ``rows`` (Nw, M)."""
    rows = np.asarray(rows, dtype=int)
    Nw, M = rows.shape
    if r_link is None:
        J = ep.j_link[:, link]                                   # (Tg, 6, n)
        cols = -np.swapaxes(J[rows], 2, 3)                       # (Nw, M, n, 6)
        return cols.reshape(Nw, M * ep.n_links, 6)
    from certo_fdi.pathways.jacobians import skew

    r_world = (ep.r_link[:, link] @ np.asarray(r_link, dtype=float)[None, :, None])[..., 0]  # (Tg,3)
    Jp = ep.j_link[:, link, 3:, :] - skew(r_world) @ ep.j_link[:, link, :3, :]                # (Tg,3,n)
    cols = -np.swapaxes(Jp[rows], 2, 3)                          # (Nw, M, n, 3)
    return cols.reshape(Nw, M * ep.n_links, 3)


def _stack_diag_batched(diag: np.ndarray, rows: np.ndarray) -> np.ndarray:
    """(Tg, n) diagonals + (Nw, M) rows -> (Nw, n*M, n)."""
    Nw, M = rows.shape
    n = diag.shape[1]
    D = np.zeros((Nw, M, n, n))
    idx = np.arange(n)
    D[:, :, idx, idx] = diag[rows]
    return D.reshape(Nw, M * n, n)


def _stack_dense_batched(cols: np.ndarray, rows: np.ndarray) -> np.ndarray:
    """(Tg, n, p) + (Nw, M) rows -> (Nw, n*M, p)."""
    Nw, M = rows.shape
    n, p = cols.shape[1], cols.shape[2]
    return cols[rows].reshape(Nw, M * n, p)


def family_dictionaries_batched(ep: EpisodePathways, rows: np.ndarray) -> dict[str, np.ndarray]:
    """Non-contact family dictionaries for every window in ``rows`` -> ``{key: (Nw, n*M, p)}``."""
    rows = np.asarray(rows, dtype=int)
    return {
        "F1_actuator": _stack_diag_batched(ep.d_gain, rows),
        "F2_viscous": _stack_diag_batched(ep.d_viscous, rows),
        "F2_coulomb": _stack_diag_batched(ep.d_coulomb, rows),
        "F2_stribeck": _stack_diag_batched(ep.d_stribeck, rows),
        "F3_payload": _stack_dense_batched(ep.y_load, rows),
        "F5_encoder_q": _stack_dense_batched(ep.d_sensor_q, rows),
        "F5_encoder_qd": _stack_dense_batched(ep.d_sensor_qd, rows),
        "F6_delay": _stack_dense_batched(ep.d_delay_buffer[:, :, None], rows),
    }
