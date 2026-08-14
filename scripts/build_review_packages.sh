#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
RUN_ROOT="${CERTO_RUN_ROOT:-}"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --run-root) shift; RUN_ROOT="${1:?--run-root requires a path}" ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done
if [ -z "$RUN_ROOT" ]; then
  printf 'ERROR: CERTO_RUN_ROOT or --run-root is required\n' >&2
  exit 2
fi
exec "$REPO_ROOT/.venv/bin/python" -m certo_fdi.packaging.build_review_package \
  --run-root "$RUN_ROOT" --repo-root "$REPO_ROOT"
