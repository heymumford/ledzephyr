# ledzephyr

CLI tool to report Zephyr Scale → qTest migration metrics per Jira project/team.

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/heymumford/ledzephyr.git
cd ledzephyr
make init

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

```bash
# Full development setup
make init                    # Install deps + pre-commit hooks

# Testing
make test                    # Unit tests only
make integration            # Integration tests
make cov                     # Full suite with coverage report

# Quality gates
make check                   # All quality checks (lint, type, test, security)
make fix                     # Auto-format and fix issues

# Individual tools
make lint                    # Static analysis (ruff + bandit)
make type                    # Type checking (mypy)
make sec                     # Security scan (bandit)
```

## License

MIT