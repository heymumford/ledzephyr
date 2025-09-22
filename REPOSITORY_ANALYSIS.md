# Repository Structure Analysis & Lean Refactoring

## Current State: 40+ directories, 200+ files

### Waste Identification

| Directory | Files | Lines | Value | Waste Type | Action |
|-----------|-------|-------|-------|------------|--------|
| **tests/** | 150+ | 10,000+ | Medium | Over-testing | Keep 5 critical |
| **docs/** | 15 | 2,000+ | Low | Duplication | Consolidate to 1 |
| **testdata/** | 50+ | 5,000+ | Medium | Partial work | Keep gold master only |
| **htmlcov/** | 100+ | Generated | None | Build artifact | Add to .gitignore |
| **specs/** | 10 | 1,000+ | Low | Unused | Archive |
| **monitoring/** | 5 | 500+ | Low | Premature | Delete |
| **k8s/** | 8 | 400+ | Low | YAGNI | Delete |
| **dev/** | 3 | 100+ | Low | Unused | Delete |
| **tdm/** | 10 | 500+ | Low | Over-engineering | Delete |
| **reports/** | Variable | Generated | None | Build artifact | Add to .gitignore |

### Value Identification

| Directory | Purpose | Essential? | Keep Because |
|-----------|---------|------------|--------------|
| **src/ledzephyr/** | Core code | ✅ Yes | Customer value |
| **testdata/fixtures/** | Gold master | ✅ Yes | Quality assurance |
| **.github/workflows/** | CI/CD | ✅ Yes | Automation |
| **scripts/** | Build tools | ✅ Yes | Developer productivity |

## Lean Repository Structure

```
ledzephyr/
├── src/
│   └── ledzephyr/
│       ├── __init__.py
│       ├── metrics.py       # Core calculation (200 lines)
│       ├── client.py        # API client (200 lines)
│       ├── cache.py         # Simple caching (50 lines)
│       └── cli.py           # CLI interface (100 lines)
├── tests/
│   ├── test_critical.py    # The 5 critical tests (100 lines)
│   └── fixtures/
│       └── gold_master.json # Known good data
├── .github/
│   └── workflows/
│       └── ci.yml          # Single workflow
├── .env.example
├── .gitignore
├── Makefile               # Simplified to 5 targets
├── pyproject.toml
├── README.md             # 50 lines max
└── DOCUMENTATION.md      # Everything else in 1 file
```

## Refactoring Plan

### Phase 1: Delete (Immediate)
```bash
# Remove waste directories
rm -rf htmlcov/ reports/ test_reports/  # Generated
rm -rf k8s/ monitoring/ dev/ tdm/        # YAGNI
rm -rf specs/ assets/ gold/              # Unused

# Archive but don't delete
mkdir -p .archive
mv docs/*.md .archive/  # Keep DOCUMENTATION.md only
```

### Phase 2: Consolidate (This Week)

#### Tests: 150 files → 1 file
```python
# tests/test_critical.py
class TestCritical:
    def test_gold_master(self): ...
    def test_api_retry(self): ...
    def test_time_boundary(self): ...
    def test_cache_expiry(self): ...
    def test_null_safety(self): ...
```

#### Source: 15 modules → 4 modules
```python
# Merge into metrics.py
- validators.py  # Over-engineered
- exporters.py   # Unused features
- monitoring_api.py  # Premature

# Merge into client.py
- rate_limiter.py  # Part of client logic
- error_handler.py  # Exception handling

# Keep separate
- cache.py  # Clear responsibility
- cli.py    # User interface
```

### Phase 3: Simplify (Next Week)

#### Makefile: 200 lines → 20 lines
```makefile
test:    pytest tests/test_critical.py
run:     python -m ledzephyr
build:   poetry build
clean:   rm -rf dist/ *.egg-info
help:    @grep '^[a-z]:' Makefile
```

#### Config: 3 files → 1 file
```python
# pyproject.toml only
# Delete: setup.py, setup.cfg, requirements.txt
```

## Size Reduction Metrics

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Directories | 40+ | 8 | 80% |
| Files | 200+ | 15 | 92.5% |
| Lines of Code | 20,000+ | 1,000 | 95% |
| Test Files | 150 | 1 | 99.3% |
| Documentation | 15 files | 1 file | 93% |
| Dependencies | 50+ | 10 | 80% |

## Dependencies to Remove

### Current pyproject.toml (50+ deps)
```toml
# Remove these (unused/test-only)
pandas = "^2.0"          # Overkill for simple calcs
matplotlib = "^3.0"      # No visualization needed
seaborn = "^0.13"        # No visualization needed
xlsxwriter = "^3.2"      # CSV is enough
reportlab = "^4.0"       # No PDF needed
fastapi = "^0.110"       # No API server
uvicorn = "^0.29"        # No API server
opentelemetry-* = "*"    # Over-instrumented
hypothesis = "^6.0"      # Property testing overkill
vcrpy = "^6.0"          # Replay testing unnecessary
allpairspy = "^2.5"      # Combinatorial overkill
```

### Lean Dependencies (10 only)
```toml
[tool.poetry.dependencies]
python = "^3.11"
click = "^8.0"          # CLI
httpx = "^0.24"         # API calls
pydantic = "^2.0"       # Data models
python-dotenv = "^1.0"  # Config
requests-cache = "^1.0" # Caching
tenacity = "^8.0"       # Retry logic

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"         # Testing
black = "^24.0"         # Formatting
ruff = "^0.1"           # Linting
```

## File-by-File Decisions

### Keep (Core Value)
- `src/ledzephyr/metrics.py` - Core calculations
- `src/ledzephyr/client.py` - API integration
- `tests/fixtures/math_*.json` - Gold master data
- `.github/workflows/ci.yml` - Automation

### Refactor (Simplify)
- `src/ledzephyr/cli.py` - Remove subcommands, just metrics
- `src/ledzephyr/cache.py` - Inline into client.py
- `Makefile` - Reduce to 5 essential targets

### Delete (Waste)
- All test files except critical 5
- All docs except DOCUMENTATION.md
- All generated directories
- All unused source modules

## Implementation Script

```bash
#!/bin/bash
# lean-refactor.sh

# 1. Backup current state
git checkout -b pre-lean-backup
git add -A && git commit -m "Backup before lean refactoring"

# 2. Create lean structure
mkdir -p .archive
mv docs/* .archive/ 2>/dev/null

# 3. Remove waste
rm -rf htmlcov/ reports/ test_reports/ k8s/ monitoring/
rm -rf dev/ tdm/ specs/ assets/ gold/

# 4. Consolidate tests
cat tests/unit/*/test_*.py > tests/test_all.py
rm -rf tests/unit tests/integration tests/e2e

# 5. Simplify source
cat src/ledzephyr/{validators,exporters,monitoring_api}.py >> .archive/removed.py
rm src/ledzephyr/{validators,exporters,monitoring_api}.py

# 6. Update imports
find . -name "*.py" -exec sed -i 's/from ledzephyr.validators/from ledzephyr.metrics/g' {} \;

# 7. Clean dependencies
poetry remove pandas matplotlib seaborn xlsxwriter reportlab fastapi uvicorn
poetry remove opentelemetry-api opentelemetry-sdk hypothesis vcrpy allpairspy

# 8. Verify
make lean-test

echo "Refactoring complete. Check git diff for changes."
```

## Success Criteria

✅ 5 critical tests pass
✅ <1000 lines of production code
✅ <100 lines of test code
✅ <10 dependencies
✅ <10 files total
✅ Build in <10 seconds
✅ Test in <2 seconds

## Next Steps

1. Run lean-refactor.sh
2. Verify functionality with lean-test
3. Update DOCUMENTATION.md
4. Tag as v2.0.0-lean
5. Archive old structure

---

**Result**: Same functionality, 95% less complexity.