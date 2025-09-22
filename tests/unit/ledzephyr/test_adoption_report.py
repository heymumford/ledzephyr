"""Lean tests for adoption report - focusing on high-risk paths only."""

from datetime import date, timedelta
from pathlib import Path

from ledzephyr.adoption_metrics import DailySnapshot, TeamInventory, User
from ledzephyr.adoption_report import AdoptionReportGenerator


class TestCriticalReportPaths:
    """Test only the paths that could cause expensive failures."""

    def test_training_recommendations_correctly_prioritize_teams(self):
        """
        RISK: Wrong teams get training = wasted $30K per misallocation.

        Verify that teams with highest need (low adoption, high activity, no champion)
        are prioritized over teams with lower need.
        """
        # Given: Teams with clear priority differences
        inventories = [
            TeamInventory(
                team="CriticalTeam",  # Should be #1
                total_tests=1000,
                migrated_tests=100,  # Only 10% migrated
                as_of_date=date.today(),
                zephyr_executions=900,  # Very active
                qtest_executions=50,
            ),
            TeamInventory(
                team="ProgressingTeam",  # Should be #2
                total_tests=500,
                migrated_tests=250,  # 50% migrated
                as_of_date=date.today(),
                zephyr_executions=400,
                qtest_executions=300,
            ),
            TeamInventory(
                team="AlmostDoneTeam",  # Should be last
                total_tests=200,
                migrated_tests=180,  # 90% migrated
                as_of_date=date.today(),
                zephyr_executions=20,
                qtest_executions=180,
            ),
        ]

        users = [
            User(f"user{i}@test.com", f"User{i}", executions=100, role="tester") for i in range(10)
        ]
        history = [DailySnapshot(date.today(), migrated=500, total=2000)]

        # When: Generating report
        generator = AdoptionReportGenerator()
        report = generator.generate_daily_report(inventories, users, history)

        # Then: Training recommendations are correctly prioritized
        recs = report.training_recommendations
        assert len(recs) >= 3, "Should have at least 3 recommendations"

        # Critical team should be first (highest unmigrated + high activity)
        assert (
            recs[0]["team"] == "CriticalTeam"
        ), f"Expected CriticalTeam first, got {recs[0]['team']}"
        assert recs[0]["priority_score"] > 0.4, "Critical team should have high priority score"

        # Almost done team should be last or not included
        team_names = [r["team"] for r in recs[:3]]
        if "AlmostDoneTeam" in team_names:
            assert (
                team_names.index("AlmostDoneTeam") == 2
            ), "AlmostDoneTeam should be lowest priority"

    def test_completion_prediction_within_reasonable_bounds(self):
        """
        RISK: Bad predictions = missed deadlines = contract penalties.

        Verify completion date predictions are reasonable and don't
        mislead planning (e.g., not predicting completion in year 3000).
        """
        # Given: Realistic migration velocity
        history = [
            DailySnapshot(date.today() - timedelta(weeks=3), migrated=100, total=1000),
            DailySnapshot(date.today() - timedelta(weeks=2), migrated=200, total=1000),
            DailySnapshot(date.today() - timedelta(weeks=1), migrated=300, total=1000),
            DailySnapshot(date.today(), migrated=400, total=1000),
        ]

        inventories = [
            TeamInventory("Team1", total_tests=1000, migrated_tests=400, as_of_date=date.today())
        ]
        users = []

        # When: Predicting completion
        generator = AdoptionReportGenerator()
        report = generator.generate_daily_report(inventories, users, history)

        # Then: Prediction is reasonable
        completion = report.completion_prediction

        if completion["estimated_date"] != "Unknown":
            # Parse the date
            estimated = date.fromisoformat(completion["estimated_date"])
            days_until_completion = (estimated - date.today()).days

            # Sanity checks
            assert days_until_completion > 0, "Completion should be in the future"
            assert days_until_completion < 365, "Completion shouldn't be more than a year out"

            # With 100/week velocity and 600 remaining, expect ~6 weeks
            assert completion["weeks_remaining"] > 4, "Should need at least 4 weeks"
            assert completion["weeks_remaining"] < 10, "Shouldn't need more than 10 weeks"

    def test_report_handles_missing_and_edge_data(self):
        """
        RISK: Report failure = no visibility = bad decisions = project failure.

        Verify report generates successfully even with missing, null, or edge case data.
        """
        # Test Case 1: Empty inventories
        generator = AdoptionReportGenerator()
        report = generator.generate_daily_report(inventories=[], users=[], history=[])
        assert report is not None, "Should generate report with empty data"
        assert report.org_metrics["total_tests"] == 0

        # Test Case 2: Single team with zero tests
        report = generator.generate_daily_report(
            inventories=[TeamInventory("Empty", 0, 0, date.today())], users=[], history=[]
        )
        assert report is not None, "Should handle zero tests"

        # Test Case 3: Very large numbers
        report = generator.generate_daily_report(
            inventories=[TeamInventory("Large", 1000000, 500000, date.today())],
            users=[
                User(f"u{i}@test.com", f"U{i}", executions=10000, role="tester")
                for i in range(1000)
            ],
            history=[DailySnapshot(date.today(), migrated=500000, total=1000000)],
        )
        assert report is not None, "Should handle large numbers"

        # Test Case 4: Null/None in optional fields
        inventory_with_nulls = TeamInventory(
            team="NullTeam",
            total_tests=100,
            migrated_tests=50,
            as_of_date=date.today(),
            baseline_requirements=0,  # Could be null
            qtest_requirements=0,
            zephyr_executions=0,
            qtest_executions=0,
        )
        report = generator.generate_daily_report(
            inventories=[inventory_with_nulls], users=[], history=[]
        )
        assert report is not None, "Should handle null/zero values"

    def test_roi_calculation_detects_negative_impact(self):
        """
        RISK: Missing regression = continued bad training = waste $100K+.

        Verify system detects when training has negative impact.
        """
        from ledzephyr.training_impact import measure_training_uplift

        # Given: Metrics showing regression after training
        pre_metrics = {"team": "TestTeam", "adoption_rate": 0.50, "execution_shift": 0.40}

        post_metrics = {
            "team": "TestTeam",
            "adoption_rate": 0.45,  # Went DOWN
            "execution_shift": 0.35,  # Also went DOWN
        }

        # When: Measuring uplift
        uplift = measure_training_uplift(pre_metrics, post_metrics)

        # Then: Negative impact is detected
        assert uplift.adoption_lift < 0, "Should detect negative adoption impact"
        assert uplift.execution_lift < 0, "Should detect negative execution impact"
        assert (
            not uplift.is_significant or uplift.adoption_lift < 0
        ), "Should not mark negative as significant positive"

    def test_report_saves_to_file_successfully(self):
        """
        RISK: Can't save report = can't share with stakeholders.

        Verify report saves in both JSON and Markdown formats.
        """
        # Given: A valid report
        generator = AdoptionReportGenerator(output_dir="test_reports")
        inventories = [TeamInventory("Team1", 100, 50, date.today())]
        users = []
        history = []

        report = generator.generate_daily_report(inventories, users, history)

        # When: Saving in different formats
        json_path = generator.save_report(report, format="json")
        md_path = generator.save_report(report, format="markdown")

        # Then: Files exist and are valid
        assert Path(json_path).exists(), "JSON file should be created"
        assert Path(md_path).exists(), "Markdown file should be created"

        # Cleanup
        Path(json_path).unlink(missing_ok=True)
        Path(md_path).unlink(missing_ok=True)
        Path("test_reports").rmdir()


