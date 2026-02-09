# LedZephyr: Epistemological Framework for Test Classification

## The Core Question

**How do we know what to test and when?**

This document explains the philosophical foundation for understanding LedZephyr's test strategy. It answers:
1. What are the core domains (DDD lens)?
2. What contracts must hold?
3. What invariants must be true?
4. What transformations must be lossless?

---

## Philosophical Foundation: Four Ways of Knowing

### 1. Contract Knowledge (Knowing by Boundary)
**"What must be true at interfaces?"**

When code crosses a boundary (internal→external, module→module, component→component), there's a **contract** — an agreement about what data flows and what form it takes.

**LedZephyr Contracts**:
- Zephyr Scale API returns data with `results` key
- qTest API returns list of project objects with `id` and `name`
- Jira API returns dict with `issues` key
- HTTP requests must timeout after 30 seconds
- Failed requests retry exactly 3 times
- Credentials must be provided via environment variables

**Test Type**: Contract Tests validate that boundaries are honored.

**Epistemology**: We know the contract is safe when we can **prove the external system returns data matching our expectations**.

---

### 2. Mathematical Knowledge (Knowing by Invariant)
**"What calculation must always be true?"**

Pure functions have **invariants** — mathematical truths that hold for all valid inputs. These are properties of the domain, not implementation details.

**LedZephyr Invariants**:
- adoption_rate = qtest_count / (zephyr_count + qtest_count)
- adoption_rate must be in [0.0, 1.0] for all inputs
- remaining = zephyr_count (always)
- total = zephyr_count + qtest_count (always)
- status = "Complete" IFF adoption_rate ≥ 1.0
- Empty data returns safe defaults, never crashes

**Test Type**: Property Tests prove invariants hold across all inputs.

**Epistemology**: We know the math is correct when we can **prove the formula is consistent, deterministic, and produces valid outputs for all cases**.

---

### 3. State Knowledge (Knowing by Lifecycle)
**"Does data survive the write→read→delete lifecycle?"**

Systems that persist state must satisfy **state machine properties** — the ability to transition through states correctly and recover data unchanged.

**LedZephyr State Transitions**:
- Create → Write snapshot to disk
- Read → Load snapshot from disk
- Filter → Load only recent snapshots (last N days)
- Isolate → Multiple projects don't interfere

**Test Type**: State Machine Tests verify data persistence and isolation.

**Epistemology**: We know persistence is safe when we can **prove data written equals data read, across multiple transactions and time windows**.

---

### 4. Behavioral Knowledge (Knowing by Integration)
**"Do domains work together?"**

When multiple subsystems interact (API fetch → data store → calculation → report), the **workflows** must succeed end-to-end without cascading failures.

**LedZephyr Workflows**:
- Fetch → Store → Calculate → Report
- Handle missing credentials gracefully
- Retry failed APIs without crashing dependent systems
- Empty data produces safe defaults (never null pointer exceptions)

**Test Type**: Integration Tests verify complete workflows function.

**Epistemology**: We know the system is resilient when we can **prove workflows complete successfully even when partial failures occur**.

---

### 5. Transformation Knowledge (Knowing by Reversibility)
**"Does data survive bidirectional conversion?"**

Converters must satisfy **lossless transformation properties** — data must survive A→B→A with no corruption or data loss.

**LedZephyr Transformations**:
- Zephyr → qTest → Zephyr (round-trip lossless)
- Status mapping is bidirectional (Approved ↔ Active)
- Unicode preserved (emoji, accents, special characters)
- Batch conversion equals sequential conversion
- Attachments preserve size and content

**Test Type**: Round-Trip Tests verify transformation fidelity.

**Epistemology**: We know transformation is safe when we can **prove A→B→A equals A, no data lost**.

---

## The Five Domains of LedZephyr

### Domain 1: API Integration Layer
**Bounded Context**: External systems (Zephyr, qTest, Jira) ↔ LedZephyr

**Invariants**:
- API responses match expected schema
- Failures are retried 3 times
- Timeouts are enforced (30 seconds)
- Missing credentials fail with clear errors

