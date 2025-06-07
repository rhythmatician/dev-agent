"""Tests for lint and format checking before commit.

This test suite validates the enhanced git tool capability to check
formatting and linting before committing patches.
Following TDD principles for V1 enhancements.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import dev_agent
from dev_agent import GitTool


class TestLintAndFormatChecking:
    """Test suite for lint and format checking functionality."""

    def test_git_tool_format_check_success(self) -> None:
        """Test successful format check before commit."""
        git_tool = GitTool()        # Mock successful black and flake8 checks
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = git_tool.check_format_and_lint("example.py")
            
            # Should return success when both checks pass
            assert result["passed"] is True
            assert "error" not in result

    def test_git_tool_format_check_failure(self) -> None:
        """Test format check failure triggers re-prompting."""
        git_tool = GitTool()        # Mock failed black check
        with patch("subprocess.run") as mock_run:
            # First call (black) fails, second call (flake8) not reached
            mock_run.return_value = MagicMock(
                returncode=1, stdout="would reformat example.py", stderr=""
            )

            result = git_tool.check_format_and_lint("example.py")
            
            # Should return failure when format check fails
            assert result["passed"] is False
            assert "would reformat" in result["error"]

    def test_git_tool_lint_check_failure(self) -> None:
        """Test lint check failure triggers re-prompting."""
        git_tool = GitTool()        # Mock successful black but failed flake8
        def mock_subprocess_side_effect(*args, **kwargs):
            if "black" in args[0]:
                return MagicMock(returncode=0)
            elif "flake8" in args[0]:
                return MagicMock(
                    returncode=1,
                    stdout="example.py:1:1: E302 expected 2 blank lines",
                    stderr="",
                )
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=mock_subprocess_side_effect):
            result = git_tool.check_format_and_lint("example.py")
            
            # Should return failure when lint check fails
            assert result["passed"] is False
            assert "E302" in result["error"]

    def test_commit_with_format_lint_check(self) -> None:
        """Test enhanced commit method that checks format and lint."""
        git_tool = GitTool()

        # Mock all subprocess calls to succeed
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # TODO: enhance commit method to include format/lint check
            result = git_tool.commit("Test commit message")

            # For now, just test the existing functionality
            assert result is True

    def test_orchestrator_handles_format_failure(self, monkeypatch) -> None:
        """Test that orchestrator re-prompts LLM on format/lint failure."""
        # TODO: This test documents the intended integration behavior
        # The orchestrator should catch format/lint failures and re-prompt

        # Mock components
        mock_test_runner = MagicMock()
        mock_test_runner.run_tests.return_value = {
            "passed": False,
            "failures": [
                {
                    "test_name": "test_example",
                    "file_path": "example.py",
                    "error_output": "AssertionError",
                }
            ],
        }

        mock_llm_generator = MagicMock()
        mock_patch_result = MagicMock()
        mock_patch_result.diff_content = "some diff"
        mock_llm_generator.generate_patch.return_value = mock_patch_result
        mock_llm_generator.validate_patch.return_value = True

        # Mock git tool to fail format check
        mock_git_tool = MagicMock()
        mock_git_tool.create_branch.return_value = True
        mock_git_tool.apply_patch.return_value = True
        # Simulate format check failure
        mock_git_tool.check_format_and_lint.return_value = {
            "passed": False,
            "error": "Format check failed",
        }

        mock_config = {
            "max_iterations": 5,
            "test_command": "pytest --maxfail=1",
            "git": {"branch_prefix": "dev-agent/fix"},
            "llm": {"model_path": "models/test.gguf"},
        }

        monkeypatch.setattr("dev_agent._load_config", lambda: mock_config)
        monkeypatch.setattr("dev_agent.TestRunner", lambda x: mock_test_runner)
        monkeypatch.setattr("dev_agent.LLMPatchGenerator", lambda x: mock_llm_generator)
        monkeypatch.setattr("dev_agent.GitTool", lambda: mock_git_tool)

        # This will currently work with existing implementation
        # TODO: Enhance to handle format/lint checking
        with pytest.raises(SystemExit):
            dev_agent.main()
