# LedZephyr Test Framework Documentation Index

This directory contains a complete epistemological framework for understanding and extending LedZephyr's test strategy. All documents are designed to work together as an integrated knowledge base.

## Quick Start (5 minutes)

Start here if you're new to LedZephyr's test philosophy:

1. Read: **TEST_FRAMEWORK_SUMMARY.txt** (this overview)
2. Reference: **TEST_CLASSIFICATION_GUIDE.md** (decision tree)
3. Apply: Use the decision tree when writing new tests

## Documentation Structure

### Level 1: Executive Summary (Executive Audience)
**File**: `TEST_FRAMEWORK_SUMMARY.txt` (261 lines)
**Time to read**: 5 minutes
**For whom**: Project leads, QA managers, developers unfamiliar with the framework
**Contains**:
- High-level overview of five test categories
- Quick reference table (category, purpose, mocks, speed)
- Test inventory summary (34 tests across 5 categories)
- Next steps for implementation

### Level 2: Practical Quick Reference (Day-to-Day Usage)
**File**: `TEST_CLASSIFICATION_GUIDE.md` (388 lines)
**Time to read**: 15 minutes
**For whom**: Developers writing and extending tests
**Contains**:
- Visual decision tree for classifying tests
- Detailed mapping of test types to functions
- Mocking patterns by category with code examples
- Common pitfalls and how to avoid them
- Naming conventions (formula and examples)
- Quick cheat sheet table

### Level 3: Comprehensive Reference (Deep Understanding)
**File**: `TEST_ONTOLOGY.md` (462 lines)
**Time to read**: 30 minutes
**For whom**: Test architects, code reviewers, those maintaining the framework
**Contains**:
- Detailed domain analysis (DDD lens)
- Five bounded contexts with invariants
- Complete test category definitions with examples
- Test inventory with all 34 tests listed
- Boundary analysis and intentional overlaps
- Coverage goals and assertions by category
- References to testing theory

### Level 4: Philosophical Foundation (Understanding WHY)
**File**: `EPISTEMOLOGY.md` (363 lines)
**Time to read**: 20 minutes
**For whom**: Those wanting to understand the philosophical reasoning
**Contains**:
- Five forms of knowing (contract, math, state, behavior, transformation)
- Epistemological hierarchy with dependencies
- Mapping philosophy to practice (code examples)
- Practical implications for feature development and debugging
- Coverage targets justified by philosophy

### Level 5: Architecture Diagrams (Visual Overview)
**File**: `TEST_ARCHITECTURE_DIAGRAM.txt` (250 lines)
**Time to read**: 10 minutes
**For whom**: Visual learners, architecture review
**Contains**:
- Epistemological hierarchy (pyramid)
- Five bounded contexts (architecture diagram)
- Data flow visualization (Fetch → Store → Calculate → Report)
- Classification decision tree (flowchart)
- Test execution sequence (layered)
- Complete test inventory (tree format)

## Reading Paths

### Path 1: "I need to write a test NOW" (5 min)
1. Open: `TEST_CLASSIFICATION_GUIDE.md`
2. Find your scenario in the decision tree
3. Look up mocking patterns for your category
4. Copy the naming convention
5. Done

### Path 2: "I'm new to the team" (30 min)
1. Read: `TEST_FRAMEWORK_SUMMARY.txt` (5 min) - overview
2. Study: `TEST_CLASSIFICATION_GUIDE.md` (10 min) - decision tree
3. Skim: `TEST_ONTOLOGY.md` (15 min) - domains and test mapping

### Path 3: "I need to understand the philosophy" (45 min)
1. Read: `TEST_FRAMEWORK_SUMMARY.txt` (5 min) - overview
2. Read: `EPISTEMOLOGY.md` (20 min) - five forms of knowing
3. Study: `TEST_ARCHITECTURE_DIAGRAM.txt` (10 min) - visual summary
4. Reference: `TEST_ONTOLOGY.md` (10 min) - detailed mapping

### Path 4: "I'm reviewing test quality" (60 min)
1. Read: `TEST_ONTOLOGY.md` (30 min) - comprehensive reference
2. Check: Against `TEST_ARCHITECTURE_DIAGRAM.txt` (10 min)
3. Reference: `EPISTEMOLOGY.md` (20 min) - philosophical grounding

### Path 5: "I want to extend the framework" (90 min)
1. Deep read: `TEST_ONTOLOGY.md` (30 min)
2. Deep read: `EPISTEMOLOGY.md` (20 min)
3. Study: `TEST_ARCHITECTURE_DIAGRAM.txt` (15 min)
4. Cross-reference: `TEST_CLASSIFICATION_GUIDE.md` (15 min)
5. Review: Existing tests in `tests/` directory (10 min)

## Files Summary

