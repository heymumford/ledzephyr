"""Unit tests for exporters module following TDD methodology."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from ledzephyr.exporters import DataExporter, ExcelExporter, HTMLExporter, PDFExporter
from ledzephyr.models import TeamMetrics, TeamSource


@pytest.fixture
def sample_team_metrics():
    """Provide sample team metrics for testing."""

    def _create_team(**overrides):
        defaults = {
            "team_name": "Team Alpha",
            "team_source": TeamSource.COMPONENT,
            "total_tests": 50,
            "zephyr_tests": 25,
            "qtest_tests": 25,
            "adoption_ratio": 0.5,
            "active_users": 5,
            "coverage_parity": 0.8,
            "defect_link_rate": 0.2,
        }
        defaults.update(overrides)
        return TeamMetrics(**defaults)

    return _create_team


@pytest.fixture
def sample_project_metrics_for_export(sample_team_metrics):
    """Provide sample project metrics specifically for export testing."""

    def _create_project(**overrides):
        # Create a mock object that has the properties the exporters expect
        mock_metrics = Mock()

        # Set default attributes
        mock_metrics.project_key = overrides.get("project_key", "EXPORT")
        mock_metrics.time_window = overrides.get("time_window", "7d")
        mock_metrics.total_tests = overrides.get("total_tests", 100)
        mock_metrics.zephyr_tests = overrides.get("zephyr_tests", 60)
        mock_metrics.qtest_tests = overrides.get("qtest_tests", 40)
        mock_metrics.adoption_ratio = overrides.get("adoption_ratio", 0.6)
        mock_metrics.active_users = overrides.get("active_users", 10)
        mock_metrics.coverage_parity = overrides.get("coverage_parity", 0.85)
        mock_metrics.defect_link_rate = overrides.get("defect_link_rate", 0.15)

        # Add teams that exporters expect
        mock_metrics.teams = [
            sample_team_metrics(),
            sample_team_metrics(team_name="Team Beta", zephyr_tests=35, qtest_tests=15),
        ]

        return mock_metrics

    return _create_project


@pytest.fixture
def sample_metrics_data(sample_project_metrics_for_export):
    """Provide sample metrics data dictionary for testing exports."""
    return {
        "7d": sample_project_metrics_for_export(),
        "30d": sample_project_metrics_for_export(
            time_window="30d",
            total_tests=200,
            zephyr_tests=120,
            qtest_tests=80,
            adoption_ratio=0.65,
        ),
    }


@pytest.fixture
def temp_output_path():
    """Provide temporary output path for file operations."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        yield Path(tmp.name)
    # Cleanup
    Path(tmp.name).unlink(missing_ok=True)


