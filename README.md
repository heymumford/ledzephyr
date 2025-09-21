# ledzephyr

**Enterprise Testing Framework**: Production-ready CLI tool with industry-standard GitHub Actions workflows for Zephyr Scale → qTest migration analytics. Features revolutionary three-layer testing architecture with Test Data Management (TDM) and parallel execution capabilities.

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/heymumford/ledzephyr.git
cd ledzephyr
make init

# 2. Verify GitHub Actions workflows
make workflows-status

# 2. Configure environment (copy .env.example to .env and edit)
cp .env.example .env
# Edit .env with your API credentials

# 3. Test connectivity
lz doctor

# 4. Generate metrics
lz metrics -p PROJECT_KEY -w 7d -w 30d --format table
```

## Configuration

### Required Environment Variables
```bash
LEDZEPHYR_JIRA_URL=https://your-domain.atlassian.net
LEDZEPHYR_JIRA_USERNAME=your.email@company.com
LEDZEPHYR_JIRA_API_TOKEN=your_jira_api_token
```

### Optional Environment Variables
```bash
# Zephyr Scale (if different from Jira URL)
LEDZEPHYR_ZEPHYR_URL=https://your-domain.atlassian.net
LEDZEPHYR_ZEPHYR_TOKEN=your_zephyr_token

# qTest
LEDZEPHYR_QTEST_URL=https://your-domain.qtestnet.com
LEDZEPHYR_QTEST_TOKEN=your_qtest_token

# HTTP Configuration
LEDZEPHYR_TIMEOUT=30
LEDZEPHYR_MAX_RETRIES=3
```

## Usage Examples

```bash
# Check API connectivity to all configured services
lz doctor

# Basic metrics for a project
lz metrics -p MYPROJECT -w 7d

# Multiple time windows with CSV output
lz metrics -p MYPROJECT -w 24h -w 7d -w 30d --format table --out metrics.csv

# Team-based metrics using component field
lz metrics -p MYPROJECT -w 7d --teams-source component

# JSON output for automation
lz metrics -p MYPROJECT -w 7d --format json
```

## Development & Testing

### School-of-Fish Testing Architecture

This project uses a revolutionary "school-of-fish" integration testing pattern where orthogonal test concerns swim independently in parallel for maximum efficiency:

```bash
# Full development setup
make init                    # Install deps + pre-commit hooks

# Layer-by-layer testing (recommended)
make unit                    # Fast unit tests (<1s) - math, parsers
make integration            # Integration tests (<10s) - API clients with doubles
make e2e                     # E2E tests (<30s) - manifest-driven pipeline

# School-of-Fish Integration Tests - NEW!
make schools-all            # Run all schools in parallel (4 workers)
make schools-list           # List all available schools and katas
make school-api             # Run API school (external API patterns)
make school-data            # Run Data school (data flow patterns)
make school-config          # Run Config school (environment patterns)
make school-performance     # Run Performance school (timing patterns)

# API Specification Management
make specs                  # Fetch and cache API specifications
make gold                   # Generate gold master test datasets
make test-specs             # Run all spec management tests

# All layers with detailed reporting
make test-all               # Run all layers with timing and statistics
make cov                     # Full coverage report with all layers

# TDM (Test Data Management)
make tdm-validate           # Validate all TDM manifests
make tdm-check              # Check manifest references and cassettes

# Quality gates
make check                   # All quality checks (lint, type, tests, security, TDM)
make fix                     # Auto-format and fix issues

# Individual tools
make lint                    # Static analysis (ruff + bandit)
make type                    # Type checking (mypy)
make sec                     # Security scan (bandit)
```

### School-of-Fish Pattern

Each "school" represents orthogonal test concerns that can run in parallel:

- **🏫 API School**: External API integration patterns (mocking, errors, timeouts)
- **🏫 Data School**: Data flow and transformation (gold master, metrics, validation)
- **🏫 Config School**: Configuration and environment patterns
- **🏫 Performance School**: Timing, resource usage, and scalability

**Benefits:**
- ⚡ **Parallel Execution**: Schools swim independently for 2-4x speedup
- 🎯 **Atomic Testing**: Each kata has 1 clear goal with built-in validation
- 🔄 **Composable Design**: Schools can be combined or run individually
- 📊 **Performance Tracking**: Detailed metrics for optimization

### Advanced Test Execution

```bash
# Use the test runner directly for more control
./scripts/test-runner.sh unit --verbose
./scripts/test-runner.sh integration --coverage
./scripts/test-runner.sh e2e --fail-fast
./scripts/test-runner.sh all --coverage --verbose

# School-of-fish direct execution
poetry run python -m tests.integration.schools.cli --workers 8
poetry run python -m tests.integration.schools.cli --school data --verbose

# TDM operations
./scripts/tdm.sh validate testdata/manifests/demo_project_2025q2.yaml
./scripts/tdm.sh validate-all
./scripts/tdm.sh list-manifests
./scripts/tdm.sh check-cassettes
```

### Test Architecture Overview

- **Unit Tests** (`tests/unit/`): Pure math, formatters, business logic - <1s execution
- **Integration Tests** (`tests/integration/`): API clients with test doubles - <10s execution
- **School-of-Fish Tests** (`tests/integration/schools/`): Parallel orthogonal integration tests - <5s execution
- **E2E Tests** (`tests/e2e/`): Full Pull→Math→Print pipeline with TDM manifests - <30s execution
- **Spec Management** (`tests/specs/`): API specification fetching and gold master generation

See `tests/README.md` for detailed testing architecture documentation.

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for comprehensive deployment instructions including:
- Docker and Kubernetes deployment
- Monitoring and observability setup
- Security considerations
- Production checklist

### Quick Start - Monitoring

```bash
# Start monitoring server
lz monitor --port 8080

# Access endpoints
curl http://localhost:8080/health  # Health checks
curl http://localhost:8080/metrics  # Prometheus metrics
```

## Observability

Ledzephyr includes comprehensive observability features:

- **Structured Logging** with correlation IDs
- **Prometheus Metrics** for monitoring
- **OpenTelemetry Tracing** for distributed tracing
- **Health Checks** for service status
- **Grafana Dashboards** for visualization
- **Alerting Rules** for proactive monitoring

## License

MIT