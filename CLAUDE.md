# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LedZephyr is a lean CLI tool for calculating migration metrics from Zephyr Scale to qTest. Following a massive simplification (79% code reduction), it now consists of a well-structured Python package with a single main module.

### Lean Transformation Achievement
- **Before**: 2,850 lines across 13 modules + 200 test files
- **After**: 605 lines in main module (`ledzephyr/main.py`) + 105 lines tests
- **Reduction**: 79% main code reduction
- **Dependencies**: Reduced from 60+ to 3 runtime (click, httpx, rich)
- **Features Added**: Production-grade logging, transaction tracing, comprehensive type safety

### Project Documentation & Integration

#### Atlassian Resources
- **Confluence Space**: https://balabushka.atlassian.net/wiki/spaces/LedZephyr/overview
  - Space ID: 8683575, Space Key: LedZephyr
  - Cloud ID: f1ecf30e-e4d0-48d9-bc3a-e738126b7afd
- **Jira Project**: LED (https://balabushka.atlassian.net/browse/LED)
  - Epic LED-46: Adoption Intelligence System
  - Tasks LED-47 through LED-52: Implementation micro-katas

#### MCP Tool Authentication
**Live Credentials Configuration:**
- **Cloud ID**: `f1ecf30e-e4d0-48d9-bc3a-e738126b7afd`
- **Site URL**: `https://balabushka.atlassian.net`
- **User**: Eric M (ericmumford@gmail.com)
- **Account ID**: `557058:feeb8338-0c0a-49bf-9930-a3cd13a18ad1`

**Environment Variables:**
```bash
export LEDZEPHYR_ATLASSIAN_URL=https://balabushka.atlassian.net
export LEDZEPHYR_ATLASSIAN_PROJECT=LED
export LEDZEPHYR_ATLASSIAN_TOKEN=<YOUR_ATLASSIAN_API_TOKEN>
```

**MCP Tool Capabilities (Verified Working):**
- ✅ **Jira** - read/write work items (LED project confirmed)
- ✅ **Confluence** - read/write pages/comments (LedZephyr space)
- ✅ **Compass** - read/write components and scorecards

**Available MCP Functions:**
- `mcp__jiraLZ__getVisibleJiraProjects` - List accessible projects
- `mcp__jiraLZ__searchJiraIssuesUsingJql` - Search issues with JQL
- `mcp__jiraLZ__createJiraIssue` - Create new issues
- `mcp__jiraLZ__getJiraIssue` - Get issue details
- `mcp__jiraLZ__editJiraIssue` - Update existing issues
- `mcp__jiraLZ__getConfluenceSpaces` - List Confluence spaces
- `mcp__jiraLZ__getConfluencePage` - Read pages
- `mcp__jiraLZ__createConfluencePage` - Create pages
- `mcp__jiraLZ__updateConfluencePage` - Update pages
- `mcp__jiraLZ__search` - Universal Rovo search across Jira/Confluence

## Essential Commands

### Development Setup
```bash
# Install dependencies (Poetry)
make install

# Show project metrics and info
make info
```

### Running LedZephyr
```bash
# Run with project (fetches fresh data and analyzes)
make run PROJECT=MYPROJECT

# Fetch fresh data only
make fetch PROJECT=MYPROJECT

# Analyze existing data only
make analyze PROJECT=MYPROJECT

# Direct execution with options
poetry run ledzephyr --project MYPROJECT
poetry run ledzephyr --project MYPROJECT --fetch
poetry run ledzephyr --project MYPROJECT --no-fetch
```

### Testing and Quality
```bash
# Run comprehensive test suite (recommended)
make test-all

# Run specific test layers
make test-unit          # Unit tests (16 tests)
make test-contract      # Contract tests (14 tests)
make test-integration   # Integration tests (11 tests)

# Run legacy test suite
make test

# Format code with black
make format

# Lint with ruff
make lint

# Type check with mypy
make type

# Security scan with bandit
make security

# Clean cache and temp files
make clean
```

**Test Execution Order**: Unit → Contract → Integration → E2E (manual)

For E2E testing instructions, see [`tests/test_e2e.md`](tests/test_e2e.md)

## Architecture Overview

Lean package architecture in `ledzephyr/main.py` (605 lines, well-structured):

1. **Logging Setup** (~50 lines) - Production-grade logging with transaction IDs
2. **API Client** (~50 lines) - Generic HTTP fetcher with retry logic
3. **Data Fetchers** (~110 lines) - Zephyr Scale, qTest, and Jira integrations
4. **Analysis Engine** (~110 lines) - Statistical calculations and trend analysis
5. **CLI Interface** (~110 lines) - Click-based command handling with comprehensive options
6. **Storage Layer** (~50 lines) - Local JSON data persistence with timestamps
7. **Data Models** (~30 lines) - Type-safe data structures
8. **Credential Management** (~25 lines) - Environment-based configuration

### Key Design Principles
- **Single main module** - Maximum simplicity while maintaining structure
- **3 runtime dependencies** - click, httpx, rich
- **Local JSON storage** - No databases, timestamped snapshots
- **6-month activity filter** - Recent data focus
- **Rich console output** - Beautiful terminal reports
- **Type safety** - Comprehensive type hints for mypy
- **Transaction tracing** - Correlate logs across distributed systems

## API Endpoints (15 Essential)

### Jira Cloud (4 endpoints)
- `GET /rest/api/3/project` - Project metadata
- `GET /rest/api/3/search` - Issue search with JQL
- `GET /rest/api/3/issue/{key}` - Issue details
- `GET /rest/api/3/project/{key}/statuses` - Project statuses

### Zephyr Scale (5 endpoints)
- `GET /rest/atm/1.0/testcase/search` - Test case search
- `GET /rest/atm/1.0/testrun/search` - Test run search
- `GET /rest/atm/1.0/execution/search` - Execution search
- `GET /rest/atm/1.0/project/{key}` - Project info
- `GET /rest/atm/1.0/automationstatus` - Automation status

### qTest (6 endpoints)
- `GET /api/v3/projects` - Project list
- `GET /api/v3/projects/{id}/test-cases` - Test cases
- `GET /api/v3/projects/{id}/test-runs` - Test runs
- `GET /api/v3/projects/{id}/test-logs` - Execution logs
- `GET /api/v3/projects/{id}/automation-jobs` - Automation jobs
- `GET /api/v3/projects/{id}/requirements` - Requirements

## Configuration

Environment variables for API access:
```bash
# Required for operation
LEDZEPHYR_JIRA_URL=https://your.atlassian.net
LEDZEPHYR_JIRA_API_TOKEN=your_jira_token
LEDZEPHYR_QTEST_URL=https://your.qtest.com
LEDZEPHYR_QTEST_API_TOKEN=your_qtest_token

# Optional configuration
LEDZEPHYR_DATA_DIR=./data           # Data storage directory
LEDZEPHYR_MONTHS_BACK=6             # Activity filter (months)
```

## Dependencies

Minimal dependency set managed by Poetry:
```toml
[tool.poetry.dependencies]
python = "^3.11"
click = "^8.1.7"      # CLI framework
httpx = "^0.27.0"     # HTTP client
rich = "^13.7.0"      # Rich console output
```

## Data Storage

Local JSON files in `data/{project}/` directory:
- `zephyr_tests.json` - Zephyr test cases
- `qtest_tests.json` - qTest test cases
- `jira_issues.json` - Jira issues
- `analysis.json` - Calculated metrics
- `timestamp.txt` - Last fetch time

## Migration Metrics Calculated

Core metrics for Zephyr → qTest migration analysis:

1. **Migration Progress** - `qtest_count / (zephyr_count + qtest_count)`
2. **Activity Trends** - 6-month velocity analysis
3. **Team Adoption** - Per-user migration patterns
4. **Quality Metrics** - Test execution rates and outcomes
5. **Automation Coverage** - Automated vs manual test ratios

## CLI Usage

Main command pattern:
```bash
# Basic usage
ledzephyr --project PROJECT_KEY

# Available options
--project TEXT    Project key (required)
--fetch          Force fresh data fetch
--no-fetch       Use cached data only
--data-dir PATH  Override data directory
--help           Show help message
```

Examples:
```bash
# Fetch and analyze ACME project
ledzephyr --project ACME

# Quick analysis of cached data
ledzephyr --project ACME --no-fetch

# Force fresh data fetch
ledzephyr --project ACME --fetch
```

## Testing

Simple test suite in `test_lean.py`:
- Unit tests for core functions
- API integration tests with mocking
- Data analysis validation
- Error handling verification

Run with: `make test` or `poetry run python test_lean.py`

## GitHub Workflows

Single lean CI workflow in `.github/workflows/lean-ci.yml`:
- Python 3.11 setup
- Dependency installation
- Code formatting check (black)
- Linting check (ruff)
- Test execution
- Simplified 45-line workflow vs previous 1000+ lines

## Development Workflow

1. Make changes to `ledzephyr_lean.py`
2. Run `make test` for validation
3. Run `make format` and `make lint` for code quality
4. Test with real project: `make run PROJECT=TEST`
5. Commit with descriptive message

## Error Handling

Simple but robust error handling:
- **API failures**: 3-retry logic with exponential backoff
- **Network issues**: Graceful degradation to cached data
- **Missing credentials**: Clear error messages with guidance
- **Invalid projects**: Validation and helpful suggestions

## Performance Characteristics

Optimized for simplicity and speed:
- **Cold start**: <5 seconds for full analysis
- **Cached analysis**: <1 second
- **Memory usage**: <50MB
- **Disk usage**: ~1MB per project
- **API calls**: Batch requests with 6-month filtering

## File Structure

Lean package organization:
```
ledzephyr/
├── ledzephyr/          # Main package
│   ├── __init__.py     # Package exports
│   ├── __main__.py     # Entry point for python -m
│   └── main.py         # Main application (605 lines)
├── test_lean.py        # Test suite (105 lines)
├── pyproject.toml      # Dependencies & tool config
├── Makefile            # Development commands
├── README.md           # Project overview
├── CLAUDE.md           # This file (AI context)
├── .github/            # CI/CD workflows
└── data/               # Local data storage
    └── {project}/      # Per-project snapshots
        ├── zephyr/     # Zephyr Scale snapshots
        ├── qtest/      # qTest snapshots
        └── jira/       # Jira snapshots
```