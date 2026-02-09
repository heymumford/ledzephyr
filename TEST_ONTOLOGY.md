# LedZephyr Test Ontology

## Epistemological Framework

**LedZephyr** is a lean test migration metrics system with three core domains operating in concert:

1. **Data Integration** (fetch/store/retrieve operations)
2. **Metrics Computation** (pure calculation engines)
3. **Reporting & Output** (presentation and analysis)

This ontology classifies tests by their **strategic testing intent**, mapping each test category to the domain it validates and the contract it enforces.

---

## Core Domains & Bounded Contexts

### Domain 1: API Integration Layer
**Purpose**: Fetch test data from three external systems (Zephyr Scale, qTest, Jira) with retry resilience and error handling.

**Bounded Context**: Data fetchers + API retry logic + credential management

**Primary Test Pattern**: **Contract Testing** (API boundaries)
- Validates that fetchers return well-formed data structures
- Enforces that API contracts match expected schemas
- Verifies retry logic and timeout configurations
- Tests error recovery paths (exponential backoff)

**Key Invariants**:
- API calls must have configurable timeouts (30s default)
- Failed requests retry up to 3 times before returning empty
- Missing credentials fail with clear error messages
- Unsupported API responses (malformed JSON, missing fields) degrade gracefully

### Domain 2: Metrics Computation Engine
**Purpose**: Pure statistical calculations on Zephyr/qTest datasets (migration progress, trends, adoption rates).

**Bounded Context**: Calculation functions + data models + pipeline orchestration

**Primary Test Pattern**: **Property-Based Testing** (invariants)
- Validates that metrics calculations produce consistent results
- Proves that adoption rate always equals qtest_count / (zephyr_count + qtest_count)
- Tests edge cases (empty data, division by zero, null handling)
- Verifies round-trip consistency (calculations idempotent)

**Key Invariants**:
- Adoption rate must be in range [0.0, 1.0]
- remaining = zephyr_count (always)
- total = zephyr_count + qtest_count
- Empty data returns predictable defaults, not crashes
- Status values consistent with adoption rate thresholds

### Domain 3: Data Persistence & Retrieval
**Purpose**: Store timestamped snapshots locally and retrieve historical data for trend analysis.

**Bounded Context**: JSON storage + filesystem I/O + time-based filtering

**Primary Test Pattern**: **State Machine Testing** (storage lifecycle)
- Validates write → read → delete consistency
- Enforces timestamp ordering and date filtering
- Tests multi-project isolation and data independence
- Verifies snapshot structure and metadata preservation

**Key Invariants**:
- Written data must be retrievable exactly as written
- Snapshots must have valid ISO 8601 timestamps
- Data older than cutoff days must be filtered out
- Multiple projects must not interfere with each other

### Domain 4: Test Conversion (Optional, Future)
**Purpose**: Bidirectional conversion between Zephyr and qTest test case formats.

**Bounded Context**: Schema mappers + field translators + batch operations

**Primary Test Pattern**: **Round-Trip Testing** (data integrity)
- Validates A→B→A preserves all data
- Tests field mapping accuracy (Zephyr status → qTest status)
- Verifies unicode and special character preservation
- Tests batch conversion scaling and performance

**Key Invariants**:
- Round-trip conversions are lossless (A→B→A = A)
- Status mappings are bidirectional and symmetric
- Attachments preserve content, size, and metadata
- Batch operations produce same results as sequential operations

---

## Test Categories (Hierarchical Ontology)

### LAYER 1: Contract Tests (API & Schema Boundaries)
**When to use**: When testing interfaces between LedZephyr and external systems or internal module boundaries.

**What to verify**:
- Response schema structure (required fields, data types)
- Enum values (status, issue types)
- Field presence and validity
- Error response formats
- HTTP status codes and timeouts
- Pagination metadata

**Example**:
```python
def test_zephyr_api_contract():
    """Contract: Zephyr API must return list with 'results' key."""
    mock_fetch.return_value = {"results": [{"key": "TEST-1", "name": "Test"}]}
    result = fetch_test_data_from_zephyr("TEST", jira_url, token)
    assert isinstance(result, list)
    assert "key" in result[0]
```

**Subclass: Error Response Contracts**
- Verify 4xx/5xx error handling
- Verify timeout behavior (DEFAULT_API_TIMEOUT_SECONDS = 30)
- Verify rate limiting (429 responses)

