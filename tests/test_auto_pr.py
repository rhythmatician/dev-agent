"""Tests for the auto PR feature in GitTool.

This test suite covers the functionality for automatically creating
pull requests after successfully fixing tests, as required for Phase 5.
"""

from unittest.mock import MagicMock, patch

import pytest
from pytest import MonkeyPatch

import dev_agent


class TestAutoPRFeature:
    """Test suite for auto PR creation feature."""

    def test_open_pr_successful(self) -> None:
        """Test successful PR creation using GitHub CLI."""
        git_tool = dev_agent.GitTool()

        # Mock subprocess.run for gh pr create command
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="https://github.com/org/repo/pull/123"
            )

            # Call open_pr
            result = git_tool.open_pr(
                "Fix failing test", "Fixes the failing test by correcting return value"
            )

            # Assert
            assert result is True
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]
            assert "gh" in cmd
            assert "pr" in cmd
            assert "create" in cmd
            assert "--title" in cmd
            assert "--body" in cmd

    def test_open_pr_failure(self) -> None:
        """Test PR creation failure handling."""
        git_tool = dev_agent.GitTool()

        # Mock subprocess.run to fail
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("gh command failed")

            # Call open_pr
            result = git_tool.open_pr(
                "Fix failing test", "Fixes the failing test by correcting return value"
            )

            # Assert
            assert result is False

    def test_auto_pr_enabled_in_main_flow(self, monkeypatch: MonkeyPatch) -> None:
        """Test that auto PR is called when enabled in config."""
        # Arrange
        mock_test_runner = MagicMock()
        mock_test_runner.run_tests.side_effect = [
            {
                "passed": False,
                "failures": [
                    {
                        "test_name": "test_example",
                        "file_path": "test.py",
                        "error_output": "Error",
                    }
                ],
            },
            {"passed": True, "failures": []},
        ]

        mock_llm_generator = MagicMock()
        mock_patch_result = MagicMock()
        mock_patch_result.diff_content = (
            "diff --git a/file.py b/file.py\n@@ -1 +1 @@\n-error\n+fixed"
        )
        mock_llm_generator.generate_patch.return_value = mock_patch_result
        mock_llm_generator.validate_patch.return_value = True

        mock_git_tool = MagicMock()
        mock_git_tool.create_branch.return_value = True
        mock_git_tool.apply_patch.return_value = True
        mock_git_tool.commit.return_value = True
        mock_git_tool.push.return_value = True
        mock_git_tool.open_pr.return_value = True

        # Config with auto_pr enabled
        mock_config = {
            "max_iterations": 5,
            "test_command": "pytest",
            "git": {
                "branch_prefix": "dev-agent/fix",
                "remote": "origin",
                "auto_pr": True,
            },
            "llm": {"model_path": "llama-cpp:model"},
            "metrics": {"enabled": True, "storage_path": None},
        }

        # Mock metrics
        mock_metrics_storage = MagicMock()
        mock_metrics = MagicMock()
        mock_metrics_storage.load_metrics.return_value = mock_metrics

        # Setup monkeypatches
        monkeypatch.setattr("dev_agent._load_config", lambda: mock_config)
        monkeypatch.setattr("dev_agent.TestRunner", lambda x: mock_test_runner)
        monkeypatch.setattr("dev_agent.LLMPatchGenerator", lambda x: mock_llm_generator)
        monkeypatch.setattr("dev_agent.GitTool", lambda: mock_git_tool)
        monkeypatch.setattr("dev_agent.MetricsStorage", lambda: mock_metrics_storage)
        monkeypatch.setattr("time.time", lambda: 100)  # Mock time

        # Act
        with pytest.raises(SystemExit) as exc_info:
            dev_agent.main()

        # Assert
        assert exc_info.value.code == 0
        mock_git_tool.push.assert_called_once()
        mock_git_tool.open_pr.assert_called_once()

    def test_auto_pr_disabled_in_main_flow(self, monkeypatch: MonkeyPatch) -> None:
        """Test that auto PR is not called when disabled in config."""
        # Arrange
        mock_test_runner = MagicMock()
        mock_test_runner.run_tests.side_effect = [
            {
                "passed": False,
                "failures": [
                    {
                        "test_name": "test_example",
                        "file_path": "test.py",
                        "error_output": "Error",
                    }
                ],
            },
            {"passed": True, "failures": []},
        ]

        mock_llm_generator = MagicMock()
        mock_patch_result = MagicMock()
        mock_patch_result.diff_content = (
            "diff --git a/file.py b/file.py\n@@ -1 +1 @@\n-error\n+fixed"
        )
        mock_llm_generator.generate_patch.return_value = mock_patch_result
        mock_llm_generator.validate_patch.return_value = True

        mock_git_tool = MagicMock()
        mock_git_tool.create_branch.return_value = True
        mock_git_tool.apply_patch.return_value = True
        mock_git_tool.commit.return_value = True
        mock_git_tool.push.return_value = True

        # Config with auto_pr disabled
        mock_config = {
            "max_iterations": 5,
            "test_command": "pytest",
            "git": {
                "branch_prefix": "dev-agent/fix",
                "remote": "origin",
                "auto_pr": False,
            },
            "llm": {"model_path": "llama-cpp:model"},
            "metrics": {"enabled": True, "storage_path": None},
        }

        # Mock metrics
        mock_metrics_storage = MagicMock()
        mock_metrics = MagicMock()
        mock_metrics_storage.load_metrics.return_value = mock_metrics

        # Setup monkeypatches
        monkeypatch.setattr("dev_agent._load_config", lambda: mock_config)
        monkeypatch.setattr("dev_agent.TestRunner", lambda x: mock_test_runner)
        monkeypatch.setattr("dev_agent.LLMPatchGenerator", lambda x: mock_llm_generator)
        monkeypatch.setattr("dev_agent.GitTool", lambda: mock_git_tool)
        monkeypatch.setattr("dev_agent.MetricsStorage", lambda: mock_metrics_storage)
        monkeypatch.setattr("time.time", lambda: 100)  # Mock time

        # Act
        with pytest.raises(SystemExit) as exc_info:
            dev_agent.main()

        # Assert
        assert exc_info.value.code == 0
        mock_git_tool.push.assert_called_once()
        mock_git_tool.open_pr.assert_not_called()
