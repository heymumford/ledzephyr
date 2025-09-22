# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LedZephyr is a CLI tool for calculating migration metrics from Zephyr Scale to qTest. It follows a lean architecture philosophy with a focus on simplicity, minimal dependencies, and risk-based testing.

### Project Documentation
- **Confluence Space**: https://balabushka.atlassian.net/wiki/spaces/LedZephyr/overview?homepageId=8683825
  - Space ID: 8683575
  - Space Key: LedZephyr
  - Homepage ID: 8683825
- **Jira Project**: LED (https://balabushka.atlassian.net/browse/LED)
- **Cloud ID**: f1ecf30e-e4d0-48d9-bc3a-e738126b7afd

## Essential Commands

### Development Setup
```bash
# Initial setup with Poetry
make init

# Run the critical 5 tests (530ms, covers 90% of risks)
make lean-test

# Format and lint code before committing
make fix
```

### Testing Commands
```bash
# Run specific test layers
make unit           # Fast unit tests (<1s)
make integration    # Integration tests with test doubles (<10s)
make e2e           # End-to-end manifest-driven tests (<30s)

# Run all tests with coverage
make cov

# Run specific test with pytest
.venv/bin/python -m pytest tests/unit/ledzephyr/test_client.py::TestAPIClientEdgeCases::test_context_manager_functionality -v

# School of Fish integration tests
make schools-all   # Run all test schools in parallel
```

### Code Quality
```bash
# Format code
make format

# Run linting and type checking
make lint
make type

# Security scanning
make sec
make audit
```

### GitHub Actions Workflows
```bash
# Check workflow status
make workflows-status

# Validate all workflows
make workflows-validate

# Trigger CI workflow
make workflows-ci
```

## Architecture Overview

The codebase follows a monolithic architecture with 4 core components:

1. **CLI Interface** (`src/ledzephyr/cli.py`) - Typer-based CLI handling user commands
2. **Metrics Calculator** (`src/ledzephyr/metrics.py`) - Pure functions for metric calculations
3. **API Client** (`src/ledzephyr/client.py`) - HTTP client with retry logic and circuit breaker
4. **Cache Layer** (`src/ledzephyr/cache.py`) - Memory-based LRU caching

### Key Architectural Decisions
- **Monolith over microservices** - Simplicity is prioritized
- **Memory cache over Redis** - No external dependencies
- **Environment variables for config** - No configuration files
- **5 critical tests over 200** - Risk coverage over code coverage

## Test Architecture

Tests are organized in three layers:

```
tests/
├── unit/          # Pure logic, no I/O (<1s execution)
├── integration/   # API clients with test doubles (<10s)
└── e2e/          # Full pipeline validation (<30s)
```

### Test Doubles Strategy
- **Stubs**: Fixed responses in `tests/integration/doubles/stub_*.py`
- **Fakes**: In-memory implementations with configurable behavior
- **Gold Master**: Algorithm validation with known input/output pairs

## Configuration

All configuration via environment variables (no config files):
```bash
LEDZEPHYR_JIRA_URL=https://your.atlassian.net
LEDZEPHYR_JIRA_API_TOKEN=your_token
LEDZEPHYR_CACHE_TTL=3600
LEDZEPHYR_RETRY_COUNT=3
```

## Dependencies

Core dependencies managed by Poetry:
- `typer` - CLI framework
- `httpx` - Modern async-ready HTTP client
- `pydantic` - Data validation
- `tenacity` - Retry logic
- `structlog` - Structured logging
- `prometheus-client` - Metrics collection

## Error Handling Pattern

The codebase follows a "fail fast, recover gracefully" pattern:
- `RateLimitError` - Automatic retry with exponential backoff
- `NetworkError` - Falls back to cached data
- Other exceptions - Log and exit immediately

## School of Fish Testing

The project implements a parallel testing architecture called "School of Fish":
- API School - External API interaction patterns
- Data School - Data flow and transformation patterns
- Config School - Environment and configuration patterns
- Performance School - Timing and performance patterns

Run with: `make schools-all`

## GitHub Actions Workflows

11 standardized workflows in `.github/workflows/`:
- `ci.yml` - Main CI/CD pipeline
- `test-unit.yml`, `test-integration.yml`, `test-e2e.yml` - Test rails
- `test-matrix.yml` - Multi-version testing
- `orchestrator-master.yml` - AI-powered workflow orchestration
- `coordinator.yml` - Cross-workflow coordination

## Important Files and Patterns

- Test runner script: `scripts/test-runner.sh` - Handles all test execution modes
- TDM validation: `scripts/tdm.sh` - Test Data Management manifest validation
- Gold master datasets: `testdata/fixtures/math_*.json`
- Test doubles: `tests/integration/doubles/`
- Observability: `src/ledzephyr/observability.py` - Logging, metrics, tracing setup

## CLI Commands

The main CLI entry points are `lz` and `ledzephyr`:

```bash
# Check API connectivity
lz doctor

# Calculate metrics
lz metrics -p PROJECT -w 7d

# Generate adoption report
lz adoption -p PROJECT -o report.csv

# Inspect cache
lz cache list
lz cache clear

# Generate training impact analysis
lz training-impact -p PROJECT --before 2024-01-01 --after 2024-02-01
```

## Development Workflow

1. Make changes to code
2. Run `make lean-test` for quick validation (530ms)
3. Run `make fix` to format and lint
4. Run full test suite with `make check`
5. Commit with proper commit message format

## Performance Targets

- Response time: <100ms (cached), <2s (cold)
- Cache hit rate: 90%
- Test execution: Unit <1s, Integration <10s, E2E <30s
- Code complexity: <10 cyclomatic complexity

## Monitoring and Observability

- Health endpoint: `/health`
- Metrics endpoint: `/metrics` (Prometheus format)
- Structured logging to stderr
- OpenTelemetry tracing support (when enabled)

## Migration Metrics

The core metrics calculated for Zephyr → qTest migration:

1. **Adoption Ratio** - `qtest_count / total_count`
2. **Coverage Parity** - `qtest_coverage / zephyr_coverage`
3. **Active Users** - Unique assignees in time window
4. **Training Impact** - Pre/post training velocity change
5. **Team Inventory** - Per-team migration progress

## Critical Test Coverage Areas

Based on risk analysis, these areas require the most test attention:

1. **adoption_report.py** (15% coverage) - User-facing reports driving $10K+ decisions
2. **identity_resolution.py** (28% coverage) - Entity matching accuracy critical
3. **training_impact.py** (39% coverage) - ROI calculations for $500K budget
4. **CLI adoption command** - New user-facing command needs smoke tests
5. **Cohort analysis** - Edge cases with uneven user distributions

## API Rate Limiting

The client implements adaptive rate limiting with circuit breakers:
- Jira API: 10 requests/second with burst of 20
- Zephyr API: Adaptive based on 429 responses
- qTest API: Token bucket with configurable limits
- Circuit breaker: 5 failures trigger 60s cooldown

## Data Models

Core data models in `src/ledzephyr/models.py`:
- `JiraProject` - Project metadata and configuration
- `TestCaseModel` - Test case with execution history
- `ProjectMetrics` - Calculated migration metrics
- `TeamSource` - Team-specific data source
- `User`, `DailySnapshot`, `TeamInventory` - Adoption tracking

## Two-Module Architecture Pattern

The codebase follows a two-module pattern for new features:
1. **Logic Module** (`adoption_metrics.py`) - Pure business logic, no I/O
2. **Report Module** (`adoption_report.py`) - I/O, formatting, presentation

This separation ensures testability and maintainability.