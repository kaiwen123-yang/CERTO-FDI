"""Phase M migration tests: classification, verification, and the source-safety rule."""

from __future__ import annotations

import shutil
from pathlib import Path

from certo_fdi_reset.paths import PersistLayout
from certo_fdi_reset.storage_migration import (
    ArtifactClass,
    classify,
    destination_for,
    inventory,
    migrate,
    write_inventory,
)

RUN_ID = "run_test_paper_reset"


def _scratchpad(tmp_path: Path) -> Path:
    src = tmp_path / "scratchpad"
    (src / "L1_discovery" / "literature_raw_export" / "arxiv").mkdir(parents=True)
    (src / "L1_discovery" / "literature_raw_export" / "arxiv" / "Q001.xml").write_text("<feed/>")
    (src / "L1_discovery" / "literature_deduplicated_library.csv").write_text("doi,title\n1,x\n")
    (src / "L1_discovery" / "database_availability.csv").write_text("database,status\nx,OK\n")
    (src / "L1_discovery.log").write_text("log line\n")
    return src


def test_classification_rules_cover_the_l1_artifacts():
    assert classify("L1_discovery/literature_raw_export/arxiv/Q001.xml") is (
        ArtifactClass.LITERATURE_RAW_EXPORT
    )
    assert classify("L1_discovery/literature_deduplicated_library.csv") is (
        ArtifactClass.LITERATURE_DERIVED_TABLE
    )
    assert classify("L1_discovery/database_availability.csv") is (
        ArtifactClass.LITERATURE_ACCESS_RECORD
    )
    assert classify("chase.log") is ArtifactClass.RUN_LOG
    assert classify("something_new.bin") is ArtifactClass.UNCLASSIFIED


def test_unclassified_is_quarantined_not_filed_by_resemblance(tmp_path):
    layout = PersistLayout(tmp_path)
    dest = destination_for("mystery.bin", ArtifactClass.UNCLASSIFIED, layout, RUN_ID)
    assert dest == layout.run_dir(RUN_ID) / "migrated_unclassified" / "mystery.bin"
    assert layout.literature_metadata not in dest.parents


def test_raw_exports_keep_their_subtree_under_frozen_sources(tmp_path):
    layout = PersistLayout(tmp_path)
    rel = "L1_discovery/literature_raw_export/crossref/Q007.json"
    assert destination_for(rel, ArtifactClass.LITERATURE_RAW_EXPORT, layout, RUN_ID) == (
        layout.literature_metadata / rel
    )


def test_migration_verifies_every_file_and_keeps_the_source(tmp_path):
    src = _scratchpad(tmp_path)
    layout = PersistLayout(tmp_path / "persist")
    before = inventory(src)

    result = migrate(src, layout, RUN_ID)

    assert result.ok, result.errors
    assert len(result.records) == len(before) == 4
    assert result.bytes_after == result.bytes_before
    for record in result.records:
        assert record.sha256_after == record.sha256_before
        assert record.dest_path.is_file()
    # §4.2.7-8: the source survives a successful migration.
    assert src.is_dir()
    assert len(inventory(src)) == 4
    # Staging is cleaned up only on full success.
    assert result.staging_dir is None


def test_immutable_classes_become_read_only_logs_do_not(tmp_path):
    src = _scratchpad(tmp_path)
    layout = PersistLayout(tmp_path / "persist")

    result = migrate(src, layout, RUN_ID)

    by_rel = {r.relpath: r for r in result.records}
    raw = by_rel["L1_discovery/literature_raw_export/arxiv/Q001.xml"]
    log = by_rel["L1_discovery.log"]
    assert raw.read_only is True
    assert raw.dest_path.stat().st_mode & 0o222 == 0
    assert log.read_only is None
    assert log.dest_path.stat().st_mode & 0o200


def test_a_truncated_copy_fails_loudly(tmp_path, monkeypatch):
    src = _scratchpad(tmp_path)
    layout = PersistLayout(tmp_path / "persist")

    real_copy = shutil.copy2

    def truncating_copy(source, dest, *args, **kwargs):
        real_copy(source, dest, *args, **kwargs)
        if Path(source).name == "Q001.xml":
            Path(dest).write_text("")
        return dest

    monkeypatch.setattr("certo_fdi_reset.storage_migration.shutil.copy2", truncating_copy)
    result = migrate(src, layout, RUN_ID)

    assert not result.ok
    assert result.errors
    failed = [r for r in result.records if not r.verified]
    assert [r.status for r in failed] == ["FAILED_STAGING_HASH"]
    # A failed run keeps its staging directory for inspection.
    assert result.staging_dir is not None


def test_rerun_over_read_only_destinations_succeeds(tmp_path):
    """The second run must not be blocked by the first run's read-only bits."""
    src = _scratchpad(tmp_path)
    layout = PersistLayout(tmp_path / "persist")

    assert migrate(src, layout, RUN_ID).ok
    assert migrate(src, layout, RUN_ID).ok


def test_inventory_csv_records_hashes_and_classes(tmp_path):
    src = _scratchpad(tmp_path)
    layout = PersistLayout(tmp_path / "persist")
    result = migrate(src, layout, RUN_ID)

    out = tmp_path / "inv.csv"
    sha = write_inventory(out, result.records, phase="before")

    text = out.read_text(encoding="utf-8")
    assert "artifact_class" in text.splitlines()[0]
    assert "LITERATURE_RAW_EXPORT" in text
    assert len(sha) == 64
