"""Stage 2A Phases 3-4: build the F1-F6 pathway dictionaries and audit their correctness.

Outputs
-------
``stage2a_pathway_dictionary_audit.csv``  rank / singular values / condition number /
    nullspace dimension / units / provenance of every dictionary, before and after whitening,
    plus the agreement between each **deployed** column and the **oracle** closed-loop
    sensitivity obtained by replaying the frozen simulator.
``stage2a_principal_angles.csv``  pairwise principal angles between fault-family dictionaries
    and between per-link contact dictionaries, per context stratum.
``stage2a_contact_observability.csv``  per-link Fisher information, smallest positive singular
    value and condition number, per context stratum.
``p4_tests/stage2a_oracle_sensitivity.csv``  the raw deployed-vs-oracle comparison rows.

The oracle sensitivities exist only to validate the deployed dictionaries; they are never an
input to a Stage 2A head.
"""

from __future__ import annotations

import csv
import json
import multiprocessing as mp
import time
from pathlib import Path
from typing import Any

import numpy as np

from certo_fdi.experiments.common import write_csv, write_json
from certo_fdi.experiments.stage2a_common import Stage, common_parser, episode_seed_map, truth_parameters
from certo_fdi.experiments.stage2a_pathway_pipeline import (
    WindowGrid,
    build_cache_parallel,
    episode_windows,
    fit_whiteners,
    load_pathways,
    truth_contact_point,
)
from certo_fdi.pathways.dictionaries import contact_columns, diagnostic_dictionaries, dictionary_column_units, family_dictionaries
from certo_fdi.pathways.geometry import dictionary_spectrum, fisher_information, principal_angles, subspace_overlap
from certo_fdi.pathways.jacobians import candidate_points
from certo_fdi.pathways.sensitivity import closed_loop_sensitivity, contact_oracle_sensitivity, direction_agreement, probes_for

ORACLE_EPISODES = 8          # stratified replay probes
ORACLE_CONTACT_LINKS = (1, 3, 5, 6)
AUDIT_WINDOWS_PER_EPISODE = 6
CONTACT_ONSET_S = 6.0        # mid-episode, well clear of the rest-to-motion blend-in
CONTACT_ONSET_WINDOW_S = 0.10  # the instantaneous comparison window after onset
ANGLE_EPISODES = 40


# --------------------------------------------------------------------------- oracle workers
def _oracle_worker(args):
    """One closed-loop replay probe (the pathway cache is built separately, before the pool)."""
    (eid, ctx_dict, seed, cfg_frozen, xml, truth, probe) = args
    from certo_fdi.data.schema import EpisodeContext
    from certo_fdi.pathways.sensitivity import closed_loop_sensitivity

    return {"episode_id": eid, **closed_loop_sensitivity(cfg_frozen, xml, truth, EpisodeContext(**ctx_dict), seed, eid, probe)}


