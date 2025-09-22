# Enterprise Testing Framework with GitHub Actions Integration
PKG := ledzephyr
SRC := src tests
PY  := poetry run

.PHONY: init hooks format lint type type-strict test unit integration e2e cov sec audit check fix tdm-validate tdm-check test-all specs gold test-specs school-api school-data school-config school-performance schools-all schools-list all clean dev-setup validate deps-logs logs test-logs lint-logs workflows-status workflows-run workflows-validate

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
	$(MAKE) sec
	$(MAKE) audit
	$(MAKE) unit
	$(MAKE) integration
	$(MAKE) schools-all
	$(MAKE) e2e
	$(MAKE) test-specs
	$(MAKE) tdm-validate

fix:     ## writer gate: autofix, then re-run checks
	$(MAKE) format
	$(MAKE) check

all: init fix workflows-validate  ## complete setup and validation

# Development workflow targets
dev-setup: init gold specs  ## setup development environment with test data

validate: check   ## alias for check - comprehensive validation

specs:   ## fetch and cache API specifications
	$(PY) python -c "from migrate_specs import fetch, config; [fetch.fetch_spec(s) for s in config.ALL]"
	$(PY) python -c "from migrate_specs import fetch, parse, config; import json, pathlib; files = {s.name: fetch.fetch_spec(s) for s in config.ALL}; pathlib.Path('specs/summary.json').write_text(__import__('json').dumps(parse.extract_shapes(files), indent=2))"

gold:    ## generate gold master test datasets
	$(PY) python -c "from migrate_specs import gold; import pathlib; gold.build_gold_master(pathlib.Path('gold'))"

test-specs:  ## run all spec management tests
	$(PY) pytest tests/specs -q --no-cov

lean-test:  ## Run only the critical 5 tests (530ms total)
	@echo "Running Critical 5 Lean Tests..."
	@$(PY) pytest \
		tests/integration/test_gold_master_algorithms.py::TestGoldMasterAlgorithms::test_basic_dataset_algorithms \
		tests/unit/ledzephyr/test_client.py::TestAPIClientRequestHandling::test_make_request_429_raises_rate_limit_error \
		tests/unit/ledzephyr/test_time_windows.py::TestParseWindowsBoundaryConditions::test_parse_windows_leap_year_february_29_calculates_correctly \
		tests/unit/ledzephyr/test_cache.py::TestSimpleAPICache::test_cache_expiration_functionality \
		tests/integration/test_gold_master_algorithms.py::TestGoldMasterAlgorithms::test_edge_cases_algorithms \
		--tb=short -q --no-cov
	@echo "✅ Core risks validated in <1 second"

# School of Fish Integration Tests
school-api:       ## run API school tests (external API patterns)
	$(PY) python -m tests.integration.schools.cli --school api

school-data:      ## run Data school tests (data flow patterns)
	$(PY) python -m tests.integration.schools.cli --school data

school-config:    ## run Config school tests (environment patterns)
	$(PY) python -m tests.integration.schools.cli --school config

school-performance: ## run Performance school tests (timing patterns)
	$(PY) python -m tests.integration.schools.cli --school performance

schools-all:      ## run all schools in parallel for maximum efficiency
	$(PY) python -m tests.integration.schools.cli --workers 4

schools-list:     ## list all available schools and their katas
	$(PY) python -m tests.integration.schools.cli --list

clean:   ## clean build artifacts and caches
	rm -rf .mypy_cache .ruff_cache .pytest_cache .coverage .hypothesis
	rm -rf reports/ htmlcov/ .ledzephyr_cache/
	rm -rf src/**/__pycache__ tests/**/__pycache__ tdm/**/__pycache__ migrate_specs/**/__pycache__
	rm -rf specs/ gold/ test_reports/

# Documentation sync and feedback
sync-docs:  ## Check documentation sync status between local/Confluence/Jira
	@LEDZEPHYR_JIRA_URL=https://balabushka.atlassian.net ./scripts/sync-docs.sh

sync-verify:  ## Verify documentation sync and detect drift
	@./scripts/sync-verify.sh

metrics:  ## Track and report lean metrics
	@./scripts/metrics-track.sh

feedback:  ## View feedback and improvement guide
	@cat FEEDBACK.md

# Log viewing targets
deps-logs:  ## Install lnav for log viewing
	@command -v lnav >/dev/null 2>&1 || { \
		echo "Installing lnav..."; \
		if [[ "$$(uname)" == "Darwin" ]]; then \
			command -v brew >/dev/null 2>&1 && brew install lnav || echo "Please install Homebrew first"; \
		else \
			echo "Please install lnav: https://lnav.org/downloads"; \
		fi; \
	}
	@echo "lnav is installed"

logs:  ## View application logs with lnav
	@chmod +x scripts/dev-logs.sh 2>/dev/null || true
	@chmod +x tools/lnav/prepare.sh 2>/dev/null || true
	@scripts/dev-logs.sh --all

test-logs:  ## Test log viewing functionality
	@chmod +x tests/shell/*.sh 2>/dev/null || true
	@chmod +x scripts/dev-logs.sh 2>/dev/null || true
	@chmod +x tools/lnav/prepare.sh 2>/dev/null || true
	@bash tests/shell/test_dev_logs.sh
	@bash tests/shell/test_log_format.sh
	@bash tests/shell/test_determinism.sh

lint-logs:  ## Validate log format schemas
	@echo "Validating log schemas..."
	@jq empty tools/lnav/formats/app.schema.json && echo "✓ app.schema.json is valid JSON"
	@jq empty tools/lnav/formats/app-format.json && echo "✓ app-format.json is valid JSON"
	@jq empty tools/lnav/lnav_config.json && echo "✓ lnav_config.json is valid JSON"
	@echo "All log configuration files are valid"

# GitHub Actions Workflow Management
workflows-status:  ## Check status of GitHub Actions workflows
	@echo "Checking GitHub Actions workflow status..."
	@gh workflow list --all || echo "GitHub CLI not available or not authenticated"
	@gh run list --limit 5 || true

workflows-run:     ## Trigger specific workflow (usage: make workflows-run WORKFLOW=ci)
	@test -n "$(WORKFLOW)" || { echo "Usage: make workflows-run WORKFLOW=<workflow-name>"; exit 1; }
	@echo "Triggering workflow: $(WORKFLOW)"
	@gh workflow run $(WORKFLOW).yml || echo "Failed to trigger workflow"

workflows-validate: ## Validate all GitHub Actions workflows
	@echo "Validating GitHub Actions workflows..."
	@for workflow in .github/workflows/*.yml; do \
		echo "Validating $$workflow..."; \
		yq eval '.name' "$$workflow" >/dev/null || { echo "❌ Invalid YAML in $$workflow"; exit 1; }; \
	done
	@echo "✅ All workflows are valid YAML"

workflows-ci:      ## Trigger CI workflow
	@make workflows-run WORKFLOW=ci

workflows-tests:   ## Trigger all test workflows in parallel
	@echo "Triggering all test workflows..."
	@gh workflow run test-unit.yml || true
	@gh workflow run test-integration.yml || true
	@gh workflow run test-e2e.yml || true
	@gh workflow run test-matrix.yml || true
	@echo "Test workflows triggered. Check status with: make workflows-status"