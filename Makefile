PYTHON ?= python3
VENV ?= .venv
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

.PHONY: venv install test test-fast hygiene r0 smoke pilot review-packages

venv:
	$(PYTHON) -m venv $(VENV)

install:
	$(VENV)/bin/python -m pip install --upgrade pip wheel setuptools
	$(VENV)/bin/python -m pip install -e '.[dev,sim,learn]'

test:
	env -u PYTHONPATH $(VENV)/bin/python -m pytest -q

test-fast:
	env -u PYTHONPATH $(VENV)/bin/python -m pytest -q -m "not slow"

hygiene:
	bash scripts/check_repo_hygiene.sh

r0:
	bash scripts/run_r0.sh configs/stage1r_pilot.yaml $(RUN_ID)

smoke:
	bash scripts/run_stage1r.sh configs/stage1r_smoke.yaml $(RUN_ID)

pilot:
	bash scripts/run_stage1r.sh configs/stage1r_pilot.yaml $(RUN_ID)

review-packages:
	bash scripts/build_review_packages.sh $(RUN_ID)
