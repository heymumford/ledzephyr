"""
School Runner: Parallel execution framework for orthogonal test schools

Implements the "school of fish" pattern where each school swims independently
and all schools can run concurrently for maximum efficiency.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import Kata, School, SchoolStatus, get_orthogonal_schools
from .metrics import get_metrics_collector


@dataclass
class KataResult:
    """Result of running a single kata."""

    name: str
    success: bool
    duration: float
    error: str | None = None


@dataclass
class SchoolResult:
    """Result of running an entire school."""

    name: str
    status: SchoolStatus
    katas: list[KataResult] = field(default_factory=list)
    total_duration: float = 0.0
    success_rate: float = 0.0

    @property
    def passed_katas(self) -> int:
        return sum(1 for k in self.katas if k.success)

    @property
    def total_katas(self) -> int:
        return len(self.katas)


class SchoolOfFishRunner:
    """
    Runs multiple schools in parallel (school of fish pattern).

    Each school represents orthogonal test concerns that don't interfere
    with each other, allowing for maximum parallelization.
    """

    def __init__(self, max_workers: int = 4, timeout_per_school: float = 120.0):
        self.max_workers = max_workers
        self.timeout_per_school = timeout_per_school
        self.results: dict[str, SchoolResult] = {}

    def run_kata(self, kata: Kata) -> KataResult:
        """Run a single kata and measure its performance."""
        start_time = time.perf_counter()
        try:
            success = kata.test_func()
            duration = time.perf_counter() - start_time
            return KataResult(name=kata.name, success=bool(success), duration=duration)
        except Exception as e:
            duration = time.perf_counter() - start_time
            return KataResult(
                name=kata.name,
                success=False,
                duration=duration,
                error=f"{type(e).__name__}: {str(e)}",
            )

    def swim_school(self, school: School) -> SchoolResult:
        """
        Run all katas in a school sequentially.

        Katas within a school may have dependencies, so they run sequentially.
        Schools themselves run in parallel.
        """
        metrics = get_metrics_collector()
        metrics.start_school(school.name)

        start_time = time.perf_counter()
        result = SchoolResult(name=school.name, status=SchoolStatus.SWIMMING)

        try:
            # Run katas sequentially within the school
            for kata in school.katas:
                kata_result = self.run_kata(kata)
                result.katas.append(kata_result)

                # Early exit if critical kata fails and has dependencies
                if not kata_result.success and kata.dependencies:
                    # Skip remaining dependent katas
                    remaining = school.katas[school.katas.index(kata) + 1 :]
                    for remaining_kata in remaining:
                        if kata.name in (remaining_kata.dependencies or []):
                            result.katas.append(
                                KataResult(
                                    name=remaining_kata.name,
                                    success=False,
                                    duration=0.0,
                                    error=f"Skipped due to dependency failure: {kata.name}",
                                )
                            )

            # Calculate final metrics
            result.total_duration = time.perf_counter() - start_time
            result.success_rate = (
                result.passed_katas / result.total_katas if result.total_katas > 0 else 0.0
            )
            result.status = (
                SchoolStatus.SCHOOLED if result.success_rate > 0.5 else SchoolStatus.SCATTERED
            )

            # Update metrics collector
            kata_durations = [k.duration for k in result.katas]
            metrics.end_school(school.name, kata_durations, result.passed_katas)

        except Exception as e:
            result.total_duration = time.perf_counter() - start_time
            result.status = SchoolStatus.SCATTERED
            result.katas.append(
                KataResult(
                    name="school_failure",
                    success=False,
                    duration=result.total_duration,
                    error=f"School-level failure: {str(e)}",
                )
            )

            # Update metrics even on failure
            metrics.end_school(school.name, [result.total_duration], 0)

        return result

    def swim_all_schools(self, schools: list[School] | None = None) -> dict[str, SchoolResult]:
        """
        Run all schools in parallel - the core 'school of fish' pattern.

        Returns results for all schools, whether they succeeded or failed.
        """
        if schools is None:
            schools = get_orthogonal_schools()

        if not schools:
            return {}

        # Use ThreadPoolExecutor for parallel school execution
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(schools))) as executor:
            # Submit all schools for parallel execution
            future_to_school = {
                executor.submit(self.swim_school, school): school for school in schools
            }

            # Collect results as they complete
            for future in as_completed(future_to_school, timeout=self.timeout_per_school):
                school = future_to_school[future]
                try:
                    result = future.result()
                    self.results[school.name] = result
                except Exception as e:
                    # Handle school-level failures
                    self.results[school.name] = SchoolResult(
                        name=school.name,
                        status=SchoolStatus.SCATTERED,
                        total_duration=0.0,
                        katas=[
                            KataResult(
                                name="executor_failure",
                                success=False,
                                duration=0.0,
                                error=f"Execution failed: {str(e)}",
                            )
                        ],
                    )

        return self.results

    def print_summary(self) -> None:
        """Print a summary of all school results."""
        if not self.results:
            print("🐟 No schools swam")
            return

        total_schools = len(self.results)
        successful_schools = sum(
            1 for r in self.results.values() if r.status == SchoolStatus.SCHOOLED
        )
        total_katas = sum(r.total_katas for r in self.results.values())
        successful_katas = sum(r.passed_katas for r in self.results.values())
        total_time = max(r.total_duration for r in self.results.values()) if self.results else 0.0

        print("\n🐟 School of Fish Summary")
        print(f"{'=' * 50}")
        print(f"Schools: {successful_schools}/{total_schools} schooled")
        print(f"Katas:   {successful_katas}/{total_katas} passed")
        print(f"Time:    {total_time:.2f}s (parallel execution)")
        print()

        for school_name, result in sorted(self.results.items()):
            status_emoji = "🐟" if result.status == SchoolStatus.SCHOOLED else "💥"
            print(
                f"{status_emoji} {school_name}: {result.passed_katas}/{result.total_katas} katas in {result.total_duration:.2f}s"
            )

            for kata in result.katas:
                kata_emoji = "✅" if kata.success else "❌"
                print(f"   {kata_emoji} {kata.name} ({kata.duration:.3f}s)")
                if kata.error:
                    print(f"      Error: {kata.error}")


def run_schools_of_fish(max_workers: int = 4, save_metrics: bool = True) -> bool:
    """
    Main entry point for running the school of fish integration tests.

    Returns True if all schools succeeded, False otherwise.
    """
    metrics = get_metrics_collector()
    run_id = f"swim_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    metrics.start_swim(run_id)

    runner = SchoolOfFishRunner(max_workers=max_workers)
    results = runner.swim_all_schools()
    runner.print_summary()

    # Complete metrics collection
    swim_metrics = metrics.end_swim(run_id)
    metrics.print_performance_summary()

    # Save metrics if requested
    if save_metrics:
        metrics_path = Path("test_reports") / "school_metrics" / f"{run_id}.json"
        metrics.save_metrics(metrics_path)
        print(f"📊 Metrics saved to: {metrics_path}")

    # Success if all schools are schooled
    return all(r.status == SchoolStatus.SCHOOLED for r in results.values())
