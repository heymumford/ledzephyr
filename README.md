# LedZephyr - The 279-Line Solution

A **lean utility** for tracking Zephyr Scale to qTest migration metrics.

## The Philosophy

> "The code to pull in data from the three API sources, store the timeseries data on disk,
> perform mathematical and statistical analysis on the trends, and output a lean intelligent
> synthesis... should take less than 300 lines of code."

We achieved this vision: **279 lines** of clean, readable Python that does exactly what's needed.

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
poetry run python ledzephyr_lean.py --project MYPROJECT

# Analyze existing data (no API calls)
poetry run python ledzephyr_lean.py --project MYPROJECT --no-fetch

# Analyze 90-day trend
poetry run python ledzephyr_lean.py --project MYPROJECT --days 90
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
- **After**: 279 lines in a single file
- **Reduction**: 90.2%

## Code Structure

```python
# === API Client (~50 lines) ===
fetch_api_data()      # Generic fetcher with retry
fetch_zephyr_tests()  # Zephyr Scale API
fetch_qtest_tests()   # qTest API

# === Storage (~40 lines) ===
store_snapshot()      # Save timestamped data
load_snapshots()      # Load historical data

# === Metrics (~40 lines) ===
calculate_metrics()   # Core calculations

# === Trends (~50 lines) ===
analyze_trends()      # Statistical analysis

# === Reports (~40 lines) ===
generate_report()     # Rich console output

# === CLI (~50 lines) ===
main()               # Click-based interface
```

## Project Management

- [Confluence Space](https://balabushka.atlassian.net/wiki/spaces/LedZephyr/overview) - Architecture, philosophy, and guides
- [Jira Project (LED)](https://balabushka.atlassian.net/browse/LED) - Work tracking and roadmap

## License

MIT - Keep it simple, keep it free.