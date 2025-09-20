# ledzephyr

Is your Jira test integration dropping out of the sky like a Led Zephyr? This is a utility to measure your migration to qTest cloud.

## Installation

This project uses Poetry for dependency management. To install:

```bash
# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

## Usage

The CLI provides a `metrics` command to retrieve metrics for specified time windows:

```bash
# Using Poetry
poetry run lz --help
poetry run lz -p <API_KEY> -w 24h --format table
poetry run lz -p <API_KEY> -w 24h -w 7d --format json

# If you've activated the shell
lz --help
lz -p <API_KEY> -w 24h --format table
```

### Options

- `-p, --password`: API password/key (required)
- `-w, --window`: Time windows (e.g., 24h, 7d) - can be specified multiple times (required)
- `--format`: Output format - either `table` or `json` (default: table)

### Time Window Formats

Currently supported time window formats:
- `24h` - 24 hours
- `7d` - 7 days

## Development

This project is built using Test-Driven Development (TDD) principles.

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test files
poetry run pytest tests/test_time_windows.py
poetry run pytest tests/test_cli.py
```

### Project Structure

```
ledzephyr/
├── ledzephyr/
│   ├── __init__.py
│   ├── cli.py           # CLI interface using Typer
│   └── time_windows.py  # Time window parsing functionality
├── tests/
│   ├── test_cli.py
│   └── test_time_windows.py
├── pyproject.toml       # Poetry configuration
└── README.md
```

## Current Status

This is the first vertical slice implementation with:
- ✅ Time window parsing (timezone-aware, second precision)
- ✅ CLI skeleton with argument validation
- ✅ Comprehensive test coverage
- ✅ Poetry script entry point

The metrics command is currently stubbed - actual integration functionality will be implemented in future iterations.
