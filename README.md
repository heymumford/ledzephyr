# ledzephyr
![Led Zephyr](assets/led-zephyr.png)

Is your Jira test integration dropping out of the sky like a Led Zephyr? This is a utility to measure your migration to qTest cloud.

## Overview

`ledzephyr` (or `lz` for short) is a production-ready Python CLI tool that reports Zephyr Scale → qTest migration metrics per Jira project/team. It helps organizations track their test management migration progress with detailed metrics and trends.

## Features

- **API Health Checks**: Test connectivity to Jira, Zephyr Scale, and qTest APIs
- **Migration Metrics**: Calculate adoption ratios, coverage parity, and defect link rates
- **Team Analytics**: Break down metrics by component, label, or group
- **Trend Analysis**: 4-week trend data for migration progress tracking
- **Multiple Output Formats**: Table, JSON, and CSV export options
- **Robust HTTP Client**: Built-in retries and exponential backoff
- **Configuration Management**: Environment variables and .env file support

## Installation

### Prerequisites
- Python 3.8 or higher
- Poetry (for development)

### Install from source
```bash
git clone https://github.com/heymumford/ledzephyr.git
cd ledzephyr
poetry install
```

### Install as package
```bash
pip install ledzephyr
```

## Quick Start

### 1. Configuration
Copy the example configuration file and update with your credentials:
```bash
cp .env.example .env
# Edit .env with your API credentials
```

Required configuration:
```bash
LEDZEPHYR_JIRA_URL=https://your-domain.atlassian.net
LEDZEPHYR_JIRA_USERNAME=your.email@company.com
LEDZEPHYR_JIRA_API_TOKEN=your_jira_api_token
```

### 2. Test API Connectivity
```bash
lz doctor
```

### 3. Generate Migration Metrics
```bash
# Basic usage
lz metrics -p PROJECT_KEY

# Advanced usage with multiple time windows and custom output
lz metrics -p PROJECT_KEY -w 24h -w 7d -w 30d --teams-source component --format json --out metrics.json
```

## Commands

### `lz doctor`
Check API connectivity and configuration.

**Example:**
```bash
$ lz doctor
🩺 ledzephyr doctor - Checking API connectivity...
Testing Jira API connection...
✅ Jira API: Connected
Testing Zephyr Scale API connection...
✅ Zephyr Scale API: Connected
Testing qTest API connection...
✅ qTest API: Connected

🎉 Doctor check complete!
```

### `lz metrics`
Generate migration metrics for a Jira project.

**Options:**
- `-p, --project TEXT`: Jira project key (required)
- `-w, --window TEXT`: Time windows (e.g., 24h, 7d, 30d) [default: 7d, 30d]
- `--teams-source [component|label|group]`: Source for team identification [default: component]
- `--format [table|json]`: Output format [default: table]
- `-o, --out PATH`: Output file path

**Examples:**
```bash
# Default 7d and 30d windows with table output
lz metrics -p PROJ

# Custom time windows
lz metrics -p PROJ -w 24h -w 7d -w 14d -w 30d

# Team identification by labels instead of components
lz metrics -p PROJ --teams-source label

# JSON output to file
lz metrics -p PROJ --format json --out migration-report.json

# CSV export
lz metrics -p PROJ --format table --out metrics.csv
```

## Metrics Explained

### Core Metrics

- **Total Tests**: Combined count of tests from Zephyr Scale and qTest
- **Zephyr Tests**: Number of tests in Zephyr Scale
- **qTest Tests**: Number of tests in qTest
- **Adoption Ratio**: Percentage of tests migrated to qTest (qtest_tests / total_tests)
- **Active Users**: Number of unique users with activity in the time window
- **Coverage Parity**: How well qTest test execution coverage matches Zephyr Scale
- **Defect Link Rate**: Percentage of tests with linked defects/issues

### Team Analytics

Metrics can be broken down by team using different sources:
- **Component**: Use Jira project components to identify teams
- **Label**: Use test case labels to identify teams
- **Group**: Use assignee groups to identify teams

### Trend Data

4-week trend analysis shows:
- Week-over-week adoption progress
- Coverage parity improvements
- User activity changes
- Migration velocity indicators

## Configuration

Configuration can be provided via environment variables or `.env` file:

### Required Settings
```bash
LEDZEPHYR_JIRA_URL=https://your-domain.atlassian.net
LEDZEPHYR_JIRA_USERNAME=your.email@company.com
LEDZEPHYR_JIRA_API_TOKEN=your_jira_api_token
```

### Optional Settings
```bash
# Zephyr Scale (if different from Jira URL)
LEDZEPHYR_ZEPHYR_URL=https://your-domain.atlassian.net
LEDZEPHYR_ZEPHYR_TOKEN=your_zephyr_token

# qTest
LEDZEPHYR_QTEST_URL=https://your-domain.qtestnet.com
LEDZEPHYR_QTEST_TOKEN=your_qtest_token

# HTTP Settings
LEDZEPHYR_TIMEOUT=30
LEDZEPHYR_MAX_RETRIES=3
LEDZEPHYR_RETRY_BACKOFF_FACTOR=0.3

# Logging
LEDZEPHYR_LOG_LEVEL=INFO
```

## Output Formats

### Table Format (Default)
```
                Migration Metrics                
┌────────┬─────────────┬─────────────┬─────────────┬──────────────┬──────────────┬────────────────┬──────────────────┐
│ Window │ Total Tests │ Zephyr Tests│ qTest Tests │ Adoption     │ Active Users │ Coverage Parity│ Defect Link Rate │
├────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┼────────────────┼──────────────────┤
│ 7d     │ 150         │ 90          │ 60          │ 40.00%       │ 8            │ 85.00%         │ 12.00%           │
│ 30d    │ 500         │ 320         │ 180         │ 36.00%       │ 15           │ 82.50%         │ 15.00%           │
└────────┴─────────────┴─────────────┴─────────────┴──────────────┴──────────────┴────────────────┴──────────────────┘
```

### JSON Format
```json
{
  "7d": {
    "project_key": "PROJ",
    "time_window": "7d",
    "total_tests": 150,
    "zephyr_tests": 90,
    "qtest_tests": 60,
    "adoption_ratio": 0.4,
    "active_users": 8,
    "coverage_parity": 0.85,
    "defect_link_rate": 0.12,
    "team_metrics": {...},
    "trend_data": {...}
  },
  "30d": {...}
}
```

### CSV Export
When using `--out filename.csv`, data is exported in CSV format suitable for Excel or other analysis tools.

## Development

### Setup Development Environment
```bash
git clone https://github.com/heymumford/ledzephyr.git
cd ledzephyr
poetry install
```

### Run Tests
```bash
poetry run pytest
```

### Code Quality
```bash
# Format code
poetry run black ledzephyr/

# Type checking
poetry run mypy ledzephyr/

# Run all quality checks
poetry run pytest --cov=ledzephyr
```

### Building
```bash
poetry build
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

For issues, feature requests, or questions, please open an issue on GitHub.
=======
