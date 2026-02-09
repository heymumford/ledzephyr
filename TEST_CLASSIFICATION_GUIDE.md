# LedZephyr Test Classification Quick Reference

## The Five Test Categories at a Glance

### 1. CONTRACT TESTS (Boundary Validation)
**Tests external interfaces and API contracts**

```
What: Do external APIs return data in the expected format?
Where: Boundaries between LedZephyr and Zephyr/qTest/Jira
Mocks: External APIs (httpx.get, fetch_api_data)
Assertions: Schema presence, field types, error codes
Example: test_zephyr_api_contract, test_retry_contract_exhausted
Count: 14 tests in test_contract.py
```

---

### 2. PROPERTY TESTS (Invariant Checking)
**Tests pure functions that should always satisfy mathematical properties**

```
What: Does this calculation always produce valid results?
Where: Pure computation functions (no I/O, no side effects)
Mocks: None (test actual logic)
Assertions: Bounds checking, idempotence, determinism
Example: test_calculate_metrics_complete_migration (rate=1.0 means complete)
Count: 6+ tests in test_unit.py
```

---

### 3. STATE MACHINE TESTS (Lifecycle & Persistence)
**Tests that data survives write → read → delete sequences**

```
What: Does this data survive storage and retrieval?
Where: Persistence layer (store_snapshot, load_snapshots)
Mocks: Filesystem (tempfile context manager)
Assertions: Data equality, timestamp ordering, isolation
Example: test_storage_and_retrieval_pipeline
Count: 3+ tests in test_unit.py
```

---

### 4. INTEGRATION TESTS (End-to-End Workflow)
**Tests multiple domains working together**

```
What: Do all components work together end-to-end?
Where: Full pipelines (fetch → store → calculate → report)
Mocks: External APIs only (not internal functions)
Assertions: Data flow correctness, error handling, graceful degradation
Example: test_full_data_collection_pipeline, test_error_handling_pipeline
Count: 11 tests in test_integration.py
```

---

### 5. ROUND-TRIP TESTS (Transformation Integrity)
**Tests that A→B→A transformations preserve data**

```
What: Does data survive bidirectional conversion?
Where: Converter functions (ZephyrToQtestConverter, QtestToZephyrConverter)
Mocks: None (test actual converters)
Assertions: Lossless conversion, unicode preservation, idempotence
Example: test_round_trip_zephyr_to_qtest, test_batch_conversion
Count: 0 tests (future use in test_zephyr_qtest_converter.py)
```

---

## Decision Tree: Which Category?

```
START: I want to test...

1. "An API endpoint or response format"?
   YES → CONTRACT TEST
   └─ Verify: Schema, fields, enums, error codes, timeouts
   └─ Mock: httpx.get, fetch_api_data
   └─ Example: test_zephyr_api_contract

2. "A pure calculation (always deterministic, no I/O)"?
   YES → PROPERTY TEST
   └─ Verify: Invariants, bounds, idempotence
   └─ Mock: None
   └─ Example: test_calculate_metrics_normal_case

3. "Writing and reading data from storage"?
   YES → STATE MACHINE TEST
   └─ Verify: Write→Read lifecycle, isolation, time filtering
   └─ Mock: Filesystem (tempfile)
   └─ Example: test_storage_and_retrieval_pipeline

4. "Multiple domains together (fetch + store + calc + report)"?
   YES → INTEGRATION TEST
   └─ Verify: Data flow, error propagation, workflows
   └─ Mock: External APIs, not internal functions
   └─ Example: test_full_data_collection_pipeline

5. "Data transformation (A → B → A)"?
   YES → ROUND-TRIP TEST
   └─ Verify: Lossless conversion, unicode, batch consistency
   └─ Mock: None
   └─ Example: test_round_trip_zephyr_to_qtest

NONE OF THE ABOVE?
   └─ Ask: "Is this testing a boundary or a behavior?"
      Boundary → CONTRACT TEST
      Behavior → PROPERTY TEST
```

---

## Mapping Test Types to LedZephyr Functions

### Contract Tests (Boundary Tests)

| Function | Test | Why |
|----------|------|-----|
| `try_api_call()` | test_api_response_contract_success | Response format must be well-formed |
| `fetch_api_data()` | test_retry_contract | Retry logic must succeed on 3rd attempt |
| `fetch_test_data_from_zephyr()` | test_zephyr_api_contract | Zephyr response must have 'results' key |
| `fetch_test_data_from_qtest()` | test_qtest_api_contract | qTest project lookup must work |
| `fetch_defect_data_from_jira()` | test_jira_api_contract | Jira response must have 'issues' key |
| `get_jira_credentials()` | test_credential_management | Env vars must be read correctly |

