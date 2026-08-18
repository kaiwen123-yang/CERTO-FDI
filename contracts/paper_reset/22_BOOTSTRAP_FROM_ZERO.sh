#!/usr/bin/env bash
set -euo pipefail

REMOTE="${CERTO_REMOTE:-git@github.com:kaiwen123-yang/CERTO-FDI.git}"
PERSIST_ROOT="${CERTO_PERSIST_ROOT:-/mnt/g/CERTO-FDI}"
REPO_ROOT="${CERTO_REPO_ROOT:-$HOME/research/CERTO-FDI}"
WT_ROOT="${CERTO_WORKTREE_ROOT:-$HOME/research/CERTO-FDI-WORKTREES/paper-reset-literature-public-benchmarks}"
BRANCH="stage/paper-reset-literature-public-benchmarks"

if [[ "$PERSIST_ROOT" == /mnt/g/* ]]; then
  mountpoint -q /mnt/g || { echo "ERROR: /mnt/g is not a real mountpoint" >&2; exit 2; }
fi

mkdir -p "$PERSIST_ROOT"/{01_frozen_sources/literature_reset/{metadata,open_fulltexts,access_manifest},01_frozen_sources/public_baseline_repos,02_research_docs/paper_reset/{literature,novelty,datasets,decisions},03_data/public/{voraus_ad,road,aursad,ur5e_graabaek,pyscrew},04_runs/paper_reset_public_benchmarks,05_reference_results/paper_reset,06_review_exchange/to_review/{thin,full}}
mkdir -p "$(dirname "$REPO_ROOT")" "$(dirname "$WT_ROOT")"

if [[ ! -d "$REPO_ROOT/.git" ]]; then
  git clone "$REMOTE" "$REPO_ROOT"
fi

git -C "$REPO_ROOT" fetch --all --prune
if [[ -e "$WT_ROOT" ]]; then
  echo "Worktree already exists: $WT_ROOT"
else
  if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git -C "$REPO_ROOT" worktree add "$WT_ROOT" "$BRANCH"
  else
    git -C "$REPO_ROOT" worktree add -b "$BRANCH" "$WT_ROOT" origin/main
  fi
fi

echo "REPO_ROOT=$REPO_ROOT"
echo "WORKTREE=$WT_ROOT"
echo "PERSIST_ROOT=$PERSIST_ROOT"
