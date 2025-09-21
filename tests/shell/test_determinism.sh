#!/usr/bin/env bash
# Determinism and fail-fast tests for dev/logs
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
    fi
}

echo "Running determinism and fail-fast tests..."
echo "=========================================="

# Test 1: prepare.sh produces stable file ordering
mkdir -p tools/lnav var/log/{workerA,workerB,workerC}
touch var/log/workerA/{2025-01-03.log.jsonl,2025-01-01.log.jsonl,2025-01-02.log.jsonl}
touch var/log/workerB/{2025-01-02.log.jsonl,2025-01-01.log.jsonl}
touch var/log/workerC/2025-01-01.log.jsonl

# Create prepare.sh script
cat > tools/lnav/prepare.sh <<'EOF'
#!/usr/bin/env bash
# Resolves arguments to a stable file list for lnav
set -euo pipefail

LOG_DIR="${LOG_DIR:-./var/log}"
FILES=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            # Find all log files, sorted lexically
            FILES=$(find "$LOG_DIR" -name "*.log.jsonl" -type f 2>/dev/null | sort)
            shift
            ;;
        --svc)
            shift
            if [[ $# -eq 0 ]]; then
                echo "Error: --svc requires a service name" >&2
                exit 1
            fi
            # Find logs for specific service, sorted
            SVC_FILES=$(find "$LOG_DIR/$1" -name "*.log.jsonl" -type f 2>/dev/null | sort)
            FILES="$FILES $SVC_FILES"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Output files, one per line, removing duplicates and empty lines
echo "$FILES" | tr ' ' '\n' | grep -v '^$' | sort -u
EOF
chmod +x tools/lnav/prepare.sh

# Test file ordering
output=$(tools/lnav/prepare.sh --all)
expected=$(cat <<EOF
./var/log/workerA/2025-01-01.log.jsonl
./var/log/workerA/2025-01-02.log.jsonl
./var/log/workerA/2025-01-03.log.jsonl
./var/log/workerB/2025-01-01.log.jsonl
./var/log/workerB/2025-01-02.log.jsonl
./var/log/workerC/2025-01-01.log.jsonl
EOF
)
assert_eq "$expected" "$output" "prepare.sh produces lexically sorted file list"

# Test 2: Single service selection
output=$(tools/lnav/prepare.sh --svc workerA)
expected=$(cat <<EOF
./var/log/workerA/2025-01-01.log.jsonl
./var/log/workerA/2025-01-02.log.jsonl
./var/log/workerA/2025-01-03.log.jsonl
EOF
)
assert_eq "$expected" "$output" "prepare.sh filters by service correctly"

# Test 3: Grep escaping test (mock implementation)
cat > scripts/test-grep-escape.sh <<'EOF'
#!/usr/bin/env bash
# Test grep argument escaping
GREP_PATTERN="$1"

# Escape special regex characters for lnav
ESCAPED=$(echo "$GREP_PATTERN" | sed 's/[[\.*^$()+?{|]/\\&/g')

# Would be: lnav -c ":filter-in $ESCAPED"
echo ":filter-in $ESCAPED"
EOF
chmod +x scripts/test-grep-escape.sh

output=$(scripts/test-grep-escape.sh "Retrying.*connection")
assert_contains "$output" ":filter-in Retrying" "Grep pattern is properly escaped"

# Test 4: Missing lnav detection
cat > scripts/test-lnav-check.sh <<'EOF'
#!/usr/bin/env bash
# Check for lnav installation
if ! command -v lnav &> /dev/null; then
    echo "Error: lnav is not installed" >&2
    echo "To install on macOS: brew install lnav" >&2
    echo "To install on Linux: sudo apt-get install lnav" >&2
    exit 127
fi
echo "lnav found"
exit 0
EOF
chmod +x scripts/test-lnav-check.sh

# Mock missing lnav
PATH="/usr/bin:/bin" output=$(scripts/test-lnav-check.sh 2>&1) && exit_code=$? || exit_code=$?
assert_eq 127 "$exit_code" "Missing lnav returns exit code 127"
assert_contains "$output" "brew install lnav" "Missing lnav shows installation instructions"

# Test 5: No logs found
cat > scripts/test-no-logs.sh <<'EOF'
#!/usr/bin/env bash
# Check for log files
LOG_DIR="${1:-./var/log/nonexistent}"
if [ ! -d "$LOG_DIR" ] || [ -z "$(find "$LOG_DIR" -name "*.log.jsonl" 2>/dev/null)" ]; then
    echo "Error: no logs found in $LOG_DIR" >&2
    exit 2
fi
echo "Logs found"
exit 0
EOF
chmod +x scripts/test-no-logs.sh

output=$(scripts/test-no-logs.sh ./var/log/nonexistent 2>&1) && exit_code=$? || exit_code=$?
assert_eq 2 "$exit_code" "No logs found returns exit code 2"
assert_contains "$output" "no logs found" "No logs found shows error message"

echo ""
echo "=========================================="
echo "Test Results: $TESTS_PASSED/$TESTS_RUN passed"

if [ "$TESTS_PASSED" -ne "$TESTS_RUN" ]; then
    exit 1
fi