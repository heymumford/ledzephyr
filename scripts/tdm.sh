#!/bin/bash
# TDM (Test Data Management) Operations Script
# Provides utilities for managing test data manifests and validation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TDM_DIR="$PROJECT_ROOT/tdm"
TESTDATA_DIR="$PROJECT_ROOT/testdata"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Show usage
show_usage() {
    cat << EOF
TDM (Test Data Management) Operations

Usage: $0 <command> [options]

Commands:
  validate <manifest>     Validate a manifest file
  validate-all           Validate all manifests in testdata/manifests/
  list-manifests         List all available manifests
  show-schema           Show the manifest JSON schema
  check-cassettes       Check that all referenced cassettes exist
  clean-cache           Clean TDM cache files
  help                  Show this help message

Examples:
  $0 validate testdata/manifests/demo_project_2025q2.yaml
  $0 validate-all
  $0 list-manifests
  $0 check-cassettes

Environment Variables:
  TDM_SALT              Salt for deterministic masking (required)
  TDM_SCHEMA_DIR        Schema directory (default: tdm/schema)
EOF
}

# Validate a single manifest
validate_manifest() {
    local manifest_path="$1"

    if [[ ! -f "$manifest_path" ]]; then
        log_error "Manifest file not found: $manifest_path"
        return 1
    fi

    log_info "Validating manifest: $manifest_path"

    cd "$PROJECT_ROOT"
    if poetry run python tdm/tools/validate_manifest.py "$manifest_path"; then
        log_success "Manifest validation passed: $manifest_path"
        return 0
    else
        log_error "Manifest validation failed: $manifest_path"
        return 1
    fi
}

# Validate all manifests
validate_all_manifests() {
    local manifest_dir="$TESTDATA_DIR/manifests"
    local failed_count=0
    local total_count=0

    if [[ ! -d "$manifest_dir" ]]; then
        log_error "Manifests directory not found: $manifest_dir"
        return 1
    fi

    log_info "Validating all manifests in $manifest_dir"

    for manifest_file in "$manifest_dir"/*.{yaml,yml}; do
        if [[ -f "$manifest_file" ]]; then
            ((total_count++))
            if ! validate_manifest "$manifest_file"; then
                ((failed_count++))
            fi
        fi
    done

    if [[ $failed_count -eq 0 ]]; then
        log_success "All $total_count manifests validated successfully"
        return 0
    else
        log_error "$failed_count out of $total_count manifests failed validation"
        return 1
    fi
}

# List all available manifests
list_manifests() {
    local manifest_dir="$TESTDATA_DIR/manifests"

    if [[ ! -d "$manifest_dir" ]]; then
        log_error "Manifests directory not found: $manifest_dir"
        return 1
    fi

    log_info "Available manifests:"
    find "$manifest_dir" -name "*.yaml" -o -name "*.yml" | sort | while read -r manifest; do
        local rel_path=$(realpath --relative-to="$PROJECT_ROOT" "$manifest")
        echo "  📋 $rel_path"
    done
}

# Show the manifest JSON schema
show_schema() {
    local schema_file="$TDM_DIR/schema/manifest.schema.json"

    if [[ ! -f "$schema_file" ]]; then
        log_error "Schema file not found: $schema_file"
        return 1
    fi

    log_info "Manifest JSON Schema:"
    cat "$schema_file" | jq '.'
}

# Check that all referenced cassettes exist
check_cassettes() {
    local manifest_dir="$TESTDATA_DIR/manifests"
    local cassettes_dir="$TESTDATA_DIR/cassettes"
    local missing_count=0

    log_info "Checking cassette file references..."

    while IFS= read -r -d '' manifest_file; do
        log_info "Checking cassettes in $(basename "$manifest_file")"

        # Extract cassette paths from manifests
        local cassette_paths
        cassette_paths=$(grep -E "cassette:" "$manifest_file" | sed 's/.*cassette: *//' | tr -d '"' || true)

        if [[ -n "$cassette_paths" ]]; then
            while IFS= read -r cassette_path; do
                if [[ -n "$cassette_path" ]]; then
                    local full_cassette_path="$PROJECT_ROOT/$cassette_path"
                    if [[ ! -f "$full_cassette_path" ]]; then
                        log_error "Missing cassette: $cassette_path (referenced in $(basename "$manifest_file"))"
                        ((missing_count++))
                    else
                        log_success "Found cassette: $cassette_path"
                    fi
                fi
            done <<< "$cassette_paths"
        fi
    done < <(find "$manifest_dir" -name "*.yaml" -o -name "*.yml" -print0)

    if [[ $missing_count -eq 0 ]]; then
        log_success "All referenced cassettes found"
        return 0
    else
        log_error "$missing_count cassette files are missing"
        return 1
    fi
}

# Clean TDM cache files
clean_cache() {
    log_info "Cleaning TDM cache files..."

    local cache_dirs=(
        "$PROJECT_ROOT/.ledzephyr_cache"
        "$PROJECT_ROOT/.hypothesis"
        "$PROJECT_ROOT/.pytest_cache"
    )

    for cache_dir in "${cache_dirs[@]}"; do
        if [[ -d "$cache_dir" ]]; then
            rm -rf "$cache_dir"
            log_success "Removed cache directory: $cache_dir"
        fi
    done

    # Clean Python bytecode
    find "$PROJECT_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null || true

    log_success "TDM cache cleanup completed"
}

# Main command dispatcher
main() {
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi

    local command="$1"
    shift

    case "$command" in
        validate)
            if [[ $# -eq 0 ]]; then
                log_error "Missing manifest file path"
                show_usage
                exit 1
            fi
            validate_manifest "$1"
            ;;
        validate-all)
            validate_all_manifests
            ;;
        list-manifests)
            list_manifests
            ;;
        show-schema)
            show_schema
            ;;
        check-cassettes)
            check_cassettes
            ;;
        clean-cache)
            clean_cache
            ;;
        help)
            show_usage
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Check dependencies
check_dependencies() {
    if ! command -v poetry &> /dev/null; then
        log_error "Poetry is required but not installed"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        log_warning "jq is recommended for better JSON output"
    fi
}

# Run main function
check_dependencies
main "$@"