**Subclass: Retry Contracts**
- Verify that failed requests retry (up to 3 times)
- Verify that success on Nth retry returns data
- Verify that exhausted retries return empty dict

**Subclass: Authentication Contracts**
- Verify bearer token format
- Verify missing token handling
- Verify token validation on each request

---

### LAYER 2: Property-Based Tests (Invariants & Invariant Preservation)
**When to use**: When testing pure computation that should hold true across all valid inputs.

**What to verify**:
- Commutative operations (order doesn't matter)
- Idempotent operations (f(f(x)) = f(x))
- Deterministic results (same input → same output always)
- Boundary conditions (0, negative, very large numbers)
- Data type invariants (adoption_rate must be [0.0, 1.0])

**Example**:
```python
def test_adoption_rate_bounds():
    """Property: adoption_rate must always be in [0.0, 1.0]."""
    for zephyr_count in range(0, 1000):
        for qtest_count in range(0, 1000):
            metrics = calculate_metrics(
                [{"id": f"Z-{i}"} for i in range(zephyr_count)],
                [{"id": f"Q-{i}"} for i in range(qtest_count)],
            )
            assert 0.0 <= metrics["adoption_rate"] <= 1.0
```

**Subclass: Mathematical Properties**
- Adoption rate formula: qtest_count / (zephyr_count + qtest_count)
- Remaining tests: always equals zephyr_count
- Total tests: always equals zephyr_count + qtest_count

**Subclass: Idempotence Properties**
- calculate_metrics(data) should be idempotent
- Metrics calculated twice should be identical
- No state mutations should occur during calculation

---

### LAYER 3: State Machine Tests (Storage & Lifecycle)
**When to use**: When testing sequences of operations that maintain state (write/read/delete patterns).

**What to verify**:
- Correct state transitions (created → stored → loaded)
- State consistency across transitions
- Isolation between concurrent operations
- Recovery from partial failures
- Snapshot versioning and history preservation

**Example**:
```python
def test_storage_lifecycle():
    """State: Data must transition through write→store→load→verify."""
    data = [{"id": "Z-1"}, {"id": "Z-2"}]
    path = store_snapshot(data, "TEST", "zephyr")
    assert path.exists()

    snapshots = load_snapshots("TEST", "zephyr", days=30)
    assert snapshots[0]["data"] == data
```

**Subclass: Multi-Project Isolation**
- Project A and Project B data must not mix
- Loading Project A must not return Project B data
- Snapshots must tag project metadata correctly

**Subclass: Time-Based Filtering**
- load_snapshots(days=30) must exclude older data
- Timestamp ordering must be preserved
- Date filtering must be exact (not off-by-one)

---

### LAYER 4: Integration Tests (End-to-End Pipeline)
**When to use**: When testing multiple domains working together (data fetch → store → calculate → report).

**What to verify**:
- Component cooperation (A → B → C → D)
- Data flow correctness (input transformation matches output)
- Error propagation (failures in A don't crash B)
- Full pipeline resilience to missing data or API failures

**Example**:
```python
def test_full_pipeline():
    """Integration: Fetch → Store → Analyze → Report works end-to-end."""
    mock_fetch.side_effect = [
        {"results": [{"key": "Z-1"}]},  # Zephyr
        [{"id": "Q-1"}],                 # qTest
        {"issues": []}                   # Jira
    ]

    data = fetch_all_data("TEST", jira_url, jira_token, qtest_url, qtest_token)
    store_snapshot(data.zephyr, "TEST", "zephyr")

    metrics = calculate_metrics(data.zephyr, data.qtest)
    assert metrics["total_tests"] == 2
```

**Subclass: Error Handling Pipeline**
- API failures in one domain shouldn't crash others
- Missing credentials should fail gracefully
- Empty data should produce predictable metrics

**Subclass: Credential Fallback**
- Primary env vars (LEDZEPHYR_ATLASSIAN_*) should work
- Fallback env vars (LEDZEPHYR_JIRA_*) should work
- Missing credentials should raise clear error

---

### LAYER 5: Round-Trip Tests (Bidirectional Data Integrity)
**When to use**: When testing converters or serialization (data must survive A→B→A transformation).

**What to verify**:
- Lossless conversion (no data dropped)
- Reversible transformation (B→A recovers original)
- Unicode preservation (emoji, accents, symbols)
- Attachment integrity (size, content, metadata)
- Null field handling (missing fields don't corrupt data)

**Example**:
```python
def test_round_trip_zephyr_to_qtest():
    """Round-trip: Zephyr → qTest → Zephyr preserves all data."""
    original = {"key": "Z-1", "name": "Test 🎯", "status": "Approved"}

    converted = ZephyrToQtestConverter.convert(original)
    restored = QtestToZephyrConverter.convert(converted)

    assert restored["key"] == original["key"]
    assert restored["name"] == original["name"]  # Unicode preserved
    assert restored["status"] == original["status"]
```

**Subclass: Field Mapping Accuracy**
- Each Zephyr field maps to correct qTest field
- Status values translate correctly (Approved→Active→Approved)
- Custom fields pass through unchanged

**Subclass: Batch Conversion Consistency**
- Batch(A, B) produces same results as sequential(A) + sequential(B)
- Large batches (1000+) maintain correctness
- Performance degrades linearly, not exponentially

---

## Decision Matrix: Classify Any New Test

Use this flowchart to classify a new test into the right category:

```
START: What are you testing?
│
├─ "External API response format"?
│  └─> CONTRACT TEST
│     └─ Verify: Response schema, field types, enums, error handling
│
├─ "Pure calculation (same input → same output always)"?
│  └─> PROPERTY TEST
│     └─ Verify: Invariants, bounds, idempotence, no mutations
│
├─ "Write → Read → Delete sequence"?
│  └─> STATE MACHINE TEST
│     └─ Verify: Lifecycle transitions, isolation, time filtering
│
├─ "Multiple domains working together (fetch + store + calc)"?
│  └─> INTEGRATION TEST
│     └─ Verify: Data flow, error propagation, end-to-end resilience
│
├─ "Data survival through A→B→A transformation"?
│  └─> ROUND-TRIP TEST
│     └─ Verify: Lossless conversion, unicode, batch consistency
│
└─ NONE OF THE ABOVE?
   └─> Ask: "Is this testing a boundary (contract) or behavior (property)?"
      ├─ Boundary → CONTRACT TEST
      └─ Behavior → PROPERTY TEST
```

---

## Test Inventory (Current)

### Contract Tests (14 tests)
Located: `tests/test_contract.py`

| Test | Validates | Domain |
|------|-----------|--------|
| test_api_response_contract_success | HTTPx success responses | API Integration |
| test_api_response_contract_failure | HTTPx error handling | API Integration |
| test_zephyr_api_contract | Zephyr response schema | API Integration |
| test_zephyr_api_contract_empty | Empty results handling | API Integration |
| test_zephyr_api_contract_error | Missing 'results' key | API Integration |
| test_qtest_api_contract | qTest response schema | API Integration |
| test_qtest_api_contract_project_not_found | Project lookup failure | API Integration |
| test_qtest_api_contract_no_token | Missing token handling | API Integration |
| test_jira_api_contract | Jira response schema | API Integration |
| test_jira_api_contract_empty | Empty Jira results | API Integration |
| test_jira_api_contract_error | Malformed response | API Integration |
| test_retry_contract | Retry success on 3rd attempt | API Integration |
| test_retry_contract_exhausted | All retries fail | API Integration |
| test_http_timeout_contract | Timeout configuration | API Integration |

### Property Tests (6 tests)
Located: `tests/test_unit.py` (subset)

| Test | Validates | Domain |
|------|-----------|--------|
| test_calculate_metrics_normal_case | Adoption rate formula | Metrics Computation |
| test_calculate_metrics_empty_data | Empty data handling | Metrics Computation |
| test_calculate_metrics_complete_migration | 100% adoption | Metrics Computation |
| test_calculate_metrics_no_migration_started | 0% adoption | Metrics Computation |
| test_find_project_id_success | Lookup correctness | Metrics Computation |
| test_find_project_id_not_found | Null handling | Metrics Computation |

### State Machine Tests (3 tests)
Located: `tests/test_unit.py` (subset)

| Test | Validates | Domain |
|------|-----------|--------|
| test_store_snapshot | Write → verify file exists | Data Persistence |
| test_load_snapshots | Read → verify content matches | Data Persistence |
| test_load_snapshots_no_directory | Graceful handling of missing dir | Data Persistence |

### Integration Tests (11 tests)
Located: `tests/test_integration.py`

| Test | Validates | Domain |
|------|-----------|--------|
| test_full_data_collection_pipeline | Fetch all APIs together | Multi-domain |
| test_data_collection_without_qtest_token | Graceful degradation | Multi-domain |
| test_storage_and_retrieval_pipeline | Store + load round-trip | Multi-domain |
| test_metrics_to_report_pipeline | Calc + report together | Multi-domain |
| test_trend_analysis_with_historical_data | Time-series analysis | Multi-domain |
| test_credential_management | Primary env vars work | API Integration |
| test_credential_fallback | Fallback env vars work | API Integration |
| test_credential_missing_raises_error | Missing creds fail cleanly | API Integration |
| test_error_handling_pipeline | API failures don't crash | Multi-domain |
| test_snapshot_with_empty_data | Empty data persists | Data Persistence |
| test_multiple_projects_isolation | Project data isolation | Data Persistence |

### Round-Trip Tests (TBD)
Located: `tests/test_zephyr_qtest_converter.py` (future)

- test_basic_field_mapping (Zephyr → qTest)
- test_status_translation (Approved → Active → Approved)
- test_unicode_preservation (emoji, accents)
- test_batch_conversion (consistency)
- test_round_trip_zephyr_to_qtest (A→B→A)

---

## Test Boundaries & Overlaps

### Intentional Overlap (by design)

**Contract + Integration**: `test_full_data_collection_pipeline`
- **Why**: Contract tests validate individual API responses; integration test validates all three APIs work together
- **Distinction**: Contract = response format; Integration = data flow

**Property + State Machine**: `test_metrics_to_report_pipeline`
- **Why**: Property tests validate metrics formula; integration test validates calculate + report work together
- **Distinction**: Property = isolated calculation; Integration = workflow

### Clear Boundaries (no overlap)

**Contract ≠ Property**: Contract validates *external* interfaces; Property validates *internal* logic
**State Machine ≠ Property**: State Machine tests sequences; Property tests single operations
**Round-Trip ≠ Property**: Round-Trip tests transformation fidelity; Property tests invariants

---

## Usage Guidelines

### When Writing New Tests

1. **Classify first**: Use Decision Matrix above
2. **Name clearly**: Include category in test name
   - ✓ `test_zephyr_api_contract_empty`
   - ✓ `test_adoption_rate_bounds_property`
   - ✓ `test_snapshot_lifecycle_state_machine`
   - ✗ `test_api_thing`

3. **Document invariants**: What should ALWAYS be true?
   ```python
   def test_adoption_rate_bounds_property():
       """Property: adoption_rate ∈ [0.0, 1.0] for all inputs."""
       # Why? Rate can't exceed 100% or be negative
   ```

4. **Use mocking strategically**:
   - **Contract tests**: Mock external APIs (httpx, fetch_api_data)
   - **Property tests**: No mocks, test pure functions
   - **State Machine tests**: Mock filesystem (tempfile context)
   - **Integration tests**: Mock external APIs only, not internal functions

5. **Test one thing**:
   - ✓ Single assertion per test (or tightly related assertions)
   - ✓ Clear failure message (test name describes expected behavior)
   - ✗ Testing both happy path AND error handling in one test

---

## Metrics & Assertions

### Success Criteria
- All 34 tests (14 contract + 6 property + 3 state + 11 integration) passing
- 0 tests take >1 second (except slow I/O tests)
- 100% of public functions covered by at least 1 test

### Coverage Goals
- **Contract tests** (14): Cover all API boundaries + retry logic
- **Property tests** (6+): Cover all calculations + data models
- **State Machine tests** (3+): Cover all I/O + persistence
- **Integration tests** (11): Cover all workflows + error paths

---

## References

**Domain-Driven Design (DDD) Lens**:
- Domain = API Integration, Metrics Computation, Data Persistence, Conversion
- Bounded Context = Clear boundaries between domains
- Contracts = Interfaces between bounded contexts

**Testing Ontology Sources**:
- Contract Testing: Martin Fowler's "Test Pyramid"
- Property-Based: Hypothesis, QuickCheck tradition
- State Machine: TLA+, model-based testing literature
- Integration: E2E testing taxonomy
- Round-Trip: Data integrity, transformation verification

**Applicable Patterns**:
- API Testing: Contract Testing, Consumer-Driven Contracts
- Calculation Testing: Property-Based Testing, Invariant Checking
- Storage Testing: State Machine Testing, Linearization
- Workflow Testing: Integration Testing, Choreography Testing
- Conversion Testing: Round-Trip Testing, Lossless Verification