### Property Tests (Calculation Tests)

| Function | Test | Why |
|----------|------|-----|
| `calculate_metrics()` | test_calculate_metrics_normal_case | adoption_rate formula must be correct |
| `calculate_metrics()` | test_calculate_metrics_complete_migration | 100% adoption = all data migrated |
| `find_project_id()` | test_find_project_id_success | Lookup must find matching project |
| `find_project_id()` | test_find_project_id_not_found | Lookup must return None if not found |
| `analyze_trends_from_data()` | test_analyze_trends_from_data_stub | Trend calculation must be deterministic |

### State Machine Tests (Persistence Tests)

| Function | Test | Why |
|----------|------|-----|
| `store_snapshot()` | test_store_snapshot | Write must create file with metadata |
| `load_snapshots()` | test_load_snapshots | Read must retrieve exact written data |
| `load_snapshots()` | test_multiple_projects_isolation | Projects must not interfere |

### Integration Tests (Workflow Tests)

| Workflow | Test | Why |
|----------|------|-----|
| Fetch → Store → Calculate | test_full_data_collection_pipeline | All APIs must work together |
| Fetch → Store → Trend | test_trend_analysis_with_historical_data | Historical data must enable trend calc |
| Fetch → Calculate → Report | test_metrics_to_report_pipeline | Metrics → Report must work seamlessly |
| (Error handling) | test_error_handling_pipeline | API failures must not crash pipeline |

### Round-Trip Tests (Conversion Tests)

| Converter | Test | Why |
|-----------|------|-----|
| ZephyrToQtestConverter | test_round_trip_zephyr_to_qtest | Z→Q→Z must preserve all data |
| QtestToZephyrConverter | test_status_translation | Status mapping must be bidirectional |
| (batch) | test_batch_conversion | Batch must equal sequential |

---

## Test Naming Convention

Use this format to make test intent crystal clear:

### Formula
```
test_[FUNCTION]_[SCENARIO]_[CATEGORY]
```

### Examples

**CONTRACT TESTS** (API/boundary focus)
- ✓ `test_zephyr_api_contract_empty` (empty response handling)
- ✓ `test_retry_contract_exhausted` (all retries fail)
- ✓ `test_http_timeout_contract` (timeout configuration)

**PROPERTY TESTS** (calculation/invariant focus)
- ✓ `test_calculate_metrics_complete_migration` (rate=1.0 edge case)
- ✓ `test_adoption_rate_bounds_property` (0 ≤ rate ≤ 1)
- ✓ `test_find_project_id_invalid_input` (robustness)

**STATE MACHINE TESTS** (lifecycle/persistence focus)
- ✓ `test_storage_and_retrieval_pipeline` (write→read)
- ✓ `test_multiple_projects_isolation` (data isolation)
- ✓ `test_snapshot_with_empty_data` (edge case)

**INTEGRATION TESTS** (workflow/end-to-end focus)
- ✓ `test_full_data_collection_pipeline` (fetch + store + calc)
- ✓ `test_error_handling_pipeline` (resilience)
- ✓ `test_trend_analysis_with_historical_data` (multi-step)

**ROUND-TRIP TESTS** (conversion/transformation focus)
- ✓ `test_round_trip_zephyr_to_qtest` (A→B→A)
- ✓ `test_batch_conversion` (consistency)
- ✓ `test_unicode_preservation` (data integrity)

---

## Mocking Patterns by Category

### Contract Tests
```python
# Mock EXTERNAL APIs
with patch("httpx.get") as mock_get:
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [...]}
    mock_get.return_value = mock_response

    result = fetch_test_data_from_zephyr(...)
    assert isinstance(result, list)
```

### Property Tests
```python
# NO MOCKING - test actual logic
def test_calculate_metrics_normal_case():
    zephyr = [{"id": f"Z-{i}"} for i in range(100)]
    qtest = [{"id": f"Q-{i}"} for i in range(75)]

    metrics = calculate_metrics(zephyr, qtest)
    assert metrics["adoption_rate"] == 0.4286  # Actual formula
```

### State Machine Tests
```python
# Mock FILESYSTEM only
with tempfile.TemporaryDirectory() as tmpdir:
    original_cwd = os.getcwd()
    try:
        os.chdir(tmpdir)  # Isolate I/O

        path = store_snapshot(data, "TEST", "zephyr")
        assert path.exists()
    finally:
        os.chdir(original_cwd)
```

