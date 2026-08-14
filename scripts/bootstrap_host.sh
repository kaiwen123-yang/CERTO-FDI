#!/usr/bin/env bash
set -euo pipefail

if grep -qiE '(microsoft|wsl)' /proc/version 2>/dev/null; then
  printf 'CERTO_HOST_MODE=WSL\n'
else
  printf 'CERTO_HOST_MODE=UBUNTU\n'
fi
for command_name in git ssh python3 sha256sum unzip zip findmnt mountpoint; do
  command -v "$command_name" >/dev/null 2>&1 || printf 'MISSING_TOOL=%s\n' "$command_name"
done
uname -a
python3 --version
git --version
