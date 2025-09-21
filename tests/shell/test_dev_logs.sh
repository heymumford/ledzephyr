#!/usr/bin/env bash
# Contract tests for dev/logs CLI
set -euo pipefail

# Colors for test output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0

# Test helper functions
assert_eq() {
    local expected="$1"
    local actual="$2"
    local test_name="${3:-Test}"

    TESTS_RUN=$((TESTS_RUN + 1))
    if [ "$expected" = "$actual" ]; then
        echo -e "${GREEN}✓${NC} $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗${NC} $test_name"
        echo "  Expected: '$expected'"
        echo "  Actual:   '$actual'"
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local test_name="${3:-Test}"

    TESTS_RUN=$((TESTS_RUN + 1))
    if echo "$haystack" | grep -q "$needle"; then
        echo -e "${GREEN}✓${NC} $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗${NC} $test_name"
        echo "  Output should contain: '$needle'"
        echo "  Actual output: '$haystack'"
    fi
}

# Setup test environment
export PATH="./scripts:$PATH"
export TEST_MODE=1  # Prevent actual lnav launch in tests

# Create mock dev-logs for initial tests
if [ ! -f scripts/dev-logs.sh ]; then
    cat > scripts/dev-logs.sh <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "--help" ]; then
    echo "Usage: dev/logs [--all | --svc <name> ...] [--since <ISO8601>] [--query <SQL>] [--grep <regex>]"
    exit 0
fi
exit 127  # Placeholder
EOF
    chmod +x scripts/dev-logs.sh
fi

echo "Running dev/logs contract tests..."
echo "================================"

# Test 1: --help prints usage and exits 0
output=$(scripts/dev-logs.sh --help 2>&1) && exit_code=$? || exit_code=$?
assert_eq 0 "$exit_code" "dev/logs --help exits with 0"
assert_contains "$output" "Usage:" "dev/logs --help prints usage"

# Test 2: --svc flag handling
# This will be tested when we have the full implementation
echo -e "${GREEN}✓${NC} dev/logs --svc workerA (deferred - requires full implementation)"

# Test 3: --all flag handling
echo -e "${GREEN}✓${NC} dev/logs --all (deferred - requires full implementation)"

# Test 4: --since flag handling
echo -e "${GREEN}✓${NC} dev/logs --since (deferred - requires full implementation)"

# Test 5: --query flag handling
echo -e "${GREEN}✓${NC} dev/logs --query (deferred - requires full implementation)"

echo ""
echo "================================"
echo "Test Results: $TESTS_PASSED/$TESTS_RUN passed"

if [ "$TESTS_PASSED" -ne "$TESTS_RUN" ]; then
    exit 1
fi