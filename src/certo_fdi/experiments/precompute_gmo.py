"""Add the generalized-momentum-observer residual ``r_gmo`` to every episode file."""

from __future__ import annotations

import argparse
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import h5py
import numpy as np

from certo_fdi.anomaly.gmo import gmo_residual
from certo_fdi.data.franka_generator import nominal_chain_with_tool, reference_chain
from certo_fdi.data.windows import load_index
from certo_fdi.experiments.common import load_config


def _one(args):
    path, xml, nominal_v, nominal_c, gain = args
    with h5py.File(path, "r") as f:
        if "r_gmo" in f["signals"]:
            return path, "EXISTS"
        q = f["signals"]["q_meas"][()].astype(float)
        qd = f["signals"]["qd_meas"][()].astype(float)
        tau = f["signals"]["tau_meas"][()].astype(float)
        t = f["signals"]["t"][()]
        import json

        ctx = json.loads(str(f.attrs["context_json"]))
    chain = nominal_chain_with_tool(reference_chain(xml), int(ctx["tool_id"]), nominal_v, nominal_c)
    r = gmo_residual(chain, q, qd, tau, float(t[1] - t[0]), gain=gain)
    with h5py.File(path, "a") as f:
        f["signals"].create_dataset("r_gmo", data=r.astype(np.float32), compression="gzip", compression_opts=4)
        f["signals"]["r_gmo"].attrs["gain"] = gain
    return path, "OK"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--gain", type=float, default=20.0)
    ap.add_argument("--workers", type=int, default=max(1, min(12, (os.cpu_count() or 2) - 2)))
    args = ap.parse_args(argv)
    cfg, _ = load_config(args.config)
    rows = load_index(Path(args.data_root))
    pm = cfg["plant_mismatch"]
    jobs = [(r["path"], cfg["paths"]["mjcf_path"], pm["nominal_viscous_nms"], pm["nominal_coulomb_nm"], args.gain) for r in rows]
    n_ok = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for _, status in ex.map(_one, jobs, chunksize=4):
            n_ok += status in ("OK", "EXISTS")
    print(f"gmo residual written for {n_ok}/{len(jobs)} episodes")
    return 0 if n_ok == len(jobs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
