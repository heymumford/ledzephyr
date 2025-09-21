#!/usr/bin/env bash
# Test grep argument escaping
GREP_PATTERN="$1"

# Escape special regex characters for lnav
ESCAPED=$(echo "$GREP_PATTERN" | sed 's/[[\.*^$()+?{|]/\\&/g')

# Would be: lnav -c ":filter-in $ESCAPED"
echo ":filter-in $ESCAPED"
