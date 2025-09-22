# Test Architecture Documentation

This directory implements a **comprehensive testing framework** with gold master validation, achieving **53.60% code coverage** with 212 passing tests.

## Test Layer Architecture

```
tests/
├── unit/               # Layer 1: Fast, isolated, pure logic tests
├── integration/        # Layer 2: API clients with test doubles
├── e2e/               # Layer 3: End-to-end manifest-driven tests
└── conftest.py        # Global test configuration and fixtures
```

## Layer 1: Unit Tests (`unit/`)

**Target**: <1 second total execution time
**Focus**: Pure math, parsers, formatters, business logic
**Dependencies**: None (completely isolated)

### Structure
- `test_math_golden.py` - Mathematical calculations with golden files
- `ledzephyr/` - Module-specific unit tests

### Characteristics
- Fast execution (milliseconds per test)
- No network dependencies
- Deterministic with fixed inputs
- Property-based testing with Hypothesis
- Golden file comparisons for complex outputs

### Example
```python
def test_adoption_ratio_calculation():
    # Pure math with known inputs/outputs
    assert calculate_adoption_ratio(5, 5) == 0.5
```

## Layer 2: Integration Tests (`integration/`)

**Target**: <10 seconds total execution time
**Focus**: API clients, cross-system interactions, retry logic
**Dependencies**: Test doubles only (no real network)

### Structure
- `doubles/` - Test doubles (stubs, fakes, spies)
  - `stub_jira.py` - Jira API stub implementations
- `test_pull_with_stubs.py` - API client integration tests
- `test_cli_integration.py` - CLI integration tests

### Test Double Types
- **Stubs**: Fixed responses for happy path testing
- **Fakes**: In-memory implementations with configurable behavior
- **Spies**: Capture and verify interaction patterns

### Example
```python
def test_api_client_with_stub():
    stub = JiraAPIStub(preset="basic_project")
    client = APIClient(config, stub)
    result = client.get_project("DEMO")
    assert result.key == "DEMO"
```

## Layer 3: E2E Tests (`e2e/`)

**Target**: <30 seconds total execution time
**Focus**: Full Pull→Math→Print pipeline validation
**Dependencies**: TDM manifests, quality gates

### Structure
- `test_manifest_replay.py` - Manifest-driven end-to-end tests

### Characteristics
- Uses real TDM manifests for scenarios
- Validates complete data flow
- Quality gate enforcement (schema, checksums)
- Multiple test modes (replay, stub, fake)

### Example
```python
def test_manifest_driven_e2e():
    manifest = load_manifest("demo_project_2025q2.yaml")
    result = run_pipeline(manifest)
    assert_quality_gates_pass(result, manifest)
```

## Test Execution Strategy

### Speed Targets
- **Unit**: <1s (immediate feedback)
- **Integration**: <10s (fast CI feedback)
- **E2E**: <30s (full validation)

### Execution Order
1. Run unit tests first (fastest feedback)
2. Run integration tests on unit success
3. Run E2E tests for full validation

### Parallel Execution
- Unit tests: Fully parallelizable
- Integration tests: Parallel within layer
- E2E tests: Sequential for resource management

## Test Markers

Tests are automatically marked based on directory:
- `@pytest.mark.unit` - All tests in `unit/`
- `@pytest.mark.integration` - All tests in `integration/`
- `@pytest.mark.e2e` - All tests in `e2e/`

Additional markers:
- `@pytest.mark.golden` - Golden file tests
- `@pytest.mark.property` - Property-based tests
- `@pytest.mark.snapshot` - Snapshot comparison tests

## Running Tests

### Individual Layers
```bash
# Unit tests only (fastest)
make unit
pytest tests/unit/ -m "unit"

# Integration tests with doubles
make integration
pytest tests/integration/ -m "integration"

# E2E tests with manifests
make e2e
pytest tests/e2e/ -m "e2e"
```

### Using Test Runner Script
```bash
# Run specific layer
./scripts/test-runner.sh unit
./scripts/test-runner.sh integration
./scripts/test-runner.sh e2e

# Run all layers with coverage
./scripts/test-runner.sh all --coverage
```

## Test Data Management

### Sources
- **Golden files**: Deterministic input/output pairs
- **Test doubles**: Realistic but controlled API responses
- **TDM manifests**: Complete scenario definitions

### Quality Gates
- Schema validation for all structured data
- Completeness checks (>98% non-null fields)
- Output checksums for regression detection

## Best Practices

### Unit Tests
- Test single units of functionality
- Use property-based testing for mathematical invariants
- Keep tests fast and deterministic
- Mock external dependencies

### Integration Tests
- Test interactions between components
- Use test doubles instead of real services
- Verify API contract compliance
- Test error handling and retry logic

### E2E Tests
- Test complete user scenarios
- Use realistic data volumes
- Validate end-to-end data flow
- Enforce quality gates

## Test Coverage Summary

### Current Coverage: 53.60%

| Test Category | Count | Purpose |
|---------------|-------|---------|
| **Unit Tests** | 156 | Core logic, calculations, parsing |
| **Integration Tests** | 48 | API clients, cross-component |
| **Gold Master Tests** | 8 | Algorithm validation |
| **Total** | 212 | Comprehensive coverage |

### Module Coverage Details

| Module | Coverage | Focus Area |
|--------|----------|------------|
| time_windows.py | 100% | Time parsing and calculations |
| observability.py | 98% | Logging, metrics, tracing |
| client.py | 95% | API interactions |
| config.py | 76% | Configuration management |
| cache.py | 71% | Request caching |
| metrics.py | 50% | Metric calculations |
| validators.py | 36% | Input validation |

## Gold Master Testing

The project implements comprehensive gold master testing for algorithm validation:

### Test Datasets
- **Basic**: Standard test cases for core functionality
- **Edge Cases**: Boundary conditions, special characters, null values
- **Large Dataset**: Performance and scalability testing

### Running Gold Master Tests
```bash
# Run all gold master tests
pytest tests/integration/test_gold_master_algorithms.py -v

# Run with coverage
pytest tests/integration/test_gold_master_algorithms.py --cov=src/ledzephyr/metrics
```

See [docs/GOLD_MASTER_TESTING.md](../docs/GOLD_MASTER_TESTING.md) for detailed documentation.

## Configuration

Global test configuration in `conftest.py`:
- Deterministic random seeds
- Hypothesis profiles (CI, dev, exhaustive)
- Shared fixtures and test data
- Custom pytest markers
- Gold master dataset loading