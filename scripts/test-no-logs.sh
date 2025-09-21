#!/usr/bin/env bash
# Check for log files
LOG_DIR="${1:-./var/log/nonexistent}"
if [ ! -d "$LOG_DIR" ] || [ -z "$(find "$LOG_DIR" -name "*.log.jsonl" 2>/dev/null)" ]; then
    echo "Error: no logs found in $LOG_DIR" >&2
    exit 2
fi
echo "Logs found"
exit 0
