# LedZephyr - Lean Implementation Makefile
SCRIPT := ledzephyr_lean.py
PY := poetry run

.PHONY: help run test format lint clean install

help:  ## Show this help
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	poetry install --no-root

run:  ## Run LedZephyr (requires PROJECT env var)
	@if [ -z "$(PROJECT)" ]; then echo "Usage: make run PROJECT=MYPROJECT"; exit 1; fi
	$(PY) python $(SCRIPT) --project $(PROJECT)

test:  ## Run lean test suite
	$(PY) python test_lean.py

format:  ## Format code with black
	$(PY) black $(SCRIPT) test_lean.py

lint:  ## Lint with ruff
	$(PY) ruff check $(SCRIPT) test_lean.py

clean:  ## Clean cache and temp files
	rm -rf __pycache__ .pytest_cache .ruff_cache
	rm -rf data/test data/TEST
	find . -type f -name "*.pyc" -delete

# Quick commands
fetch:  ## Fetch fresh data (requires PROJECT)
	@if [ -z "$(PROJECT)" ]; then echo "Usage: make fetch PROJECT=MYPROJECT"; exit 1; fi
	$(PY) python $(SCRIPT) --project $(PROJECT) --fetch

analyze:  ## Analyze existing data (requires PROJECT)
	@if [ -z "$(PROJECT)" ]; then echo "Usage: make analyze PROJECT=MYPROJECT"; exit 1; fi
	$(PY) python $(SCRIPT) --project $(PROJECT) --no-fetch

# Info
info:  ## Show lean metrics
	@echo "📊 LedZephyr Lean Metrics"
	@echo "========================"
	@echo "Lines of code: $$(wc -l < $(SCRIPT))"
	@echo "Dependencies: 3 (click, httpx, rich)"
	@echo "API endpoints: 15"
	@echo ""
	@echo "Before: 2,850 lines across 13 files"
	@echo "After: 306 lines in 1 file"
	@echo "Reduction: 89.3%"