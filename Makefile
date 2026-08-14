PYTHON ?= python3
VENV ?= .venv

.PHONY: venv install test test-fast hygiene stage1 review-packages

venv:
	$(PYTHON) -m venv $(VENV)

install:
	$(VENV)/bin/python -m pip install --upgrade pip wheel setuptools
	$(VENV)/bin/python -m pip install -e '.[dev]'

test:
	$(VENV)/bin/python -m pytest -q

test-fast:
	$(VENV)/bin/python -m pytest -q -m "not slow"

hygiene:
	bash scripts/check_repo_hygiene.sh

stage1:
	bash scripts/run_stage1.sh --clean

review-packages:
	bash scripts/build_review_packages.sh
