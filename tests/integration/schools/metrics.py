"""
Performance metrics and tracking for school of fish execution.

Provides detailed timing, resource usage, and efficiency metrics
for optimizing the parallel test execution.
"""

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import psutil


@dataclass
class SystemMetrics:
    """System resource metrics at a point in time."""

    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    active_threads: int


@dataclass
class SchoolMetrics:
    """Performance metrics for a school execution."""

    school_name: str
    start_time: float
    end_time: float
    duration: float
    kata_count: int
    success_count: int
    success_rate: float
    avg_kata_duration: float
    max_kata_duration: float
    min_kata_duration: float
    system_start: SystemMetrics
    system_end: SystemMetrics


@dataclass
class SwimMetrics:
    """Aggregate metrics for an entire school of fish run."""

    run_id: str
    start_time: float
    end_time: float
    total_duration: float
    parallel_efficiency: float  # How much faster than sequential
    school_count: int
    total_kata_count: int
    overall_success_rate: float
    max_concurrent_schools: int
    schools: list[SchoolMetrics]
    system_peak: SystemMetrics


class MetricsCollector:
    """Collects and analyzes performance metrics during test execution."""

    def __init__(self):
        self.current_metrics: SwimMetrics | None = None
        self.school_metrics: dict[str, SchoolMetrics] = {}
        self.system_samples: list[SystemMetrics] = []
        self.start_time: float | None = None

    def _capture_system_metrics(self) -> SystemMetrics:
        """Capture current system resource usage."""
        process = psutil.Process()
        return SystemMetrics(
            timestamp=time.perf_counter(),
            cpu_percent=psutil.cpu_percent(interval=None),
            memory_mb=process.memory_info().rss / 1024 / 1024,
            memory_percent=process.memory_percent(),
            active_threads=process.num_threads(),
        )

    def start_swim(self, run_id: str) -> None:
        """Start tracking metrics for a school of fish run."""
        self.start_time = time.perf_counter()
        self.system_samples = [self._capture_system_metrics()]
        print(f"📊 Started metrics collection for run: {run_id}")

    def start_school(self, school_name: str) -> None:
        """Start tracking metrics for a specific school."""
        if school_name not in self.school_metrics:
            self.school_metrics[school_name] = SchoolMetrics(
                school_name=school_name,
                start_time=time.perf_counter(),
                end_time=0,
                duration=0,
                kata_count=0,
                success_count=0,
                success_rate=0,
                avg_kata_duration=0,
                max_kata_duration=0,
                min_kata_duration=float("inf"),
                system_start=self._capture_system_metrics(),
                system_end=SystemMetrics(0, 0, 0, 0, 0),
            )

    def end_school(self, school_name: str, kata_durations: list[float], success_count: int) -> None:
        """End tracking for a specific school and calculate metrics."""
        if school_name in self.school_metrics:
            metrics = self.school_metrics[school_name]
            metrics.end_time = time.perf_counter()
            metrics.duration = metrics.end_time - metrics.start_time
            metrics.kata_count = len(kata_durations)
            metrics.success_count = success_count
            metrics.success_rate = success_count / len(kata_durations) if kata_durations else 0
            metrics.system_end = self._capture_system_metrics()

            if kata_durations:
                metrics.avg_kata_duration = sum(kata_durations) / len(kata_durations)
                metrics.max_kata_duration = max(kata_durations)
                metrics.min_kata_duration = min(kata_durations)

    def end_swim(self, run_id: str) -> SwimMetrics:
        """End tracking and generate comprehensive metrics."""
        end_time = time.perf_counter()
        total_duration = end_time - (self.start_time or end_time)

        # Calculate parallel efficiency
        sequential_time = sum(m.duration for m in self.school_metrics.values())
        parallel_efficiency = sequential_time / total_duration if total_duration > 0 else 1.0

        # Find system peak usage
        self.system_samples.append(self._capture_system_metrics())
        system_peak = max(self.system_samples, key=lambda s: s.memory_mb)

        # Calculate aggregate stats
        total_katas = sum(m.kata_count for m in self.school_metrics.values())
        total_successes = sum(m.success_count for m in self.school_metrics.values())
        overall_success_rate = total_successes / total_katas if total_katas > 0 else 0

        self.current_metrics = SwimMetrics(
            run_id=run_id,
            start_time=self.start_time or 0,
            end_time=end_time,
            total_duration=total_duration,
            parallel_efficiency=parallel_efficiency,
            school_count=len(self.school_metrics),
            total_kata_count=total_katas,
            overall_success_rate=overall_success_rate,
            max_concurrent_schools=len(self.school_metrics),  # Simplified
            schools=list(self.school_metrics.values()),
            system_peak=system_peak,
        )

        return self.current_metrics

    def save_metrics(self, output_path: Path) -> None:
        """Save metrics to JSON file for analysis."""
        if self.current_metrics:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(asdict(self.current_metrics), f, indent=2)

    def print_performance_summary(self) -> None:
        """Print a performance-focused summary."""
        if not self.current_metrics:
            print("No metrics available")
            return

        m = self.current_metrics
        print("\n📊 Performance Metrics Summary")
        print(f"{'=' * 50}")
        print(f"Total Time:      {m.total_duration:.3f}s")
        print(f"Efficiency:      {m.parallel_efficiency:.2f}x (vs sequential)")
        print(f"Success Rate:    {m.overall_success_rate:.1%}")
        print(f"Schools:         {m.school_count}")
        print(f"Total Katas:     {m.total_kata_count}")
        print(f"Peak Memory:     {m.system_peak.memory_mb:.1f} MB")
        print(f"Peak CPU:        {m.system_peak.cpu_percent:.1f}%")
        print()

        # School-by-school breakdown
        print("School Performance:")
        for school in sorted(m.schools, key=lambda s: s.duration, reverse=True):
            efficiency_indicator = (
                "🚀" if school.success_rate > 0.8 else "⚠️" if school.success_rate > 0.5 else "🐌"
            )
            print(
                f"  {efficiency_indicator} {school.school_name}: {school.duration:.3f}s "
                f"({school.success_count}/{school.kata_count} katas)"
            )

        print(
            f"\n💡 Parallel efficiency: {m.parallel_efficiency:.2f}x speedup over sequential execution"
        )


# Global metrics collector instance
_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _collector
