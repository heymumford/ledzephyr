# Contributing

## Setup

```bash
git clone https://github.com/yourusername/ledzephyr.git
cd ledzephyr
poetry install
pre-commit install
```

## Development

```bash
# Run tests
poetry run pytest

# Quality checks
poetry run pre-commit run --all-files

# Architecture validation
poetry run python scripts/check-dependencies.py
poetry run python scripts/check-architecture.py
```

## Pull Requests

1. Create feature branch
2. Write tests first (TDD)
3. Ensure all checks pass
4. Submit PR with clear description

## Standards

- Follow clean architecture layers (Domain → Application → Infrastructure → Presentation)
- No dependencies pointing inward
- 90% test coverage required
- Property-based tests for business logic
- Type annotations mandatory