# Balanced Testing POC with TDM Framework
PKG := ledzephyr
SRC := src tests
PY  := poetry run

.PHONY: init hooks format lint type type-strict test unit integration e2e cov sec audit check fix tdm-validate tdm-check test-all all clean

init:
	poetry lock
	poetry install --sync
	$(PY) pre-commit install

hooks:
	$(PY) pre-commit run --all-files

format:  ## auto-format and import sort
	$(PY) black $(SRC)
	$(PY) ruff check --fix $(SRC)

lint:    ## static checks without modifying code
	$(PY) ruff check $(SRC)
	$(PY) bandit -q -r src

type:    ## fast type check
	$(PY) mypy -p $(PKG)

type-strict:  ## stricter mode if you opt-in per module
	$(PY) mypy --strict -p $(PKG)

test:    ## run unit tests by default
	$(PY) pytest -m "unit"

unit:    ## fast unit tests (math, parsers, pure logic)
	./scripts/test-runner.sh unit

integration:  ## integration tests with test doubles
	./scripts/test-runner.sh integration

e2e:     ## end-to-end tests with manifest replay
	./scripts/test-runner.sh e2e

cov:     ## full test suite with coverage artifacts
	./scripts/test-runner.sh all --coverage

sec:     ## code security scan
	$(PY) bandit -q -r src

audit:   ## dependency vulnerability scan (lockfile-based)
	$(PY) pip-audit --desc

tdm-validate:  ## validate TDM manifests
	./scripts/tdm.sh validate-all

tdm-check:     ## check TDM cassettes and manifests
	./scripts/tdm.sh check-cassettes

test-all:      ## run all test layers with timing
	./scripts/test-runner.sh all --verbose

check:   ## read-only CI-equivalent gate
	$(MAKE) lint
	$(MAKE) type
	$(MAKE) unit
	$(MAKE) integration
	$(MAKE) e2e
	$(MAKE) sec
	$(MAKE) tdm-validate

fix:     ## writer gate: autofix, then re-run checks
	$(MAKE) format
	$(MAKE) check

all: init fix

clean:   ## clean build artifacts and caches
	rm -rf .mypy_cache .ruff_cache .pytest_cache .coverage .hypothesis
	rm -rf reports/ htmlcov/ .ledzephyr_cache/
	rm -rf src/**/__pycache__ tests/**/__pycache__ tdm/**/__pycache__