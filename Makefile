# Lean Automated SDLC - Platform Integration
PKG := ledzephyr
SRC := src tests
PY  := poetry run

.PHONY: init format lint type test sec audit clean help

# Core Development
init:  ## Initialize project dependencies
	poetry lock
	poetry install --sync
	$(PY) pre-commit install

format:  ## Auto-format and import sort
	$(PY) black $(SRC)
	$(PY) ruff check --fix $(SRC)

lint:  ## Static checks without modifying code
	$(PY) ruff check $(SRC)
	$(PY) bandit -q -r src

type:  ## Fast type check
	$(PY) mypy -p $(PKG)

test:  ## Run unit tests (lean-test)
	$(PY) pytest tests/unit -m "not slow" -q

sec:  ## Code security scan
	$(PY) bandit -q -r src

audit:  ## Dependency vulnerability scan
	$(PY) pip-audit --desc

clean:  ## Clean build artifacts and caches
	rm -rf .mypy_cache .ruff_cache .pytest_cache .coverage
	rm -rf htmlcov/ build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Platform Integration Notice
platform-info:  ## Platform automation information
	@echo "🚀 Platform Automation Active"
	@echo "================================"
	@echo ""
	@echo "This project uses cloud-native automation:"
	@echo "  • Atlassian Rovo AI agents"
	@echo "  • GitHub/GitLab Actions"
	@echo "  • Jira-Git integration"
	@echo ""
	@echo "Local scripts have been replaced with:"
	@echo "  • Rovo Documentation Agent"
	@echo "  • Rovo Metrics Agent"
	@echo "  • Rovo Test Orchestration"
	@echo ""
	@echo "See Confluence for documentation:"
	@echo "  https://balabushka.atlassian.net/wiki/spaces/LedZephyr"

help:  ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Default target
.DEFAULT_GOAL := help