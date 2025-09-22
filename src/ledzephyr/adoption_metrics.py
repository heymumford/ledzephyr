"""Adoption metrics and cohort tracking for Zephyr to qTest migration."""

from dataclasses import dataclass
from datetime import date


@dataclass
class TeamInventory:
    """Snapshot of team test inventory."""

    team: str
    total_tests: int
    migrated_tests: int
    as_of_date: date
    baseline_requirements: int = 0
    qtest_requirements: int = 0
    baseline_defect_links: int = 0
    qtest_defect_links: int = 0
    zephyr_executions: int = 0
    qtest_executions: int = 0


@dataclass
class ExecutionStats:
    """Test execution statistics."""

    zephyr_execs: int
    qtest_execs: int
    period_days: int = 7


@dataclass
class AdoptionMetrics:
    """Core adoption metrics."""

    adoption_rate: float
    remaining_tests: int
    percent_complete: float
    execution_shift: float = 0.0
    coverage_retained: float = 0.0
    defect_link_parity: float = 0.0


@dataclass
class User:
    """User with testing activity."""

    email: str
    name: str
    executions: int
    role: str
    team: str | None = None
    last_active: date | None = None


@dataclass
class DailySnapshot:
    """Daily migration snapshot."""

    date: date
    migrated: int
    total: int
    team: str | None = None


@dataclass
class AdoptionVelocity:
    """Migration velocity metrics."""

    weekly_average: float
    current_week: int
    trend: str  # accelerating, steady, slowing
    estimated_completion_date: date | None = None


@dataclass
class AdoptionSnapshot:
    """Point-in-time adoption snapshot."""

    team: str
    date: date
    adoption_rate: float


@dataclass
class MigrationPlan:
    """Planned migration target."""

    team: str
    target_date: date
    target_rate: float
    wave: str | None = None  # Wave identifier


@dataclass
class PlanVariance:
    """Variance from plan."""

    percent_variance: float
    status: str  # ahead, on_track, behind
    days_off_track: int


@dataclass
class CohortMetrics:
    """Metrics for a user cohort."""

    cohort_name: str
    user_count: int
    total_tests: int
    migrated_tests: int
    adoption_rate: float


@dataclass
class CohortAnalysis:
    """Analysis of cohort adoption."""

    leader_cohort: str
    laggard_cohort: str
    adoption_gap: float
    recommendation: str


@dataclass
class OrgMetrics:
    """Organization-level metrics."""

    total_tests: int
    total_migrated: int
    overall_adoption_rate: float
    team_metrics: list[AdoptionMetrics]


def calculate_adoption_metrics(inventory: TeamInventory) -> AdoptionMetrics:
    """Calculate adoption metrics from inventory."""
    adoption_rate = (
        inventory.migrated_tests / inventory.total_tests if inventory.total_tests > 0 else 0.0
    )
    remaining = inventory.total_tests - inventory.migrated_tests
    percent_complete = adoption_rate * 100

    # Calculate execution shift
    execution_shift = 0.0
    total_execs = inventory.zephyr_executions + inventory.qtest_executions
    if total_execs > 0:
        execution_shift = inventory.qtest_executions / total_execs

    # Calculate secondary metrics
    coverage_retained = 0.0
    if inventory.baseline_requirements > 0:
        coverage_retained = inventory.qtest_requirements / inventory.baseline_requirements

    defect_parity = 0.0
    if inventory.baseline_defect_links > 0:
        defect_parity = inventory.qtest_defect_links / inventory.baseline_defect_links

    return AdoptionMetrics(
        adoption_rate=adoption_rate,
        remaining_tests=remaining,
        percent_complete=percent_complete,
        execution_shift=execution_shift,
        coverage_retained=coverage_retained,
        defect_link_parity=defect_parity,
    )


def calculate_execution_shift(stats: ExecutionStats) -> float:
    """Calculate shift of executions to qTest."""
    total = stats.zephyr_execs + stats.qtest_execs
    return stats.qtest_execs / total if total > 0 else 0.0


