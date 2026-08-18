PYTHON ?= python3
VENV ?= .venv

.PHONY: venv install install-paper-reset test test-fast hygiene stage1 paper-reset-freeze paper-reset-provenance review-packages

venv:
	$(PYTHON) -m venv $(VENV)

install:
	$(VENV)/bin/python -m pip install --upgrade pip wheel setuptools
	$(VENV)/bin/python -m pip install -e '.[dev]'

install-paper-reset:
	$(VENV)/bin/python -m pip install -e '.[dev,paper-reset]'

test:
	$(VENV)/bin/python -m pytest -q

test-fast:
	$(VENV)/bin/python -m pytest -q -m "not slow"

hygiene:
	bash scripts/check_repo_hygiene.sh

stage1:
	bash scripts/run_stage1.sh --clean

paper-reset-freeze:
	$(VENV)/bin/python -m certo_fdi_reset.freeze --config configs/paper_reset.yaml

paper-reset-provenance:
	$(VENV)/bin/python -m certo_fdi_reset.provenance_report --config configs/paper_reset.yaml

review-packages:
	bash scripts/build_review_packages.sh
