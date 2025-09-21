"""Unit tests for domain models following AAA pattern."""

import pytest
from ledzephyr.models import ProjectMetrics, TrendData, TeamMetrics, TeamSource


@pytest.mark.unit
class TestProjectMetrics:
    """Test ProjectMetrics domain model."""

    def test_create_basic_project_metrics_valid_data_creates_instance(self, sample_project_metrics):
        """Test creating ProjectMetrics with valid data creates instance."""
        # Arrange & Act
        metrics = sample_project_metrics()

        # Assert
        assert metrics.project_key == "DEMO"
        assert metrics.time_window == "7d"
        assert metrics.total_tests == 100
        assert metrics.adoption_ratio == 0.4

    def test_adoption_ratio_calculation_zero_total_tests_returns_zero(self, sample_project_metrics):
        """Test adoption ratio calculation with zero total tests returns zero."""
        # Arrange & Act
        metrics = sample_project_metrics(
            total_tests=0,
            qtest_tests=0,
            zephyr_tests=0,
            adoption_ratio=0.0
        )

        # Assert
        assert metrics.adoption_ratio == 0.0

    def test_adoption_ratio_validation_exceeds_one_accepts_value(self, sample_project_metrics):
        """Test adoption ratio validation accepts values that exceed 1.0."""
        # Arrange & Act
        metrics = sample_project_metrics(adoption_ratio=1.5)

        # Assert
        assert metrics.adoption_ratio == 1.5

    def test_project_key_validation_empty_string_accepts_value(self, sample_project_metrics):
        """Test project key validation accepts empty string."""
        # Arrange & Act
        metrics = sample_project_metrics(project_key="")

        # Assert
        assert metrics.project_key == ""

    def test_test_counts_negative_values_accepts_values(self, sample_project_metrics):
        """Test test counts accept negative values (no validation)."""
        # Arrange & Act
        metrics = sample_project_metrics(
            total_tests=-5,
            qtest_tests=-2,
            zephyr_tests=-3
        )

        # Assert
        assert metrics.total_tests == -5
        assert metrics.qtest_tests == -2
        assert metrics.zephyr_tests == -3


@pytest.mark.unit
class TestTrendData:
    """Test TrendData domain model."""

    def test_create_trend_data_valid_data_creates_instance(self, sample_trend_data):
        """Test creating TrendData with valid data creates instance."""
        # Arrange & Act
        trend = sample_trend_data()

        # Assert
        assert "adoption_ratio" in trend.week_1
        assert "coverage_parity" in trend.week_1
        assert trend.adoption_trend == 0.07

    def test_empty_week_data_empty_dict_creates_instance(self, sample_trend_data):
        """Test creating TrendData with empty week data creates instance."""
        # Arrange & Act
        trend = sample_trend_data(
            week_1={},
            week_2={},
            week_3={},
            week_4={}
        )

        # Assert
        assert trend.week_1 == {}
        assert trend.week_2 == {}


@pytest.mark.unit
class TestTeamMetrics:
    """Test TeamMetrics domain model."""

    def test_create_team_metrics_valid_data_creates_instance(self, sample_team_metrics):
        """Test creating TeamMetrics with valid data creates instance."""
        # Arrange & Act
        team = sample_team_metrics()

        # Assert
        assert team.team_name == "Team Alpha"
        assert team.team_source == TeamSource.COMPONENT
        assert team.total_tests == 50

    def test_team_source_validation_valid_enum_accepts_value(self, sample_team_metrics):
        """Test team source validation accepts valid enum values."""
        # Arrange & Act
        team = sample_team_metrics(team_source=TeamSource.LABEL)

        # Assert
        assert team.team_source == TeamSource.LABEL

    def test_adoption_ratio_calculation_zero_total_accepts_value(self, sample_team_metrics):
        """Test adoption ratio calculation with zero total accepts value."""
        # Arrange & Act
        team = sample_team_metrics(
            total_tests=0,
            qtest_tests=0,
            adoption_ratio=0.0
        )

        # Assert
        assert team.adoption_ratio == 0.0


@pytest.mark.unit
class TestTeamSource:
    """Test TeamSource enum."""

    def test_team_source_values_component_has_correct_value(self):
        """Test TeamSource enum has correct component value."""
        # Arrange & Act & Assert
        assert TeamSource.COMPONENT == "component"

    def test_team_source_values_label_has_correct_value(self):
        """Test TeamSource enum has correct label value."""
        # Arrange & Act & Assert
        assert TeamSource.LABEL == "label"

    def test_team_source_values_group_has_correct_value(self):
        """Test TeamSource enum has correct group value."""
        # Arrange & Act & Assert
        assert TeamSource.GROUP == "group"