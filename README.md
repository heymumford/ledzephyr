# LedZephyr - The Lean Solution

A **lean utility** for tracking Zephyr Scale to qTest migration metrics.

## The Philosophy

> "The code to pull in data from the three API sources, store the timeseries data on disk,
> perform mathematical and statistical analysis on the trends, and output a lean intelligent
> synthesis... should be as lean as possible while remaining maintainable."

We achieved radical simplification: **605 lines** of clean, readable Python with comprehensive logging, type safety, and error handling.

## What It Does

1. **Fetches** data from Zephyr Scale, qTest, and Jira APIs
2. **Stores** timestamped snapshots locally (avoiding repeated API calls)
3. **Analyzes** migration trends with statistical projections
4. **Generates** actionable insights and completion estimates

## Installation

```bash
poetry install
```

## Usage

```bash
# Fetch fresh data and analyze
poetry run ledzephyr --project MYPROJECT

# Or using make
make run PROJECT=MYPROJECT

# Analyze existing data (no API calls)
poetry run ledzephyr --project MYPROJECT --no-fetch

# Analyze 90-day trend
poetry run ledzephyr --project MYPROJECT --days 90
```

## Configuration

Set environment variables:

```bash
export LEDZEPHYR_JIRA_URL=https://your.atlassian.net
export LEDZEPHYR_JIRA_API_TOKEN=your_token
export LEDZEPHYR_QTEST_URL=https://your.qtestnet.com
export LEDZEPHYR_QTEST_TOKEN=your_token
```

## The Journey

- **Before**: 2,850 lines across 13 files
- **After**: 605 lines in primary module (+ 105 tests)
- **Reduction**: 79% main code reduction
- **Achievement**: Single-file simplicity with production-grade logging and type safety

## Code Structure

```python
# ledzephyr/main.py (605 lines, well-organized)

# === Logging (~50 lines) ===
setup_logging()       # Production-grade logging with transaction IDs

# === API Client (~110 lines) ===
fetch_api_data()      # Generic fetcher with retry
fetch_test_data_from_zephyr()  # Zephyr Scale API
fetch_test_data_from_qtest()   # qTest API
fetch_defect_data_from_jira()  # Jira API

# === Storage (~50 lines) ===
store_snapshot()      # Save timestamped data
load_snapshots()      # Load historical data

# === Metrics & Analysis (~110 lines) ===
calculate_metrics()   # Core calculations
analyze_trends()      # Statistical analysis with projections

# === Reports (~40 lines) ===
generate_report()     # Rich console output

# === CLI (~110 lines) ===
main()               # Click-based interface with comprehensive options
```

## Project Management

- [Confluence Space](https://balabushka.atlassian.net/wiki/spaces/LedZephyr/overview) - Architecture, philosophy, and guides
- [Jira Project (LED)](https://balabushka.atlassian.net/browse/LED) - Work tracking and roadmap

## License

MIT - Keep it simple, keep it free.