"""Run the official voraus-AD training for several seeds and emit a JSON trace.

Standalone on purpose: it has to execute inside the official Track A environment
(Python 3.9 / torch 1.12) and inside the Track B environment (Python 3.10 / torch
2.13), neither of which has certo_fdi_reset installed. It therefore imports nothing
but the official code and the standard library.

It does NOT modify the official source. It overrides two configuration fields in
memory before calling train.train(), which is exactly what the project's own
tests/test_train.py does for `epochs`.

    python scripts/voraus_seed_sweep.py --seeds 260818,260819,260820 --epochs 10 \
        --out /path/to/track_a_seeds.json
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--track", required=True, choices=["A", "B"])
    args = parser.parse_args()

    import numpy
    import torch

    sys.path.insert(0, str(Path.cwd()))
    import train  # the official module, unmodified

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    device = str(train.DEVICE)
    runs = []

    original_epochs = train.configuration.epochs
    original_seed = train.configuration.seed
    try:
        for seed in seeds:
            train.configuration.epochs = args.epochs
            train.configuration.seed = seed
            # train.train() reads configuration.seed for the dataloader split, but the
            # global RNG is seeded at import time, so re-seed here to make each run of
            # the sweep independent and reproducible.
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            numpy.random.seed(seed)
            random.seed(seed)

            # Capture the configuration AS RUN, before the finally block restores the
            # official defaults. Dumping train.configuration after the loop records
            # seed=177 / epochs=70 and misrepresents what actually executed.
            config_as_run = json.loads(train.configuration.json())

            started = time.time()
            result = train.train()
            elapsed = time.time() - started

            runs.append(
                {
                    "seed": seed,
                    "wall_seconds": round(elapsed, 3),
                    "epochs": [
                        {"epoch": i, "auroc_mean": float(r["aurocMean"])}
                        for i, r in enumerate(result)
                    ],
                    "final_auroc_mean": float(result[-1]["aurocMean"]),
                    "best_auroc_mean": max(float(r["aurocMean"]) for r in result),
                    "config_as_run": config_as_run,
                }
            )
            print(
                f"seed {seed}: final={runs[-1]['final_auroc_mean']:.4f} "
                f"best={runs[-1]['best_auroc_mean']:.4f} in {elapsed:.1f}s",
                flush=True,
            )
    finally:
        train.configuration.epochs = original_epochs
        train.configuration.seed = original_seed

    payload = {
        "track": args.track,
        "device": device,
        "epochs_per_run": args.epochs,
        "seeds": seeds,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "cudnn": (torch.backends.cudnn.version() if torch.cuda.is_available() else None),
        "gpu": (torch.cuda.get_device_name(0) if torch.cuda.is_available() else None),
        "numpy": numpy.__version__,
        # The official defaults, restored. The per-run overrides that actually applied
        # are in each run's "config_as_run", and in "seeds"/"epochs_per_run".
        "config_defaults_after_restore": json.loads(train.configuration.json()),
        "runs": runs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
