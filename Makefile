# Minimal local quality gates
PKG := ledzephyr
SRC := src tests
PY  := poetry run

.PHONY: init hooks format lint type type-strict test unit integration cov sec audit check fix all clean

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

unit:
	$(PY) pytest -m "unit"

integration:
	$(PY) pytest -m "integration"

cov:     ## full suite with coverage artifacts
	$(PY) pytest -q --cov=$(PKG) --cov-report=term-missing
	$(PY) coverage xml -o reports/coverage.xml
	$(PY) coverage html -d reports/coverage_html

sec:     ## code security scan
	$(PY) bandit -q -r src

audit:   ## dependency vulnerability scan (lockfile-based)
	$(PY) pip-audit --desc

check:   ## read-only CI-equivalent gate
	$(MAKE) lint
	$(MAKE) type
	$(MAKE) test
	$(MAKE) cov
	$(MAKE) sec
	$(MAKE) audit

fix:     ## writer gate: autofix, then re-run checks
	$(MAKE) format
	$(MAKE) check

all: init fix

clean:
	rm -rf .mypy_cache .ruff_cache .pytest_cache .coverage reports/coverage* reports/coverage_html .cache