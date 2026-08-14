from __future__ import annotations

import json
from pathlib import Path

from certo_fdi.experiments.common import status_metadata, write_csv_with_schema


def test_output_schema_statuses_are_explicit_and_disjoint(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    contract = json.loads((root / "schemas/stage1_output_contract.json").read_text())
    metadata = {
        "run_id": "run_test_deadbee",
        "seed": 260809,
        "git_sha": "deadbeef",
        "config_sha256": "0" * 64,
    }
    row = status_metadata(
        metadata,
        strict_certificate=False,
        empirical_screening=True,
        provisional=False,
    )
    assert set(contract["required_common_columns"]).issubset(row)
    assert not (row["strict_certificate"] and row["empirical_screening"])
    path = tmp_path / "example.csv"
    write_csv_with_schema([row], path)
    assert path.exists()
    assert path.with_suffix(".schema.json").exists()
