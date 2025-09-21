# Project Structure Documentation

## Overview

ledzephyr implements a **balanced testing POC** demonstrating three-layer testing architecture with comprehensive Test Data Management (TDM) framework.

## Directory Structure

```
ledzephyr/
├── src/
│   └── ledzephyr/          # Main application package
│       ├── __init__.py
│       ├── cli.py          # Command-line interface
│       ├── client.py       # API clients (Pull layer)
│       ├── config.py       # Configuration management
│       ├── metrics.py      # Core calculations (Math layer)
│       ├── models.py       # Data models and types
│       ├── time_windows.py # Time parsing utilities
│       └── cache.py        # Caching layer
├── tests/
│   ├── unit/               # Layer 1: Fast, isolated tests (<1s)
│   │   ├── ledzephyr/      # Module-specific unit tests
│   │   └── test_math_golden.py  # Golden file math tests
│   ├── integration/        # Layer 2: API client tests (<10s)
│   │   ├── doubles/        # Test doubles (stubs, fakes, spies)
│   │   │   └── stub_jira.py
│   │   ├── test_pull_with_stubs.py
│   │   └── test_cli_integration.py
│   ├── e2e/               # Layer 3: End-to-end tests (<30s)
│   │   └── test_manifest_replay.py
│   ├── conftest.py        # Global test configuration
│   └── README.md          # Test architecture documentation
├── testdata/              # All test data organized by purpose
│   ├── cassettes/         # VCR cassettes for API replay
│   ├── expected/          # Expected outputs for validation
│   ├── fixtures/          # Golden test input/output files
│   ├── manifests/         # TDM configuration files
│   ├── masks/             # Data masking examples
│   └── README.md          # Test data documentation
├── tdm/                   # Test Data Management framework
│   ├── schema/            # JSON schemas for validation
│   │   └── manifest.schema.json
│   ├── tools/             # TDM utilities and scripts
│   │   └── validate_manifest.py
│   └── README.md          # TDM framework documentation
├── scripts/               # Development and automation scripts
│   ├── tdm.sh            # TDM operations script
│   └── test-runner.sh    # Balanced testing script
├── docs/                 # Documentation
│   └── project-structure.md  # This file
├── reports/              # Generated reports (coverage, etc.)
├── .github/              # GitHub workflows and templates
│   └── workflows/
├── Makefile              # Build and development tasks
├── pyproject.toml        # Project configuration and dependencies
└── README.md             # Main project documentation
```

## Architecture Layers

### Pull Layer (Data Ingestion)
- **Location**: `src/ledzephyr/client.py`
- **Purpose**: API clients for Jira, Zephyr, qTest
- **Testing**: Integration tests with test doubles

### Math Layer (Core Logic)
- **Location**: `src/ledzephyr/metrics.py`, `src/ledzephyr/models.py`
- **Purpose**: Business calculations and data transformations
- **Testing**: Unit tests with golden files and property-based testing

### Print Layer (Output)
- **Location**: `src/ledzephyr/cli.py` formatters
- **Purpose**: CLI output formatting and serialization
- **Testing**: Unit tests for formatters

## Test Data Management (TDM)

### Manifest-Driven Testing
- **Configuration**: YAML manifests in `testdata/manifests/`
- **Schema**: JSON Schema validation in `tdm/schema/`
- **Modes**: Replay (VCR), Stub (fixed), Fake (configurable)

### Quality Gates
- Schema compliance validation
- Data completeness checks (>98% non-null)
- Output checksum validation for regression detection

### Data Security
- Deterministic masking with configurable salt
- Scrubbed cassettes with no sensitive data
- Tokenization for linkable but anonymous data

## Development Scripts

### `scripts/test-runner.sh`
Balanced testing script with layer-specific execution:
- Runs tests in speed-optimized order
- Provides detailed timing and statistics
- Supports coverage reporting and fail-fast modes

### `scripts/tdm.sh`
TDM operations and validation:
- Manifest validation against JSON schema
- Cassette file reference checking
- Quality gate enforcement

## Configuration Files

### `pyproject.toml`
- Python packaging and dependency management
- Tool configurations (pytest, mypy, ruff, black)
- Testing framework setup with markers

### `Makefile`
- Standardized development tasks
- Quality gate enforcement
- Integration with custom scripts

### `.pre-commit-config.yaml`
- Code quality hooks
- Automated formatting and linting
- Security scanning with bandit

## Testing Framework

### Hypothesis Integration
- Property-based testing for mathematical invariants
- Configurable profiles (CI, dev, exhaustive)
- Deterministic seeds for reproducibility

### Pytest Markers
- Automatic marking based on test location
- Custom markers for test types (golden, property, snapshot)
- Selective test execution

### Coverage Reporting
- Module-level coverage tracking
- HTML and XML report generation
- Integration with CI/CD pipelines

## Quality Assurance

### Static Analysis
- **ruff**: Fast Python linter with extensive rule set
- **mypy**: Type checking with strict mode support
- **bandit**: Security vulnerability scanning

### Code Formatting
- **black**: Opinionated code formatting
- **ruff**: Import sorting and additional formatting

### Security
- Dependency vulnerability scanning with pip-audit
- Pre-commit hooks for security checks
- Data masking for sensitive test data

## Build and Deployment

### Poetry Package Management
- Deterministic dependency resolution
- Virtual environment management
- Build system integration

### CI/CD Integration
- GitHub Actions workflows
- Quality gate enforcement
- Automated testing and coverage reporting

## Documentation Standards

### README Files
- Project root: High-level overview and quick start
- Module READMEs: Specific component documentation
- Architecture documentation in `docs/`

### Code Documentation
- Docstrings for all public APIs
- Type hints for all function signatures
- Inline comments for complex logic

### Change Management
- Git commit message standards
- Version tagging strategy
- Release notes and changelogs

This structure supports rapid development while maintaining high code quality through automated testing, quality gates, and comprehensive documentation.