# Test Data Management (TDM) Implementation

## Overview

This document describes the lean Test Data Management (TDM) proof-of-concept implementation for LedZephyr. The implementation demonstrates balanced unit and integration testing with test doubles, backed by a simple but real Test Data Management plan.

## Key Components

### 1. Test Doubles (`tests/integration/doubles/`)

Three types of test doubles for each vendor API (Jira, Zephyr Scale, qTest):

#### Stub Implementation
- **Files**: `stub_jira.py`, `stub_zephyr.py`, `stub_qtest.py`
- **Purpose**: Fixed responses for happy paths
- **Features**:
  - Deterministic data generation
  - Pagination support
  - Multiple presets (happy_small, empty)
  - Call counting

#### Fake Implementation
- **File**: `fake_jira.py`
- **Purpose**: In-memory stateful API simulation
- **Features**:
  - Full CRUD operations
  - Error simulation toggles (rate limit, auth, network)
  - JQL parsing and filtering
  - Request history tracking

#### Spy Transport
- **File**: `spy_transport.py`
- **Purpose**: Capture request metadata and assertions
- **Features**:
  - Request/response logging
  - Pagination tracking
  - Auth header verification
  - Rate limit monitoring
  - Performance metrics

### 2. VCR Replay (`tests/integration/doubles/vcr_replay.py`)

**Purpose**: Deterministic request/response replay for E2E tests

**Features**:
- Record/replay/record_once modes
- Request matching via SHA256 hash
- JSON cassette storage
- Hit/miss statistics
- Auto-save on recording

### 3. TDM Manifest (`tests/tdm/manifest_schema.py`)

**Purpose**: Configuration-driven test data management

**Schema Components**:
- **TestDataSet**: Dataset definitions with fields and sensitivity
- **TestScenario**: Test scenarios with preconditions and expected outcomes
- **DataField**: Field-level metadata including masking strategy
- **QualityGates**: Performance and coverage thresholds

**Validator Features**:
- Schema validation via Pydantic
- Completeness checks
- Checksum verification
- Sensitive data validation

### 4. Data Masking (`tests/tdm/data_masker.py`)

**Masking Strategies**:
- **Tokenize**: Replace with deterministic tokens (TOKEN_000001)
- **Redact**: Complete removal ([REDACTED])
- **Hash**: One-way SHA256 hash
- **Partial**: Show partial data (***@example.com)
- **Synthetic**: Generate realistic fake data

**Golden Data Generator**:
- Deterministic test data generation
- Consistent across test runs
- Vendor-specific formats

### 5. Quality Gates (`tests/tdm/quality_gates.py`)

**Gate Types**:
- **SchemaCompleteness**: Verify all fields are defined (95% threshold)
- **DataCoverage**: Check test scenario coverage (80% threshold)
- **PerformanceGate**: Validate execution times (2s threshold)
- **SensitiveDataGate**: Ensure proper masking
- **DeterminismGate**: Verify consistent results across runs

### 6. E2E Replay Test (`tests/e2e/test_manifest_driven_replay.py`)

**Orchestration Flow**:
1. Load manifest configuration
2. Setup test doubles based on mode
3. Initialize VCR for replay
4. Execute test scenarios
5. Apply data masking
6. Run quality gates
7. Generate evidence and reports

## Directory Structure

```
tests/
├── integration/
│   └── doubles/          # Test doubles
│       ├── stub_*.py     # Fixed response stubs
│       ├── fake_*.py     # Stateful fakes
│       ├── spy_transport.py
│       └── vcr_replay.py
├── tdm/                  # Test Data Management
│   ├── manifest_schema.py
│   ├── data_masker.py
│   ├── quality_gates.py
│   └── golden/          # Golden test data
├── e2e/
│   └── test_manifest_driven_replay.py
├── cassettes/           # VCR recordings
├── evidence/            # Test evidence
└── specs/              # OpenAPI specifications
```

## Usage Examples

### Running the E2E Test

```bash
# Run with stubs (CI mode)
poetry run pytest tests/e2e/test_manifest_driven_replay.py -v

# Run with fakes (stateful testing)
poetry run python tests/e2e/test_manifest_driven_replay.py
```

### Using Test Doubles Directly

```python
from tests.integration.doubles import JiraStub, SpyTransport

# Create stub with preset data
jira_stub = JiraStub("happy_small")

# Wrap with spy for assertions
spy = SpyTransport(jira_stub)

# Make API calls
response = spy.request("GET", "/rest/api/3/search", 
                      params={"jql": "project = TEST"})

# Assert pagination was used
assert spy.assert_pagination_used()
```

### Data Masking Example

```python
from tests.tdm import DataMasker

masker = DataMasker()

# Mask sensitive fields
data = {"email": "user@example.com", "status": "active"}
field_masks = {"email": "tokenize"}

masked = masker.mask_dict(data, field_masks)
# Result: {"email": "TOKEN_000001", "status": "active"}
```

## Quality Gate Results

The implementation includes comprehensive quality gates that validate:

1. **Schema Completeness**: ✅ 100% (all fields defined)
2. **Data Coverage**: Tracks scenario execution coverage
3. **Performance**: Monitors execution times
4. **Sensitive Data**: Validates masking strategies
5. **Determinism**: Ensures consistent results

## Benefits

1. **No Live Network Calls**: All tests run with test doubles in CI
2. **Deterministic Results**: Reproducible test outcomes
3. **Data Privacy**: Automatic masking of sensitive information
4. **Performance Tracking**: Built-in performance monitoring
5. **Evidence Generation**: Automatic report creation
6. **Flexible Modes**: Support for stub, fake, and spy patterns
7. **VCR Replay**: Record once, replay forever
8. **Quality Assurance**: Built-in quality gates

## Next Steps

1. **Expand Fake Implementations**: Create stateful fakes for Zephyr and qTest
2. **Add More Scenarios**: Cover error paths and edge cases
3. **Enhance Masking**: Add format-preserving encryption
4. **Performance Baselines**: Establish performance benchmarks
5. **Contract Testing**: Add OpenAPI contract validation
6. **Chaos Engineering**: Add fault injection capabilities
7. **Data Synthesis**: Generate larger synthetic datasets
8. **Monitoring Integration**: Connect to observability stack

## Conclusion

This lean TDM proof-of-concept demonstrates how to achieve comprehensive API testing without live network calls. The combination of test doubles, VCR replay, data masking, and quality gates provides a robust foundation for continuous testing in CI/CD pipelines.
