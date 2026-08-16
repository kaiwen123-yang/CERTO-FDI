PYTHON ?= python3
VENV ?= .venv
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

.PHONY: venv install test test-fast hygiene freeze baseline dictionaries tests ablations metrics decide finalize review-packages

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

CONFIG ?= configs/stage2a_pathway_audit.yaml

freeze:
	bash scripts/run_stage2a.sh freeze $(CONFIG) $(RUN_ID)

baseline:
	bash scripts/run_stage2a.sh baseline $(CONFIG) $(RUN_ID)

dictionaries:
	bash scripts/run_stage2a.sh dictionaries $(CONFIG) $(RUN_ID)

ablations:
	bash scripts/run_stage2a.sh ablations $(CONFIG) $(RUN_ID)

metrics:
	bash scripts/run_stage2a.sh metrics $(CONFIG) $(RUN_ID)

decide:
	bash scripts/run_stage2a.sh decide $(CONFIG) $(RUN_ID)

finalize:
	bash scripts/run_stage2a.sh finalize $(CONFIG) $(RUN_ID)

review-packages:
	bash scripts/run_stage2a.sh package $(CONFIG) $(RUN_ID)