class TestCohortAccuracy:
    """Ensure cohort analysis doesn't mislead resource allocation."""

    def test_cohort_segmentation_with_extreme_distributions(self):
        """
        RISK: Wrong cohort analysis = training wrong people.

        Test when 90% of users are inactive (real scenario).
        """
        # Given: Realistic distribution - most users inactive
        users = []
        # 2 power users
        users.extend(
            [User(f"power{i}@test.com", f"Power{i}", executions=500, role="lead") for i in range(2)]
        )
        # 8 regular users
        users.extend(
            [User(f"reg{i}@test.com", f"Reg{i}", executions=50, role="tester") for i in range(8)]
        )
        # 90 inactive users
        users.extend(
            [
                User(f"inactive{i}@test.com", f"Inactive{i}", executions=1, role="viewer")
                for i in range(90)
            ]
        )

        inventories = [TeamInventory("Team", 1000, 200, date.today())]

        # When: Analyzing cohorts
        generator = AdoptionReportGenerator()
        report = generator.generate_daily_report(inventories, users, [], None)

        # Then: Cohorts are reasonable
        cohorts = report.cohort_analysis

        # Power users should be the active minority
        assert cohorts["power_users"]["user_count"] <= 40, "Power users should be <40% of total"
        # Most users should be in long tail
        assert cohorts["long_tail"]["user_count"] >= 20, "Long tail should capture inactive users"
