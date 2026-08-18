"""Phase D0 acquisition: integrity checks must fail loudly, not silently pass."""

from __future__ import annotations

import hashlib

import pytest

from certo_fdi_reset.datasets import acquire


def test_acquisition_table_is_declarative_and_complete():
    """Every entry names a dataset, a key, an https/http URL and a licence note."""
    assert acquire.ACQUISITIONS
    for item in acquire.ACQUISITIONS:
        assert item.dataset_id and item.key and item.purpose
        assert item.url.startswith(("http://", "https://"))
        assert item.redistribution, f"{item.key} has no redistribution note"


def test_no_duplicate_destinations():
    """Two entries must never write to the same file under one dataset."""
    seen = {(i.dataset_id, i.key) for i in acquire.ACQUISITIONS}
    assert len(seen) == len(acquire.ACQUISITIONS)


def test_identity_encoding_is_requested():
    """A gzip Content-Length is not the size of the file we store (see SARCOS)."""
    assert acquire._session().headers["Accept-Encoding"] == "identity"


@pytest.mark.parametrize(
    ("expected_bytes", "expected_md5", "local_bytes", "local_md5", "want"),
    [
        (10, "", 10, None, "OK"),
        (10, "", 9, None, "MISMATCH"),
        (None, "", 9, None, "OK"),
        (10, "abc", 10, "abc", "OK"),
        (10, "abc", 10, "def", "MISMATCH"),
    ],
)
def test_check_flags_size_and_md5(expected_bytes, expected_md5, local_bytes, local_md5, want):
    item = acquire.Acquisition(
        "d", "k", "https://example.invalid/k", "p",
        expected_bytes=expected_bytes, expected_md5=expected_md5,
    )
    record = {"local_bytes": local_bytes, "local_md5": local_md5, "status": "DOWNLOADED"}
    out = acquire._check(record, item)
    assert out["integrity"] == want
    # A mismatch must overwrite the status, so a caller cannot read it as success.
    assert (out["status"] == "FAILED_INTEGRITY") == (want == "MISMATCH")


def test_already_present_file_is_not_redownloaded(tmp_path):
    """A local copy is hashed and reported, never fetched again."""
    item = acquire.Acquisition("d", "k.bin", "https://example.invalid/k.bin", "p")
    (tmp_path / "k.bin").write_bytes(b"payload")

    class Boom:
        def get(self, *a, **k):  # pragma: no cover - must never be called
            raise AssertionError("re-downloaded an existing file")

    record = acquire.acquire_one(item, tmp_path, Boom())
    assert record["status"] == "ALREADY_PRESENT"
    assert record["downloaded"] is False
    assert record["local_sha256"] == hashlib.sha256(b"payload").hexdigest()
