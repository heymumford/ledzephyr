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
