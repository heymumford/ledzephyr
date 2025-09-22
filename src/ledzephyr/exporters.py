"""Simple data export for metrics - JSON and CSV only."""

import csv
import json
from pathlib import Path

from ledzephyr.models import ProjectMetrics


class DataExporter:
    """Export metrics to JSON or CSV format."""

    def export(
        self,
        metrics_data: dict[str, ProjectMetrics],
        output_path: str | Path,
    ) -> Path:
        """
        Export metrics data to JSON or CSV based on file extension.

        Args:
            metrics_data: Dictionary of metrics by time window
            output_path: Output file path

        Returns:
            Path to exported file
        """
        output_path = Path(output_path)

        if output_path.suffix == ".json":
            return self._export_json(metrics_data, output_path)
        elif output_path.suffix == ".csv":
            return self._export_csv(metrics_data, output_path)
        else:
            # Default to JSON
            output_path = output_path.with_suffix(".json")
            return self._export_json(metrics_data, output_path)

    def _export_json(self, metrics_data: dict[str, ProjectMetrics], output_path: Path) -> Path:
        """Export metrics to JSON."""
        data = {window: metrics.model_dump() for window, metrics in metrics_data.items()}

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        return output_path

    def _export_csv(self, metrics_data: dict[str, ProjectMetrics], output_path: Path) -> Path:
        """Export metrics to CSV."""
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "window",
                    "total_tests",
                    "zephyr_tests",
                    "qtest_tests",
                    "adoption_ratio",
                    "active_users",
                    "coverage_parity",
                    "defect_link_rate",
                ],
            )
            writer.writeheader()

            for window, metrics in metrics_data.items():
                writer.writerow(
                    {
                        "window": window,
                        "total_tests": metrics.total_tests,
                        "zephyr_tests": metrics.zephyr_tests,
                        "qtest_tests": metrics.qtest_tests,
                        "adoption_ratio": metrics.adoption_ratio,
                        "active_users": metrics.active_users,
                        "coverage_parity": metrics.coverage_parity,
                        "defect_link_rate": metrics.defect_link_rate,
                    }
                )

        return output_path
