#!/usr/bin/env bash
# Repository hygiene gate: reject non-code artifacts, secrets, oversized files,
# and hard-coded external storage paths in business Python.
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

FAIL=0
note() { printf 'HYGIENE_FAIL: %s\n' "$1"; FAIL=1; }

TRACKED="$(git ls-files)"

# 1. Archives must never be tracked.
while IFS= read -r f; do
  case "$f" in
    *.zip|*.tar|*.tar.gz|*.tgz|*.7z) note "tracked archive: $f" ;;
  esac
done <<< "$TRACKED"

# 2. Data artifacts only allowed as small hand-made fixtures under tests/fixtures/,
#    or as frozen contract registries/templates under contracts/ (these are
#    protocol text shipped in the kickoff package, not experimental data).
while IFS= read -r f; do
  case "$f" in
    tests/fixtures/*) continue ;;
    contracts/*/*.csv) continue ;;
  esac
  case "$f" in
    *.csv|*.npz|*.parquet|*.pkl|*.h5) note "tracked data artifact outside tests/fixtures: $f" ;;
  esac
done <<< "$TRACKED"

# 2b. Contract CSVs are protocol text: they must stay small and must never carry
#     measured results (a results row would smuggle data into git).
while IFS= read -r f; do
  case "$f" in
    contracts/*/*.csv)
      size=$(stat -c%s "$f")
      [ "$size" -gt 65536 ] && note "contract CSV too large to be protocol text: $f ($size bytes)"
      ;;
  esac
done <<< "$TRACKED"

# 3. Forbidden result/audit directories.
while IFS= read -r f; do
  case "$f" in
    results/*|runs/*|data/raw/*|audit/*) note "forbidden directory tracked: $f" ;;
  esac
done <<< "$TRACKED"

# 4. Oversized files (> 2 MiB) need an explicit whitelist entry.
WHITELIST_FILE=".hygiene_size_whitelist"
while IFS= read -r f; do
  [ -f "$f" ] || continue
  size=$(stat -c%s "$f")
  if [ "$size" -gt 2097152 ]; then
    if ! { [ -f "$WHITELIST_FILE" ] && grep -qxF "$f" "$WHITELIST_FILE"; }; then
      note "file exceeds 2 MiB without whitelist: $f ($size bytes)"
    fi
  fi
done <<< "$TRACKED"

# 5. Secrets / private material.
while IFS= read -r f; do
  case "$f" in
    configs/paths.example.env) continue ;;
  esac
  case "$f" in
    *.env|.env|*id_rsa*|*id_ed25519*|*.pem|.ssh/*) note "secret-like file tracked: $f" ;;
  esac
done <<< "$TRACKED"
if git grep -nIE 'ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY' -- . >/dev/null 2>&1; then
  note "credential-like pattern found in tracked content:"
  git grep -nIE 'ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY' -- . || true
fi

# 6. Caches and virtual envs.
while IFS= read -r f; do
  case "$f" in
    *__pycache__*|.venv/*|.pytest_cache/*|.hypothesis/*) note "cache/venv tracked: $f" ;;
  esac
done <<< "$TRACKED"

# 7. No hard-coded external storage root in business Python (src/).
if git grep -nI '/mnt/g' -- 'src/*.py' 'src/**/*.py' >/dev/null 2>&1; then
  note "hard-coded /mnt/g path inside src/ Python:"
  git grep -nI '/mnt/g' -- 'src/*.py' 'src/**/*.py' || true
fi

if [ "$FAIL" -ne 0 ]; then
  echo "Repository hygiene check FAILED."
  exit 1
fi
echo "Repository hygiene check passed."