### Integration Tests
```python
# Mock EXTERNAL APIs only, not internal functions
with patch("ledzephyr.main.fetch_api_data") as mock_fetch:
    mock_fetch.side_effect = [
        {"results": [...]},  # Zephyr
        [...],               # qTest
        {"issues": [...]},   # Jira
    ]

    data = fetch_all_data(...)  # Call actual function
    # Verify multiple domains work together
```

### Round-Trip Tests
```python
# NO MOCKING - test actual converters
original = {"key": "Z-1", "name": "Test"}

converted = ZephyrToQtestConverter.convert(original)
restored = QtestToZephyrConverter.convert(converted)

assert restored == original  # Exact preservation
```

---

## Test Execution Strategy

### Run Order (Dependencies)

1. **Unit Tests** (fast, isolated)
   - Property tests (no I/O, no mocks)
   - State machine tests (tempfile isolation)
   - ~1 second total

2. **Contract Tests** (medium speed, mocked)
   - API contract validation
   - Retry logic
   - ~1-2 seconds total

3. **Integration Tests** (slower, full pipelines)
   - End-to-end workflows
   - Error handling
   - ~2-3 seconds total

4. **E2E Tests** (manual, real APIs)
   - Only run on demand with real credentials
   - See tests/test_e2e.md

### Command
```bash
# Run all test layers in order
make test-all

# Or individually
make test-unit          # ~1s
make test-contract      # ~1s
make test-integration   # ~2s
```

---

## Common Pitfalls

### Pitfall 1: Contract Test That's Actually a Property Test
```python
# WRONG - No API involved, tests pure logic
def test_api_response_format():
    data = {"results": [...]}
    assert isinstance(data["results"], list)

# RIGHT - Tests actual API response
def test_zephyr_api_contract():
    with patch("httpx.get") as mock:
        mock.return_value.json.return_value = {"results": [...]}
        result = fetch_test_data_from_zephyr(...)
        assert isinstance(result, list)
```

### Pitfall 2: Multiple Assertions That Test Different Things
```python
# WRONG - Three different concerns
def test_fetch_and_store():
    data = fetch_test_data_from_zephyr(...)  # Test 1: Fetch
    assert len(data) > 0

    path = store_snapshot(data, "TEST", "zephyr")  # Test 2: Store
    assert path.exists()

    snapshots = load_snapshots("TEST", "zephyr")  # Test 3: Load
    assert snapshots[0]["data"] == data

# RIGHT - Separate tests
def test_fetch_returns_list():
    # Test fetch only

def test_store_creates_file():
    # Test store only

def test_load_retrieves_data():
    # Test load only
```

### Pitfall 3: Integration Test That Doesn't Actually Integrate
```python
# WRONG - Only tests one function
def test_integration_fetch():
    with patch("fetch_api_data"):
        data = fetch_all_data(...)

# RIGHT - Tests multiple functions together
def test_integration_fetch_store_calculate():
    with patch("fetch_api_data") as mock:
        data = fetch_all_data(...)  # Fetch

    store_snapshot(data.zephyr, "TEST", "zephyr")  # Store
    metrics = calculate_metrics(data.zephyr, data.qtest)  # Calculate

    assert metrics["total_tests"] > 0  # Verify end-to-end
```

---

## Quick Reference: Test Category Cheat Sheet

| Category | Primary Question | Mocking | Assertions | Speed | Count |
|----------|------------------|---------|-----------|-------|-------|
| **Contract** | Do APIs return correct schema? | httpx, fetch_api_data | Schema, types, enums | ~70ms | 14 |
| **Property** | Do calculations satisfy invariants? | None | Bounds, determinism | ~10ms | 6+ |
| **State** | Does data survive write→read? | tempfile | Equality, ordering | ~100ms | 3+ |
| **Integration** | Do domains work together? | External APIs | Data flow, resilience | ~200ms | 11 |
| **Round-Trip** | Does A→B→A preserve data? | None | Lossless, unicode | ~50ms | 0+ |

---

## References

- **Test Pyramid** (Mike Cohn): Fast unit tests at base, slower E2E at top
- **Contract Testing** (Martin Fowler): Test API contracts between services
- **Property-Based Testing** (QuickCheck): Prove invariants hold for all inputs
- **State Machine Testing** (TLA+): Verify correct state transitions
- **Integration Testing** (XUnit): Verify components work together
- **Transformation Testing**: Verify bidirectional conversions
