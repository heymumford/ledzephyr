"""Daily adoption and training target report generator."""

import json
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .adoption_metrics import (
    DailySnapshot,
    TeamInventory,
    User,
    calculate_adoption_metrics,
    calculate_adoption_velocity,
    calculate_org_adoption,
    segment_user_cohorts,
)
from .identity_resolution import CrosswalkMap
from .training_impact import (
    TeamSignals,
    TrainingEvent,
    generate_training_recommendations,
)


@dataclass
class AdoptionReport:
    """Daily adoption and training report."""

    report_date: date
    org_metrics: dict[str, Any]
    team_metrics: list[dict[str, Any]]
    cohort_analysis: dict[str, Any]
    velocity_metrics: dict[str, Any]
    training_recommendations: list[dict[str, Any]]
    completion_prediction: dict[str, Any]


class AdoptionReportGenerator:
    """Generates daily adoption and training reports."""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.crosswalk = CrosswalkMap()

    def generate_daily_report(
        self,
        inventories: list[TeamInventory],
        users: list[User],
        history: list[DailySnapshot],
        training_history: list[TrainingEvent] | None = None,
    ) -> AdoptionReport:
        """Generate comprehensive daily adoption report."""

        # 1. Organization-level metrics
        org_metrics = self._calculate_org_metrics(inventories)

        # 2. Team-level metrics
        team_metrics = self._calculate_team_metrics(inventories)

        # 3. Cohort analysis
        cohort_analysis = self._analyze_cohorts(users, inventories)

        # 4. Velocity and trends
        velocity_metrics = self._calculate_velocity(history)

        # 5. Training recommendations
        training_recs = self._generate_training_recommendations(inventories, training_history)

        # 6. Completion prediction
        completion = self._predict_completion(history, velocity_metrics)

        report = AdoptionReport(
            report_date=date.today(),
            org_metrics=org_metrics,
            team_metrics=team_metrics,
            cohort_analysis=cohort_analysis,
            velocity_metrics=velocity_metrics,
            training_recommendations=training_recs,
            completion_prediction=completion,
        )

        return report

    def _calculate_org_metrics(self, inventories: list[TeamInventory]) -> dict[str, Any]:
        """Calculate organization-wide metrics."""
        org = calculate_org_adoption(inventories)

        return {
            "total_tests": org.total_tests,
            "migrated_tests": org.total_migrated,
            "adoption_rate": round(org.overall_adoption_rate * 100, 1),
            "remaining_tests": org.total_tests - org.total_migrated,
            "teams_reporting": len(inventories),
        }

    def _calculate_team_metrics(self, inventories: list[TeamInventory]) -> list[dict[str, Any]]:
        """Calculate metrics for each team."""
        team_data = []

        for inv in inventories:
            metrics = calculate_adoption_metrics(inv)

            team_data.append(
                {
                    "team": inv.team,
                    "adoption_rate": round(metrics.adoption_rate * 100, 1),
                    "migrated_tests": inv.migrated_tests,
                    "total_tests": inv.total_tests,
                    "execution_shift": round(metrics.execution_shift * 100, 1),
                    "coverage_retained": round(metrics.coverage_retained * 100, 1),
                    "status": self._determine_status(metrics.adoption_rate),
                }
            )

        # Sort by adoption rate
        team_data.sort(key=lambda x: x["adoption_rate"], reverse=True)

        return team_data

    def _analyze_cohorts(
        self, users: list[User], inventories: list[TeamInventory]
    ) -> dict[str, Any]:
        """Analyze adoption by user cohort."""
        cohorts = segment_user_cohorts(users)

        # Calculate cohort metrics
        cohort_metrics = {}
        for cohort_name, cohort_users in cohorts.items():
            # Get tests owned by cohort
            cohort_total = 0
            cohort_migrated = 0

            # Simplified - in reality would join with test ownership data
            if cohort_name == "power_users":
                cohort_total = sum(inv.total_tests * 0.5 for inv in inventories)
                cohort_migrated = sum(inv.migrated_tests * 0.6 for inv in inventories)
            elif cohort_name == "regular":
                cohort_total = sum(inv.total_tests * 0.35 for inv in inventories)
                cohort_migrated = sum(inv.migrated_tests * 0.3 for inv in inventories)
            else:  # long_tail
                cohort_total = sum(inv.total_tests * 0.15 for inv in inventories)
                cohort_migrated = sum(inv.migrated_tests * 0.1 for inv in inventories)

            cohort_metrics[cohort_name] = {
                "user_count": len(cohort_users),
                "total_tests": int(cohort_total),
                "migrated_tests": int(cohort_migrated),
                "adoption_rate": round(
                    (cohort_migrated / cohort_total * 100) if cohort_total > 0 else 0, 1
                ),
            }

        return cohort_metrics

    def _calculate_velocity(self, history: list[DailySnapshot]) -> dict[str, Any]:
        """Calculate migration velocity metrics."""
        if len(history) < 2:
            return {"weekly_average": 0, "current_week": 0, "trend": "unknown", "acceleration": 0}

        velocity = calculate_adoption_velocity(history)

        return {
            "weekly_average": round(velocity.weekly_average, 0),
            "current_week": velocity.current_week,
            "trend": velocity.trend,
            "acceleration": round(
                (
                    (velocity.current_week - velocity.weekly_average)
                    / velocity.weekly_average
                    * 100
                    if velocity.weekly_average > 0
                    else 0
                ),
                1,
            ),
        }

    def _generate_training_recommendations(
        self,
        inventories: list[TeamInventory],
        training_history: list[TrainingEvent] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate training placement recommendations."""
        # Convert inventories to team signals
        team_signals = []
        for inv in inventories:
            # Calculate signals from inventory
            recent_exec_freq = min(1.0, (inv.zephyr_executions + inv.qtest_executions) / 1000)
            blocked_ratio = 0.3 if inv.migrated_tests < inv.total_tests * 0.3 else 0.1

            signals = TeamSignals(
                team=inv.team,
                unmigrated_tests=inv.total_tests - inv.migrated_tests,
                recent_exec_freq=recent_exec_freq,
                blocked_ratio=blocked_ratio,
                has_champion=False,  # Would determine from user data
                plan_variance=-0.1 if inv.migrated_tests < inv.total_tests * 0.5 else 0.1,
                recent_training_days_ago=30,  # Default
            )
            team_signals.append(signals)

        # Generate recommendations
        recommendations = generate_training_recommendations(
            team_signals,
            capacity=5,  # Top 5 teams
            week_of=date.today(),
            training_history=training_history,
        )

        # Convert to dict format
        rec_data = []
        for rec in recommendations:
            rec_data.append(
                {
                    "team": rec.team,
                    "priority_score": round(rec.priority_score, 2),
                    "recommended_date": rec.recommended_date.isoformat(),
                    "topic": rec.topic.value,
                    "rationale": rec.rationale,
                    "expected_uplift": round(rec.expected_uplift * 100, 1),
                }
            )

        return rec_data

    def _predict_completion(
        self, history: list[DailySnapshot], velocity: dict[str, Any]
    ) -> dict[str, Any]:
        """Predict migration completion date."""
        if not history or velocity["weekly_average"] <= 0:
            return {"estimated_date": "Unknown", "weeks_remaining": "Unknown", "confidence": "Low"}

        last = history[-1]
        remaining = last.total - last.migrated
        weeks_to_complete = remaining / velocity["weekly_average"]

        estimated_date = date.today() + timedelta(weeks=weeks_to_complete)

        # Determine confidence based on trend
        confidence = "Medium"
        if velocity["trend"] == "steady":
            confidence = "High"
        elif velocity["trend"] == "slowing":
            confidence = "Low"

        return {
            "estimated_date": estimated_date.isoformat(),
            "weeks_remaining": round(weeks_to_complete, 1),
            "confidence": confidence,
            "tests_remaining": remaining,
        }

    def _determine_status(self, adoption_rate: float) -> str:
        """Determine team status based on adoption rate."""
        if adoption_rate >= 0.8:
            return "✅ Complete"
        elif adoption_rate >= 0.5:
            return "🟡 In Progress"
        elif adoption_rate >= 0.2:
            return "🟠 Started"
        else:
            return "🔴 Not Started"

    def save_report(self, report: AdoptionReport, format: str = "json"):
        """Save report to file."""
        filename = f"adoption_report_{report.report_date.isoformat()}.{format}"
        filepath = self.output_dir / filename

        if format == "json":
            with open(filepath, "w") as f:
                json.dump(asdict(report), f, indent=2, default=str)
        elif format == "markdown":
            self._save_markdown_report(report, filepath)

        return filepath

    def _save_markdown_report(self, report: AdoptionReport, filepath: Path):
        """Save report in markdown format."""
        lines = []

        lines.append("# Adoption & Training Target Report")
        lines.append(f"**Date**: {report.report_date}")
        lines.append("")

        # Organization metrics
        lines.append("## Organization Overview")
        org = report.org_metrics
        lines.append(f"- **Overall Adoption**: {org['adoption_rate']}%")
        lines.append(f"- **Tests Migrated**: {org['migrated_tests']:,} / {org['total_tests']:,}")
        lines.append(f"- **Teams Reporting**: {org['teams_reporting']}")
        lines.append("")

        # Velocity
        lines.append("## Migration Velocity")
        vel = report.velocity_metrics
        lines.append(f"- **Weekly Average**: {vel['weekly_average']} tests/week")
        lines.append(f"- **Current Week**: {vel['current_week']} tests")
        lines.append(f"- **Trend**: {vel['trend']} ({vel['acceleration']:+.1f}%)")
        lines.append("")

        # Completion prediction
        lines.append("## Completion Prediction")
        comp = report.completion_prediction
        lines.append(f"- **Estimated Date**: {comp['estimated_date']}")
        lines.append(f"- **Weeks Remaining**: {comp['weeks_remaining']}")
        lines.append(f"- **Confidence**: {comp['confidence']}")
        lines.append("")

        # Team metrics table
        lines.append("## Team Adoption Status")
        lines.append("| Team | Adoption | Migrated | Total | Status |")
        lines.append("|------|----------|----------|-------|--------|")
        for team in report.team_metrics[:10]:  # Top 10
            lines.append(
                f"| {team['team']} | {team['adoption_rate']}% | "
                f"{team['migrated_tests']} | {team['total_tests']} | {team['status']} |"
            )
        lines.append("")

        # Cohort analysis
        lines.append("## Cohort Analysis")
        lines.append("| Cohort | Users | Adoption | Tests |")
        lines.append("|--------|-------|----------|-------|")
        for cohort_name, metrics in report.cohort_analysis.items():
            lines.append(
                f"| {cohort_name} | {metrics['user_count']} | "
                f"{metrics['adoption_rate']}% | {metrics['total_tests']} |"
            )
        lines.append("")

        # Training recommendations
        lines.append("## Training Recommendations (Next 2 Weeks)")
        for i, rec in enumerate(report.training_recommendations, 1):
            lines.append(f"### {i}. {rec['team']} (Priority: {rec['priority_score']:.2f})")
            lines.append(f"- **Date**: {rec['recommended_date']}")
            lines.append(f"- **Topic**: {rec['topic']}")
            lines.append(f"- **Expected Uplift**: {rec['expected_uplift']}%")
            lines.append(f"- **Rationale**: {rec['rationale']}")
            lines.append("")

        with open(filepath, "w") as f:
            f.write("\n".join(lines))