@pytest.mark.unit
@pytest.mark.exporters
class TestExcelExporter:
    """Test ExcelExporter class following TDD."""

    def test_init_creates_workbook_none_initially(self):
        """Test ExcelExporter initialization sets workbook to None initially."""
        # Arrange & Act
        exporter = ExcelExporter()

        # Assert
        assert exporter.workbook is None
        assert exporter.styles is not None
        assert "header" in exporter.styles
        assert "data" in exporter.styles

    def test_create_styles_returns_expected_style_keys(self):
        """Test _create_styles method returns all expected style keys."""
        # Arrange
        exporter = ExcelExporter()

        # Act
        styles = exporter._create_styles()

        # Assert
        expected_keys = ["header", "subheader", "data", "percentage", "number"]
        for key in expected_keys:
            assert key in styles
        assert styles["header"]["font"].bold is True
        assert styles["percentage"]["number_format"] == "0.00%"

    @patch("ledzephyr.exporters.Workbook")
    def test_export_metrics_creates_workbook_and_saves_without_charts(
        self, mock_workbook_class, sample_metrics_data, temp_output_path
    ):
        """Test export_metrics creates workbook and saves to specified path without charts."""
        # Arrange
        mock_workbook = Mock()
        mock_worksheet = Mock()
        # Enable item assignment for worksheet
        mock_worksheet.__setitem__ = Mock()
        mock_worksheet.__getitem__ = Mock(return_value=Mock())
        mock_worksheet.cell = Mock(return_value=Mock())
        mock_worksheet.merge_cells = Mock()
        mock_worksheet.columns = []
        mock_worksheet.column_dimensions = {}

        mock_workbook_class.return_value = mock_workbook
        mock_workbook.active = Mock()
        mock_workbook.create_sheet.return_value = mock_worksheet

        exporter = ExcelExporter()

        # Act - disable charts to avoid complex mocking
        result_path = exporter.export_metrics(
            sample_metrics_data, temp_output_path, include_charts=False
        )

        # Assert
        mock_workbook_class.assert_called_once()
        mock_workbook.remove.assert_called_once()
        mock_workbook.save.assert_called_once_with(temp_output_path)
        assert result_path == temp_output_path

    @patch("ledzephyr.exporters.Workbook")
    def test_export_metrics_with_no_teams_skips_team_section(
        self, mock_workbook_class, temp_output_path
    ):
        """Test export_metrics with metrics that have no teams skips team section."""
        # Arrange
        mock_workbook = Mock()
        mock_worksheet = Mock()
        mock_worksheet.__setitem__ = Mock()
        mock_worksheet.__getitem__ = Mock(return_value=Mock())
        mock_worksheet.cell = Mock(return_value=Mock())
        mock_worksheet.merge_cells = Mock()
        mock_worksheet.columns = []
        mock_worksheet.column_dimensions = {}

        mock_workbook_class.return_value = mock_workbook
        mock_workbook.active = Mock()
        mock_workbook.create_sheet.return_value = mock_worksheet

        # Create metrics without teams
        mock_metrics = Mock()
        mock_metrics.project_key = "TEST"
        mock_metrics.time_window = "7d"
        mock_metrics.total_tests = 50
        mock_metrics.zephyr_tests = 30
        mock_metrics.qtest_tests = 20
        mock_metrics.adoption_ratio = 0.4
        mock_metrics.active_users = 5
        mock_metrics.coverage_parity = 0.8
        mock_metrics.defect_link_rate = 0.2
        mock_metrics.teams = []  # Empty teams list

        metrics_data = {"7d": mock_metrics}

        exporter = ExcelExporter()

        # Act
        result_path = exporter.export_metrics(metrics_data, temp_output_path, include_charts=False)

        # Assert
        mock_workbook.save.assert_called_once_with(temp_output_path)
        assert result_path == temp_output_path

    @patch("ledzephyr.exporters.Workbook")
    def test_export_metrics_creates_summary_sheet(
        self, mock_workbook_class, sample_metrics_data, temp_output_path
    ):
        """Test export_metrics creates summary sheet with correct data."""
        # Arrange
        mock_workbook = Mock()
        mock_worksheet = Mock()
        # Enable item assignment for worksheet
        mock_worksheet.__setitem__ = Mock()
        mock_worksheet.__getitem__ = Mock(return_value=Mock())
        mock_worksheet.cell = Mock(return_value=Mock())
        mock_worksheet.merge_cells = Mock()
        mock_worksheet.columns = []
        mock_worksheet.column_dimensions = {}

        mock_workbook_class.return_value = mock_workbook
        mock_workbook.active = Mock()
        mock_workbook.create_sheet.return_value = mock_worksheet

        exporter = ExcelExporter()

        # Act - disable charts to avoid complex mocking
        exporter.export_metrics(sample_metrics_data, temp_output_path, include_charts=False)

        # Assert
        # Verify summary sheet creation
        mock_workbook.create_sheet.assert_any_call("Summary")
        # Verify sheet is populated with title
        mock_worksheet.__setitem__.assert_any_call("A1", "Ledzephyr Migration Metrics Summary")


@pytest.mark.unit
@pytest.mark.exporters
class TestPDFExporter:
    """Test PDFExporter class following TDD."""

    def test_init_creates_styles_and_custom_styles(self):
        """Test PDFExporter initialization creates styles and adds custom styles."""
        # Arrange & Act
        exporter = PDFExporter()

        # Assert
        assert exporter.styles is not None
        assert "CustomTitle" in exporter.styles
        assert "CustomHeading" in exporter.styles
        assert exporter.styles["CustomTitle"].fontSize == 24

    @patch("ledzephyr.exporters.SimpleDocTemplate")
    def test_export_metrics_creates_pdf_and_saves(
        self, mock_doc_class, sample_metrics_data, temp_output_path
    ):
        """Test export_metrics creates PDF document and saves to specified path."""
        # Arrange
        mock_doc = Mock()
        mock_doc_class.return_value = mock_doc

        # Change path to .pdf extension
        pdf_path = temp_output_path.with_suffix(".pdf")

        exporter = PDFExporter()

        # Act
        result_path = exporter.export_metrics(sample_metrics_data, pdf_path)

        # Assert
        mock_doc_class.assert_called_once()
        mock_doc.build.assert_called_once()
        assert result_path == pdf_path

    @patch("ledzephyr.exporters.SimpleDocTemplate")
    def test_export_metrics_without_charts_builds_pdf(
        self, mock_doc_class, sample_metrics_data, temp_output_path
    ):
        """Test export_metrics without charts builds PDF successfully."""
        # Arrange
        mock_doc = Mock()
        mock_doc_class.return_value = mock_doc

        pdf_path = temp_output_path.with_suffix(".pdf")
        exporter = PDFExporter()

        # Act
        result_path = exporter.export_metrics(sample_metrics_data, pdf_path, include_charts=False)

        # Assert
        mock_doc.build.assert_called_once()
        assert result_path == pdf_path

    @patch("ledzephyr.exporters.SimpleDocTemplate")
    def test_export_metrics_with_empty_teams_builds_pdf(self, mock_doc_class, temp_output_path):
        """Test export_metrics with empty teams list builds PDF successfully."""
        # Arrange
        mock_doc = Mock()
        mock_doc_class.return_value = mock_doc

        # Create metrics with empty teams
        mock_metrics = Mock()
        mock_metrics.project_key = "TEST"
        mock_metrics.time_window = "7d"
        mock_metrics.total_tests = 50
        mock_metrics.zephyr_tests = 30
        mock_metrics.qtest_tests = 20
        mock_metrics.adoption_ratio = 0.4
        mock_metrics.active_users = 5
        mock_metrics.coverage_parity = 0.8
        mock_metrics.defect_link_rate = 0.2
        mock_metrics.teams = []

        metrics_data = {"7d": mock_metrics}
        pdf_path = temp_output_path.with_suffix(".pdf")

        exporter = PDFExporter()

        # Act
        result_path = exporter.export_metrics(metrics_data, pdf_path)

        # Assert
        mock_doc.build.assert_called_once()
        assert result_path == pdf_path


