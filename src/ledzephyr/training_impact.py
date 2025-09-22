"""Training impact model with ROI tracking for migration acceleration."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum


class TrainingTopic(Enum):
    """Training session topics."""

    INTRO_QTEST = "Introduction to qTest"
    MIGRATION_BASICS = "Migration Basics"
    ADVANCED_FEATURES = "Advanced qTest Features"
    API_AUTOMATION = "API and Automation"
    REPORTING = "Reporting and Analytics"
    BEST_PRACTICES = "Best Practices"


@dataclass
class TeamSignals:
    """Signals for team training prioritization."""

    team: str
    unmigrated_tests: int
    recent_exec_freq: float  # 0-1 scale, executions in last 14 days
    blocked_ratio: float  # % of team blocked on migration
    has_champion: bool  # Has identified power user
    plan_variance: float  # Negative if behind plan
    recent_training_days_ago: int  # Days since last training
    team_size: int = 10
    avg_test_complexity: float = 1.0  # 1-5 scale


@dataclass
class TrainingWeights:
    """Weights for priority scoring."""

    w1_unmigrated: float = 0.25  # Unmigrated inventory weight
    w2_execution: float = 0.20  # Recent execution frequency weight
    w3_blocked: float = 0.15  # Blocked ratio weight
    w4_champion: float = 0.15  # Champion absence weight
    w5_variance: float = 0.20  # Plan variance weight
    w6_saturation: float = 0.05  # Training saturation weight


@dataclass
class TrainingEvent:
    """Record of a training session."""

    session_id: str
    team: str
    date: date
    attendees: list[str]
    topic: TrainingTopic
    duration_hours: float
    trainer: str | None = None
    feedback_score: float | None = None  # 1-5 scale


@dataclass
class TrainingRecommendation:
    """Training placement recommendation."""

    team: str
    priority_score: float
    recommended_date: date
    topic: TrainingTopic
    rationale: str
    expected_uplift: float  # Expected adoption rate increase


@dataclass
class TrainingUplift:
    """Measured uplift from training."""

    team: str
    training_date: date
    adoption_before: float
    adoption_after: float
    adoption_lift: float  # Actual increase
    execution_before: float
    execution_after: float
    execution_lift: float
    is_significant: bool  # Statistical significance
    control_lift: float | None = None  # Control group lift for comparison


@dataclass
class TrainerSchedule:
    """Weekly trainer schedule."""

    week_of: date
    capacity: int  # Number of sessions available
    assignments: list[TrainingRecommendation] = field(default_factory=list)
    utilization: float = 0.0  # % of capacity used


def calculate_priority_score(signals: TeamSignals, weights: TrainingWeights | None = None) -> float:
    """Calculate team priority score for training placement."""
    if weights is None:
        weights = TrainingWeights()

    # Normalize unmigrated tests (0-1 scale, capped at 1000)
    unmigrated_norm = min(1.0, signals.unmigrated_tests / 1000)

    # Training saturation (decreases score if recently trained)
    saturation = 1.0 / max(1, signals.recent_training_days_ago)

    # Calculate weighted score
    score = (
        weights.w1_unmigrated * unmigrated_norm
        + weights.w2_execution * signals.recent_exec_freq
        + weights.w3_blocked * signals.blocked_ratio
        + weights.w4_champion * (1.0 if not signals.has_champion else 0.0)
        + weights.w5_variance * abs(signals.plan_variance)
        - weights.w6_saturation * saturation
    )

    # Boost score for teams behind plan
    if signals.plan_variance < -0.1:  # More than 10% behind
        score *= 1.2

    # Normalize to 0-1 range
    return min(1.0, max(0.0, score))


def recommend_training_topic(signals: TeamSignals, history: list[TrainingEvent]) -> TrainingTopic:
    """Recommend appropriate training topic based on team signals."""
    # Check training history
    past_topics = [e.topic for e in history if e.team == signals.team]

    # New to qTest - start with basics
    if not past_topics:
        return TrainingTopic.INTRO_QTEST

    # Behind plan and low migration - need migration help
    if signals.plan_variance < -0.15 and signals.unmigrated_tests > 500:
        if TrainingTopic.MIGRATION_BASICS not in past_topics:
            return TrainingTopic.MIGRATION_BASICS

    # High complexity tests - need advanced features
    if signals.avg_test_complexity > 3.0:
        if TrainingTopic.ADVANCED_FEATURES not in past_topics:
            return TrainingTopic.ADVANCED_FEATURES

    # Active team but low adoption - need best practices
    if signals.recent_exec_freq > 0.7 and signals.unmigrated_tests > 200:
        return TrainingTopic.BEST_PRACTICES

    # Default to next logical progression
    progression = [
        TrainingTopic.INTRO_QTEST,
        TrainingTopic.MIGRATION_BASICS,
        TrainingTopic.ADVANCED_FEATURES,
        TrainingTopic.API_AUTOMATION,
        TrainingTopic.REPORTING,
        TrainingTopic.BEST_PRACTICES,
    ]

    for topic in progression:
        if topic not in past_topics:
            return topic

    # All topics covered - repeat best practices
    return TrainingTopic.BEST_PRACTICES


def generate_training_recommendations(
    team_signals: list[TeamSignals],
    capacity: int,
    week_of: date,
    weights: TrainingWeights | None = None,
    training_history: list[TrainingEvent] | None = None,
) -> list[TrainingRecommendation]:
    """Generate prioritized training recommendations for the week."""
    if training_history is None:
        training_history = []

    recommendations = []

    # Score all teams
    scored_teams = []
    for signals in team_signals:
        score = calculate_priority_score(signals, weights)
        topic = recommend_training_topic(signals, training_history)

        # Generate rationale
        rationale_parts = []
        if signals.unmigrated_tests > 500:
            rationale_parts.append(f"{signals.unmigrated_tests} unmigrated tests")
        if signals.plan_variance < -0.1:
            rationale_parts.append(f"{abs(signals.plan_variance)*100:.0f}% behind plan")
        if not signals.has_champion:
            rationale_parts.append("no champion identified")
        if signals.blocked_ratio > 0.3:
            rationale_parts.append(f"{signals.blocked_ratio*100:.0f}% blocked")

        rationale = (
            f"Priority factors: {', '.join(rationale_parts)}"
            if rationale_parts
            else "Regular training cycle"
        )

        # Estimate uplift based on historical data or defaults
        expected_uplift = estimate_training_uplift(signals, topic)

        scored_teams.append((signals, score, topic, rationale, expected_uplift))

    # Sort by score and select top teams within capacity
    scored_teams.sort(key=lambda x: x[1], reverse=True)

    for i, (signals, score, topic, rationale, uplift) in enumerate(scored_teams[:capacity]):
        # Schedule throughout the week
        training_date = week_of + timedelta(days=i % 5)  # Mon-Fri

        recommendations.append(
            TrainingRecommendation(
                team=signals.team,
                priority_score=score,
                recommended_date=training_date,
                topic=topic,
                rationale=rationale,
                expected_uplift=uplift,
            )
        )

    return recommendations


def estimate_training_uplift(signals: TeamSignals, topic: TrainingTopic) -> float:
    """Estimate expected uplift from training."""
    # Base uplift by topic
    base_uplift = {
        TrainingTopic.INTRO_QTEST: 0.15,
        TrainingTopic.MIGRATION_BASICS: 0.20,
        TrainingTopic.ADVANCED_FEATURES: 0.10,
        TrainingTopic.API_AUTOMATION: 0.12,
        TrainingTopic.REPORTING: 0.08,
        TrainingTopic.BEST_PRACTICES: 0.10,
    }

    uplift = base_uplift.get(topic, 0.10)

    # Adjust based on team characteristics
    if not signals.has_champion:
        uplift *= 1.2  # Higher impact when no champion

    if signals.blocked_ratio > 0.5:
        uplift *= 1.3  # Higher impact for heavily blocked teams

    if signals.recent_training_days_ago < 30:
        uplift *= 0.5  # Diminishing returns from recent training

    # Cap at reasonable maximum
    return min(0.30, uplift)


def measure_training_uplift(
    pre_metrics: dict[str, float],
    post_metrics: dict[str, float],
    control_metrics: dict[str, float] | None = None,
    measurement_days: int = 14,
) -> TrainingUplift:
    """Measure actual uplift from training intervention."""
    # Calculate raw lifts
    adoption_before = pre_metrics.get("adoption_rate", 0.0)
    adoption_after = post_metrics.get("adoption_rate", 0.0)
    adoption_lift = adoption_after - adoption_before

    execution_before = pre_metrics.get("execution_shift", 0.0)
    execution_after = post_metrics.get("execution_shift", 0.0)
    execution_lift = execution_after - execution_before

    # Adjust for control group if available (difference-in-differences)
    control_lift = None
    if control_metrics:
        control_before = control_metrics.get("adoption_rate_before", 0.0)
        control_after = control_metrics.get("adoption_rate_after", 0.0)
        control_lift = control_after - control_before
        adoption_lift -= control_lift  # Net lift after removing organic growth

    # Determine statistical significance (simplified)
    # In reality, would use proper statistical tests
    is_significant = adoption_lift > 0.05  # 5% threshold

    return TrainingUplift(
        team=pre_metrics.get("team", "unknown"),
        training_date=date.today(),  # Would pass actual date
        adoption_before=adoption_before,
        adoption_after=adoption_after,
        adoption_lift=adoption_lift,
        execution_before=execution_before,
        execution_after=execution_after,
        execution_lift=execution_lift,
        is_significant=is_significant,
        control_lift=control_lift,
    )


def optimize_trainer_schedule(
    teams: list[TeamSignals],
    trainer_capacity: dict[date, int],  # Available slots per day
    constraints: dict | None = None,
) -> TrainerSchedule:
    """Optimize trainer schedule for maximum impact."""
    if constraints is None:
        constraints = {}

    # Get week start
    week_start = next(iter(trainer_capacity.keys()))
    week_start = week_start - timedelta(days=week_start.weekday())  # Monday

    total_capacity = sum(trainer_capacity.values())

    # Generate recommendations
    recommendations = generate_training_recommendations(teams, total_capacity, week_start)

    # Create schedule
    schedule = TrainerSchedule(
        week_of=week_start,
        capacity=total_capacity,
        assignments=recommendations,
        utilization=len(recommendations) / total_capacity if total_capacity > 0 else 0,
    )

    return schedule


def calculate_training_roi(
    uplift: TrainingUplift,
    team_size: int,
    tests_per_person: int = 50,
    value_per_test: float = 10.0,
    training_cost: float = 500.0,
) -> dict[str, float]:
    """Calculate ROI of training intervention."""
    # Value generated
    tests_migrated = uplift.adoption_lift * team_size * tests_per_person
    value_generated = tests_migrated * value_per_test

    # ROI calculation
    roi = (value_generated - training_cost) / training_cost if training_cost > 0 else 0

    # Payback period (days)
    daily_value = value_generated / 14  # Assuming 14-day measurement
    payback_days = training_cost / daily_value if daily_value > 0 else 999

    return {
        "tests_migrated": tests_migrated,
        "value_generated": value_generated,
        "training_cost": training_cost,
        "roi_percent": roi * 100,
        "payback_days": payback_days,
    }
