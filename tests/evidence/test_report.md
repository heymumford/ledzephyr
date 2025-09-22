# Test Data Management - E2E Test Report

**Test Run:** 2025-09-21 21:58:09
**Manifest:** tests/tdm/manifest.json
**Mode:** stub

## Scenarios Executed

### Integration Happy Path
- **Execution Time:** 0.00s
- **API Calls:** 0
- **Errors:** 0
- **Test Results:**
  - jira_project: PASS
  - jira_search_page1: PASS
  - jira_search_page2: PASS
  - zephyr_testcases: PASS
  - zephyr_testcycles: PASS
  - qtest_projects: PASS
  - qtest_testcases: PASS

### Pagination Test
- **Execution Time:** 0.00s
- **API Calls:** 0
- **Errors:** 1

## Quality Gates

### integration_happy_path
- **Overall Status:** GateStatus.FAILED
- **Passed:** 1/5
  - ✅ schema_completeness: Schema completeness 100.0% >= 95%
  - ❌ data_coverage: Data coverage 0.0% < 80%
  - ⏭️ performance: No performance data available
  - ❌ sensitive_data: 3 sensitive fields not masked
  - ⏭️ determinism: Need at least 2 runs to verify determinism

### pagination_test
- **Overall Status:** GateStatus.FAILED
- **Passed:** 1/5
  - ✅ schema_completeness: Schema completeness 100.0% >= 95%
  - ❌ data_coverage: Data coverage 0.0% < 80%
  - ⏭️ performance: No performance data available
  - ❌ sensitive_data: 3 sensitive fields not masked
  - ⏭️ determinism: Need at least 2 runs to verify determinism

## VCR Replay Statistics
- **Cache Hits:** 0
- **Cache Misses:** 0
- **Recordings:** 0

## Data Masking
- **Tokens Generated:** 0