@pytest.mark.unit
@pytest.mark.exporters
class TestHTMLExporter:
    """Test HTMLExporter class following TDD."""

    @patch("ledzephyr.exporters.Template")
    def test_init_loads_template(self, mock_template_class):
        """Test HTMLExporter initialization loads template."""
        # Arrange
        mock_template = Mock()
        mock_template_class.return_value = mock_template

        # Act
        exporter = HTMLExporter()

        # Assert
        assert exporter.template == mock_template
        mock_template_class.assert_called_once()

    @patch("ledzephyr.exporters.Template")
    @patch("pathlib.Path.write_text")
    def test_export_metrics_renders_template_and_writes_file(
        self, mock_write_text, mock_template_class, sample_metrics_data, temp_output_path
    ):
        """Test export_metrics renders template and writes HTML file."""
        # Arrange
        mock_template = Mock()
        mock_template.render.return_value = "<html>Test HTML</html>"
        mock_template_class.return_value = mock_template

        html_path = temp_output_path.with_suffix(".html")
        exporter = HTMLExporter()

        # Act
        result_path = exporter.export_metrics(sample_metrics_data, html_path)

        # Assert
        mock_write_text.assert_called_once()
        mock_template.render.assert_called_once()
        assert result_path == html_path

    @patch("ledzephyr.exporters.Template")
    @patch("pathlib.Path.write_text")
    def test_export_metrics_with_single_metric_renders_correctly(
        self, mock_write_text, mock_template_class, temp_output_path
    ):
        """Test export_metrics with single metric renders correctly."""
        # Arrange
        mock_template = Mock()
        test_html_content = "<html>Ledzephyr Migration Metrics Report</html>"
        mock_template.render.return_value = test_html_content
        mock_template_class.return_value = mock_template

        mock_metrics = Mock()
        mock_metrics.project_key = "SINGLE"
        mock_metrics.time_window = "30d"
        mock_metrics.total_tests = 75
        mock_metrics.zephyr_tests = 45
        mock_metrics.qtest_tests = 30
        mock_metrics.adoption_ratio = 0.6
        mock_metrics.active_users = 8
        mock_metrics.coverage_parity = 0.9
        mock_metrics.defect_link_rate = 0.1
        mock_metrics.model_dump.return_value = {
            "project_key": "SINGLE",
            "time_window": "30d",
            "total_tests": 75,
            "zephyr_tests": 45,
            "qtest_tests": 30,
            "adoption_ratio": 0.6,
            "active_users": 8,
            "coverage_parity": 0.9,
            "defect_link_rate": 0.1,
        }

        metrics_data = {"30d": mock_metrics}
        html_path = temp_output_path.with_suffix(".html")

        exporter = HTMLExporter()

        # Act
        result_path = exporter.export_metrics(metrics_data, html_path)

        # Assert
        mock_write_text.assert_called_once_with(test_html_content)
        mock_template.render.assert_called_once()
        assert result_path == html_path


