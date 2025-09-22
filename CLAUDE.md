# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LedZephyr is a lean CLI tool for calculating migration metrics from Zephyr Scale to qTest. Following a massive simplification (89% code reduction), it now consists of a single ~306-line Python file with minimal dependencies.

### Lean Transformation Achievement
- **Before**: 2,850 lines across 13 modules + 200 test files
- **After**: 306 lines in single file (`ledzephyr_lean.py`)
- **Reduction**: 89.3%
- **Dependencies**: Reduced from 60+ to 3 (click, httpx, rich)

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
export LEDZEPHYR_ATLASSIAN_TOKEN=ATATT3xFfGF0xHPw7c1IcpPdKajFvbeC28F0_Ywtd__9BOZnghqfRmW4NS9ggs5lX9iwpn_AhViikttbKcLMTbc7jW9B3RPoCLX_QlEql_WLGbgMoSv_nT2Bin5ZEq_Vfwr50qWrh9QNdwu9QTtQ9MvREVbkUr5c4SLlpXMTIk6lnOATtD4X21g=002D05A2
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
poetry run python ledzephyr_lean.py --project MYPROJECT
poetry run python ledzephyr_lean.py --project MYPROJECT --fetch
poetry run python ledzephyr_lean.py --project MYPROJECT --no-fetch
```

### Testing and Quality
```bash
# Run lean test suite
make test

# Format code with black
make format

# Lint with ruff
make lint

# Clean cache and temp files
make clean
```

## Architecture Overview

Ultra-lean single-file architecture in `ledzephyr_lean.py` (~306 lines):

1. **API Client** (~50 lines) - Generic HTTP fetcher with retry logic
2. **Data Fetchers** (~100 lines) - Zephyr Scale, qTest, and Jira integrations
3. **Analysis Engine** (~80 lines) - Statistical calculations and trend analysis
4. **CLI Interface** (~50 lines) - Click-based command handling
5. **Storage Layer** (~25 lines) - Local JSON data persistence

### Key Design Principles
- **Single file over modules** - Maximum simplicity
- **3 dependencies only** - click, httpx, rich
- **Local JSON storage** - No databases
- **6-month activity filter** - Recent data focus
- **Rich console output** - Beautiful terminal reports

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

Extremely lean file organization:
```
ledzephyr/
├── ledzephyr_lean.py    # Main application (306 lines)
├── test_lean.py         # Test suite
├── pyproject.toml       # Dependencies
├── Makefile            # Development commands
├── README.md           # Project overview
├── CLAUDE.md           # This file
└── data/               # Local data storage
    └── {project}/      # Per-project data
```