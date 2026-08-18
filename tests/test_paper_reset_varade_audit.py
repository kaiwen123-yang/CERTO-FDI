"""The VARADE audit must find the real defects, and stay quiet on a clean repo."""

from __future__ import annotations

import pickle
import subprocess

import pytest

from certo_fdi_reset.baselines import varade_audit


def _git_init(path):
    for args in (["init", "-q"], ["config", "user.email", "t@example.invalid"],
                 ["config", "user.name", "t"], ["add", "-A"],
                 ["commit", "-q", "-m", "x"]):
        subprocess.run(["git", "-C", str(path), *args], check=False, capture_output=True)


@pytest.fixture
def clean_repo(tmp_path):
    """A repo with a licence, a seed, a training call and no duplicate checkpoints."""
    repo = tmp_path / "clean"
    (repo / "checkpoints").mkdir(parents=True)
    (repo / "data").mkdir()
    (repo / "LICENSE").write_text("MIT\n")
    (repo / "README.md").write_text("# clean\n")
    (repo / "main.py").write_text(
        "import numpy\n"
        "numpy.random.seed(7)\n"
        "model.fit(x)\n"
        "reader = Reader('./data/training.pkl', './data/collision.pkl',"
        " './data/weight.pkl', './data/velocity.pkl')\n"
    )
    for name in varade_audit.CONTRACT_NAMED_FILES:
        (repo / name).write_text("# stub\n")
    (repo / "checkpoints" / "A.pkl").write_bytes(pickle.dumps([1, 2, 3]))
    (repo / "checkpoints" / "B.pkl").write_bytes(pickle.dumps({"different": True}))
    _git_init(repo)
    return repo


def test_clean_repo_raises_no_blocking_finding(clean_repo):
    report = varade_audit.audit(clean_repo, None)
    ids = {f["id"] for f in report["findings"]}
    assert "VARADE_NO_LICENCE" not in ids
    assert "VARADE_DUPLICATE_CHECKPOINTS" not in ids
    assert "VARADE_NO_SEED" not in ids
    assert "VARADE_SKIPS_FIRST_RECORDING" not in ids
    assert "VARADE_COLLISION_SUBSET_ONLY" not in ids


def test_duplicate_checkpoints_are_reported(clean_repo):
    """Two names, one artifact: at most one published baseline can be real."""
    payload = (clean_repo / "checkpoints" / "A.pkl").read_bytes()
    (clean_repo / "checkpoints" / "B.pkl").write_bytes(payload)
    report = varade_audit.audit(clean_repo, None)
    finding = next(f for f in report["findings"] if f["id"] == "VARADE_DUPLICATE_CHECKPOINTS")
    assert finding["severity"] == "reproduction_blocking"
    assert report["reproduction_level"] == "POLICY_BASELINE"


def test_missing_licence_is_reported(clean_repo):
    (clean_repo / "LICENSE").unlink()
    ids = {f["id"] for f in varade_audit.audit(clean_repo, None)["findings"]}
    assert "VARADE_NO_LICENCE" in ids


def test_skipped_first_recording_is_reported(clean_repo):
    """The cursor starting at 1 drops a whole recording; whitespace must not hide it."""
    (clean_repo / "main.py").write_text("self.recordingCursor   =   1\n")
    ids = {f["id"] for f in varade_audit.audit(clean_repo, None)["findings"]}
    assert "VARADE_SKIPS_FIRST_RECORDING" in ids


def test_collision_only_coverage_is_reported(clean_repo):
    (clean_repo / "main.py").write_text("open('./data/collision.pkl')\nnumpy.random.seed(1)\n")
    ids = {f["id"] for f in varade_audit.audit(clean_repo, None)["findings"]}
    assert "VARADE_COLLISION_SUBSET_ONLY" in ids


def test_pickle_classes_reads_opcodes_without_unpickling(tmp_path):
    """Identification must not execute the pickle: a poisoned payload stays inert."""
    import sklearn.tree  # noqa: F401  (imported so the class name is realistic)

    path = tmp_path / "x.pkl"
    path.write_bytes(pickle.dumps({"a": [1, 2, 3]}))
    assert isinstance(varade_audit.pickle_classes(path), list)

    # A truncated pickle must not raise -- the scan is expected to run out of bytes.
    truncated = tmp_path / "t.pkl"
    truncated.write_bytes(pickle.dumps([0] * 10_000)[:200])
    assert isinstance(varade_audit.pickle_classes(truncated), list)


def test_road_data_redistribution_is_detected(clean_repo, tmp_path):
    road = tmp_path / "road"
    (road / "RoADDataset" / "data").mkdir(parents=True)
    payload = b"identical-array-bytes"
    (road / "RoADDataset" / "data" / "training.pkl").write_bytes(payload)
    (clean_repo / "data" / "training.pkl").write_bytes(payload)
    report = varade_audit.audit(clean_repo, road)
    finding = next(f for f in report["findings"] if f["id"] == "VARADE_REDISTRIBUTES_ROAD_DATA")
    assert "training.pkl" in finding["claim"]
    assert report["data_identical_to_road"] == ["training.pkl"]