**Test Strategy**: Contract Tests
**Epistemology**: Know the boundary is safe by proving external responses are well-formed

---

### Domain 2: Metrics Computation
**Bounded Context**: Test data → Statistical calculations

**Invariants**:
- adoption_rate ∈ [0.0, 1.0]
- Formula: adoption_rate = qtest / (qtest + zephyr)
- Calculations are deterministic (same input → same output)
- Empty data returns safe defaults

**Test Strategy**: Property Tests
**Epistemology**: Know the math is correct by proving formulas always satisfy domain constraints

---

### Domain 3: Data Persistence
**Bounded Context**: Memory ↔ Filesystem ↔ Memory

**Invariants**:
- Written data ≡ Read data
- Timestamps are valid ISO 8601
- Projects don't interfere
- Old data is filtered by date

**Test Strategy**: State Machine Tests
**Epistemology**: Know persistence works by proving write→read fidelity

---

### Domain 4: Workflow Orchestration
**Bounded Context**: Fetch → Store → Analyze → Report

**Invariants**:
- All domains work together end-to-end
- API failures don't crash dependent operations
- Missing data triggers graceful degradation
- Error messages are clear and actionable

**Test Strategy**: Integration Tests
**Epistemology**: Know workflows work by proving end-to-end completion despite partial failures

---

### Domain 5: Test Case Conversion (Future)
**Bounded Context**: Zephyr ↔ qTest field mapping

**Invariants**:
- Zephyr → qTest → Zephyr = original
- Status mapping is symmetric
- Unicode is preserved
- Batch ≡ sequential

**Test Strategy**: Round-Trip Tests
**Epistemology**: Know conversion is safe by proving A→B→A equals A

---

## Mapping Philosophy to Practice

### Contract Knowledge
```python
# Question: Do external APIs return well-formed data?
# Answer: We test by mocking the API and verifying response structure

def test_zephyr_api_contract():
    """Zephyr API MUST return dict with 'results' key."""
    with patch("fetch_api_data") as mock:
        mock.return_value = {"results": [{"key": "Z-1"}]}
        result = fetch_test_data_from_zephyr(...)
        assert isinstance(result, list)
        # Epistemology: We KNOW the contract is safe because:
        # 1. We tested the boundary
        # 2. We verified the response structure
        # 3. We confirmed the transformation (dict→list)
```

### Mathematical Knowledge
```python
# Question: Is adoption_rate formula always correct?
# Answer: We prove the invariant holds for all inputs

def test_adoption_rate_formula():
    """Property: adoption_rate = qtest / (qtest + zephyr), always."""
    for zephyr_count in range(1000):
        for qtest_count in range(1000):
            metrics = calculate_metrics(
                [{"id": f"Z-{i}"} for i in range(zephyr_count)],
                [{"id": f"Q-{i}"} for i in range(qtest_count)],
            )
            # Epistemology: We KNOW the formula is correct because:
            # 1. We tested all combinations of inputs
            # 2. The calculation is deterministic
            # 3. The result always satisfies the mathematical property
```

### State Knowledge
```python
# Question: Does data survive write→read→delete?
# Answer: We test the state machine lifecycle

def test_state_machine_write_read():
    """State: data.written ≡ data.read"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        original = [{"id": "Z-1"}]
        path = store_snapshot(original, "TEST", "zephyr")
        
        snapshots = load_snapshots("TEST", "zephyr")
        retrieved = snapshots[0]["data"]
        
        # Epistemology: We KNOW persistence is safe because:
        # 1. We wrote data to disk
        # 2. We read data from disk
        # 3. We verified exact equality
        assert retrieved == original
```

