#!/bin/bash
# Track and report lean metrics for the project

set -e

# Output file for metrics history
METRICS_FILE=".metrics/history.jsonl"
mkdir -p .metrics

# Gather metrics
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

# Documentation metrics
DOC_COUNT=$(find . -name "*.md" -not -path "./.venv/*" | wc -l | xargs)
DOC_SIZE=$(find . -name "*.md" -not -path "./.venv/*" -exec stat -f%z {} \; 2>/dev/null | awk '{sum+=$1} END {print sum}' || echo 0)

# Code metrics
PY_FILES=$(find src tests -name "*.py" -type f | wc -l | xargs)
TEST_FILES=$(find tests -name "test_*.py" -type f | wc -l | xargs)
LOC=$(find src -name "*.py" -exec cat {} \; | wc -l | xargs)

# Test metrics
COVERAGE=$(grep -oP 'coverage-\K[^%]+' README.md 2>/dev/null || echo "unknown")
TEST_COUNT=$(grep -oP 'tests-\K[^-]+' README.md 2>/dev/null || echo "unknown")

# Performance metrics (if available)
if command -v hyperfine &> /dev/null; then
    LEAN_TEST_TIME=$(hyperfine --warmup 1 --runs 3 "make lean-test" --export-json /tmp/lean-test.json 2>/dev/null && jq '.results[0].median' /tmp/lean-test.json || echo "unknown")
else
    LEAN_TEST_TIME="unknown"
fi

# Create JSON record
cat << EOF >> "$METRICS_FILE"
{"timestamp":"$TIMESTAMP","commit":"$COMMIT","branch":"$BRANCH","docs":{"count":$DOC_COUNT,"size":$DOC_SIZE},"code":{"files":$PY_FILES,"tests":$TEST_FILES,"loc":$LOC},"quality":{"coverage":"$COVERAGE","test_count":"$TEST_COUNT"},"performance":{"lean_test_time":"$LEAN_TEST_TIME"}}
EOF

echo "📈 Lean Metrics Report"
echo "======================"
echo ""
echo "📚 Documentation:"
echo "  Files: $DOC_COUNT (target: ≤3)"
echo "  Total size: $(echo $DOC_SIZE | numfmt --to=iec-i --suffix=B 2>/dev/null || echo "$DOC_SIZE bytes")"
echo ""
echo "🐍 Codebase:"
echo "  Python files: $PY_FILES"
echo "  Test files: $TEST_FILES"
echo "  Lines of code: $LOC"
echo ""
echo "✅ Quality:"
echo "  Coverage: $COVERAGE%"
echo "  Test count: $TEST_COUNT"
echo ""
echo "⚡ Performance:"
echo "  Lean test time: ${LEAN_TEST_TIME}s"
echo ""
echo "📊 Metrics saved to: $METRICS_FILE"

# Trend analysis (if we have history)
if [ -f "$METRICS_FILE" ] && [ $(wc -l < "$METRICS_FILE") -gt 1 ]; then
    echo ""
    echo "📈 Trends (last 5 entries):"
    tail -5 "$METRICS_FILE" | jq -r '"\(.timestamp): docs=\(.docs.count), coverage=\(.quality.coverage)%"'
fi