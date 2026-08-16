from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("OMP_NUM_THREADS", "4")


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(260815)


def _has(module: str) -> bool:
    try:
        __import__(module)
    except Exception:  # pragma: no cover - environment dependent
        return False
    return True


HAS_MUJOCO = _has("mujoco")
HAS_PIN = _has("pinocchio")
HAS_TORCH = _has("torch")

requires_sim = pytest.mark.skipif(not (HAS_MUJOCO and HAS_PIN), reason="mujoco/pinocchio unavailable")
requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="torch unavailable")