### Behavioral Knowledge
```python
# Question: Do all domains work together?
# Answer: We test the full pipeline end-to-end

def test_integration_fetch_store_calculate():
    """Integration: Fetch → Store → Calculate works end-to-end."""
    with patch("fetch_api_data") as mock:
        mock.side_effect = [
            {"results": [{"key": "Z-1"}]},  # Zephyr
            [{"id": "Q-1"}],                 # qTest
            {"issues": []}                   # Jira
        ]
        
        data = fetch_all_data(...)
        store_snapshot(data.zephyr, "TEST", "zephyr")
        metrics = calculate_metrics(data.zephyr, data.qtest)
        
        # Epistemology: We KNOW the workflow works because:
        # 1. We tested fetch from all APIs
        # 2. We tested storage of fetched data
        # 3. We tested calculation on stored data
        # 4. We verified all domains cooperate correctly
        assert metrics["total_tests"] == 2
```

### Transformation Knowledge
```python
# Question: Does data survive A→B→A?
# Answer: We test round-trip fidelity

def test_round_trip_zephyr_qtest():
    """Round-trip: Zephyr → qTest → Zephyr = original"""
    original = {"key": "Z-1", "name": "Test 🎯", "status": "Approved"}
    
    converted = ZephyrToQtestConverter.convert(original)
    restored = QtestToZephyrConverter.convert(converted)
    
    # Epistemology: We KNOW the conversion is safe because:
    # 1. We started with original data
    # 2. We converted to target format
    # 3. We converted back to original format
    # 4. We verified the result equals the original
    assert restored["key"] == original["key"]
    assert restored["name"] == original["name"]  # Unicode preserved!
    assert restored["status"] == original["status"]
```

---

## The Epistemological Hierarchy

```
Level 5: TRANSFORMATION KNOWLEDGE (Can data survive A→B→A?)
         └─ Tested by: Round-Trip Tests
         └─ Proves: Lossless bidirectional conversion

Level 4: BEHAVIORAL KNOWLEDGE (Do domains work together?)
         └─ Tested by: Integration Tests
         └─ Proves: End-to-end workflows function

Level 3: STATE KNOWLEDGE (Does data persist correctly?)
         └─ Tested by: State Machine Tests
         └─ Proves: Write→Read fidelity

Level 2: MATHEMATICAL KNOWLEDGE (Do calculations satisfy invariants?)
         └─ Tested by: Property Tests
         └─ Proves: Formulas are correct for all inputs

Level 1: CONTRACT KNOWLEDGE (Are boundaries honored?)
         └─ Tested by: Contract Tests
         └─ Proves: External interfaces are well-formed
```

Each level depends on lower levels. You can't test integration (L4) if contracts (L1) aren't validated.

---

## Practical Implications

### When Adding a New Feature
1. **Define contracts** (L1): What do external APIs return?
2. **Define invariants** (L2): What must the calculation always satisfy?
3. **Define state** (L3): What data persists and how?
4. **Define workflow** (L4): How do domains cooperate?
5. **Define transformation** (L5): Does data survive conversion?

### When Debugging a Failure
1. **Is it a contract violation?** (L1) → Fix contract test
2. **Is it a broken invariant?** (L2) → Fix property test
3. **Is it a state issue?** (L3) → Fix state machine test
4. **Is it a workflow problem?** (L4) → Fix integration test
5. **Is it a conversion issue?** (L5) → Fix round-trip test

### When Deciding Test Coverage
- **L1 (Contract)**: 100% coverage of API calls
- **L2 (Property)**: 100% coverage of calculations
- **L3 (State)**: 100% coverage of I/O operations
- **L4 (Integration)**: 80%+ coverage of workflows
- **L5 (Transformation)**: 100% coverage of converters

---

## Summary: The LedZephyr Testing Philosophy

**We build confidence in LedZephyr through five forms of knowledge:**

1. **Contract Tests** prove external boundaries are safe
2. **Property Tests** prove calculations are mathematically sound
3. **State Machine Tests** prove data persistence works
4. **Integration Tests** prove domains cooperate correctly
5. **Round-Trip Tests** prove bidirectional conversion is lossless

**Together, these five test categories answer the fundamental question:**

> "Can we trust LedZephyr to correctly migrate test data from Zephyr Scale to qTest?"

**Answer**: Yes, because we've proven:
- External APIs return expected data (Contract)
- Calculations always satisfy invariants (Property)
- Data persists correctly (State)
- Domains work together (Integration)
- Conversions are lossless (Round-Trip)

