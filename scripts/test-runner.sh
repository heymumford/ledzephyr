#!/bin/bash
# Balanced Testing Script for ledzephyr
# Runs unit, integration, and e2e tests with proper reporting

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test timing
START_TIME=""
LAYER_START_TIME=""

# Statistics tracking
UNIT_DURATION=0
INTEGRATION_DURATION=0
E2E_DURATION=0

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

log_layer() {
    echo -e "${CYAN}🔄 $1${NC}"
}

# Timer functions
start_timer() {
    START_TIME=$(date +%s)
}

start_layer_timer() {
    LAYER_START_TIME=$(date +%s)
}

get_duration() {
    local start_time="$1"
    local end_time=$(date +%s)
    echo $((end_time - start_time))
}

# Show usage
show_usage() {
    cat << EOF
Balanced Testing Runner for ledzephyr

Usage: $0 [layer] [options]

Test Layers:
  unit                   Fast unit tests (pure math, parsers) - Target: <1s
  integration           Integration tests with doubles - Target: <10s
  e2e                   End-to-end manifest-driven tests - Target: <30s
  all                   Run all test layers in sequence

Options:
  --verbose, -v         Verbose output
  --coverage, -c        Generate coverage report
  --parallel, -p        Run tests in parallel where possible
  --fail-fast, -f       Stop on first failure
  --markers MARKERS     Run only tests with specific markers
  --quiet, -q           Minimal output

Examples:
  $0 unit                    # Run unit tests only
  $0 integration --verbose  # Run integration tests with verbose output
  $0 all --coverage         # Run all layers with coverage
  $0 e2e --fail-fast        # Run e2e tests, stop on first failure

Test Structure:
  Unit Tests:        tests/unit/          Math, parsers, formatters
  Integration Tests: tests/integration/   API clients with test doubles
  E2E Tests:         tests/e2e/           Manifest-driven pipeline tests
EOF
}

# Run unit tests
run_unit_tests() {
    local verbose="$1"
    local coverage="$2"
    local fail_fast="$3"
    local markers="$4"
    local quiet="$5"

    log_layer "🧮 Running Unit Tests (Target: <1s)"
    start_layer_timer

    local pytest_args=()
    pytest_args+=("tests/unit/")
    pytest_args+=("-m" "unit")

    [[ "$verbose" == "true" ]] && pytest_args+=("-v")
    [[ "$quiet" == "true" ]] && pytest_args+=("-q")
    [[ "$fail_fast" == "true" ]] && pytest_args+=("-x")
    [[ -n "$markers" ]] && pytest_args+=("-m" "$markers")

    if [[ "$coverage" == "true" ]]; then
        pytest_args+=("--cov=ledzephyr" "--cov-append")
    fi

    cd "$PROJECT_ROOT"

    local exit_code=0
    poetry run pytest "${pytest_args[@]}" || exit_code=$?

    local duration=$(get_duration "$LAYER_START_TIME")
    UNIT_DURATION=$duration

    if [[ $exit_code -eq 0 ]]; then
        log_success "Unit tests passed in ${duration}s"
        return 0
    else
        log_error "Unit tests failed in ${duration}s"
        return $exit_code
    fi
}

# Run integration tests
run_integration_tests() {
    local verbose="$1"
    local coverage="$2"
    local fail_fast="$3"
    local markers="$4"
    local quiet="$5"

    log_layer "🔗 Running Integration Tests with Test Doubles (Target: <10s)"
    start_layer_timer

    local pytest_args=()
    pytest_args+=("tests/integration/")
    pytest_args+=("-m" "integration")

    [[ "$verbose" == "true" ]] && pytest_args+=("-v")
    [[ "$quiet" == "true" ]] && pytest_args+=("-q")
    [[ "$fail_fast" == "true" ]] && pytest_args+=("-x")
    [[ -n "$markers" ]] && pytest_args+=("-m" "$markers")

    if [[ "$coverage" == "true" ]]; then
        pytest_args+=("--cov=ledzephyr" "--cov-append")
    fi

    cd "$PROJECT_ROOT"

    local exit_code=0
    poetry run pytest "${pytest_args[@]}" || exit_code=$?

    local duration=$(get_duration "$LAYER_START_TIME")
    INTEGRATION_DURATION=$duration

    if [[ $exit_code -eq 0 ]]; then
        log_success "Integration tests passed in ${duration}s"
        return 0
    else
        log_error "Integration tests failed in ${duration}s"
        return $exit_code
    fi
}

