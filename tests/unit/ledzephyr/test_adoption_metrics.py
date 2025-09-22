"""Test-first implementation of adoption metrics and cohort tracking."""

from dataclasses import dataclass
from datetime import date

import pytest


def test_adoption_rate_calculation():
    """Test adoption rate = migrated/total."""
    # Given
    team_inventory = TeamInventory(
        team="Platform Team", total_tests=1000, migrated_tests=750, as_of_date=date.today()
    )

    # When
    metrics = calculate_adoption_metrics(team_inventory)

    # Then
    assert metrics.adoption_rate == 0.75
    assert metrics.remaining_tests == 250
    assert metrics.percent_complete == 75.0


def test_execution_shift_metric():
    """Test execution shift to qTest."""
    # Given
    executions = ExecutionStats(zephyr_execs=100, qtest_execs=400, period_days=7)

    # When
    shift = calculate_execution_shift(executions)

    # Then
    assert shift == 0.80  # 400/(100+400)


def test_coverage_retention_metric():
    """Test requirement coverage retained after migration."""
    # Given
    inventory = TeamInventory(
        team="API Team",
        total_tests=500,
        migrated_tests=400,
        baseline_requirements=100,
        qtest_requirements=85,
        as_of_date=date.today(),
    )

    # When
    metrics = calculate_adoption_metrics(inventory)

    # Then
    assert metrics.coverage_retained == 0.85  # 85/100


def test_defect_link_parity():
    """Test defect linking parity between systems."""
    # Given
    inventory = TeamInventory(
        team="QA Team",
        total_tests=200,
        migrated_tests=180,
        baseline_defect_links=50,
        qtest_defect_links=45,
        as_of_date=date.today(),
    )

    # When
    metrics = calculate_adoption_metrics(inventory)

    # Then
    assert metrics.defect_link_parity == 0.90  # 45/50


def test_cohort_segmentation():
    """Test cohort grouping and baselining."""
    # Given users with activity
    users = [
        User("alice@example.com", "Alice", executions=500, role="lead"),
        User("bob@example.com", "Bob", executions=50, role="tester"),
        User("charlie@example.com", "Charlie", executions=5, role="viewer"),
        User("david@example.com", "David", executions=200, role="tester"),
        User("eve@example.com", "Eve", executions=10, role="tester"),
    ]

    # When segmenting
    cohorts = segment_user_cohorts(users)

    # Then - with 5 users: top 2 (40%) are power, next 2 (40%) are regular, last 1 (20%) is long_tail
    assert "alice@example.com" in cohorts["power_users"]
    assert "david@example.com" in cohorts["power_users"]  # Top 40%
    assert "bob@example.com" in cohorts["regular"]  # Middle 40%
    assert "eve@example.com" in cohorts["regular"]  # Middle 40%
    assert "charlie@example.com" in cohorts["long_tail"]  # Bottom 20%


def test_team_adoption_aggregation():
    """Test aggregating adoption across teams."""
    # Given multiple team inventories
    inventories = [
        TeamInventory("Team A", total_tests=100, migrated_tests=90, as_of_date=date.today()),
        TeamInventory("Team B", total_tests=200, migrated_tests=100, as_of_date=date.today()),
        TeamInventory("Team C", total_tests=150, migrated_tests=75, as_of_date=date.today()),
    ]

    # When calculating org-level metrics
    org_metrics = calculate_org_adoption(inventories)

    # Then
    assert org_metrics.total_tests == 450
    assert org_metrics.total_migrated == 265
    assert org_metrics.overall_adoption_rate == pytest.approx(0.589, rel=0.01)  # 265/450
    assert len(org_metrics.team_metrics) == 3


def test_adoption_velocity():
    """Test calculating migration velocity over time."""
    # Given historical snapshots
    history = [
        DailySnapshot(date(2024, 1, 1), migrated=100, total=1000),
        DailySnapshot(date(2024, 1, 8), migrated=200, total=1000),
        DailySnapshot(date(2024, 1, 15), migrated=300, total=1000),
        DailySnapshot(date(2024, 1, 22), migrated=380, total=1000),
    ]

    # When calculating velocity
    velocity = calculate_adoption_velocity(history)

    # Then
    assert velocity.weekly_average == pytest.approx(93.33, rel=0.01)  # (380-100)/3 weeks
    assert velocity.current_week == 80  # Last week: 380-300
    assert velocity.trend == "slowing"  # 80 < 93.33


def test_plan_variance_calculation():
    """Test variance from migration plan."""
    # Given actual vs planned
    actual = AdoptionSnapshot(team="Frontend", date=date(2024, 2, 1), adoption_rate=0.60)

    plan = MigrationPlan(team="Frontend", target_date=date(2024, 2, 1), target_rate=0.70)

    # When calculating variance
    variance = calculate_plan_variance(actual, plan)

    # Then
    assert variance.percent_variance == pytest.approx(-14.3, rel=0.01)  # (0.60-0.70)/0.70 * 100
    assert variance.status == "behind"
    assert variance.days_off_track == pytest.approx(10, abs=2)  # Estimated


def test_cohort_adoption_comparison():
    """Test comparing adoption rates across cohorts."""
    # Given cohort metrics
    cohort_data = {
        "power_users": CohortMetrics(
            cohort_name="power_users",
            user_count=10,
            total_tests=500,
            migrated_tests=450,
            adoption_rate=0.90,
        ),
        "regular": CohortMetrics(
            cohort_name="regular",
            user_count=30,
            total_tests=800,
            migrated_tests=400,
            adoption_rate=0.50,
        ),
        "long_tail": CohortMetrics(
            cohort_name="long_tail",
            user_count=60,
            total_tests=200,
            migrated_tests=50,
            adoption_rate=0.25,
        ),
    }

    # When analyzing cohort performance
    analysis = analyze_cohort_adoption(cohort_data)

    # Then
    assert analysis.leader_cohort == "power_users"
    assert analysis.laggard_cohort == "long_tail"
    assert analysis.adoption_gap == 0.65  # 0.90 - 0.25
    assert "Focus training on long_tail users" in analysis.recommendation


# Implementation stubs (TDD - implement after tests)


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


@dataclass
class DailySnapshot:
    """Daily migration snapshot."""

    date: date
    migrated: int
    total: int


@dataclass
class AdoptionVelocity:
    """Migration velocity metrics."""

    weekly_average: float
    current_week: int
    trend: str  # accelerating, steady, slowing


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

    return AdoptionVelocity(weekly_average=weekly_avg, current_week=current_week, trend=trend)


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
