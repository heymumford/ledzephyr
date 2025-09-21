# Contributing

## Setup

```bash
git clone https://github.com/heymumford/ledzephyr.git
cd ledzephyr
make init  # Installs dependencies and pre-commit hooks
```

## Development

```bash
# Run tests
make test                    # Unit tests only
make cov                     # Full test suite with coverage

# Quality checks
make check                   # All quality gates (lint, type, test, security)
make fix                     # Auto-format and fix issues

# Individual checks
make lint                    # Static analysis
make type                    # Type checking
make sec                     # Security scan
```

## Pull Requests

1. Create feature branch
2. Write tests first (TDD)
3. Run `make check` to ensure all gates pass
4. Submit PR with clear description

## Standards

- Simple CLI tool focused on Jira/qTest/Zephyr APIs
- 80% test coverage required
- Type annotations mandatory
- Property-based tests for business logic