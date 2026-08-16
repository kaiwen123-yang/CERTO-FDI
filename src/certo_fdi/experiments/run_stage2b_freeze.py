"""Stage 2B Phase 0: input provenance freeze and reproduction of the frozen Stage 2A results.

Three mandatory hashes are checked before anything is computed (kickoff §B):

* the Stage 2A FULL review package;
* the Stage 2A branch head, locally **and** on the remote;
* the frozen dataset content manifest.

Any mismatch writes ``BLOCKED_INPUT_PROVENANCE`` and stops scientific evaluation; the runner
still completes everything that does not depend on the mismatched input so a failure review
package can be produced.

It then reproduces, inside this run:

* the frozen ``chain_gnn_aug`` healthy encoder (retrained from scratch at H40, three seeds) --
  this doubles as the H40 arm of the Phase 4 learning curve;
* the Stage 2A contact localizer (episode-level F4 top-1 and mean chain distance).

Both must land within 2 % relative of the frozen references or the stage is ``BLOCKED``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

from certo_fdi.experiments.common import sha256_file, utc_now, write_csv, write_json
from certo_fdi.experiments.stage2b_common import Stage, common_parser
from certo_fdi.paths import git_sha
from certo_fdi.stage2b.decision_stage2b import reproduction_gate


def _mount_info(path: Path) -> dict:
    out = subprocess.run(["findmnt", "-T", str(path), "-n", "-o", "SOURCE,FSTYPE,OPTIONS"],
                         check=False, text=True, capture_output=True).stdout.strip()
    p = out.split(None, 2)
    return {"raw": out, "source": p[0] if p else "", "fstype": p[1] if len(p) > 1 else "", "options": p[2] if len(p) > 2 else ""}


def _find_stage2a_package(storage: Path, expect_sha: str) -> dict:
    """Search only the finite locations the contract allows.

    Deliberately **not** a recursive scan: ``/mnt/c`` and ``/mnt/g`` are 9p/drvfs mounts where an
    ``rglob`` over a user profile takes minutes and looks like a hang. The contract lists
    specific directories, so each is globbed exactly one level deep.
    """
    cands: list[Path] = []
    for d in (storage / "06_review_exchange" / "to_review" / "full",
              storage / "06_review_exchange" / "to_review" / "thin",
              Path.home() / "Downloads"):
        if d.is_dir():
            cands += sorted(d.glob("CERTO_FDI_stage2a_*_FULL.zip"))
    users = Path("/mnt/c/Users")
    if users.is_dir():
        for user in sorted(users.glob("*")):
            dl = user / "Downloads"
            if dl.is_dir():
                cands += sorted(dl.glob("CERTO_FDI_stage2a_*_FULL.zip"))
    ref = storage / "05_reference_results" / "stage2a"
    if ref.is_dir():
        for d in sorted(ref.glob("*")):
            cands += sorted(d.glob("CERTO_FDI_stage2a_*_FULL.zip"))
    seen = []
    for p in sorted(set(cands)):
        sha = sha256_file(p)
        seen.append({"path": str(p), "sha256": sha, "size_bytes": p.stat().st_size, "match": sha == expect_sha})
        if sha == expect_sha:
            return {"found": True, "path": str(p), "sha256": sha, "size_bytes": p.stat().st_size, "candidates": seen}
    return {"found": False, "path": None, "sha256": None, "candidates": seen}


def main() -> int:
    ap = common_parser("Stage 2B Phase 0: input freeze and reproduction")
    ap.add_argument("--skip-reproduction", action="store_true")
    args = ap.parse_args()
    st = Stage(args, "freeze")
    cfg = st.cfg
    fi = cfg["frozen_inputs"]
    storage = Path(cfg["paths"]["persistent_root"])
    blocked: list[str] = []

    # ---------------------------------------------------------------- storage
    mount = _mount_info(storage)
    disk = shutil.disk_usage(storage)
    st.log(f"storage {storage}: {mount['source']} ({mount['fstype']}), free {disk.free / 1e9:.0f} GB")
    if not storage.is_dir() or mount["fstype"] in ("", "tmpfs", "overlay"):
        blocked.append(f"{storage} is not a real persistent mount (fstype={mount['fstype']!r})")
    if disk.free / 1e9 < 5.0:
        blocked.append(f"less than 5 GB free on {storage}")

    # ---------------------------------------------------------------- 1. Stage 2A package
    pkg = _find_stage2a_package(storage, fi["stage2a_full_zip_sha256"])
    if pkg["found"]:
        st.log(f"Stage 2A FULL package MATCH: {pkg['path']}")
    else:
        blocked.append(f"Stage 2A FULL package sha256 {fi['stage2a_full_zip_sha256']} not found among {len(pkg['candidates'])} candidates")
        st.log(f"BLOCKED_INPUT_PROVENANCE: Stage 2A package mismatch ({len(pkg['candidates'])} candidates seen)")

    # ---------------------------------------------------------------- 2. Stage 2A git SHA
    base_branch = cfg["repository"]["base_branch"]
    local_sha = subprocess.run(["git", "-C", str(st.repo_root), "rev-parse", base_branch],
                               check=False, text=True, capture_output=True).stdout.strip()
    remote_out = subprocess.run(["git", "-C", str(st.repo_root), "ls-remote", "origin", f"refs/heads/{base_branch}"],
                                check=False, text=True, capture_output=True).stdout.strip()
    remote_sha = remote_out.split()[0] if remote_out else ""
    git_ok = local_sha == fi["stage2a_git_sha"] and remote_sha == fi["stage2a_git_sha"]
    st.log(f"Stage 2A git sha local={local_sha[:12]} remote={remote_sha[:12]} expected={fi['stage2a_git_sha'][:12]} -> {'MATCH' if git_ok else 'MISMATCH'}")
    if not git_ok:
        blocked.append(f"Stage 2A git sha mismatch (local {local_sha}, remote {remote_sha}, expected {fi['stage2a_git_sha']})")

    # the Stage 2B branch must actually descend from that commit
    merge_base = subprocess.run(["git", "-C", str(st.repo_root), "merge-base", "HEAD", fi["stage2a_git_sha"]],
                                check=False, text=True, capture_output=True).stdout.strip()
    stacked_ok = merge_base == fi["stage2a_git_sha"]
    if not stacked_ok:
        blocked.append(f"the Stage 2B branch does not descend from {fi['stage2a_git_sha']} (merge-base {merge_base})")

    # ---------------------------------------------------------------- 3. dataset content manifest
    data_root = st.data_root
    if not data_root.is_dir():
        blocked.append(f"frozen dataset root missing: {data_root}")
        write_json(st.layout.results / "stage2b_input_freeze.json",
                   {"gate": "BLOCKED_INPUT_PROVENANCE", "blocked": blocked})
        return 2
    with (data_root / "episode_index.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    st.log(f"content-hashing {len(rows)} frozen episodes ...")
    t0 = time.time()
    per_ep = []
    for r in rows:
        p = Path(r["path"])
        per_ep.append({"episode_id": r["episode_id"], "kind": r["kind"], "partition": r["partition"],
                       "split": r["split"], "family": r["family"], "exists": p.exists(),
                       "sha256_content_now": sha256_file(p) if p.exists() else "MISSING"})
    joint = hashlib.sha256("\n".join(f"{r['episode_id']},{r['sha256_content_now']}"
                                     for r in sorted(per_ep, key=lambda x: x["episode_id"])).encode()).hexdigest()
    write_csv(st.layout.sub("provenance") / "frozen_episode_sha256_manifest.csv", per_ep)
    man_ok = joint == fi["dataset_content_manifest_sha256"]
    st.log(f"dataset content manifest {joint[:16]} expected {fi['dataset_content_manifest_sha256'][:16]} -> {'MATCH' if man_ok else 'MISMATCH'} ({time.time() - t0:.0f}s)")
    if not man_ok:
        blocked.append(f"dataset content manifest mismatch (got {joint}, expected {fi['dataset_content_manifest_sha256']})")

    mjcf = Path(cfg["paths"]["mjcf_path"])
    mjcf_sha = sha256_file(mjcf) if mjcf.exists() else "MISSING"
    if mjcf_sha != fi["mjcf_sha256"]:
        blocked.append(f"MJCF sha mismatch: {mjcf_sha}")

    # ---------------------------------------------------------------- historical PR heads untouched
    expected_heads = {
        "stage/stage1-closedloop-certificate": "07850efcd8adb82dcaf9048200e53cb8dfa44f00",
        "stage/stage1r-ligra-representation": "4e94370696c193770c8f270c627e50b07cac13ee",
        "stage/stage1r-b-equivariant-capacity-audit": "11134fb695b1c70c9664150d8d70a9670b95de51",
        "stage/stage2a-chain-jacobian-pathway-audit": fi["stage2a_git_sha"],
    }
    ls = subprocess.run(["git", "-C", str(st.repo_root), "ls-remote", "origin", "refs/heads/stage/*"],
                        check=False, text=True, capture_output=True).stdout
    remote_heads = {ln.split("\t")[1].replace("refs/heads/", ""): ln.split("\t")[0] for ln in ls.strip().splitlines() if "\t" in ln}
    pr_rows = []
    for br, exp in expected_heads.items():
        got = remote_heads.get(br, "")
        ok = got == exp
        pr_rows.append({"branch": br, "expected_head": exp, "observed_head": got, "unchanged": ok})
        if not ok:
            blocked.append(f"historical branch {br} head changed ({got} != {exp})")
    st.log(f"historical PR heads unchanged: {all(r['unchanged'] for r in pr_rows)}")

    gate = "BLOCKED_INPUT_PROVENANCE" if blocked else "PASS"
    freeze = {
        "gate": gate,
        "blocked": blocked,
        "run_id": st.layout.run_id,
        "timestamp_utc": utc_now(),
        "git": {"sha": git_sha(st.repo_root), "base_branch": base_branch, "base_local_sha": local_sha,
                "base_remote_sha": remote_sha, "stacked_on_stage2a": stacked_ok,
                "dirty": bool(subprocess.run(["git", "-C", str(st.repo_root), "status", "--porcelain"],
                                             check=False, text=True, capture_output=True).stdout.strip())},
        "storage": {"root": str(storage), "mount": mount,
                    "free_gb": disk.free / 1e9, "total_gb": disk.total / 1e9},
        "stage2a_package": pkg,
        "stage2a_git_sha": fi["stage2a_git_sha"],
        "dataset_content_manifest_sha256": joint,
        "dataset_content_manifest_expected": fi["dataset_content_manifest_sha256"],
        "dataset_root": str(data_root),
        "n_frozen_episodes": len(rows),
        "mjcf_sha256": mjcf_sha,
        "kickoff_zip_sha256": fi["stage2b_kickoff_zip_sha256"],
        "historical_branch_heads": pr_rows,
        "regenerate_frozen_data": False,
        "notes": [
            "The episode_index.csv sha256 column predates the in-place r_gmo append; the content hashes "
            "recomputed here are what every Stage 2B table cites (identical convention to Stage 2A).",
            "Stage 2B is a stacked branch: the Stage 2A implementation is inherited, not copied.",
        ],
    }
    write_json(st.layout.results / "stage2b_input_freeze.json", freeze)
    st.log(f"input freeze gate: {gate}" + (f" -- blocked: {blocked}" if blocked else ""))
    if blocked:
        st.finish({"gate": gate})
        return 3

    if args.skip_reproduction:
        st.finish({"gate": gate})
        return 0

    # ---------------------------------------------------------------- reproduction
    st.freeze = freeze
    st.manifest_sha = joint
    rc = _reproduce(st)
    st.finish({"gate": gate, "reproduction": rc})
    return rc


def _reproduce(st: Stage) -> int:
    """Retrain chain_gnn_aug at H40 (3 seeds) and reproduce the Stage 2A contact localizer."""
    import torch

    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.experiments.evaluation_chain_baseline import evaluate_run_stage1rb
    from certo_fdi.experiments.pipeline import load_checkpoint, train_model
    from certo_fdi.experiments.run_stage2a_baseline import summarise
    from certo_fdi.experiments.stage2b_common import ensure_model_cfg, train_cfg
    from certo_fdi.experiments.common import seed_everything

    cfg = ensure_model_cfg(st.cfg)
    bundle = st.bundle
    seeds = [int(s) for s in cfg["seed_list"]]
    fc = cfg["models"]["frozen_best_config"]["chain_gnn_aug"]
    tcfg = train_cfg(cfg)
    ckpt_dir = st.layout.sub("checkpoints")
    runs = st.layout.sub("p0_freeze") / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    tables: dict[str, list[dict]] = {k: [] for k in ("healthy_prediction", "detection", "ood_healthy", "localization", "localization_detail", "frame_invariance", "latency", "heads")}
    train_infos = []
    for seed in seeds:
        out_json = runs / f"chain_gnn_aug_H40_seed{seed}.json"
        if out_json.exists():
            res = json.loads(out_json.read_text())
            st.log(f"[H40 seed {seed}] loaded cached reproduction job")
        else:
            seed_everything(seed)
            t0 = time.time()
            info = train_model("chain_gnn_aug", seed, list(bundle.train_ids), bundle, cfg, ckpt_dir, st.device,
                               epochs=tcfg["epochs"], batch_size=tcfg["batch_size"], lr=float(fc["lr"]),
                               patience=tcfg["patience"], min_epochs=tcfg["min_epochs"], log=st.lines,
                               scheduler=fc["scheduler"], weight_decay=tcfg["weight_decay"],
                               grad_clip=tcfg["grad_clip"], tag=fc["tag"])
            st.log(f"[H40 seed {seed}] trained: params={info['n_params']} epochs={info['epochs_run']} best_val={info['best_val_loss']:.4f} ({time.time() - t0:.0f}s)")
            brow = {"run_id": st.layout.run_id, "git_sha": git_sha(st.repo_root), "config_sha256": st.cfg_sha,
                    "dataset_sha256_or_manifest_sha": st.manifest_sha, "model": info["name"], "seed": seed,
                    "split": "", "checkpoint_sha256": info["checkpoint_sha256"], "status": "OK",
                    "provisional": False, "strict_claim": "", "training_fraction": 1.0,
                    "config_tag": fc["tag"], "lr": float(fc["lr"]), "scheduler": fc["scheduler"],
                    "healthy_total": 40}
            ev = evaluate_run_stage1rb(info["model"], info, list(bundle.train_ids), bundle, cfg, brow, st.device,
                                       full=True, frame_manifest=None, quantile=0.995, log=st.lines,
                                       acceleration_diagnostic=False)
            res = {"train_info": [{k: v for k, v in info.items() if k != "model"}], **ev}
            res["train_info"][0].update({"training_fraction": 1.0, "seed": seed, "healthy_total": 40,
                                         "n_train_episodes": len(bundle.train_ids)})
            write_json(out_json, res)
            del info
            if st.device.startswith("cuda"):
                torch.cuda.empty_cache()
        for k in tables:
            tables[k] += res.get(k, [])
        train_infos += res.get("train_info", [])

    summary = summarise(tables)
    m = summary.get("chain_gnn_aug", {})
    ref = cfg["baseline"]["reference"]
    observed_encoder = {
        "n_params": float(train_infos[0]["n_params"]) if train_infos else float("nan"),
        "auroc_all": m.get("auroc_ALL", float("nan")),
        "auroc_s1": m.get("auroc_S1", float("nan")),
        "auroc_s2_s4": float(np.mean([m.get("auroc_S2", float("nan")), m.get("auroc_S4", float("nan"))])),
        "healthy_rmse_s0_nm": m.get("rmse_post_S0", float("nan")),
    }
    gate_encoder = reproduction_gate(observed_encoder, {**ref, "n_params": cfg["models"]["parameter_count"]},
                                     float(cfg["baseline"]["reproduction_tolerance_relative"]))
    st.log(f"encoder reproduction gate: {gate_encoder['gate']} (worst {gate_encoder['worst_relative_deviation']:.4f})")
    for r in gate_encoder["rows"]:
        st.log(f"  {r['metric']:22s} ref={r['reference']} obs={r['observed']} rel={r['relative_deviation']} {r['status']}")

    for k, rowsk in tables.items():
        if rowsk:
            write_csv(st.layout.sub("p0_freeze") / f"stage2b_repro_{k}.csv", rowsk)
    write_csv(st.layout.sub("p0_freeze") / "stage2b_repro_train_info.csv", train_infos)
    write_json(st.layout.results / "stage2b_baseline_metrics_summary.json", summary)

    rows = []
    for r in gate_encoder["rows"]:
        rows.append(st.base_row(method="chain_gnn_aug", partition="frozen_test", split="ALL", seed="mean",
                                fault_family="ALL", quantity=r["metric"], reference=r["reference"],
                                observed=r["observed"], relative_deviation=r["relative_deviation"],
                                within_tolerance=r["within_tolerance"], status=r["status"],
                                tolerance=gate_encoder["tolerance"], reference_source="Stage 2A frozen (PR #4, bcf2ad5)"))
    st.write_table("stage2b_baseline_reproduction.csv", rows,
                   units="AUROC dimensionless; RMSE in N m; relative_deviation dimensionless",
                   schema={"quantity": "reproduced frozen metric", "reference_source": "where the frozen value comes from"})
    write_json(st.layout.results / "stage2b_reproduction_gate.json",
               {"encoder": gate_encoder, "observed_encoder": observed_encoder,
                "frozen_reference": {**ref, "n_params": cfg["models"]["parameter_count"]},
                "note": "the contact-localizer reproduction is added by run_stage2b_loadpath (it needs the pathway cache)"})
    return 0 if gate_encoder["gate"] == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
