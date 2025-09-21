# Test Data Management (TDM) Framework

## Overview

This TDM framework provides **manifest-driven test data** for ledzephyr's balanced testing approach. It enables reproducible tests with **multiple API sources** (Jira, Zephyr, qTest) while maintaining data quality and security.

## Key Features

- ✅ **Manifest-driven**: YAML configs control data sources and scenarios
- ✅ **Multiple modes**: Replay (VCR), Stub (fixed), Fake (in-memory APIs)
- ✅ **Data masking**: Deterministic tokenization for sensitive fields
- ✅ **Quality gates**: Schema validation, completeness checks, checksums
- ✅ **Time consistency**: "as-of" timestamps for reproducible snapshots

## Quick Start

### 1. Validate a Manifest

```bash
python tdm/tools/validate_manifest.py testdata/manifests/demo_project_2025q2.yaml
```

### 2. Run Tests with Manifest

```bash
# Unit tests (fast, pure math)
pytest tests/unit/ -m "unit"

# Integration tests (with API doubles)
pytest tests/integration/ -m "integration"

# E2E tests (manifest-driven)
pytest tests/e2e/ -m "e2e"
```

### 3. Check Quality Gates

All tests automatically validate:
- Schema compliance against JSON Schema
- Data completeness (≥98% non-null by default)
- Output checksums match expected values

## Manifest Structure

```yaml
dataset_id: demo-project-q2-2025
as_of: "2025-06-30T23:59:59Z"

sources:
  jira:
    mode: replay                    # Use VCR cassette
    cassette: testdata/cassettes/jira_demo_project.yaml
  zephyr:
    mode: stub                      # Fixed responses
    preset: mixed_execution_status
  qtest:
    mode: fake                      # In-memory API
    config:
      total_tests: 150
      error_rate: 0.1

normalization:
  currency: USD
  timezone: UTC
  rounding: HALF_UP

masking:
  - field: test_id
    op: deterministic_tokenize      # Linkable but anonymous
    salt_ref: env:TDM_SALT
    alphabet: base32

quality_gates:
  schema_compliance: error
  completeness_min: 0.98
  expected_checksum: a1b2c3d4e5f6...  # SHA256 of expected output
```

## Data Source Modes

### Replay Mode (VCR)
- **Use**: Real API interactions for high-fidelity tests
- **Setup**: Record once, replay deterministically
- **Files**: YAML cassettes in `testdata/cassettes/`

```yaml
jira:
  mode: replay
  cassette: testdata/cassettes/jira_full_project.yaml
```

### Stub Mode (Fixed)
- **Use**: Fast, predictable responses for happy paths
- **Setup**: Predefined presets in test doubles
- **Options**: `basic_project`, `large_project`, `empty_project`

```yaml
zephyr:
  mode: stub
  preset: mixed_execution_status    # Some tests executed, some not
```

### Fake Mode (In-Memory)
- **Use**: Complex scenarios with errors, pagination, rate limits
- **Setup**: Configurable behavior via YAML
- **Features**: Error injection, rate limiting, pagination

```yaml
qtest:
  mode: fake
  config:
    total_tests: 150
    error_rate: 0.1               # 10% of requests fail
    pagination_size: 50
```

## Adding Test Data

### 1. Create New Manifest

```bash
# Copy template
cp testdata/manifests/demo_project_2025q2.yaml testdata/manifests/my_scenario.yaml

# Edit for your test case
# Change dataset_id, sources, quality gates
```

### 2. Add VCR Cassette (if using replay)

```bash
# Record real API interactions
# Save as YAML in testdata/cassettes/
# Scrub sensitive data (tokens, emails)
```

### 3. Validate Manifest

```bash
python tdm/tools/validate_manifest.py testdata/manifests/my_scenario.yaml
```

### 4. Use in Tests

```python
def test_my_scenario(tmp_path):
    manifest_path = "testdata/manifests/my_scenario.yaml"

    # Validate manifest first
    assert validate_manifest(manifest_path)

    # Load and use in test
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    # Run Pull→Math→Print pipeline
    # Assert expected outputs
```

## Data Security

### Masking Rules

```yaml
masking:
  - field: user_email
    op: hash                      # One-way hash
    salt_ref: env:TDM_SALT
  - field: test_id
    op: deterministic_tokenize    # Reversible with salt
    alphabet: base32
  - field: sensitive_data
    op: redact                    # Complete removal
```

### Environment Variables

```bash
# Required for deterministic masking
export TDM_SALT="your-secret-salt-here"

# Used by quality gates
export TDM_SCHEMA_DIR="tdm/schema"
```

## Quality Gates

### Schema Compliance
- **Validates**: Output structure matches expected JSON Schema
- **Action**: `error` (fail), `warn` (log), `ignore` (skip)
- **Files**: Schema definitions in `tdm/schema/`

### Data Completeness
- **Validates**: Minimum ratio of non-null values
- **Default**: 98% completeness required
- **Configurable**: Per field or overall

### Output Checksums
- **Validates**: Final output matches expected SHA256 hash
- **Use**: Detect drift in calculations or data changes
- **Files**: Expected checksums in `testdata/expected/`

## Test Layers

### Unit Tests (`tests/unit/`)
- **Target**: Pure math, formatters, parsers
- **Approach**: Golden files + property-based testing
- **Speed**: <1s total
- **Dependencies**: None (isolated)

### Integration Tests (`tests/integration/`)
- **Target**: API clients, cross-source joins, retry logic
- **Approach**: Stubs, fakes, spies - no real network
- **Speed**: <10s total
- **Dependencies**: Test doubles only

### E2E Tests (`tests/e2e/`)
- **Target**: Full Pull→Math→Print pipeline
- **Approach**: Manifest-driven with multiple scenarios
- **Speed**: <30s total
- **Dependencies**: Manifests, quality gates

## Troubleshooting

### Validation Errors

```bash
❌ Schema validation failed: 'total_tests' is not of type 'integer'
```
**Fix**: Check data types in manifest match schema requirements

### Missing Cassettes

```bash
❌ Validation error: Cassette file not found: testdata/cassettes/missing.yaml
```
**Fix**: Create cassette file or change mode to `stub`/`fake`

### Quality Gate Failures

```bash
❌ Completeness check failed: 85% < 98% required
```
**Fix**: Improve data quality or lower threshold in manifest

### Checksum Mismatches

```bash
❌ Expected checksum abc123... but got def456...
```
**Fix**: Update expected checksum or investigate calculation changes

## Schema Reference

- **Manifest Schema**: `tdm/schema/manifest.schema.json`
- **Validation Tool**: `tdm/tools/validate_manifest.py`
- **Masking Tool**: `tdm/tools/apply_mask.py` (future)
- **Quality Gates**: `tdm/tools/quality_gates.py` (future)

---

This TDM framework enables **balanced, reproducible testing** while maintaining data quality and security. It supports the **Pull → Math → Print** architecture with deterministic outputs and comprehensive validation.