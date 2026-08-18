"""Record a native-baseline smoke run against the reproduction contract.

``11_PUBLIC_BASELINE_REPRODUCTION_PROTOCOL.md`` §8.1 requires a smoke to be
reported with the environment it ran in and the deltas from the official one, so
that a later GPU port can be checked against it rather than against a memory of
it. This module parses the official runner's own stdout -- it never restates a
result by hand -- and writes the contract's files.

A reproduction level is claimed here only when it is earned: EXACT_OFFICIAL_CPU
requires the official pinned dependency set to have installed with no deltas AND
the official code to be unmodified.

    python -m certo_fdi_reset.baselines.smoke_record --config configs/paper_reset.yaml \
        --dataset voraus_ad --log <pytest stdout> --repo <official checkout>
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ..config import load_config
from ..provenance import sha256_file, utc_stamp, write_manifest

EPOCH_RE = re.compile(r"Epoch\s+(\d+):\s*auroc\(mean\)=([0-9.]+),\s*loss=(-?[0-9.]+)")
TIMING_RE = re.compile(r"^(.*?) took ([0-9.]+) seconds")
DURATION_RE = re.compile(r"(\d+) passed in ([0-9.]+)s")


@dataclass
class SmokeResult:
    dataset_id: str
    epochs: list[dict] = field(default_factory=list)
    stage_timings: dict[str, float] = field(default_factory=dict)
    tests_passed: int = 0
    wall_seconds: float = 0.0
    outcome: str = "UNKNOWN"

    @property
    def final_auroc(self) -> float | None:
        return self.epochs[-1]["auroc_mean"] if self.epochs else None

    @property
    def best_auroc(self) -> float | None:
        return max((e["auroc_mean"] for e in self.epochs), default=None)


def parse_log(text: str, dataset_id: str) -> SmokeResult:
    result = SmokeResult(dataset_id=dataset_id)
    for line in text.splitlines():
        epoch = EPOCH_RE.search(line)
        if epoch:
            result.epochs.append(
                {
                    "epoch": int(epoch.group(1)),
                    "auroc_mean": float(epoch.group(2)),
                    "loss": float(epoch.group(3)),
                }
            )
            continue
        timing = TIMING_RE.match(line.strip())
        if timing:
            result.stage_timings[timing.group(1).strip()] = float(timing.group(2))
        duration = DURATION_RE.search(line)
        if duration:
            result.tests_passed = int(duration.group(1))
            result.wall_seconds = float(duration.group(2))
    if "PASSED" in text and result.epochs:
        result.outcome = "PASS"
    elif "FAILED" in text or "failed" in text:
        result.outcome = "FAIL"
    return result


def installed_versions(python_bin: Path) -> dict[str, str]:
    output = subprocess.run(
        [str(python_bin), "-m", "pip", "list", "--format=freeze"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    versions: dict[str, str] = {}
    for line in output.splitlines():
        if "==" in line:
            name, _, version = line.partition("==")
            versions[name.strip().casefold()] = version.strip()
    return versions


def parse_requirements(path: Path) -> dict[str, str]:
    """Official pins. A VCS requirement records its ref rather than a version."""
    pins: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "@" in line and "git+" in line:
            name, _, spec = line.partition("@")
            pins[name.strip().casefold()] = f"git:{spec.strip().rpartition('@')[2]}"
        elif "==" in line:
            name, _, version = line.partition("==")
            pins[name.strip().casefold()] = version.strip()
    return pins


def dependency_deltas(pins: dict[str, str], installed: dict[str, str]) -> list[dict]:
    rows: list[dict] = []
    for name, want in sorted(pins.items()):
        got = installed.get(name, "MISSING")
        if want.startswith("git:"):
            status = "PRESENT_FROM_VCS" if got != "MISSING" else "MISSING"
        elif got == want:
            status = "MATCH"
        elif got == "MISSING":
            status = "MISSING"
        else:
            status = "MISMATCH"
        rows.append({"package": name, "official_pin": want, "installed": got, "status": status})
    return rows


def reproduction_level(
    deltas: list[dict], code_modified: bool, device: str, track: str = "A"
) -> str:
    """Name the level this run actually earned (§9.1), never the one hoped for.

    Track A claims EXACT_OFFICIAL only when the official pins installed with zero
    deltas AND the official source is untouched. Track B is a different claim: its
    dependency deltas are the whole point (torch 1.12 has no kernels for sm_120), so
    mismatches do NOT demote it -- but a modified source does, because then it is no
    longer the official algorithm being run.
    """
    mismatched = [d for d in deltas if d["status"] in {"MISMATCH", "MISSING"}]
    if code_modified:
        return "FAITHFUL_PAPER"
    if track.upper() == "B":
        return "FAITHFUL_OFFICIAL_GPU_PORT"
    if mismatched:
        return "FAITHFUL_PAPER"
    return "EXACT_OFFICIAL_CPU" if device == "cpu" else "EXACT_OFFICIAL"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certo_fdi_reset.baselines.smoke_record")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--python-bin", required=True, type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--data-file", type=Path, default=None)
    parser.add_argument(
        "--track",
        default="A",
        choices=["A", "B"],
        help="A = EXACT_OFFICIAL_CPU attempt; B = FAITHFUL_OFFICIAL_GPU_PORT attempt.",
    )
    parser.add_argument(
        "--out-name",
        default=None,
        help="Output subdirectory under b0/. Defaults to the dataset id; a second track "
             "must pass its own name so it cannot overwrite the first track's evidence.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    out_dir = cfg.layout.run_dir(cfg.run_id) / "b0" / (args.out_name or args.dataset)
    out_dir.mkdir(parents=True, exist_ok=True)

    log_text = args.log.read_text(encoding="utf-8", errors="replace")
    result = parse_log(log_text, args.dataset)

    pins = parse_requirements(args.repo / "requirements.txt")
    installed = installed_versions(args.python_bin)
    deltas = dependency_deltas(pins, installed)

    dirty = subprocess.run(
        ["git", "-C", str(args.repo), "status", "--porcelain", "--untracked-files=no"],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    code_commit = subprocess.run(
        ["git", "-C", str(args.repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    level = reproduction_level(deltas, bool(dirty), args.device, args.track)

    delta_csv = out_dir / "dependency_delta.csv"
    with delta_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=("package", "official_pin", "installed", "status"))
        writer.writeheader()
        writer.writerows(deltas)

    payload = {
        "run_id": cfg.run_id,
        "dataset_id": args.dataset,
        "generated_utc": utc_stamp(),
        "track": args.track,
        "reproduction_level": level,
        "device": args.device,
        "outcome": result.outcome,
        "official_code_commit": code_commit,
        "official_code_modified": bool(dirty),
        "epochs_run": len(result.epochs),
        "final_auroc_mean": result.final_auroc,
        "best_auroc_mean": result.best_auroc,
        "epoch_trace": result.epochs,
        "stage_timings_seconds": result.stage_timings,
        "wall_seconds": result.wall_seconds,
        "tests_passed": result.tests_passed,
        "dependency_summary": {
            "pinned": len(pins),
            "match": sum(1 for d in deltas if d["status"] == "MATCH"),
            "from_vcs": sum(1 for d in deltas if d["status"] == "PRESENT_FROM_VCS"),
            "mismatch": sum(1 for d in deltas if d["status"] == "MISMATCH"),
            "missing": sum(1 for d in deltas if d["status"] == "MISSING"),
        },
        "data_file": str(args.data_file) if args.data_file else "",
        "data_sha256": sha256_file(args.data_file) if args.data_file and args.data_file.exists() else "",
    }
    # The contract names both files (§8.1); each track writes its own so a reviewer can
    # diff them instead of finding one overwritten by the other.
    manifest_path = out_dir / (
        "gpu_port_smoke.json" if args.track.upper() == "B" else "official_cpu_smoke.json"
    )
    manifest_sha = write_manifest(manifest_path, payload)

    print(f"outcome            {result.outcome}")
    print(f"reproduction_level {level}")
    print(f"epochs             {len(result.epochs)}")
    print(f"final auroc(mean)  {result.final_auroc}")
    print(f"wall seconds       {result.wall_seconds}")
    print(f"deps match/total   {payload['dependency_summary']['match']}/{payload['dependency_summary']['pinned']}"
          f" (+{payload['dependency_summary']['from_vcs']} vcs, {payload['dependency_summary']['mismatch']} mismatch)")
    print(f"code modified      {bool(dirty)}")
    print(f"manifest           {manifest_path} sha256={manifest_sha}")
    print(f"dependency_delta   {delta_csv}")
    return 0 if result.outcome == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