@pytest.mark.unit
@pytest.mark.exporters
class TestDataExporter:
    """Test DataExporter main orchestration class following TDD."""

    @patch("ledzephyr.exporters.HTMLExporter")
    def test_init_creates_all_exporters(self, mock_html_class):
        """Test DataExporter initialization creates all sub-exporters."""
        # Arrange
        mock_html_class.return_value = Mock()

        # Act
        exporter = DataExporter()

        # Assert
        assert isinstance(exporter.excel_exporter, ExcelExporter)
        assert isinstance(exporter.pdf_exporter, PDFExporter)
        mock_html_class.assert_called_once()

    @patch("ledzephyr.exporters.HTMLExporter")
    @patch.object(ExcelExporter, "export_metrics")
    def test_export_excel_format_calls_excel_exporter(
        self, mock_excel_export, mock_html_class, sample_metrics_data, temp_output_path
    ):
        """Test export with excel format calls excel exporter."""
        # Arrange
        mock_html_class.return_value = Mock()
        mock_excel_export.return_value = temp_output_path
        exporter = DataExporter()

        # Act
        result = exporter.export(sample_metrics_data, temp_output_path, "excel")

        # Assert
        mock_excel_export.assert_called_once_with(sample_metrics_data, temp_output_path, True)
        assert result == temp_output_path

    @patch("ledzephyr.exporters.HTMLExporter")
    @patch.object(PDFExporter, "export_metrics")
    def test_export_pdf_format_calls_pdf_exporter(
        self, mock_pdf_export, mock_html_class, sample_metrics_data, temp_output_path
    ):
        """Test export with pdf format calls pdf exporter."""
        # Arrange
        mock_html_class.return_value = Mock()
        mock_pdf_export.return_value = temp_output_path
        exporter = DataExporter()

        # Act
        result = exporter.export(sample_metrics_data, temp_output_path, "pdf")

        # Assert
        mock_pdf_export.assert_called_once_with(sample_metrics_data, temp_output_path, True)
        assert result == temp_output_path

    @patch("ledzephyr.exporters.HTMLExporter")
    @patch.object(HTMLExporter, "export_metrics")
    def test_export_html_format_calls_html_exporter(
        self, mock_html_export, mock_html_class, sample_metrics_data, temp_output_path
    ):
        """Test export with html format calls html exporter."""
        # Arrange
        mock_html_instance = Mock()
        mock_html_instance.export_metrics.return_value = temp_output_path
        mock_html_class.return_value = mock_html_instance
        exporter = DataExporter()

        # Act
        result = exporter.export(sample_metrics_data, temp_output_path, "html")

        # Assert
        mock_html_instance.export_metrics.assert_called_once_with(
            sample_metrics_data, temp_output_path
        )
        assert result == temp_output_path

    @patch("ledzephyr.exporters.HTMLExporter")
    @patch("pandas.DataFrame.to_csv")
    def test_export_csv_format_uses_pandas(
        self, mock_to_csv, mock_html_class, sample_metrics_data, temp_output_path
    ):
        """Test export with csv format uses pandas to_csv."""
        # Arrange
        mock_html_class.return_value = Mock()
        csv_path = temp_output_path.with_suffix(".csv")
        exporter = DataExporter()

        # Act
        result = exporter.export(sample_metrics_data, csv_path, "csv")

        # Assert
        mock_to_csv.assert_called_once_with(csv_path, index=False)
        assert result == csv_path

    @patch("ledzephyr.exporters.HTMLExporter")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_export_json_format_uses_json_dump(
        self, mock_json_dump, mock_file, mock_html_class, sample_metrics_data, temp_output_path
    ):
        """Test export with json format uses json dump."""
        # Arrange
        mock_html_class.return_value = Mock()
        json_path = temp_output_path.with_suffix(".json")
        exporter = DataExporter()

        # Act
        result = exporter.export(sample_metrics_data, json_path, "json")

        # Assert
        mock_json_dump.assert_called_once()
        assert result == json_path

    @patch("ledzephyr.exporters.HTMLExporter")
    def test_export_unsupported_format_raises_value_error(
        self, mock_html_class, sample_metrics_data, temp_output_path
    ):
        """Test export with unsupported format raises ValueError."""
        # Arrange
        mock_html_class.return_value = Mock()
        exporter = DataExporter()

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported export format: unsupported"):
            exporter.export(sample_metrics_data, temp_output_path, "unsupported")

    @patch("ledzephyr.exporters.HTMLExporter")
    @patch.object(ExcelExporter, "export_metrics")
    def test_export_with_charts_disabled_passes_parameter(
        self, mock_excel_export, mock_html_class, sample_metrics_data, temp_output_path
    ):
        """Test export with include_charts=False passes parameter correctly."""
        # Arrange
        mock_html_class.return_value = Mock()
        mock_excel_export.return_value = temp_output_path
        exporter = DataExporter()

        # Act
        exporter.export(sample_metrics_data, temp_output_path, "excel", include_charts=False)

        # Assert
        mock_excel_export.assert_called_once_with(sample_metrics_data, temp_output_path, False)
