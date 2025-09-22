#!/bin/bash
# Verify documentation synchronization and detect drift

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 LedZephyr Documentation Drift Detection"
echo "=========================================="

# Track findings
WARNINGS=0
ERRORS=0

# Check 1: Essential files exist
echo ""
echo "📁 Essential Files Check:"
for file in README.md CLAUDE.md DOCUMENTATION.md; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file exists"
    else
        echo -e "  ${RED}✗${NC} $file MISSING"
        ((ERRORS++))
    fi
done

# Check 2: No unauthorized documentation
echo ""
echo "🚫 Unauthorized Documentation Check:"
EXTRA_DOCS=$(find . -name "*.md" -type f -not -path "./.venv/*" -not -path "./node_modules/*" -not -path "./.pytest_cache/*" -not -name "README.md" | grep -v -E "^./(CLAUDE|DOCUMENTATION|FEEDBACK)\.md$" | wc -l)
if [ "$EXTRA_DOCS" -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} No unauthorized documentation files"
else
    echo -e "  ${YELLOW}⚠${NC} Found $EXTRA_DOCS extra documentation files:"
    find . -name "*.md" -type f -not -path "./.venv/*" -not -path "./.pytest_cache/*" -not -name "README.md" | grep -v -E "^./(CLAUDE|DOCUMENTATION|FEEDBACK)\.md$" | head -5
    ((WARNINGS++))
fi

# Check 3: Links validation
echo ""
echo "🔗 External Links Check:"
if grep -q "balabushka.atlassian.net" README.md; then
    echo -e "  ${GREEN}✓${NC} Confluence link present in README"
else
    echo -e "  ${RED}✗${NC} Confluence link missing from README"
    ((ERRORS++))
fi

if grep -q "browse/LED" README.md; then
    echo -e "  ${GREEN}✓${NC} Jira link present in README"
else
    echo -e "  ${RED}✗${NC} Jira link missing from README"
    ((ERRORS++))
fi

# Check 4: File size limits (lean documentation)
echo ""
echo "📏 File Size Check (Lean Limits):"
for file in README.md CLAUDE.md DOCUMENTATION.md; do
    if [ -f "$file" ]; then
        SIZE=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        if [ "$SIZE" -lt 20000 ]; then
            echo -e "  ${GREEN}✓${NC} $file is lean ($(echo $SIZE | numfmt --to=iec-i --suffix=B))"
        else
            echo -e "  ${YELLOW}⚠${NC} $file exceeds 20KB ($(echo $SIZE | numfmt --to=iec-i --suffix=B))"
            ((WARNINGS++))
        fi
    fi
done

# Check 5: Git status
echo ""
echo "🔄 Repository Cleanliness:"
UNCOMMITTED=$(git status --porcelain | wc -l | xargs)
if [ "$UNCOMMITTED" -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} Working directory clean"
else
    echo -e "  ${YELLOW}⚠${NC} $UNCOMMITTED uncommitted changes"
    ((WARNINGS++))
fi

# Check 6: Test coverage threshold
echo ""
echo "📊 Quality Metrics:"
# Extract coverage percentage (e.g., "53.60" from "coverage-53.60%25")
COVERAGE=$(grep -o 'coverage-[0-9.]*' README.md | cut -d'-' -f2 | head -1)
if [ -n "$COVERAGE" ]; then
    # Compare as floating point
    if [ $(echo "$COVERAGE >= 50" | bc) -eq 1 ] 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Coverage at $COVERAGE% (above 50% threshold)"
    else
        echo -e "  ${YELLOW}⚠${NC} Coverage at $COVERAGE% (below 50% threshold)"
        ((WARNINGS++))
    fi
else
    echo -e "  ${YELLOW}⚠${NC} Coverage metric not found"
    ((WARNINGS++))
fi

# Summary
echo ""
echo "=========================================="
if [ "$ERRORS" -eq 0 ] && [ "$WARNINGS" -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    exit 0
elif [ "$ERRORS" -eq 0 ]; then
    echo -e "${YELLOW}⚠ Passed with $WARNINGS warnings${NC}"
    exit 0
else
    echo -e "${RED}❌ Failed with $ERRORS errors and $WARNINGS warnings${NC}"
    exit 1
fi