def _oracle_contact_worker(args):
    (eid, ctx_dict, seed, cfg_frozen, xml, truth, link, r_link, direction, force, onset) = args
    from certo_fdi.data.schema import EpisodeContext
    from certo_fdi.pathways.sensitivity import contact_oracle_sensitivity

    res = contact_oracle_sensitivity(cfg_frozen, xml, truth, EpisodeContext(**ctx_dict), seed, eid, link, r_link, direction, force, onset)
    return {"episode_id": eid, **res}


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = common_parser("Stage 2A Phases 3-4: pathway dictionaries and their correctness audit")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--skip-oracle", action="store_true")
    args = ap.parse_args()
    st = Stage(args, "dictionaries")
    if not st.require_freeze():
        return 3
    import torch
    import yaml

    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.experiments.pipeline import load_checkpoint

    cfg = st.cfg
    bundle = st.bundle
    grid = WindowGrid.build(int(cfg["simulation"]["window_samples"]), int(cfg["pathway"]["window_time_points"]))
    st.log(f"window grid: offsets={grid.offsets.tolist()} stride={grid.sample_stride} first={grid.first_sample}")
    cache_root = st.layout.sub("p3_dictionaries") / "cache"
    seeds = episode_seed_map(st.data_root)

    with (st.data_root / "episode_index.csv").open(newline="", encoding="utf-8") as f:
        index_rows = list(csv.DictReader(f))
    by_id = {r["episode_id"]: r for r in index_rows}
    needed = [by_id[e] for e in (bundle.train_ids + bundle.val_ids + bundle.test_ids) if e in by_id]
    build_cache_parallel(needed, seeds, cfg, grid, st.data_root, cache_root, n_workers=args.workers, log=st.log)

    # ---------------------------------------------------------------- whitener (seed 0 model)
    seed0 = int(cfg["seed_list"][0])
    fc = cfg["models"]["frozen_best_config"]["chain_gnn_aug"]
    ckpt = st.layout.sub("checkpoints") / f"chain_gnn_aug_{fc['tag']}_seed{seed0}_frac{len(bundle.train_ids)}ep.pt"
    if not ckpt.exists():
        st.log(f"BLOCKED: frozen baseline checkpoint missing ({ckpt}); run the baseline phase first")
        return 4
    from certo_fdi.experiments.stage2a_common import ensure_model_cfg

    mcfg = ensure_model_cfg(cfg)
    info = load_checkpoint("chain_gnn_aug", ckpt, bundle, mcfg, st.device)
    model = info["model"]
    tc = TorchChain.from_chain(bundle.base_chain, dtype=torch.float32, device=st.device)
    healthy_ids = bundle.train_ids + bundle.val_ids
    t0 = time.time()
    healthy_w = [episode_windows(model, bundle.episodes[e], bundle, tc, grid, st.device) for e in healthy_ids]
    win_wh, inst_wh = fit_whiteners(healthy_w, cfg)
    st.log(f"whiteners fitted on {sum(len(h.label) for h in healthy_w)} healthy train+val windows ({time.time() - t0:.0f}s)")
    write_json(st.layout.results / "stage2a_whitening_diagnostics.json", {
        "window": win_wh.to_dict(), "instantaneous": inst_wh.to_dict(),
        "grid": {"window_samples": grid.window, "n_time_points": grid.n_points, "offsets": grid.offsets.tolist(),
                 "residual_dimension": int(grid.n_points * bundle.n_links)},
        "seed_used_for_the_correction": seed0,
        "rationale": __import__("certo_fdi.pathways.whitening", fromlist=["x"]).WINDOW_SUBSAMPLE_RATIONALE,
    })

    # ---------------------------------------------------------------- dictionary spectra
    units = dictionary_column_units()
    audit_rows: list[dict] = []
    rng = np.random.default_rng(20260816)
    audit_ids = [e for e in bundle.test_ids if bundle.episodes[e].kind == "healthy"][:6] + [e for e in bundle.test_ids if bundle.episodes[e].family == "F4_contact"][:6]
    for eid in audit_ids:
        ea = bundle.episodes[eid]
        pw = load_pathways(cache_root, eid)
        ew = episode_windows(model, ea, bundle, tc, grid, st.device)
        pick = rng.choice(len(ew.starts), size=min(AUDIT_WINDOWS_PER_EPISODE, len(ew.starts)), replace=False)
        for w in pick:
            rows_w = ew.rows[w]
            base = st.base_row(model="chain_gnn_aug", split=ea.split, fault_family=ea.family, seed=seed0,
                               controller=str(ea.context["controller"]), episode_id=eid, window_start=int(ew.starts[w]))
            fam = {**family_dictionaries(pw, rows_w), **diagnostic_dictionaries(pw, rows_w)}
            for key, D in fam.items():
                for whitened, Dm in (("raw", D), ("whitened", win_wh.whiten_dictionary(D))):
                    spec = dictionary_spectrum(Dm)
                    audit_rows.append({**base, "dictionary": key, "form": "window_stacked", "whitening": whitened,
                                       "parameter_units": " | ".join(units.get(key, [])), **{k: v for k, v in spec.items() if k != "singular_values"},
                                       "singular_values": json.dumps([round(v, 8) for v in spec["singular_values"]]),
                                       "sign_convention": "columns = d E_W / d theta with theta the physical fault parameter"})
            for l in range(bundle.n_links):
                D6 = contact_columns(pw, rows_w, l, None)
                for whitened, Dm in (("raw", D6), ("whitened", win_wh.whiten_dictionary(D6))):
                    spec = dictionary_spectrum(Dm)
                    audit_rows.append({**base, "dictionary": f"F4_contact_link{l}", "form": "window_stacked_body_wrench", "whitening": whitened,
                                       "parameter_units": " | ".join(units["F4_contact_wrench"]), **{k: v for k, v in spec.items() if k != "singular_values"},
                                       "singular_values": json.dumps([round(v, 8) for v in spec["singular_values"]]), "link": l,
                                       "sign_convention": "D = -J_l^T so the fitted coefficient is the contact wrench itself"})
                Di = -pw.j_link[rows_w[-1], l].astype(np.float64).T
                spec = dictionary_spectrum(inst_wh.whitener @ Di)
                audit_rows.append({**base, "dictionary": f"F4_contact_link{l}", "form": "instantaneous_body_wrench", "whitening": "whitened",
                                   "parameter_units": " | ".join(units["F4_contact_wrench"]), **{k: v for k, v in spec.items() if k != "singular_values"},
                                   "singular_values": json.dumps([round(v, 8) for v in spec["singular_values"]]), "link": l,
                                   "sign_convention": "D = -J_l^T"})
                for pname, r_link in candidate_points(bundle.base_chain)[l]:
                    D3 = win_wh.whiten_dictionary(contact_columns(pw, rows_w, l, r_link))
                    spec = dictionary_spectrum(D3)
                    audit_rows.append({**base, "dictionary": f"F4_contact_link{l}_{pname}", "form": "window_stacked_point_force", "whitening": "whitened",
                                       "parameter_units": " | ".join(units["F4_contact_point"]), **{k: v for k, v in spec.items() if k != "singular_values"},
                                       "singular_values": json.dumps([round(v, 8) for v in spec["singular_values"]]), "link": l, "candidate_point": pname,
                                       "sign_convention": "D = -J_{l,p}^T"})
    st.log(f"dictionary spectra: {len(audit_rows)} rows from {len(audit_ids)} episodes")

    # ---------------------------------------------------------------- principal angles + observability
    angle_rows: list[dict] = []
    obs_rows: list[dict] = []
    ids = [e for e in bundle.test_ids][:ANGLE_EPISODES]
    fam_keys = list(family_dictionaries(load_pathways(cache_root, ids[0]), np.arange(grid.n_points)).keys())
    for eid in ids:
        ea = bundle.episodes[eid]
        pw = load_pathways(cache_root, eid)
        ew = episode_windows(model, ea, bundle, tc, grid, st.device)
        pick = rng.choice(len(ew.starts), size=min(3, len(ew.starts)), replace=False)
        for w in pick:
            rows_w = ew.rows[w]
            base = st.base_row(model="chain_gnn_aug", split=ea.split, fault_family=ea.family, seed=seed0,
                               controller=str(ea.context["controller"]), episode_id=eid, window_start=int(ew.starts[w]),
                               speed_band=str(ea.context.get("speed_band", "")), region=str(ea.context.get("region_name", "")),
                               tool=str(ea.context.get("tool_name", "")))
            fam = {k: win_wh.whiten_dictionary(v) for k, v in family_dictionaries(pw, rows_w).items()}
            link = {l: win_wh.whiten_dictionary(contact_columns(pw, rows_w, l, None)) for l in range(bundle.n_links)}
            for i in range(len(fam_keys)):
                for j in range(i + 1, len(fam_keys)):
                    a, b = fam_keys[i], fam_keys[j]
                    th = principal_angles(fam[a], fam[b])
                    angle_rows.append({**base, "pair_kind": "fault_family", "a": a, "b": b,
                                       "min_principal_angle_rad": float(th.min()), "min_principal_angle_deg": float(np.degrees(th.min())),
                                       "max_principal_angle_deg": float(np.degrees(th.max())), "n_angles": int(th.size),
                                       "subspace_overlap": subspace_overlap(fam[a], fam[b])})
            for a in range(bundle.n_links):
                for b in range(a + 1, bundle.n_links):
                    th = principal_angles(link[a], link[b])
                    angle_rows.append({**base, "pair_kind": "contact_link", "a": f"link{a}", "b": f"link{b}",
                                       "min_principal_angle_rad": float(th.min()), "min_principal_angle_deg": float(np.degrees(th.min())),
                                       "max_principal_angle_deg": float(np.degrees(th.max())), "n_angles": int(th.size),
                                       "subspace_overlap": subspace_overlap(link[a], link[b])})
            for l in range(bundle.n_links):
                spec = dictionary_spectrum(link[l])
                fish = fisher_information(link[l])
                obs_rows.append({**base, "link": l, "form": "window_stacked_body_wrench", **fish,
                                 "rank": spec["rank"], "nullspace_dimension": spec["nullspace_dimension"],
                                 "sigma_min_positive": spec["singular_value_min_positive"], "condition_number": spec["condition_number"],
                                 "units": "whitened residual per N m / N; Fisher eigenvalues are dimensionless in whitened coordinates"})
    st.log(f"principal angles: {len(angle_rows)} rows; contact observability: {len(obs_rows)} rows")

    # ---------------------------------------------------------------- oracle sensitivities
    oracle_rows: list[dict] = []
    if not args.skip_oracle:
        frozen_cfg = yaml.safe_load((Path(args.repo_root) / "configs" / "frozen_dataset_protocol.yaml").read_text())
        truth = truth_parameters(st.data_root)
        xml = str(cfg["paths"]["mjcf_path"])
        probe_ids = [e for e in bundle.val_ids][:4] + [e for e in bundle.test_ids if bundle.episodes[e].kind == "healthy"][:ORACLE_EPISODES - 4]
        probes = probes_for(bundle.n_links,
                            encoder_delta=2e-3, gain_delta=0.02, viscous_delta=0.2, coulomb_delta=0.2,
                            delay_delta=float(cfg["pathway"]["delay_delta_s"]), payload_delta=0.05)
        tasks = []
        for eid in probe_ids:
            ea = bundle.episodes[eid]
            for pr in probes:
                tasks.append((eid, dict(ea.context), seeds[eid], frozen_cfg, xml, truth, pr))
        st.log(f"oracle closed-loop sensitivities: {len(tasks)} replays on {len(probe_ids)} episodes with {args.workers} workers...")
        t0 = time.time()
        results = []
        with mp.get_context("spawn").Pool(args.workers) as pool:
            for i, r in enumerate(pool.imap_unordered(_oracle_worker, tasks, chunksize=1), 1):
                results.append(r)
                if i % 20 == 0:
                    st.log(f"  oracle {i}/{len(tasks)} ({time.time() - t0:.0f}s)")
        st.log(f"oracle replays done ({time.time() - t0:.0f}s)")

        # contact oracle probes
        c_tasks = []
        for eid in probe_ids[:4]:
            ea = bundle.episodes[eid]
            for l in ORACLE_CONTACT_LINKS:
                c_tasks.append((eid, dict(ea.context), seeds[eid], frozen_cfg, xml, truth, l, np.array([0.0, 0.0, 0.06]), np.array([0.3, -0.6, 0.74]), 1.0, CONTACT_ONSET_S))
        with mp.get_context("spawn").Pool(args.workers) as pool:
            c_results = list(pool.imap_unordered(_oracle_contact_worker, c_tasks, chunksize=1))
        st.log(f"contact oracle replays done ({len(c_results)})")

        # compare against the deployed columns on the cached grid
        pw_cache = {eid: load_pathways(cache_root, eid) for eid in probe_ids}
        settle = int(round(float(cfg["simulation"]["eval_settle_s"]) / float(cfg["simulation"]["control_dt_s"])))
        for r in results:
            pw = pw_cache[r["episode_id"]]
            t_idx = pw.t_index
            keep = t_idx >= settle
            key, col = r["dictionary_key"], r["dictionary_column"]
            if key == "F1_actuator":
                dep = np.zeros((len(t_idx), pw.n_links)); dep[:, col] = pw.d_gain[:, col]
            elif key == "F2_viscous":
                dep = np.zeros((len(t_idx), pw.n_links)); dep[:, col] = pw.d_viscous[:, col] * float(np.asarray(truth["truth_viscous"])[col])
            elif key == "F2_coulomb":
                dep = np.zeros((len(t_idx), pw.n_links)); dep[:, col] = pw.d_coulomb[:, col] * float(np.asarray(truth["truth_coulomb"])[col])
            elif key == "F5_encoder_q":
                dep = pw.d_sensor_q[:, :, col]
            elif key == "F6_delay":
                dep = pw.d_delay_buffer
            elif key == "F3_payload":
                dep = pw.y_load[:, :, 0]
            else:
                continue
            oracle = np.asarray(r["sensitivity"])[t_idx]
            agree = direction_agreement(oracle, dep, keep)
            oracle_rows.append(st.base_row(model="chain_gnn_aug", seed=seeds[r["episode_id"]], fault_family=r["family"],
                                           split=bundle.episodes[r["episode_id"]].split,
                                           controller=str(bundle.episodes[r["episode_id"]].context["controller"]),
                                           episode_id=r["episode_id"], probe=r["key"], dictionary=key, column=col,
                                           delta=r["delta"], scheme=r["scheme"], units=r["units"], comparison="full_episode_after_settle", **agree))
        for r in c_results:
            pw = pw_cache[r["episode_id"]]
            t_idx = pw.t_index
            l = r["link"]
            dirn = np.asarray(r["direction"])
            R = pw.r_link[:, l].astype(np.float64)
            from certo_fdi.pathways.jacobians import skew

            r_world = (R @ np.asarray(r["r_link"])[None, :, None])[..., 0]
            J = pw.j_link[:, l].astype(np.float64)
            Jp = J[:, 3:, :] - skew(r_world) @ J[:, :3, :]
            dep = -np.einsum("tkn,k->tn", Jp, dirn)
            oracle = np.asarray(r["sensitivity"])[t_idx]
            dt_s = float(cfg["simulation"]["control_dt_s"])
            k0 = int(round(CONTACT_ONSET_S / dt_s))
            early = (t_idx >= k0) & (t_idx < k0 + int(round(CONTACT_ONSET_WINDOW_S / dt_s)))
            oracle_rows.append(st.base_row(model="chain_gnn_aug", seed=seeds[r["episode_id"]], fault_family="F4_contact",
                                           split=bundle.episodes[r["episode_id"]].split, controller=str(bundle.episodes[r["episode_id"]].context["controller"]),
                                           episode_id=r["episode_id"], probe=r["key"], dictionary=f"F4_contact_link{l}", column=-1,
                                           delta=r["force_n"], scheme=r["scheme"], units=r["units"], link=l,
                                           comparison="onset_window_instantaneous", onset_s=CONTACT_ONSET_S, **direction_agreement(oracle, dep, early)))
            oracle_rows.append(st.base_row(model="chain_gnn_aug", seed=seeds[r["episode_id"]], fault_family="F4_contact",
                                           split=bundle.episodes[r["episode_id"]].split, controller=str(bundle.episodes[r["episode_id"]].context["controller"]),
                                           episode_id=r["episode_id"], probe=r["key"], dictionary=f"F4_contact_link{l}", column=-1,
                                           delta=r["force_n"], scheme=r["scheme"], units=r["units"], link=l,
                                           comparison="full_episode_closed_loop", onset_s=CONTACT_ONSET_S, **direction_agreement(oracle, dep, t_idx >= k0)))
        write_csv(st.layout.sub("p4_tests") / "stage2a_oracle_sensitivity.csv", oracle_rows)
        st.log(f"oracle vs deployed comparison: {len(oracle_rows)} rows")

    # fold the oracle agreement into the audit table as one summary row per dictionary
    if oracle_rows:
        import pandas as pd

        od = pd.DataFrame(oracle_rows)
        for (dic, comp), g in od.groupby(["dictionary", "comparison"]):
            audit_rows.append(st.base_row(model="chain_gnn_aug", seed=seed0, fault_family="", split="ALL",
                                          dictionary=dic, form="oracle_agreement", whitening="n/a",
                                          comparison=comp, n_probes=int(len(g)),
                                          median_angle_deg=float(g["angle_deg"].median()),
                                          median_abs_cosine=float(g["cosine"].abs().median()),
                                          median_relative_error=float(g["relative_error"].median()),
                                          median_norm_ratio=float(g["norm_ratio_deployed_over_oracle"].median()),
                                          note="deployed column vs frozen-simulator closed-loop finite difference; sign-agnostic angle"))

    st.write_table("stage2a_pathway_dictionary_audit.csv", audit_rows,
                   units="singular values in whitened residual units per parameter unit; angles in degrees",
                   schema={"whitening": "raw = D, whitened = W_0 D", "form": "window_stacked | instantaneous | point_force | oracle_agreement"})
    st.write_table("stage2a_principal_angles.csv", angle_rows,
                   units="angles in radians and degrees; subspace_overlap = mean cos^2 of the principal angles",
                   schema={"pair_kind": "fault_family | contact_link"})
    st.write_table("stage2a_contact_observability.csv", obs_rows,
                   units="Fisher eigenvalues dimensionless in whitened coordinates; sigma in whitened residual per N",
                   schema={"fisher_eigenvalue_min_positive": "contact observability of that link in that window"})
    write_json(st.layout.results / "stage2a_dictionary_summary.json", {
        "n_audit_rows": len(audit_rows), "n_angle_rows": len(angle_rows), "n_observability_rows": len(obs_rows),
        "n_oracle_rows": len(oracle_rows), "family_keys": fam_keys, "candidate_points": [n for n, _ in candidate_points(bundle.base_chain)[0]],
        "grid": {"window_samples": grid.window, "n_time_points": grid.n_points, "offsets": grid.offsets.tolist()},
        "cache_root": str(cache_root), "n_cached": len(list(cache_root.glob("*.npz"))),
    })
    st.finish({"n_audit_rows": len(audit_rows)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
