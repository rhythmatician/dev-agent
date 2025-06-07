"""Test for metrics integration in dev_agent.py.

This test suite covers how the dev_agent orchestrator records and uses
metrics during the patch generation process.
"""

from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, patch

import pytest
from pytest import MonkeyPatch

import dev_agent
from agent_lib.metrics import DevAgentMetrics, PatchMetrics


class TestDevAgentMetricsIntegration:
    """Test suite for dev-agent's metrics integration."""

    def test_successful_patch_records_metrics(self, monkeypatch: MonkeyPatch) -> None:
        """Test that successful patch generation records metrics."""
        # Arrange
        test_failure = {
            "test_name": "test_example",
            "file_path": "test_example.py",
            "error_output": "AssertionError: test failed",
        }

        # Mock test runner to first fail, then pass
        mock_test_runner = MagicMock()
        mock_test_runner.run_tests.side_effect = [
            {"passed": False, "failures": [test_failure]},
            {"passed": True, "failures": []},
        ]

        # Mock LLM patch generator
        mock_llm_generator = MagicMock()
        mock_patch_result = MagicMock()
        mock_patch_result.diff_content = "diff --git a/example.py b/example.py\n"
        mock_llm_generator.generate_patch.return_value = mock_patch_result
        mock_llm_generator.validate_patch.return_value = True

        # Mock git tool
        mock_git_tool = MagicMock()
        mock_git_tool.create_branch.return_value = True
        mock_git_tool.apply_patch.return_value = True
        mock_git_tool.commit.return_value = True
        mock_git_tool.push.return_value = True

        # Mock config
        mock_config = {
            "max_iterations": 5,
            "test_command": "pytest --maxfail=1",
            "git": {"branch_prefix": "dev-agent/fix"},
            "llm": {"model_path": "llama-cpp:codellama"},
        }

        # Mock metrics storage
        mock_metrics = DevAgentMetrics()
        mock_metrics_storage = MagicMock()
        mock_metrics_storage.load_metrics.return_value = mock_metrics

        # Setup monkeypatches
        monkeypatch.setattr("dev_agent._load_config", lambda: mock_config)
        monkeypatch.setattr("dev_agent.TestRunner", lambda x: mock_test_runner)
        monkeypatch.setattr("dev_agent.LLMPatchGenerator", lambda x: mock_llm_generator)
        monkeypatch.setattr("dev_agent.GitTool", lambda: mock_git_tool)
        monkeypatch.setattr("dev_agent.MetricsStorage", lambda: mock_metrics_storage)

        # Mock time.time to return predictable values
        mock_time = MagicMock()
        mock_time.side_effect = [100.0, 101.5]  # 1.5 seconds duration
        monkeypatch.setattr("time.time", mock_time)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            dev_agent.main()

        # Assert
        assert exc_info.value.code == 0
        mock_metrics_storage.save_metrics.assert_called_once()

        # Verify metrics content by capturing the argument to save_metrics
        saved_metrics = mock_metrics_storage.save_metrics.call_args[0][0]
        assert len(saved_metrics.patch_results) == 1
        assert saved_metrics.patch_results[0].test_name == "test_example"
        assert saved_metrics.patch_results[0].llm_backend == "llama-cpp"
        assert saved_metrics.patch_results[0].model_name == "codellama"
        assert saved_metrics.patch_results[0].iterations == 1
        assert saved_metrics.patch_results[0].success is True
        assert saved_metrics.patch_results[0].duration_ms == 1500  # 1.5 seconds

    def test_max_iterations_records_failure_metrics(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test that reaching max iterations records failure metrics."""
        # Arrange
        test_failure = {
            "test_name": "test_persistent_failure",
            "file_path": "test_example.py",
            "error_output": "AssertionError: persistent error",
        }

        # Mock test runner to always fail
        mock_test_runner = MagicMock()
        mock_test_runner.run_tests.return_value = {
            "passed": False,
            "failures": [test_failure],
        }

        # Mock LLM patch generator
        mock_llm_generator = MagicMock()
        mock_patch_result = MagicMock()
        mock_patch_result.diff_content = "diff --git a/example.py b/example.py\n"
        mock_llm_generator.generate_patch.return_value = mock_patch_result
        mock_llm_generator.validate_patch.return_value = True

        # Mock git tool
        mock_git_tool = MagicMock()
        mock_git_tool.create_branch.return_value = True
        mock_git_tool.apply_patch.return_value = True
        mock_git_tool.commit.return_value = True

        # Mock config with max_iterations=2
        mock_config = {
            "max_iterations": 2,  # Will try twice and then fail
            "test_command": "pytest --maxfail=1",
            "git": {"branch_prefix": "dev-agent/fix"},
            "llm": {"model_path": "ollama:phi"},
        }

        # Mock metrics storage
        mock_metrics = DevAgentMetrics()
        mock_metrics_storage = MagicMock()
        mock_metrics_storage.load_metrics.return_value = mock_metrics

        # Setup monkeypatches
        monkeypatch.setattr("dev_agent._load_config", lambda: mock_config)
        monkeypatch.setattr("dev_agent.TestRunner", lambda x: mock_test_runner)
        monkeypatch.setattr("dev_agent.LLMPatchGenerator", lambda x: mock_llm_generator)
        monkeypatch.setattr("dev_agent.GitTool", lambda: mock_git_tool)
        monkeypatch.setattr("dev_agent.MetricsStorage", lambda: mock_metrics_storage)

        # Mock time.time to return predictable values
        mock_time = MagicMock()
        mock_time.side_effect = [100.0, 103.0]  # 3 seconds duration
        monkeypatch.setattr("time.time", mock_time)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            dev_agent.main()

        # Assert
        assert exc_info.value.code == 1
        mock_metrics_storage.save_metrics.assert_called_once()

        # Verify metrics content
        saved_metrics = mock_metrics_storage.save_metrics.call_args[0][0]
        assert len(saved_metrics.patch_results) == 1
        assert saved_metrics.patch_results[0].test_name == "test_persistent_failure"
        assert saved_metrics.patch_results[0].llm_backend == "ollama"
        assert saved_metrics.patch_results[0].model_name == "phi"
        assert saved_metrics.patch_results[0].iterations == 2  # Max iterations
        assert saved_metrics.patch_results[0].success is False
        assert saved_metrics.patch_results[0].duration_ms == 3000  # 3 seconds
