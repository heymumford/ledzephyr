#!/usr/bin/env python3
import re
import subprocess


def get_test_count(path):
    """Count tests in a path."""
    result = subprocess.run(
        ["poetry", "run", "pytest", path, "--co", "-q"], capture_output=True, text=True
    )
    # Extract test count from output
    if "passed" in result.stdout:
        match = re.search(r"(\d+) passed", result.stdout)
        if match:
            return int(match.group(1))
    return 0


def get_coverage_for_path(path, name):
    """Get coverage for specific test path."""
    result = subprocess.run(
        ["poetry", "run", "pytest", path, "--cov=ledzephyr", "--cov-report=term", "--tb=no", "-q"],
        capture_output=True,
        text=True,
    )

    # Extract coverage percentage
    coverage = 0
    if "TOTAL" in result.stdout:
        for line in result.stdout.split("\n"):
            if "TOTAL" in line:
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        coverage = float(part.rstrip("%"))
                        break

    return coverage


# Test counts
print("=" * 60)
print("TEST COVERAGE REPORT BY TYPE")
print("=" * 60)
print()

test_types = {
    "Unit Tests": "tests/unit",
    "Integration Tests": "tests/integration",
    "E2E Tests": "tests/e2e",
    "School Tests": "tests/integration/schools",
    "Benchmark Tests": "tests/benchmarks",
}

results = []
for test_name, test_path in test_types.items():
    count = get_test_count(test_path)
    coverage = get_coverage_for_path(test_path, test_name)
    results.append((test_name, count, coverage))
    print(f"{test_name:20} {count:4} tests   {coverage:6.2f}% coverage")

print()
print("-" * 60)

# Overall stats
total_tests = sum(r[1] for r in results)
if len(results) > 0:
    avg_coverage = sum(r[2] for r in results) / len(results)
else:
    avg_coverage = 0

print(f"{'TOTAL':20} {total_tests:4} tests   {avg_coverage:6.2f}% avg coverage")

# Get overall coverage
overall_result = subprocess.run(
    ["poetry", "run", "pytest", "--cov=ledzephyr", "--cov-report=term", "--tb=no", "-q"],
    capture_output=True,
    text=True,
)

overall_coverage = 0
if "TOTAL" in overall_result.stdout:
    for line in overall_result.stdout.split("\n"):
        if "TOTAL" in line:
            parts = line.split()
            for part in parts:
                if "%" in part:
                    overall_coverage = float(part.rstrip("%"))
                    break

print(f"{'OVERALL':20} {total_tests:4} tests   {overall_coverage:6.2f}% total coverage")
print("=" * 60)

# Module-level coverage
print("\nMODULE-LEVEL COVERAGE:")
print("-" * 60)

module_result = subprocess.run(
    [
        "poetry",
        "run",
        "pytest",
        "--cov=ledzephyr",
        "--cov-report=term-missing:skip-covered",
        "--tb=no",
        "-q",
    ],
    capture_output=True,
    text=True,
)

# Parse and display module coverage
in_coverage = False
for line in module_result.stdout.split("\n"):
    if "Name" in line and "Stmts" in line:
        in_coverage = True
        print(f"{'Module':<40} {'Stmts':>8} {'Miss':>8} {'Coverage':>10}")
        print("-" * 66)
        continue
    if in_coverage:
        if "TOTAL" in line:
            print("-" * 66)
            parts = line.split()
            if len(parts) >= 5:
                print(f"{'TOTAL':<40} {parts[1]:>8} {parts[2]:>8} {parts[-1]:>10}")
            break
        elif "ledzephyr" in line:
            parts = line.split()
            if len(parts) >= 5:
                module = parts[0].replace("src/", "").replace(".py", "")
                print(f"{module:<40} {parts[1]:>8} {parts[2]:>8} {parts[-1]:>10}")
