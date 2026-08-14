#!/usr/bin/env bash
set -euo pipefail

REMOTE="${CERTO_GIT_REMOTE:-git@github.com:kaiwen123-yang/CERTO-FDI.git}"
REPO_ROOT="${CERTO_REPO_ROOT:-${HOME}/research/CERTO-FDI}"
WORKTREE_ROOT="${CERTO_WORKTREE_ROOT:-${HOME}/research/CERTO-FDI-WORKTREES/stage1-closedloop-certificate}"
STAGE_BRANCH="${CERTO_STAGE_BRANCH:-stage/stage1-closedloop-certificate}"

mkdir -p "$(dirname "$REPO_ROOT")" "$(dirname "$WORKTREE_ROOT")"
if [ ! -d "$REPO_ROOT/.git" ]; then
  if [ -e "$REPO_ROOT" ] && [ -n "$(find "$REPO_ROOT" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    printf 'ERROR: non-empty non-Git path is preserved: %s\n' "$REPO_ROOT" >&2
    exit 12
  fi
  git clone "$REMOTE" "$REPO_ROOT"
fi
actual_remote=$(git -C "$REPO_ROOT" remote get-url origin)
if [ "$actual_remote" != "$REMOTE" ]; then
  printf 'ERROR: origin mismatch; expected=%s actual=%s\n' "$REMOTE" "$actual_remote" >&2
  exit 13
fi
git -C "$REPO_ROOT" fetch origin
if [ ! -e "$WORKTREE_ROOT/.git" ]; then
  if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$STAGE_BRANCH"; then
    git -C "$REPO_ROOT" worktree add "$WORKTREE_ROOT" "$STAGE_BRANCH"
  elif git -C "$REPO_ROOT" show-ref --verify --quiet "refs/remotes/origin/$STAGE_BRANCH"; then
    git -C "$REPO_ROOT" worktree add --track -b "$STAGE_BRANCH" "$WORKTREE_ROOT" "origin/$STAGE_BRANCH"
  else
    git -C "$REPO_ROOT" worktree add -b "$STAGE_BRANCH" "$WORKTREE_ROOT" main
  fi
fi
printf 'CERTO_REPO_ROOT=%s\nCERTO_WORKTREE_ROOT=%s\nCERTO_STAGE_BRANCH=%s\n' \
  "$REPO_ROOT" "$WORKTREE_ROOT" "$STAGE_BRANCH"
