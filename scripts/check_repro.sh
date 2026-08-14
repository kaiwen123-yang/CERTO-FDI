#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
pytest -q
python - <<'PY'
from pathlib import Path
import json
p=Path('results/generated/stage1_run_manifest.json')
if not p.exists():
    raise SystemExit('missing run manifest')
obj=json.loads(p.read_text())
print(json.dumps(obj, indent=2, sort_keys=True))
PY
