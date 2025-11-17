# End-to-End (E2E) Testing Guide

E2E tests verify the complete LedZephyr system with real API credentials and live services. These tests are manual and should be run before production releases.

## Prerequisites

1. **Valid API Credentials**
   - Jira/Atlassian API token with read access
   - qTest API token with read access (optional)
   - Test project with real data

2. **Environment Setup**
   ```bash
   export LEDZEPHYR_ATLASSIAN_URL=https://your.atlassian.net
   export LEDZEPHYR_ATLASSIAN_TOKEN=your_actual_token
   export LEDZEPHYR_QTEST_URL=https://your.qtestnet.com
   export LEDZEPHYR_QTEST_TOKEN=your_actual_token
   ```

## E2E Test Scenarios

### Scenario 1: Fresh Data Fetch and Analysis

**Objective**: Verify complete data collection and analysis pipeline

**Steps**:
```bash
# 1. Clear any cached data
rm -rf data/TESTPROJECT

# 2. Run with fresh data fetch
poetry run ledzephyr --project TESTPROJECT --fetch

# 3. Verify output
```

**Expected Results**:
- ✓ Successfully connects to all APIs
- ✓ Retrieves test data from Zephyr Scale
- ✓ Retrieves test data from qTest (if token provided)
- ✓ Retrieves defect data from Jira
- ✓ Displays migration metrics
- ✓ Shows adoption rate percentage
- ✓ Saves snapshots to `data/TESTPROJECT/`

**Failure Indicators**:
- ✗ API connection errors
- ✗ Authentication failures
- ✗ Empty data returned when data exists
- ✗ Crashes or exceptions

---

### Scenario 2: Cached Data Analysis

**Objective**: Verify offline analysis using cached data

**Steps**:
```bash
# 1. Ensure cached data exists (run Scenario 1 first)
ls data/TESTPROJECT/

# 2. Run without fetching
poetry run ledzephyr --project TESTPROJECT --no-fetch

# 3. Verify output
```

**Expected Results**:
- ✓ Loads data from disk without API calls
- ✓ Displays correct metrics from cached data
- ✓ Completes in <1 second

**Failure Indicators**:
- ✗ Attempts API calls despite --no-fetch
- ✗ "No recent data" error when cache exists
- ✗ Incorrect metrics compared to fresh fetch

---

### Scenario 3: Historical Trend Analysis

**Objective**: Verify trend calculation with multiple snapshots

**Steps**:
```bash
# 1. Fetch data on Day 1
poetry run ledzephyr --project TESTPROJECT --fetch

# 2. Wait 1 day (or modify timestamps manually for testing)

# 3. Fetch data on Day 2
poetry run ledzephyr --project TESTPROJECT --fetch

# 4. Verify trends appear
```

**Expected Results**:
- ✓ Multiple snapshots stored
- ✓ Trend direction shown (↑, ↓, or →)
- ✓ Completion estimate calculated
- ✓ Recent history displayed

**Failure Indicators**:
- ✗ "Insufficient historical data" despite multiple snapshots
- ✗ Trend calculations incorrect
- ✗ Completion date illogical

---

### Scenario 4: Error Handling - Invalid Project

**Objective**: Verify graceful handling of non-existent project

**Steps**:
```bash
poetry run ledzephyr --project NONEXISTENT_PROJECT --fetch
```

**Expected Results**:
- ✓ Displays clear error message
- ✓ Doesn't crash
- ✓ Returns empty results gracefully

**Failure Indicators**:
- ✗ Unhandled exception/stack trace
- ✗ Unclear error messages

---

### Scenario 5: Network Resilience

**Objective**: Verify retry logic and fallback behavior

**Steps**:
```bash
# 1. Temporarily disconnect network or use invalid URL
export LEDZEPHYR_ATLASSIAN_URL=https://invalid.example.com

# 2. Run with fetch
poetry run ledzephyr --project TESTPROJECT --fetch

# 3. Verify error handling
```

**Expected Results**:
- ✓ Retries failed requests (3 attempts)
- ✓ Shows retry progress messages
- ✓ Falls back to cached data if available
- ✓ Displays appropriate error messages

**Failure Indicators**:
- ✗ No retry attempts
- ✗ Immediate failure without fallback
- ✗ Crashes on network error

