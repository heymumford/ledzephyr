#!/bin/bash
# Sync documentation references between local and Atlassian systems

set -e

echo "📚 LedZephyr Documentation Sync"
echo "================================"

# Check environment
if [ -z "$LEDZEPHYR_JIRA_URL" ]; then
    echo "❌ Missing LEDZEPHYR_JIRA_URL environment variable"
    exit 1
fi

# Local documentation inventory
echo ""
echo "📁 Local Documentation (3 files):"
ls -la *.md | awk '{print "  -", $9, "("$5" bytes)"}'

# Confluence pages (reference only)
echo ""
echo "☁️  Confluence Documentation:"
echo "  - Mission Control: Lean philosophy and strategy"
echo "  - Technical Vault: Architecture and implementation"
echo "  - Operations Manual: Development guidelines"
echo "  - URL: https://balabushka.atlassian.net/wiki/spaces/LedZephyr"

# Jira work items (reference only)
echo ""
echo "📋 Jira Active Work:"
echo "  - Epic LED-46: Adoption Intelligence System"
echo "  - Tasks LED-47 to LED-51: Micro-kata implementation"
echo "  - URL: https://balabushka.atlassian.net/browse/LED"

# Code metrics
echo ""
echo "📊 Codebase Metrics:"
echo "  - Python files: $(find src tests -name "*.py" -type f | wc -l | xargs)"
echo "  - Test files: $(find tests -name "test_*.py" -type f | wc -l | xargs)"
echo "  - Coverage: $(grep -oP 'coverage-\K[^%]+' README.md 2>/dev/null || echo "unknown")%"

# Git status
echo ""
echo "🔄 Repository Status:"
git_status=$(git status --porcelain | wc -l | xargs)
if [ "$git_status" -eq 0 ]; then
    echo "  ✅ Working directory clean"
else
    echo "  ⚠️  $git_status uncommitted changes"
fi

echo ""
echo "✨ Sync check complete!"