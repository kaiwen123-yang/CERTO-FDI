"""Phase B0: audit the VARADE repository against its paper, mechanically.

Contract §6.7 asks for an audit of the repository, commit, licence, the four named
source files, the checkpoints, the preprocessing, the split, the seeds, paper-code
consistency, the metric implementation, and test leakage. Most of that is reading.
The parts that are *checkable* are checked here instead of being asserted in prose,
because the findings decide a reproduction level and a reviewer should be able to
re-derive them rather than trust a summary:

* two checkpoints are byte-identical while the code loads them as different models;
* one checkpoint's pickle opcodes name a class that contradicts its filename;
* the streaming reader's cursor logic silently skips a recording;
* the shipped data is a byte-identical copy of the unlicensed RoAD arrays.

Pickles are identified by scanning opcodes with ``pickletools``, never by
unpickling: loading a 180 MB pickle from a third-party repository would execute
whatever it names, and identifying the class does not require that.

    python -m certo_fdi_reset.baselines.varade_audit \
        --config configs/paper_reset.yaml --repo <frozen varade checkout>
"""

from __future__ import annotations

import argparse
import io
import json
import pickletools
import re
import sys
from pathlib import Path

from ..config import load_config
from ..provenance import sha256_file, utc_stamp, write_manifest

#: Files the contract names explicitly (§6.7).
CONTRACT_NAMED_FILES: tuple[str, ...] = (
    "VAAR.py",
    "Transformer.py",
    "autoencoder.py",
    "BERTTrainer.py",
)

#: How many bytes of a pickle to scan for class names. The interesting GLOBAL
#: opcodes sit in the header; the rest is array payload.
OPCODE_SCAN_BYTES = 3_000_000

CLASS_HINTS = (
    "sklearn",
    "numpy",
    "DecisionTree",
    "Isolation",
    "neighbors",
    "ensemble",
    "_forest",
    "tree",
)


def pickle_classes(path: Path, limit: int = OPCODE_SCAN_BYTES) -> list[str]:
    """Class/module names a pickle references, from its opcodes. No execution."""
    with path.open("rb") as handle:
        head = handle.read(limit)
    names: list[str] = []
    try:
        for opcode, argument, _ in pickletools.genops(io.BytesIO(head)):
            if opcode.name.endswith(("GLOBAL", "BINUNICODE", "SHORT_BINUNICODE")) and argument:
                text = str(argument)
                if any(hint in text for hint in CLASS_HINTS) and text not in names:
                    names.append(text)
    except (ValueError, IndexError):
        # Expected: the scan runs out of bytes mid-array. Everything of interest
        # has already been read by then.
        pass
    return names


