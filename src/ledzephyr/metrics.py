"""Metrics calculation and analysis."""

import logging
from datetime import datetime, timedelta

from ledzephyr.client import APIClient
from ledzephyr.models import ProjectMetrics, TeamMetrics, TeamSource, TestCaseModel, TrendData

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate migration metrics for projects and teams."""

    def __init__(self, client: APIClient = None):
        self.client = client

    def calculate_metrics(
        self, project_key: str, time_window: str, teams_source: TeamSource = TeamSource.COMPONENT
    ) -> ProjectMetrics:
        """Calculate comprehensive metrics for a project."""
        logger.info(f"Calculating metrics for {project_key} over {time_window}")

        # Parse time window
        end_date = datetime.now()
        start_date = self._parse_time_window(time_window, end_date)

        # Get project information
        _project = self.client.get_jira_project(project_key)

        # Get test cases from both systems
        zephyr_tests = self.client.get_zephyr_tests(project_key, start_date, end_date)
        qtest_tests = self.client.get_qtest_tests(project_key, start_date, end_date)

        # Combine all tests
        all_tests = zephyr_tests + qtest_tests

        # Get execution data
        zephyr_test_ids = [test.id for test in zephyr_tests]
        qtest_test_ids = [test.id for test in qtest_tests]

        zephyr_executions = self.client.get_test_executions(project_key, zephyr_test_ids, "zephyr")
        qtest_executions = self.client.get_test_executions(project_key, qtest_test_ids, "qtest")

        # Update test cases with execution data
        self._update_tests_with_executions(zephyr_tests, zephyr_executions)
        self._update_tests_with_executions(qtest_tests, qtest_executions)

        # Calculate basic metrics
        total_tests = len(all_tests)
        zephyr_count = len(zephyr_tests)
        qtest_count = len(qtest_tests)

        adoption_ratio = qtest_count / total_tests if total_tests > 0 else 0.0
        coverage_parity = self._calculate_coverage_parity(zephyr_tests, qtest_tests)
        defect_link_rate = self._calculate_defect_link_rate(all_tests)
        active_users = self._count_active_users(all_tests)

        # Calculate team metrics
        team_metrics = self._calculate_team_metrics(
            all_tests, teams_source, zephyr_tests, qtest_tests
        )

        # Calculate 4-week trend (if enough data)
        trend_data = self._calculate_trend_data(project_key, teams_source, end_date)

        return ProjectMetrics(
            project_key=project_key,
            time_window=time_window,
            total_tests=total_tests,
            zephyr_tests=zephyr_count,
            qtest_tests=qtest_count,
            adoption_ratio=adoption_ratio,
            coverage_parity=coverage_parity,
            defect_link_rate=defect_link_rate,
            active_users=active_users,
            team_metrics=team_metrics,
            trend_data=trend_data,
        )

    def calculate_project_metrics(
        self,
        test_cases: list[TestCaseModel],
        project_key: str,
        time_window: str,
        teams_source: TeamSource = TeamSource.COMPONENT,
    ) -> ProjectMetrics:
        """Calculate metrics directly from test cases (for testing purposes)."""

        # Separate tests by source system
        zephyr_tests = [t for t in test_cases if t.source_system == "zephyr"]
        qtest_tests = [t for t in test_cases if t.source_system == "qtest"]

        # Calculate basic metrics
        total_tests = len(test_cases)
        zephyr_count = len(zephyr_tests)
        qtest_count = len(qtest_tests)

        # Calculate adoption ratio (qtest / total, but 0 if no tests)
        adoption_ratio = qtest_count / total_tests if total_tests > 0 else 0.0

        # Calculate coverage parity
        coverage_parity = self._calculate_coverage_parity(zephyr_tests, qtest_tests)

        # Calculate defect link rate
        defect_link_rate = self._calculate_defect_link_rate(test_cases)

        # Calculate active users (unique assignees)
        active_users = len(set(t.assignee for t in test_cases if t.assignee))

        # Calculate team metrics
        team_metrics = self._calculate_team_metrics(
            test_cases, teams_source, zephyr_tests, qtest_tests
        )

        return ProjectMetrics(
            project_key=project_key,
            time_window=time_window,
            total_tests=total_tests,
            zephyr_tests=zephyr_count,
            qtest_tests=qtest_count,
            adoption_ratio=adoption_ratio,
            coverage_parity=coverage_parity,
            defect_link_rate=defect_link_rate,
            active_users=active_users,
            team_metrics=team_metrics,
            trend_data=None,  # Not calculated for direct method
        )

    def _parse_time_window(self, time_window: str, end_date: datetime) -> datetime:
        """Parse time window string into start date."""
        window = time_window.lower()

        try:
            if window.endswith("h"):
                hours = int(window[:-1])
                return end_date - timedelta(hours=hours)
            elif window.endswith("d"):
                days = int(window[:-1])
                return end_date - timedelta(days=days)
            elif window.endswith("w"):
                weeks = int(window[:-1])
                return end_date - timedelta(weeks=weeks)
            else:
                # Try to parse as plain number (days)
                days = int(window)
                return end_date - timedelta(days=days)
        except (ValueError, TypeError):
            logger.warning(f"Invalid time window: {window}, defaulting to 7 days")
            return end_date - timedelta(days=7)

    def _update_tests_with_executions(
        self, tests: list[TestCaseModel], executions: dict[str, dict]
    ) -> None:
        """Update test cases with execution data."""
        for test in tests:
            execution_data = executions.get(test.id, {})

            if execution_data.get("last_execution"):
                try:
                    test.last_execution = datetime.fromisoformat(
                        execution_data["last_execution"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            test.execution_status = execution_data.get("status")
            test.linked_defects = execution_data.get("linked_defects", [])

    def _calculate_coverage_parity(
        self, zephyr_tests: list[TestCaseModel], qtest_tests: list[TestCaseModel]
    ) -> float:
        """Calculate coverage parity between Zephyr and qTest."""
        if not zephyr_tests:
            return 1.0 if qtest_tests else 0.0

        # Simple implementation: compare test execution rates
        zephyr_executed = sum(1 for test in zephyr_tests if test.last_execution)
        qtest_executed = sum(1 for test in qtest_tests if test.last_execution)

        zephyr_exec_rate = zephyr_executed / len(zephyr_tests) if zephyr_tests else 0
        qtest_exec_rate = qtest_executed / len(qtest_tests) if qtest_tests else 0

        # Parity is how close qTest execution rate is to Zephyr
        if zephyr_exec_rate == 0:
            return 1.0 if qtest_exec_rate == 0 else 0.0

        return min(qtest_exec_rate / zephyr_exec_rate, 1.0)

    def _calculate_defect_link_rate(self, tests: list[TestCaseModel]) -> float:
        """Calculate the rate of tests with linked defects."""
        if not tests:
            return 0.0

        linked_tests = sum(1 for test in tests if test.linked_defects)
        return linked_tests / len(tests)

    def _count_active_users(self, tests: list[TestCaseModel]) -> int:
        """Count unique active users (based on assignees and recent updates)."""
        active_users = set()

        for test in tests:
            # User is active if they have tests assigned
            if test.assignee:
                active_users.add(test.assignee)

        return len(active_users)

    def _calculate_team_metrics(
        self,
        all_tests: list[TestCaseModel],
        teams_source: TeamSource,
        zephyr_tests: list[TestCaseModel],
        qtest_tests: list[TestCaseModel],
    ) -> dict[str, TeamMetrics]:
        """Calculate metrics broken down by team."""
        teams: dict[str, list[TestCaseModel]] = {}

        # Group tests by team
        for test in all_tests:
            team_name = self._get_team_name(test, teams_source)
            if not team_name:
                team_name = "Unassigned"

            if team_name not in teams:
                teams[team_name] = []
            teams[team_name].append(test)

        # Calculate metrics for each team
        team_metrics = {}
        for team_name, team_tests in teams.items():
            team_zephyr = [t for t in team_tests if t.source_system == "zephyr"]
            team_qtest = [t for t in team_tests if t.source_system == "qtest"]

            total_team_tests = len(team_tests)
            adoption_ratio = len(team_qtest) / total_team_tests if total_team_tests > 0 else 0.0

            team_metrics[team_name] = TeamMetrics(
                team_name=team_name,
                team_source=teams_source,
                total_tests=total_team_tests,
                zephyr_tests=len(team_zephyr),
                qtest_tests=len(team_qtest),
                adoption_ratio=adoption_ratio,
                coverage_parity=self._calculate_coverage_parity(team_zephyr, team_qtest),
                defect_link_rate=self._calculate_defect_link_rate(team_tests),
                active_users=self._count_active_users(team_tests),
            )

        return team_metrics

    def _get_team_name(self, test: TestCaseModel, teams_source: TeamSource) -> str:
        """Get team name based on the specified source."""
        if teams_source == TeamSource.COMPONENT:
            return test.component or ""
        elif teams_source == TeamSource.LABEL:
            # Use first label as team, or return empty string
            return test.labels[0] if test.labels else ""
        elif teams_source == TeamSource.GROUP:
            # For group, use assignee as a proxy (would need more sophisticated logic)
            return test.assignee or ""
        else:
            return ""

    def _calculate_trend_data(
        self, project_key: str, teams_source: TeamSource, end_date: datetime
    ) -> TrendData:
        """Calculate 4-week trend data."""
        trend_data = TrendData(
            adoption_trend=0.0,
            coverage_trend=0.0,
            activity_trend=0.0,
        )

        # Calculate metrics for each of the past 4 weeks
        for week in range(1, 5):
            week_end = end_date - timedelta(weeks=week - 1)
            week_start = week_end - timedelta(weeks=1)

            try:
                # Get tests for this week
                zephyr_tests = self.client.get_zephyr_tests(project_key, week_start, week_end)
                qtest_tests = self.client.get_qtest_tests(project_key, week_start, week_end)

                all_tests = zephyr_tests + qtest_tests
                total = len(all_tests)

                if total > 0:
                    adoption = len(qtest_tests) / total
                    coverage = self._calculate_coverage_parity(zephyr_tests, qtest_tests)
                    activity = self._count_active_users(all_tests)

                    week_data = {
                        "adoption_ratio": adoption,
                        "coverage_parity": coverage,
                        "active_users": activity,
                        "total_tests": total,
                    }

                    setattr(trend_data, f"week_{week}", week_data)

            except Exception as e:
                logger.debug(f"Could not calculate trend for week {week}: {e}")

        # Calculate trend indicators
        if trend_data.week_1 and trend_data.week_4:
            trend_data.adoption_trend = trend_data.week_1.get(
                "adoption_ratio", 0
            ) - trend_data.week_4.get("adoption_ratio", 0)
            trend_data.coverage_trend = trend_data.week_1.get(
                "coverage_parity", 0
            ) - trend_data.week_4.get("coverage_parity", 0)
            trend_data.activity_trend = trend_data.week_1.get(
                "active_users", 0
            ) - trend_data.week_4.get("active_users", 0)

        return trend_data
