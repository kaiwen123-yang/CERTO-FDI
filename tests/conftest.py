from __future__ import annotations

from pathlib import Path

import pytest

from certo_fdi.config import build_closed_loop_params, load_yaml


@pytest.fixture(scope="session")
def smoke_config():
    root = Path(__file__).resolve().parents[1]
    return load_yaml(root / "configs" / "experiments" / "smoke.yaml")


@pytest.fixture(scope="session")
def params(smoke_config):
    return build_closed_loop_params(smoke_config)
