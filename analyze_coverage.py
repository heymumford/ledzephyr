#!/usr/bin/env python3
import json
import subprocess


def run_coverage(test_path, test_type):
    """Run coverage for specific test type."""
    print(f"\n{'='*60}")
    print(f" {test_type.upper()} TEST COVERAGE")
    print("=" * 60)

    cmd = [
        "poetry",
        "run",
        "pytest",
        test_path,
        "--cov=ledzephyr",
        "--cov-report=json",
        "--tb=no",
        "-q",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        # Read the coverage.json file
        with open("coverage.json") as f:
            data = json.load(f)

        # Extract summary
        summary = data.get("totals", {})

        print(f"Statements: {summary.get('num_statements', 0)}")
        print(f"Missing: {summary.get('missing_lines', 0)}")
        print(f"Coverage: {summary.get('percent_covered', 0):.2f}%")

        # Show file-level coverage
        print("\nTop files by coverage:")
        files = data.get("files", {})
        sorted_files = sorted(
            files.items(), key=lambda x: x["summary"]["percent_covered"], reverse=True
        )[:10]

        for file_path, file_data in sorted_files:
            if "ledzephyr" in file_path:
                file_summary = file_data.get("summary", {})
                percent = file_summary.get("percent_covered", 0)
                print(f"  {file_path.split('ledzephyr/')[-1]:40} {percent:6.2f}%")

        return summary.get("percent_covered", 0)

    except Exception as e:
        print(f"Error analyzing coverage: {e}")
        return 0


# Run coverage for each test type
coverages = {}
coverages["Unit"] = run_coverage("tests/unit", "Unit")
coverages["Integration"] = run_coverage("tests/integration", "Integration")
coverages["E2E"] = run_coverage("tests/e2e", "E2E")

# Overall summary
print(f"\n{'='*60}")
print(" OVERALL COVERAGE SUMMARY")
print("=" * 60)
for test_type, coverage in coverages.items():
    print(f"{test_type:15} {coverage:6.2f}%")

avg_coverage = sum(coverages.values()) / len(coverages) if coverages else 0
print(f"\nAverage Coverage: {avg_coverage:.2f}%")