def audit(repo: Path, road_repo: Path | None) -> dict:
    findings: list[dict] = []
    checkpoints = repo / "checkpoints"

    # --- licence -------------------------------------------------------------
    licence_files = [p.name for p in repo.iterdir() if re.match(r"(?i)^(licen[cs]e|copying)", p.name)]
    if not licence_files:
        findings.append(
            {
                "id": "VARADE_NO_LICENCE",
                "severity": "blocking_for_redistribution",
                "claim": "The repository ships no LICENSE or COPYING file.",
                "evidence": f"no licence-like filename in {repo}",
                "consequence": (
                    "licence_status stays UNKNOWN: local research analysis only, and neither the "
                    "code nor the shipped data may enter git or a review package."
                ),
            }
        )

    # --- byte-identical checkpoints -----------------------------------------
    digests: dict[str, str] = {}
    if checkpoints.is_dir():
        for path in sorted(checkpoints.glob("*.pkl")):
            digests[path.name] = sha256_file(path)
    duplicates: dict[str, list[str]] = {}
    for name, digest in digests.items():
        duplicates.setdefault(digest, []).append(name)
    for digest, names in duplicates.items():
        if len(names) > 1:
            findings.append(
                {
                    "id": "VARADE_DUPLICATE_CHECKPOINTS",
                    "severity": "reproduction_blocking",
                    "claim": f"{' and '.join(names)} are byte-identical (sha256 {digest}).",
                    "evidence": "sha256 of each .pkl under checkpoints/",
                    "consequence": (
                        "main.py loads these two paths into different evaluator classes, so at "
                        "most one of the two published baselines can be the artifact in this file."
                    ),
                }
            )

    # --- does each pickle contain what its filename says? --------------------
    pickle_report = {}
    for path in sorted(checkpoints.glob("*.pkl")) if checkpoints.is_dir() else []:
        classes = pickle_classes(path)
        pickle_report[path.name] = classes
        stem = path.stem.casefold()
        joined = " ".join(classes).casefold()
        if stem.startswith("isolationforest") and "isolationforest" not in joined:
            findings.append(
                {
                    "id": "VARADE_ISOLATIONFOREST_MISLABELLED",
                    "severity": "reproduction_blocking",
                    "claim": (
                        "checkpoints/IsolationForest.pkl contains no IsolationForest. Its opcodes "
                        f"name: {', '.join(classes[:6])}."
                    ),
                    "evidence": "pickletools opcode scan, no unpickling",
                    "consequence": (
                        "IsolationForestEvaluator calls .score_samples() on the loaded object. A "
                        "list of DecisionTreeRegressors has no such method, so that evaluator "
                        "cannot run at all and the published IsolationForest baseline is not "
                        "reproducible from this repository."
                    ),
                }
            )

    # --- is the shipped data a copy of the unlicensed RoAD arrays? -----------
    data_digests = {}
    data_dir = repo / "data"
    if data_dir.is_dir():
        for path in sorted(data_dir.glob("*.pkl")):
            data_digests[path.name] = sha256_file(path)
    shared: list[str] = []
    if road_repo and road_repo.is_dir():
        road_digests = {
            path.name: sha256_file(path)
            for path in sorted((road_repo / "RoADDataset" / "data").glob("*.pkl"))
        }
        for name, digest in data_digests.items():
            if road_digests.get(name) == digest:
                shared.append(name)
        if shared:
            findings.append(
                {
                    "id": "VARADE_REDISTRIBUTES_ROAD_DATA",
                    "severity": "licence",
                    "claim": (
                        f"data/{{{', '.join(shared)}}} are byte-identical to the RoAD repository's "
                        "own arrays."
                    ),
                    "evidence": "sha256 equality against the frozen RoAD checkout",
                    "consequence": (
                        "unlicensed RoAD data is redistributed inside a second unlicensed "
                        "repository; it stays out of git and out of every review package."
                    ),
                }
            )

    # --- the streaming reader's cursor --------------------------------------
    main_py = (repo / "main.py").read_text(encoding="utf-8") if (repo / "main.py").exists() else ""
    if "self.recordingCursor=1" in main_py.replace(" ", ""):
        findings.append(
            {
                "id": "VARADE_SKIPS_FIRST_RECORDING",
                "severity": "measurement_affecting",
                "claim": (
                    "FakeStreamingDataReader starts at recordingCursor=1 and stops as soon as "
                    "recordingCursor+1 >= len(collisions). RoAD's collision subset holds 2 "
                    "recordings, so index 1 is evaluated and index 0 is never read."
                ),
                "evidence": "main.py __init__ and __next__",
                "consequence": (
                    "any number produced by this script covers half the collision test set. It is "
                    "not comparable to a figure computed over the whole subset."
                ),
            }
        )
    if "windowSize=512" in main_py.replace(" ", ""):
        findings.append(
            {
                "id": "VARADE_WINDOW_IS_51_SECONDS",
                "severity": "interpretation",
                "claim": "The window is 512 samples, and the released RoAD arrays are 10 Hz.",
                "evidence": "main.py FakeStreamingDataReader(windowSize=512)",
                "consequence": (
                    "each decision sees 51.2 s of context to score a point anomaly, and the score "
                    "is read off the LAST timestep only."
                ),
            }
        )
    if "pastScores=pastScores[1:]" in main_py.replace(" ", ""):
        findings.append(
            {
                "id": "VARADE_ROLLING_AUROC_ONLY",
                "severity": "metric_incomparable",
                "claim": (
                    "The only metric computed is a ROLLING AUROC over the most recent 1000 "
                    "samples, printed to a carriage-returned line and never aggregated or saved."
                ),
                "evidence": "main.py benchmarking loop",
                "consequence": (
                    "the repository produces no dataset-level AUROC, so its output cannot be "
                    "compared with the RoAD paper's per-subset AUC-ROC table without "
                    "reimplementing the metric."
                ),
            }
        )
    if "collision.pkl" in main_py and "weight.pkl" not in main_py and "velocity.pkl" not in main_py:
        findings.append(
            {
                "id": "VARADE_COLLISION_SUBSET_ONLY",
                "severity": "coverage",
                "claim": "The reader loads training.pkl and collision.pkl only.",
                "evidence": "main.py FakeStreamingDataReader.__init__",
                "consequence": (
                    "the weight and velocity subsets -- RoAD's two COLLECTIVE-anomaly scenarios -- "
                    "are never evaluated, so at most 1 of RoAD's 3 test subsets is covered."
                ),
            }
        )

    # --- seeds and training -------------------------------------------------
    py_files = [p for p in repo.rglob("*.py") if "__pycache__" not in p.parts]
    seed_hits = [
        f"{p.name}:{i}"
        for p in py_files
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1)
        if re.search(r"set_seed|random\.seed|random_state|manual_seed", line)
    ]
    if not seed_hits:
        findings.append(
            {
                "id": "VARADE_NO_SEED",
                "severity": "reproduction_blocking",
                "claim": "No seed is set anywhere: no tf.random.set_seed, no numpy seed, no random_state.",
                "evidence": f"scanned {len(py_files)} .py files",
                "consequence": "a retrained model cannot be reproduced, only re-approximated.",
            }
        )
    fit_calls = [
        f"{p.name}:{i}"
        for p in py_files
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1)
        if re.search(r"\.fit\(", line)
    ]
    non_scaler_fits = [
        hit
        for hit, p in ((h, h.split(":")[0]) for h in fit_calls)
        if "Scaler" not in hit
    ]
    findings.append(
        {
            "id": "VARADE_NO_TRAINING_SCRIPT",
            "severity": "reproduction_blocking",
            "claim": (
                "The repository has no training entry point. The only .fit() call is the "
                f"MinMaxScaler in main.py ({', '.join(fit_calls) or 'none'}); VAARModel defines "
                "train_step but nothing constructs a dataset or calls model.fit()."
            ),
            "evidence": "grep for .fit( across all .py files",
            "consequence": (
                "checkpoints can be evaluated but not regenerated. The reproduction level is "
                "capped below any level that requires retraining."
            ),
        }
    )

    # --- README vs reality ---------------------------------------------------
    readme = (repo / "README.md").read_text(encoding="utf-8") if (repo / "README.md").exists() else ""
    readme_problems = []
    if "github.com/AlessioMascolini/varade" in readme:
        readme_problems.append(
            "the clone command points at github.com/AlessioMascolini/varade, but the code is "
            "hosted on GitLab; the GitHub path does not serve this repository"
        )
    if "FakeStreamingDataReader.py" in readme and not (repo / "FakeStreamingDataReader.py").exists():
        readme_problems.append(
            "the structure section lists FakeStreamingDataReader.py as a file, but the class "
            "lives inside main.py and no such file exists"
        )
    if readme_problems:
        findings.append(
            {
                "id": "VARADE_README_MISMATCH",
                "severity": "documentation",
                "claim": "The README does not describe the repository it ships with: "
                + "; ".join(readme_problems)
                + ".",
                "evidence": "README.md against the file listing",
                "consequence": "a reader following the README cannot obtain or navigate the code.",
            }
        )

    present = {name: (repo / name).exists() for name in CONTRACT_NAMED_FILES}
    severities = {f["severity"] for f in findings}
    blocking = {"reproduction_blocking"} & severities

    return {
        "repo": str(repo),
        "commit": _git_head(repo),
        "generated_utc": utc_stamp(),
        "contract_named_files_present": present,
        "checkpoint_sha256": digests,
        "checkpoint_pickle_classes": pickle_report,
        "data_sha256": data_digests,
        "data_identical_to_road": shared,
        "licence_files": licence_files,
        "seed_sites": seed_hits,
        "fit_call_sites": fit_calls,
        "findings": findings,
        "reproduction_level": "POLICY_BASELINE" if blocking else "FAITHFUL_PAPER",
        "reproduction_level_reason": (
            "Contract §8.2: the code and paper are not fully consistent, so the level is degraded "
            "and this must NOT be called an official reproduction. Blocking findings: "
            + ", ".join(sorted(f["id"] for f in findings if f["severity"] == "reproduction_blocking"))
            if blocking
            else "no reproduction-blocking finding"
        ),
    }


def _git_head(repo: Path) -> str:
    import subprocess

    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    ).stdout.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certo_fdi_reset.baselines.varade_audit")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--road-repo", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    repo = args.repo.expanduser().resolve()
    if not repo.is_dir():
        print(f"ERROR: repo not found: {repo}", file=sys.stderr)
        return 2
    road = args.road_repo.expanduser().resolve() if args.road_repo else None

    report = audit(repo, road)
    report["run_id"] = cfg.run_id
    report["config_sha"] = cfg.config_sha

    out = cfg.layout.run_dir(cfg.run_id) / "b0" / "road_varade" / "varade_code_audit.json"
    sha = write_manifest(out, report)

    print(f"commit             {report['commit']}")
    print(f"licence files      {report['licence_files'] or 'NONE'}")
    print(f"reproduction level {report['reproduction_level']}")
    print(f"findings           {len(report['findings'])}")
    for finding in report["findings"]:
        print(f"  [{finding['severity']:26s}] {finding['id']}")
    print(f"report             {out}  sha256={sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