# Run e2e tests
run_e2e_tests() {
    local verbose="$1"
    local coverage="$2"
    local fail_fast="$3"
    local markers="$4"
    local quiet="$5"

    log_layer "🎯 Running End-to-End Tests with Manifest Replay (Target: <30s)"
    start_layer_timer

    # Validate manifests first
    log_info "Validating TDM manifests before E2E tests..."
    if ! "$PROJECT_ROOT/scripts/tdm.sh" validate-all; then
        log_error "Manifest validation failed - cannot run E2E tests"
        return 1
    fi

    local pytest_args=()
    pytest_args+=("tests/e2e/")
    pytest_args+=("-m" "e2e")

    [[ "$verbose" == "true" ]] && pytest_args+=("-v")
    [[ "$quiet" == "true" ]] && pytest_args+=("-q")
    [[ "$fail_fast" == "true" ]] && pytest_args+=("-x")
    [[ -n "$markers" ]] && pytest_args+=("-m" "$markers")

    if [[ "$coverage" == "true" ]]; then
        pytest_args+=("--cov=ledzephyr" "--cov-append")
    fi

    cd "$PROJECT_ROOT"

    local exit_code=0
    poetry run pytest "${pytest_args[@]}" || exit_code=$?

    local duration=$(get_duration "$LAYER_START_TIME")
    E2E_DURATION=$duration

    if [[ $exit_code -eq 0 ]]; then
        log_success "E2E tests passed in ${duration}s"
        return 0
    else
        log_error "E2E tests failed in ${duration}s"
        return $exit_code
    fi
}

# Generate coverage report
generate_coverage_report() {
    log_info "Generating coverage report..."

    cd "$PROJECT_ROOT"

    # Create reports directory if it doesn't exist
    mkdir -p reports/

    # Generate reports
    poetry run coverage report --show-missing
    poetry run coverage xml -o reports/coverage.xml
    poetry run coverage html -d reports/coverage_html

    log_success "Coverage report generated:"
    log_info "  XML: reports/coverage.xml"
    log_info "  HTML: reports/coverage_html/index.html"
}

# Show test summary
show_summary() {
    local total_duration=$1

    echo
    echo "=================================="
    echo "🎯 BALANCED TESTING SUMMARY"
    echo "=================================="

    # Show durations for executed layers
    if [[ $UNIT_DURATION -gt 0 ]]; then
        echo -e "🧮 Unit Tests:        ✅ Completed (${UNIT_DURATION}s)"
    fi

    if [[ $INTEGRATION_DURATION -gt 0 ]]; then
        echo -e "🔗 Integration Tests: ✅ Completed (${INTEGRATION_DURATION}s)"
    fi

    if [[ $E2E_DURATION -gt 0 ]]; then
        echo -e "🎯 E2E Tests:         ✅ Completed (${E2E_DURATION}s)"
    fi

    echo "----------------------------------"
    echo "⏱️  Total Duration: ${total_duration}s"
    echo "=================================="
}

# Main function
main() {
    local layer="unit"
    local verbose="false"
    local coverage="false"
    local parallel="false"
    local fail_fast="false"
    local markers=""
    local quiet="false"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            unit|integration|e2e|all)
                layer="$1"
                shift
                ;;
            --verbose|-v)
                verbose="true"
                shift
                ;;
            --coverage|-c)
                coverage="true"
                shift
                ;;
            --parallel|-p)
                parallel="true"
                shift
                ;;
            --fail-fast|-f)
                fail_fast="true"
                shift
                ;;
            --markers)
                markers="$2"
                shift 2
                ;;
            --quiet|-q)
                quiet="true"
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    start_timer

    log_info "🚀 Starting balanced testing for ledzephyr"
    [[ "$coverage" == "true" ]] && rm -f .coverage

    local overall_exit_code=0

    case "$layer" in
        unit)
            run_unit_tests "$verbose" "$coverage" "$fail_fast" "$markers" "$quiet" || overall_exit_code=$?
            ;;
        integration)
            run_integration_tests "$verbose" "$coverage" "$fail_fast" "$markers" "$quiet" || overall_exit_code=$?
            ;;
        e2e)
            run_e2e_tests "$verbose" "$coverage" "$fail_fast" "$markers" "$quiet" || overall_exit_code=$?
            ;;
        all)
            run_unit_tests "$verbose" "$coverage" "$fail_fast" "$markers" "$quiet" || overall_exit_code=$?

            if [[ $overall_exit_code -eq 0 || "$fail_fast" != "true" ]]; then
                run_integration_tests "$verbose" "$coverage" "$fail_fast" "$markers" "$quiet" || overall_exit_code=$?
            fi

            if [[ $overall_exit_code -eq 0 || "$fail_fast" != "true" ]]; then
                run_e2e_tests "$verbose" "$coverage" "$fail_fast" "$markers" "$quiet" || overall_exit_code=$?
            fi
            ;;
    esac

    local total_duration=$(get_duration "$START_TIME")

    if [[ "$coverage" == "true" ]]; then
        generate_coverage_report
    fi

    show_summary "$total_duration"

    exit $overall_exit_code
}

# Check dependencies
check_dependencies() {
    if ! command -v poetry &> /dev/null; then
        log_error "Poetry is required but not installed"
        exit 1
    fi
}

# Run main function
check_dependencies
main "$@"