| File | Lines | Purpose | Audience | Time |
|------|-------|---------|----------|------|
| **TEST_FRAMEWORK_SUMMARY.txt** | 261 | Executive overview | Leads, unfamiliar devs | 5 min |
| **TEST_CLASSIFICATION_GUIDE.md** | 388 | Daily quick reference | All developers | 15 min |
| **TEST_ONTOLOGY.md** | 462 | Comprehensive reference | Architects, reviewers | 30 min |
| **EPISTEMOLOGY.md** | 363 | Philosophical foundation | Thinking deeply | 20 min |
| **TEST_ARCHITECTURE_DIAGRAM.txt** | 250 | Visual overview | Visual learners | 10 min |
| **TEST_FRAMEWORK_INDEX.md** | this | Navigation guide | All users | 5 min |

**Total**: 1,774 lines of documentation
**Approximate reading time**: 15-90 minutes depending on path

## Core Concepts at a Glance

### The Five Test Categories

1. **CONTRACT TESTS** (14 existing)
   - Answer: "Do external APIs return expected data?"
   - Mock: httpx, API endpoints
   - Verify: Schema, fields, error codes
   - Speed: ~70ms

2. **PROPERTY TESTS** (6+ existing)
   - Answer: "Do calculations always satisfy invariants?"
   - Mock: None
   - Verify: Bounds, determinism, mathematical properties
   - Speed: ~10ms

3. **STATE MACHINE TESTS** (3+ existing)
   - Answer: "Does data survive write→read→delete?"
   - Mock: tempfile (filesystem only)
   - Verify: Data equality, isolation, timestamps
   - Speed: ~100ms

4. **INTEGRATION TESTS** (11 existing)
   - Answer: "Do all domains work together?"
   - Mock: External APIs (not internal functions)
   - Verify: Data flow, error handling, workflows
   - Speed: ~200ms

5. **ROUND-TRIP TESTS** (0 existing, future)
   - Answer: "Does data survive A→B→A transformation?"
   - Mock: None
   - Verify: Lossless conversion, unicode, batch consistency
   - Speed: ~50ms

### The Five Domains

1. **API Integration Layer** → tested by Contract Tests
2. **Metrics Computation Engine** → tested by Property Tests
3. **Data Persistence & Retrieval** → tested by State Machine Tests
4. **Workflow Orchestration** → tested by Integration Tests
5. **Test Case Conversion** (future) → tested by Round-Trip Tests

### The Epistemological Hierarchy

```
Level 5: Transformation Knowledge (A→B→A = A?) → Round-Trip Tests
  ↑ depends on
Level 4: Behavioral Knowledge (Do domains cooperate?) → Integration Tests
  ↑ depends on
Level 3: State Knowledge (Does data persist?) → State Machine Tests
  ↑ depends on
Level 2: Mathematical Knowledge (Invariants true?) → Property Tests
  ↑ depends on
Level 1: Contract Knowledge (APIs well-formed?) → Contract Tests
```

## How to Use This Framework

### When Adding a Feature
1. Define the contracts (L1): What APIs do you call?
2. Define the invariants (L2): What must always be true?
3. Define the state (L3): What data persists?
4. Define the workflow (L4): How do domains cooperate?
5. Define the transformation (L5): Is conversion lossless?

### When Debugging a Failure
1. Is it a **contract violation**? → Fix contract test
2. Is it a **broken invariant**? → Fix property test
3. Is it a **state issue**? → Fix state machine test
4. Is it a **workflow problem**? → Fix integration test
5. Is it a **conversion issue**? → Fix round-trip test

### When Writing a New Test
1. Open `TEST_CLASSIFICATION_GUIDE.md`
2. Follow the decision tree
3. Look up mocking pattern for your category
4. Use naming convention
5. Done

## Key Metrics

- **Total tests**: 34+
- **Test categories**: 5
- **Test domains**: 5
- **Documentation**: 1,774 lines
- **Coverage goal**: 100% of boundaries, 100% of calculations, 100% of I/O, 80%+ of workflows
- **Execution time**: ~4-5 seconds total

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2025-02-09 | 1.0 | Initial framework documentation |

---

**Last Updated**: 2025-02-09
**Framework Version**: 1.0
**Test Count**: 34+
**Status**: Active and maintained

## Quick Links

- **Decision Tree**: See `TEST_CLASSIFICATION_GUIDE.md` (250+ lines)
- **Test Inventory**: See `TEST_ONTOLOGY.md` (200+ lines)
- **Philosophical Foundation**: See `EPISTEMOLOGY.md` (300+ lines)
- **Visual Diagrams**: See `TEST_ARCHITECTURE_DIAGRAM.txt` (250+ lines)
- **Executive Summary**: See `TEST_FRAMEWORK_SUMMARY.txt` (261 lines)

---

**TL;DR**: Use `TEST_CLASSIFICATION_GUIDE.md` for decision-making. Use `TEST_ONTOLOGY.md` for deep dives. Use `EPISTEMOLOGY.md` to understand why. Use `TEST_ARCHITECTURE_DIAGRAM.txt` for visuals.
