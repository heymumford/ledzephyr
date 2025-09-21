#!/usr/bin/env bash
# Format validation tests for structured logs
set -euo pipefail

# Colors for test output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0

# Test helper
validate_log() {
    local log_file="$1"
    local test_name="$2"

    TESTS_RUN=$((TESTS_RUN + 1))

    # Check if jq is available
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}✗${NC} $test_name - jq not installed"
        return 1
    fi

    # Validate each line is valid JSON
    local line_num=0
    local errors=""

    while IFS= read -r line; do
        line_num=$((line_num + 1))

        # Check valid JSON
        if ! echo "$line" | jq '.' > /dev/null 2>&1; then
            errors="${errors}Line $line_num: Invalid JSON\n"
            continue
        fi

        # Check required fields
        local ts=$(echo "$line" | jq -r '.ts // empty')
        local level=$(echo "$line" | jq -r '.level // empty')
        local msg=$(echo "$line" | jq -r '.msg // empty')
        local svc=$(echo "$line" | jq -r '.svc // empty')
        local pid=$(echo "$line" | jq -r '.pid // empty')
        local tid=$(echo "$line" | jq -r '.tid // empty')

        if [ -z "$ts" ]; then
            errors="${errors}Line $line_num: Missing 'ts' field\n"
        elif ! echo "$ts" | grep -qE '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$'; then
            errors="${errors}Line $line_num: Invalid timestamp format (not UTC ISO-8601): $ts\n"
        fi

        if [ -z "$level" ]; then
            errors="${errors}Line $line_num: Missing 'level' field\n"
        elif ! echo "$level" | grep -qE '^(debug|info|notice|warning|err|crit|alert|emerg)$'; then
            errors="${errors}Line $line_num: Invalid level: $level\n"
        fi

        if [ -z "$msg" ]; then
            errors="${errors}Line $line_num: Missing 'msg' field\n"
        fi

        if [ -z "$svc" ]; then
            errors="${errors}Line $line_num: Missing 'svc' field\n"
        fi

        if [ -z "$pid" ]; then
            errors="${errors}Line $line_num: Missing 'pid' field\n"
        fi

        if [ -z "$tid" ]; then
            errors="${errors}Line $line_num: Missing 'tid' field\n"
        fi

        # Check optional fields if present
        local trace_id=$(echo "$line" | jq -r '.trace_id // empty')
        if [ -n "$trace_id" ] && ! echo "$trace_id" | grep -qE '^[0-9a-f]{32}$'; then
            errors="${errors}Line $line_num: Invalid trace_id format: $trace_id\n"
        fi

        local span_id=$(echo "$line" | jq -r '.span_id // empty')
        if [ -n "$span_id" ] && ! echo "$span_id" | grep -qE '^[0-9a-f]{16}$'; then
            errors="${errors}Line $line_num: Invalid span_id format: $span_id\n"
        fi

        local elapsed_ms=$(echo "$line" | jq -r '.elapsed_ms // empty')
        if [ -n "$elapsed_ms" ]; then
            if ! echo "$line" | jq '.elapsed_ms | type == "number"' | grep -q true; then
                errors="${errors}Line $line_num: elapsed_ms must be numeric: $elapsed_ms\n"
            elif (( $(echo "$elapsed_ms < 0" | bc -l) )); then
                errors="${errors}Line $line_num: elapsed_ms must be non-negative: $elapsed_ms\n"
            fi
        fi

    done < "$log_file"

    if [ -z "$errors" ]; then
        echo -e "${GREEN}✓${NC} $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $test_name"
        echo -e "$errors"
        return 1
    fi
}

echo "Running log format validation tests..."
echo "======================================"

# Create sample valid log for testing
mkdir -p testdata/logs/workerA testdata/logs/workerB

# Valid log sample
cat > testdata/logs/workerA/sample-valid.log.jsonl <<'EOF'
{"ts":"2025-09-21T10:30:45.123456Z","level":"info","msg":"Worker started","svc":"workerA","pid":1234,"tid":"thread-1"}
{"ts":"2025-09-21T10:30:46.234567Z","level":"debug","msg":"Processing item","svc":"workerA","pid":1234,"tid":"thread-1","trace_id":"abcdef0123456789abcdef0123456789","span_id":"0123456789abcdef"}
{"ts":"2025-09-21T10:30:47.345678Z","level":"warning","msg":"Retrying connection","svc":"workerA","pid":1234,"tid":"thread-2","elapsed_ms":125.5}
EOF

# Invalid log samples for testing
cat > testdata/logs/workerB/sample-invalid.log.jsonl <<'EOF'
{"level":"info","msg":"Missing timestamp","svc":"workerB","pid":5678,"tid":"thread-1"}
{"ts":"2025-09-21 10:30:45","level":"info","msg":"Invalid timestamp format","svc":"workerB","pid":5678,"tid":"thread-1"}
{"ts":"2025-09-21T10:30:45.123456Z","level":"invalid","msg":"Invalid level","svc":"workerB","pid":5678,"tid":"thread-1"}
{"ts":"2025-09-21T10:30:45.123456Z","level":"info","msg":"Missing required fields"}
EOF

# Test valid logs
validate_log "testdata/logs/workerA/sample-valid.log.jsonl" "Valid log format validation"

# Test invalid logs (expect failure - this validates our error detection)
TESTS_RUN=$((TESTS_RUN + 1))
output=$(validate_log "testdata/logs/workerB/sample-invalid.log.jsonl" "Invalid log format detection" 2>&1) && result=0 || result=1
if [ "$result" -eq 1 ]; then
    echo -e "${GREEN}✓${NC} Invalid log format correctly detected"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗${NC} Failed to detect invalid log format"
fi

echo ""
echo "======================================"
echo "Test Results: $TESTS_PASSED/$TESTS_RUN passed"

if [ "$TESTS_PASSED" -ne "$TESTS_RUN" ]; then
    exit 1
fi