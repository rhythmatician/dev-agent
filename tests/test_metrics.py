"""Tests for the metrics module.

This test suite covers the metrics collection and reporting functionality
for the dev-agent system. These metrics are part of Phase 5 features
to track performance, iteration counts, and success rates.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_lib.metrics import (
    DevAgentMetrics,
    MetricsStorage,
    PatchMetrics,
    generate_metrics_report,
    record_metrics,
)


class TestMetricsCollection:
    """Test suite for metrics collection functionality."""

    def test_patch_metrics_creation(self) -> None:
        """Test PatchMetrics creation and properties."""
        # Arrange & Act
        patch_metrics = PatchMetrics(
            test_name="test_example",
            llm_backend="llama-cpp",
            model_name="codellama",
            iterations=2,
            success=True,
            duration_ms=1500,
        )

        # Assert
        assert patch_metrics.test_name == "test_example"
        assert patch_metrics.llm_backend == "llama-cpp"
        assert patch_metrics.model_name == "codellama"
        assert patch_metrics.iterations == 2
        assert patch_metrics.success is True
        assert patch_metrics.duration_ms == 1500

    def test_dev_agent_metrics_add_patch_result(self) -> None:
        """Test adding patch results to DevAgentMetrics."""
        # Arrange
        metrics = DevAgentMetrics()
        patch_result = PatchMetrics(
            test_name="test_example",
            llm_backend="llama-cpp",
            model_name="codellama",
            iterations=1,
            success=True,
            duration_ms=1000,
        )

        # Act
        metrics.add_patch_result(patch_result)

        # Assert
        assert len(metrics.patch_results) == 1
        assert metrics.patch_results[0].test_name == "test_example"
        assert metrics.total_iterations == 1
        assert metrics.successful_patches == 1
        assert metrics.failed_patches == 0

    def test_dev_agent_metrics_summary(self) -> None:
        """Test summary statistics from DevAgentMetrics."""
        # Arrange
        metrics = DevAgentMetrics()

        # Add successful patch
        metrics.add_patch_result(
            PatchMetrics(
                test_name="test_success",
                llm_backend="llama-cpp",
                model_name="codellama",
                iterations=2,
                success=True,
                duration_ms=1500,
            )
        )

        # Add failed patch
        metrics.add_patch_result(
            PatchMetrics(
                test_name="test_failure",
                llm_backend="llama-cpp",
                model_name="codellama",
                iterations=3,
                success=False,
                duration_ms=2000,
            )
        )

        # Act
        summary = metrics.get_summary()

        # Assert
        assert summary["total_tests"] == 2
        assert summary["successful_patches"] == 1
        assert summary["failed_patches"] == 1
        assert summary["success_rate"] == 0.5
        assert summary["total_iterations"] == 5
        assert summary["avg_iterations_per_test"] == 2.5
        assert summary["avg_duration_ms"] > 0
        assert "llama-cpp" in summary["backends"]

    @pytest.fixture
    def temp_metrics_file(self, tmp_path: Path) -> Path:
        """Create a temporary metrics file for testing."""
        metrics_file = tmp_path / "metrics.json"
        return metrics_file

    def test_metrics_storage_save_load(self, temp_metrics_file: Path) -> None:
        """Test saving and loading metrics to/from storage."""
        # Arrange
        metrics = DevAgentMetrics()
        metrics.add_patch_result(
            PatchMetrics(
                test_name="test_example",
                llm_backend="llama-cpp",
                model_name="codellama",
                iterations=1,
                success=True,
                duration_ms=1000,
            )
        )
        storage = MetricsStorage(metrics_file=temp_metrics_file)

        # Act - Save
        storage.save_metrics(metrics)

        # Act - Load
        loaded_metrics = storage.load_metrics()

        # Assert
        assert loaded_metrics is not None
        assert len(loaded_metrics.patch_results) == 1
        assert loaded_metrics.patch_results[0].test_name == "test_example"
        assert loaded_metrics.total_iterations == 1
        assert loaded_metrics.successful_patches == 1

    @patch("agent_lib.metrics.MetricsStorage")
    def test_record_metrics_decorator(self, mock_storage_class: MagicMock) -> None:
        """Test the record_metrics decorator."""
        # Arrange
        mock_storage_instance = MagicMock()
        mock_storage_class.return_value = mock_storage_instance

        # Mock loaded metrics
        mock_metrics = DevAgentMetrics()
        mock_storage_instance.load_metrics.return_value = mock_metrics

        # Define a test function with the decorator
        @record_metrics(llm_backend="llama-cpp", model_name="codellama")
        def test_function(test_name: str) -> bool:
            # Simulates some work and returns success
            return test_name == "should_succeed"

        # Act
        result1 = test_function("should_succeed")
        result2 = test_function("should_fail")

        # Assert
        assert result1 is True
        assert result2 is False
        # The decorator should have saved metrics twice
        assert mock_storage_instance.save_metrics.call_count == 2

    def test_generate_metrics_report(self) -> None:
        """Test generating a metrics report."""
        # Arrange
        metrics = DevAgentMetrics()
        metrics.add_patch_result(
            PatchMetrics(
                test_name="test_example1",
                llm_backend="llama-cpp",
                model_name="codellama",
                iterations=1,
                success=True,
                duration_ms=1000,
            )
        )
        metrics.add_patch_result(
            PatchMetrics(
                test_name="test_example2",
                llm_backend="ollama",
                model_name="codellama",
                iterations=3,
                success=False,
                duration_ms=3000,
            )
        )

        # Act
        report = generate_metrics_report(metrics)

        # Assert
        assert "Dev Agent Metrics Report" in report
        assert "Success Rate: 50.0%" in report
        assert "Total Tests: 2" in report
        assert "Average Iterations: 2.0" in report
        assert "Backend Performance:" in report
        assert "llama-cpp" in report
        assert "ollama" in report