---

### Scenario 6: Large Dataset Performance

**Objective**: Verify performance with real-world data volumes

**Steps**:
```bash
# Use project with 1000+ test cases
poetry run ledzephyr --project LARGE_PROJECT --fetch
```

**Expected Results**:
- ✓ Completes within 30 seconds
- ✓ Handles pagination correctly
- ✓ Memory usage <100MB
- ✓ All data captured

**Failure Indicators**:
- ✗ Timeout errors
- ✗ Memory exhaustion
- ✗ Truncated results

---

### Scenario 7: Logging and Debugging

**Objective**: Verify production logging works correctly

**Steps**:
```bash
# 1. Run with trace mode
poetry run ledzephyr --project TESTPROJECT --fetch --trace

# 2. Check logs
cat logs/ledzephyr.log | tail -50

# 3. Verify transaction IDs
```

**Expected Results**:
- ✓ Logs written to `logs/ledzephyr.log`
- ✓ Each log entry has transaction ID
- ✓ Trace mode shows detailed debug info
- ✓ API calls logged with URLs (tokens redacted)

**Failure Indicators**:
- ✗ No log file created
- ✗ Sensitive data (tokens) in logs
- ✗ Missing transaction correlation

---

### Scenario 8: Multiple Concurrent Projects

**Objective**: Verify data isolation between projects

**Steps**:
```bash
# Fetch data for multiple projects
poetry run ledzephyr --project PROJECT_A --fetch
poetry run ledzephyr --project PROJECT_B --fetch
poetry run ledzephyr --project PROJECT_C --fetch

# Verify data separation
ls data/
```

**Expected Results**:
- ✓ Separate directories for each project
- ✓ No data cross-contamination
- ✓ Correct metrics for each project

**Failure Indicators**:
- ✗ Mixed data between projects
- ✗ Overwritten snapshots

---

## E2E Test Checklist

Before release, verify:

- [ ] Scenario 1: Fresh data fetch works
- [ ] Scenario 2: Cached analysis works
- [ ] Scenario 3: Trend analysis works
- [ ] Scenario 4: Invalid project handled
- [ ] Scenario 5: Network errors handled
- [ ] Scenario 6: Large datasets work
- [ ] Scenario 7: Logging works correctly
- [ ] Scenario 8: Multi-project isolation works

## Security Considerations

**Important**: E2E tests use real API credentials

1. **Never commit credentials**
   - Use environment variables only
   - Never hardcode tokens in test files

2. **Use test/sandbox accounts**
   - Don't use production API tokens
   - Use projects with non-sensitive data

3. **Rate limiting**
   - Be mindful of API rate limits
   - Add delays between rapid-fire tests if needed

4. **Data privacy**
   - Verify no PII in logs
   - Ensure snapshots stored securely

## Automated E2E (Future)

To automate E2E tests in CI/CD:

1. **Setup test environment**
   - Create dedicated test Jira/qTest projects
   - Generate service account tokens
   - Store as GitHub secrets

2. **Add to CI workflow**
   ```yaml
   - name: E2E Tests
     if: github.event_name == 'push' && github.ref == 'refs/heads/main'
     env:
       LEDZEPHYR_ATLASSIAN_URL: ${{ secrets.TEST_JIRA_URL }}
       LEDZEPHYR_ATLASSIAN_TOKEN: ${{ secrets.TEST_JIRA_TOKEN }}
     run: poetry run python tests/test_e2e_automated.py
   ```

3. **Create automated test script**
   - Run all scenarios programmatically
   - Assert on expected outcomes
   - Clean up test data after run

## Troubleshooting

### "API authentication failed"
- Verify token has correct permissions
- Check token hasn't expired
- Ensure URL is correct (include https://)

### "No data returned"
- Verify project exists
- Check project has test cases
- Ensure updated in last 6 months (filter applied)

### "Insufficient historical data"
- Run fetch at least twice, 1+ day apart
- Or manually create multiple snapshots

### Performance issues
- Check network latency
- Verify API rate limits not exceeded
- Consider reducing data fetch range

## Report Issues

If E2E tests fail, report with:
1. Exact command run
2. Error message/output
3. Log file contents (redact tokens!)
4. Environment details (OS, Python version)
5. Project size (number of test cases)