def segment_user_cohorts(users: list[User]) -> dict[str, list[str]]:
    """Segment users into cohorts based on activity."""
    # Sort by execution count
    sorted_users = sorted(users, key=lambda u: u.executions, reverse=True)

    cohorts = {"power_users": [], "regular": [], "long_tail": []}

    total_users = len(sorted_users)
    if total_users == 0:
        return cohorts

    # Top 40% are power users
    power_cutoff = int(total_users * 0.4)
    # Next 40% are regular
    regular_cutoff = int(total_users * 0.8)

    for i, user in enumerate(sorted_users):
        if i < power_cutoff:
            cohorts["power_users"].append(user.email)
        elif i < regular_cutoff:
            cohorts["regular"].append(user.email)
        else:
            cohorts["long_tail"].append(user.email)

    return cohorts


def calculate_org_adoption(inventories: list[TeamInventory]) -> OrgMetrics:
    """Calculate organization-wide adoption metrics."""
    total_tests = sum(inv.total_tests for inv in inventories)
    total_migrated = sum(inv.migrated_tests for inv in inventories)

    team_metrics = [calculate_adoption_metrics(inv) for inv in inventories]

    return OrgMetrics(
        total_tests=total_tests,
        total_migrated=total_migrated,
        overall_adoption_rate=total_migrated / total_tests if total_tests > 0 else 0.0,
        team_metrics=team_metrics,
    )


def calculate_adoption_velocity(history: list[DailySnapshot]) -> AdoptionVelocity:
    """Calculate migration velocity from history."""
    if len(history) < 2:
        return AdoptionVelocity(0.0, 0, "unknown")

    # Calculate weekly velocity
    first = history[0]
    last = history[-1]
    weeks = (last.date - first.date).days / 7
    total_migrated = last.migrated - first.migrated

    weekly_avg = total_migrated / weeks if weeks > 0 else 0

    # Current week velocity (last 7 days)
    current_week = 0
    if len(history) >= 2:
        current_week = history[-1].migrated - history[-2].migrated

    # Determine trend
    trend = "steady"
    if current_week > weekly_avg * 1.1:
        trend = "accelerating"
    elif current_week < weekly_avg * 0.9:
        trend = "slowing"

    # Estimate completion date
    remaining = last.total - last.migrated
    weeks_to_complete = remaining / weekly_avg if weekly_avg > 0 else 999
    from datetime import timedelta

    estimated_completion = last.date + timedelta(weeks=weeks_to_complete)

    return AdoptionVelocity(
        weekly_average=weekly_avg,
        current_week=current_week,
        trend=trend,
        estimated_completion_date=estimated_completion if weeks_to_complete < 100 else None,
    )


def calculate_plan_variance(actual: AdoptionSnapshot, plan: MigrationPlan) -> PlanVariance:
    """Calculate variance from migration plan."""
    variance = (
        ((actual.adoption_rate - plan.target_rate) / plan.target_rate) * 100
        if plan.target_rate > 0
        else 0
    )

    status = "on_track"
    if variance < -5:
        status = "behind"
    elif variance > 5:
        status = "ahead"

    # Estimate days off track (simplified)
    days_off = abs(int(variance * 0.7))  # Rough estimate

    return PlanVariance(percent_variance=variance, status=status, days_off_track=days_off)


def analyze_cohort_adoption(cohort_data: dict[str, CohortMetrics]) -> CohortAnalysis:
    """Analyze adoption across cohorts."""
    if not cohort_data:
        return CohortAnalysis("", "", 0.0, "No data")

    # Find leader and laggard
    sorted_cohorts = sorted(cohort_data.values(), key=lambda c: c.adoption_rate, reverse=True)
    leader = sorted_cohorts[0]
    laggard = sorted_cohorts[-1]

    gap = leader.adoption_rate - laggard.adoption_rate

    # Generate recommendation
    recommendation = f"Focus training on {laggard.cohort_name} users"
    if gap > 0.5:
        recommendation = f"Urgent: {recommendation} - significant adoption gap"

    return CohortAnalysis(
        leader_cohort=leader.cohort_name,
        laggard_cohort=laggard.cohort_name,
        adoption_gap=gap,
        recommendation=recommendation,
    )
