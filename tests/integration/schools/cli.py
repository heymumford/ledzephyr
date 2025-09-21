#!/usr/bin/env python3
"""
Command-line interface for running school of fish integration tests.

Usage:
    python -m tests.integration.schools.cli                    # Run all schools
    python -m tests.integration.schools.cli --school api       # Run specific school
    python -m tests.integration.schools.cli --list             # List available schools
    python -m tests.integration.schools.cli --workers 8        # Use 8 parallel workers
"""

import argparse
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.integration.schools import get_orthogonal_schools
from tests.integration.schools.runner import SchoolOfFishRunner, run_schools_of_fish


def list_schools():
    """List all available schools and their katas."""
    schools = get_orthogonal_schools()
    if not schools:
        print("No schools registered")
        return

    print("🐟 Available Schools:")
    print("=" * 50)
    for school in sorted(schools, key=lambda s: s.name):
        print(f"\n{school.name}: {school.description}")
        print(f"  Parallel Safe: {'Yes' if school.parallel_safe else 'No'}")
        print(f"  Katas ({len(school.katas)}):")
        for kata in school.katas:
            print(f"    • {kata.name}: {kata.goal}")


def run_specific_school(school_name: str, max_workers: int = 4) -> bool:
    """Run a specific school by name."""
    schools = get_orthogonal_schools()
    target_school = None

    for school in schools:
        if school.name == school_name or school.name.replace("_school", "") == school_name:
            target_school = school
            break

    if not target_school:
        print(f"❌ School '{school_name}' not found")
        available = [s.name for s in schools]
        print(f"Available schools: {', '.join(available)}")
        return False

    print(f"🐟 Swimming single school: {target_school.name}")
    runner = SchoolOfFishRunner(max_workers=1)  # Single school doesn't need parallelism
    results = runner.swim_all_schools([target_school])
    runner.print_summary()

    return target_school.name in results and results[target_school.name].success_rate > 0.5


def main():
    parser = argparse.ArgumentParser(
        description="Run school of fish integration tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run all schools in parallel
  %(prog)s --school api             # Run only the API school
  %(prog)s --school data            # Run only the data school
  %(prog)s --list                   # List all available schools
  %(prog)s --workers 8              # Use 8 parallel workers
        """,
    )

    parser.add_argument(
        "--school",
        type=str,
        help="Run a specific school (e.g., 'api', 'data', 'config', 'performance')",
    )

    parser.add_argument("--list", action="store_true", help="List all available schools and exit")

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers for running schools (default: 4)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    if args.list:
        list_schools()
        return 0

    if args.school:
        success = run_specific_school(args.school, args.workers)
        return 0 if success else 1

    # Run all schools
    print(f"🐟 Swimming all schools with {args.workers} workers...")
    success = run_schools_of_fish(max_workers=args.workers)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
