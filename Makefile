PYTHON ?= python3
DEV_PYTHON := .venv/bin/python
export PYTHONPATH := src:.
export OMP_NUM_THREADS := 1
export OPENBLAS_NUM_THREADS := 1
export MKL_NUM_THREADS := 1

.PHONY: setup core-test test lint format-check config-check codex-check check experiment benchmark
setup:
	$(PYTHON) -m venv .venv
	$(DEV_PYTHON) -m pip install --disable-pip-version-check -r requirements-dev.txt
	$(DEV_PYTHON) -m pip install --no-build-isolation --no-deps -e .
core-test:
	$(PYTHON) -m unittest discover -s tests -q
test:
	$(DEV_PYTHON) -m pytest -q
lint:
	$(DEV_PYTHON) -m ruff check tools tests/dev
	$(DEV_PYTHON) -m ruff check --select E9,F63,F7,F82 src tests examples
format-check:
	$(DEV_PYTHON) -m ruff format --check tools tests/dev
config-check:
	$(DEV_PYTHON) tools/validate_environment.py
codex-check:
	$(DEV_PYTHON) tools/check_codex.py
check: lint format-check config-check test
experiment:
	$(DEV_PYTHON) tools/qtre_experiment.py run
benchmark:
	$(DEV_PYTHON) examples/benchmark_f1.py --repetitions 3
