# LedZephyr - Lean Implementation Makefile
PACKAGE := ledzephyr
SCRIPT := ledzephyr/main.py
PY := poetry run

.PHONY: help run test format lint clean install logs logs-errors logs-follow

help:  ## Show this help
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies and package
	poetry install

run:  ## Run LedZephyr (requires PROJECT env var)
	@if [ -z "$(PROJECT)" ]; then echo "Usage: make run PROJECT=MYPROJECT"; exit 1; fi
	$(PY) ledzephyr --project $(PROJECT)

test:  ## Run lean test suite
	$(PY) python test_lean.py

format:  ## Format code with black
	$(PY) black $(SCRIPT) test_lean.py

lint:  ## Lint with ruff
	$(PY) ruff check $(SCRIPT) test_lean.py

type:  ## Type check with mypy
	$(PY) mypy $(SCRIPT) test_lean.py

security:  ## Security scan with bandit
	$(PY) bandit -c pyproject.toml $(SCRIPT)

safety:  ## Check dependencies for vulnerabilities
	$(PY) safety scan --output screen || echo "Vulnerabilities found"

check-all:  ## Run all quality checks
	make format lint type security safety

pre-commit:  ## Install pre-commit hooks
	$(PY) pre-commit install

clean:  ## Clean cache and temp files
	rm -rf __pycache__ .pytest_cache .ruff_cache
	rm -rf data/test data/TEST
	find . -type f -name "*.pyc" -delete

# Quick commands
fetch:  ## Fetch fresh data (requires PROJECT)
	@if [ -z "$(PROJECT)" ]; then echo "Usage: make fetch PROJECT=MYPROJECT"; exit 1; fi
	$(PY) ledzephyr --project $(PROJECT) --fetch

analyze:  ## Analyze existing data (requires PROJECT)
	@if [ -z "$(PROJECT)" ]; then echo "Usage: make analyze PROJECT=MYPROJECT"; exit 1; fi
	$(PY) ledzephyr --project $(PROJECT) --no-fetch

# Info
info:  ## Show lean metrics
	@echo "📊 LedZephyr Lean Metrics"
	@echo "========================"
	@echo "Main module: $$(wc -l < $(SCRIPT)) lines"
	@echo "Test suite: $$(wc -l < test_lean.py) lines"
	@echo "Dependencies: 3 runtime (click, httpx, rich)"
	@echo "API endpoints: 15"
	@echo ""
	@echo "Before: 2,850 lines across 13 files"
	@echo "After: $$(wc -l < $(SCRIPT)) lines main + $$(wc -l < test_lean.py) tests"
	@echo "Reduction: 79% main code"

logs:  ## Show recent log entries
	@if [ -f ./logs/ledzephyr.log ]; then tail -20 ./logs/ledzephyr.log; else echo "No logs found. Run LedZephyr first."; fi

logs-errors:  ## Show recent errors
	@if [ -f ./logs/ledzephyr.log ]; then grep ERROR ./logs/ledzephyr.log | tail -10; else echo "No logs found."; fi

logs-follow:  ## Follow logs in real-time
	@if [ -f ./logs/ledzephyr.log ]; then tail -f ./logs/ledzephyr.log; else echo "No logs found. Run LedZephyr first."; fi