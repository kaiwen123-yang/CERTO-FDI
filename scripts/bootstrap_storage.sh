#!/usr/bin/env bash
set -euo pipefail

STORAGE_ROOT="${1:-${CERTO_STORAGE_ROOT:-}}"
if [ -z "$STORAGE_ROOT" ]; then
  printf 'usage: %s STORAGE_ROOT\n' "$0" >&2
  exit 2
fi
if [ "$STORAGE_ROOT" = "/mnt/g/CERTO-FDI" ] && ! mountpoint -q /mnt/g; then
  printf 'ERROR: /mnt/g is not a real mount point\n' >&2
  exit 10
fi
mkdir -p \
  "$STORAGE_ROOT"/{00_inbox/{auto_discovered,bootstrap,audit_sources,reviewer_returns},01_frozen_sources/{archives,extracted},02_research_docs/{contracts,math,literature,ledgers,decisions,runbooks,corrections},03_data/{raw,interim,processed,manifests},04_runs/stage1_2r_closedloop_certificate,05_reference_results/{accepted,rejected},06_review_exchange/{package_staging/{working,failed},to_review/{thin,full},from_review,extracted_reviews},07_backups/{git_bundles,milestone_archives},08_cache/disposable}
printf 'CERTO_STORAGE_ROOT=%s\n' "$STORAGE_ROOT"
