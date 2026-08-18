"""Stage config loading with a content hash (``config_sha``)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .paths import PersistLayout, resolve_persist_root
from .provenance import sha256_text


@dataclass(frozen=True)
class StageConfig:
    raw: dict[str, Any]
    config_sha: str
    source_path: Path

    @property
    def persist_root(self) -> Path:
        return resolve_persist_root(self.raw.get("storage", {}).get("persistent_root"))

    @property
    def layout(self) -> PersistLayout:
        return PersistLayout(self.persist_root)

    @property
    def run_id(self) -> str:
        run_id = os.environ.get("CERTO_RUN_ID") or self.raw.get("run", {}).get("run_id")
        if not run_id:
            raise ValueError("run_id missing: set CERTO_RUN_ID or run.run_id in the config")
        return str(run_id)

    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self.raw
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node


def load_config(path: str | os.PathLike[str]) -> StageConfig:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    return StageConfig(
        raw=yaml.safe_load(text) or {},
        config_sha=sha256_text(text),
        source_path=source.resolve(),
    )
