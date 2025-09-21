#!/usr/bin/env bash
# dev/logs - Live log viewing with lnav for parallel workers
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="${LOG_DIR:-$PROJECT_ROOT/var/log}"
LNAV_CONFIG="$PROJECT_ROOT/tools/lnav/lnav_config.json"
LNAV_FORMATS="$PROJECT_ROOT/tools/lnav/formats"
PREPARE_SCRIPT="$PROJECT_ROOT/tools/lnav/prepare.sh"

# Default values
SERVICES=()
ALL_SERVICES=false
SINCE_TIME=""
GREP_PATTERN=""
SQL_QUERY=""

# Print usage
usage() {
    cat <<EOF
Usage: dev/logs [--all | --svc <name> ...] [--since <ISO8601>] [--query <SQL>] [--grep <regex>]

Options:
  --all          Include logs from all services
  --svc <name>   Include logs from specific service(s)
  --since <time> Show logs since ISO8601 timestamp
  --grep <regex> Filter logs matching regex pattern
  --query <SQL>  Execute SQL query and exit
  --help         Show this help message

Examples:
  dev/logs --all                                    # View all service logs
  dev/logs --svc workerA --svc workerB             # View specific service logs
  dev/logs --all --grep "Retrying"                 # Filter for retry messages
  dev/logs --since 2025-09-21T10:00:00Z            # Logs since timestamp
  dev/logs --query "select level, count(*) from logs group by level"

EOF
    exit 0
}

# Check dependencies
check_dependencies() {
    # Check for lnav
    if ! command -v lnav &> /dev/null; then
        echo "Error: lnav is not installed" >&2
        echo "To install on macOS: brew install lnav" >&2
        echo "To install on Linux: sudo apt-get install lnav" >&2
        exit 127
    fi

    # Check for log directory
    if [ ! -d "$LOG_DIR" ]; then
        echo "Error: Log directory not found: $LOG_DIR" >&2
        echo "Please ensure services are running and logging to $LOG_DIR" >&2
        exit 2
    fi
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                usage
                ;;
            --all)
                ALL_SERVICES=true
                shift
                ;;
            --svc)
                shift
                if [[ $# -eq 0 ]]; then
                    echo "Error: --svc requires a service name" >&2
                    exit 1
                fi
                SERVICES+=("$1")
                shift
                ;;
            --since)
                shift
                if [[ $# -eq 0 ]]; then
                    echo "Error: --since requires an ISO8601 timestamp" >&2
                    exit 1
                fi
                SINCE_TIME="$1"
                shift
                ;;
            --grep)
                shift
                if [[ $# -eq 0 ]]; then
                    echo "Error: --grep requires a regex pattern" >&2
                    exit 1
                fi
                GREP_PATTERN="$1"
                shift
                ;;
            --query)
                shift
                if [[ $# -eq 0 ]]; then
                    echo "Error: --query requires an SQL statement" >&2
                    exit 1
                fi
                SQL_QUERY="$1"
                shift
                ;;
            *)
                echo "Error: Unknown option: $1" >&2
                echo "Use --help for usage information" >&2
                exit 1
                ;;
        esac
    done
}

# Get list of log files
get_log_files() {
    local files=""

    if [ "$ALL_SERVICES" = true ]; then
        # Get all log files
        files=$(find "$LOG_DIR" -name "*.log.jsonl" -type f 2>/dev/null | sort)
    elif [ ${#SERVICES[@]} -gt 0 ]; then
        # Get logs for specific services
        for svc in "${SERVICES[@]}"; do
            local svc_files=$(find "$LOG_DIR/$svc" -name "*.log.jsonl" -type f 2>/dev/null | sort)
            if [ -n "$svc_files" ]; then
                files="$files$svc_files"$'\n'
            fi
        done
    else
        # Default: get all logs if no specific selection
        files=$(find "$LOG_DIR" -name "*.log.jsonl" -type f 2>/dev/null | sort | head -10)
    fi

    # Remove empty lines and duplicates
    echo "$files" | grep -v '^$' | sort -u
}

# Build lnav command
build_lnav_command() {
    local files="$1"
    local cmd="lnav"

    # Add basic flags
    cmd="$cmd -t"  # Tail mode for live viewing

    # Load custom format
    if [ -d "$LNAV_FORMATS" ]; then
        cmd="$cmd -I $LNAV_FORMATS"
    fi

    # Add configuration
    if [ -f "$LNAV_CONFIG" ]; then
        cmd="$cmd -c ':config $LNAV_CONFIG'"
    fi

    # Add grep filter
    if [ -n "$GREP_PATTERN" ]; then
        # Escape special characters for lnav
        local escaped_pattern=$(echo "$GREP_PATTERN" | sed 's/[[\.*^$()+?{|]/\\&/g')
        cmd="$cmd -c ':filter-in $escaped_pattern'"
    fi

    # Add time filter
    if [ -n "$SINCE_TIME" ]; then
        cmd="$cmd -c ':goto $SINCE_TIME'"
        cmd="$cmd -c ':filter-in ts >= \"$SINCE_TIME\"'"
    fi

    # Add SQL query
    if [ -n "$SQL_QUERY" ]; then
        cmd="$cmd -n"  # Non-interactive mode
        cmd="$cmd -c ';$SQL_QUERY'"
        cmd="$cmd -c ':write-csv-to /tmp/lnav_out.csv'"
        cmd="$cmd -c ':quit'"
    fi

    # Add log files
    cmd="$cmd $files"

    echo "$cmd"
}

# Main execution
main() {
    # For testing mode, just validate args and exit
    if [ "${TEST_MODE:-0}" = "1" ]; then
        parse_args "$@"
        exit 0
    fi

    # Parse arguments
    parse_args "$@"

    # Check dependencies
    check_dependencies

    # Get log files
    echo "Scanning for log files..." >&2
    LOG_FILES=$(get_log_files)

    if [ -z "$LOG_FILES" ]; then
        echo "Error: no logs found in $LOG_DIR" >&2
        echo "Please check that services are running and logging" >&2
        exit 2
    fi

    # Count files for user feedback
    FILE_COUNT=$(echo "$LOG_FILES" | wc -l | tr -d ' ')
    echo "Found $FILE_COUNT log file(s)" >&2

    # Build and execute lnav command
    LNAV_CMD=$(build_lnav_command "$LOG_FILES")

    if [ -n "$SQL_QUERY" ]; then
        echo "Executing SQL query..." >&2
        eval "$LNAV_CMD"
        if [ -f "/tmp/lnav_out.csv" ]; then
            cat /tmp/lnav_out.csv
            rm -f /tmp/lnav_out.csv
        fi
    else
        echo "Launching lnav..." >&2
        echo "Press 'q' to quit, '?' for help" >&2
        eval "$LNAV_CMD"
    fi
}

# Run main function
main "$@"