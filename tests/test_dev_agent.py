"""Tests for the DevAgent orchestrator loop.

This test suite covers the main orchestration logic that ties together
the test runner, LLM patch generator, and git tools. Following TDD
principles as outlined in docs/PROJECT-OUTLINE.md Phase 3.

All tests use mocked dependencies to ensure we're testing only the
orchestrator logic without actual LLM calls or git operations.
"""

from typing import Any, Dict, Generator, List, TypedDict, cast
from unittest.mock import MagicMock, patch

import pytest
from pytest import MonkeyPatch

import dev_agent


# Custom exceptions that the orchestrator should handle
class NoTestsFoundError(Exception):
    """Raised when no tests are discovered."""

    pass


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


class PatchApplicationError(Exception):
    """Raised when patch cannot be applied."""

    pass


# Type definitions for better mypy support
class TestFailure(TypedDict):
    """Type definition for a test failure."""

    test_name: str
    file_path: str
    error_output: str


class TestResult(TypedDict):
    """Type definition for test run results."""

    passed: bool
    failures: List[TestFailure]


class DevAgentConfig(TypedDict):
    """Type definition for DevAgent configuration."""

    max_iterations: int
    test_command: str
    git: Dict[str, str]


@pytest.fixture(autouse=True)
def mock_sys_exit() -> Generator[MagicMock, None, None]:
    """Mock sys.exit to raise SystemExit instead of actually exiting."""
    with patch("sys.exit") as mock_exit:
        mock_exit.side_effect = SystemExit
        yield mock_exit


class TestDevAgentOrchestrator:
    """Test suite for DevAgent orchestrator functionality."""

    def test_exit_zero_when_no_failures(self, monkeypatch: MonkeyPatch) -> None:
        """Test immediate exit with code 0 when tests pass on first run."""
        # Arrange
        mock_test_runner = MagicMock()
        mock_test_runner.run_tests.return_value = {"passed": True, "failures": []}

        mock_llm_generator = MagicMock()
        mock_git_tool = MagicMock()  # Mock the _load_config function
        mock_config: DevAgentConfig = {
            "max_iterations": 5,
            "test_command": "pytest --maxfail=1",
            "git": {"branch_prefix": "dev-agent/fix"},
        }
        monkeypatch.setattr("dev_agent._load_config", lambda: mock_config)

        # Mock all the component constructors
        monkeypatch.setattr("dev_agent.TestRunner", lambda x: mock_test_runner)
        monkeypatch.setattr("dev_agent.LLMPatchGenerator", lambda x: mock_llm_generator)
        monkeypatch.setattr("dev_agent.GitTool", lambda: mock_git_tool)

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            dev_agent.main()

        assert exc_info.value.code == 0
        # Assert LLM and Git tools are never called
        mock_llm_generator.generate_patch.assert_not_called()
        mock_git_tool.create_branch.assert_not_called()
        mock_git_tool.apply_patch.assert_not_called()

    def test_single_failure_then_success(self, monkeypatch: MonkeyPatch) -> None:
        """Test single iteration with failure, then success after patch."""
        # Arrange
        test_failure: TestFailure = {
            "test_name": "test_example",
            "file_path": "test_example.py",
            "error_output": "AssertionError: assert 1 == 2",
        }

        mock_test_runner = MagicMock()
        # First call returns failure, second call returns success
        mock_test_runner.run_tests.side_effect = [
            {"passed": False, "failures": [test_failure]},
            {"passed": True, "failures": []},
        ]

        mock_llm_generator = MagicMock()
        mock_patch_result = MagicMock()
        mock_patch_result.diff_content = "diff --git a/example.py b/example.py\nindex 123..456\n--- a/example.py\n+++ b/example.py\n@@ -1 +1 @@\n-return 1\n+return 2"
        mock_llm_generator.generate_patch.return_value = mock_patch_result

        mock_git_tool = MagicMock()

        mock_config = {
            "max_iterations": 5,
            "test_command": "pytest --maxfail=1",
            "git": {"branch_prefix": "dev-agent/fix"},
        }
        monkeypatch.setattr("dev_agent._load_config", lambda: mock_config)
        monkeypatch.setattr("dev_agent.TestRunner", lambda x: mock_test_runner)
        monkeypatch.setattr("dev_agent.LLMPatchGenerator", lambda x: mock_llm_generator)
        monkeypatch.setattr("dev_agent.GitTool", lambda: mock_git_tool)

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            dev_agent.main()

        assert exc_info.value.code == 0

        # Assert correct sequence of calls
        mock_git_tool.create_branch.assert_called_once_with(
            "dev-agent/fix_test_example"
        )
        mock_git_tool.apply_patch.assert_called_once_with(
            mock_patch_result.diff_content
        )
        mock_git_tool.commit.assert_called_once_with("TDD: fix test_example")
        mock_git_tool.push.assert_called_once()

    def test_max_iterations_reached_exits_one(self, monkeypatch: MonkeyPatch) -> None:
        """Test exit code 1 when max iterations reached without success."""
        # Arrange
        test_failure = {
            "test_name": "test_persistent_failure",
            "file_path": "test_example.py",
            "error_output": "AssertionError: stubborn failure",
        }

        mock_test_runner = MagicMock()
        # Always return failure
        mock_test_runner.run_tests.return_value = {
            "passed": False,
            "failures": [test_failure],
        }

        mock_llm_generator = MagicMock()
        mock_patch_result = MagicMock()
        mock_patch_result.diff_content = (
            "diff --git a/example.py b/example.py\nindex 123..456"
        )
        mock_llm_generator.generate_patch.return_value = mock_patch_result

        mock_git_tool = MagicMock()

        # Config with max_iterations = 2
        mock_config = {
            "max_iterations": 2,
            "test_command": "pytest --maxfail=1",
            "git": {"branch_prefix": "dev-agent/fix"},
        }
        monkeypatch.setattr("dev_agent._load_config", lambda: mock_config)
        monkeypatch.setattr("dev_agent.TestRunner", lambda x: mock_test_runner)
        monkeypatch.setattr("dev_agent.LLMPatchGenerator", lambda x: mock_llm_generator)
        monkeypatch.setattr("dev_agent.GitTool", lambda: mock_git_tool)

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            dev_agent.main()

        assert exc_info.value.code == 1

        # Assert patch generation was called twice
        assert mock_llm_generator.generate_patch.call_count == 2

        # Assert branch creation was called twice with iteration numbers
        expected_calls = [
            ("dev-agent/fix_test_persistent_failure",),
            ("dev-agent/fix_test_persistent_failure_2",),
        ]
        actual_calls = [call[0] for call in mock_git_tool.create_branch.call_args_list]
        assert actual_calls == expected_calls

        # Assert push is never called on failure
        mock_git_tool.push.assert_not_called()

    def test_patch_validation_failure_exits_two(self, monkeypatch: MonkeyPatch) -> None:
        """Test exit code 2 when patch validation fails."""
        # Arrange
        test_failure = {
            "test_name": "test_bad_patch",
            "file_path": "test_example.py",
            "error_output": "SyntaxError: invalid syntax",
        }

        mock_test_runner = MagicMock()
        mock_test_runner.run_tests.return_value = {
            "passed": False,
            "failures": [test_failure],
        }

        mock_llm_generator = MagicMock()
        mock_patch_result = MagicMock()
        mock_patch_result.diff_content = "invalid diff content"
        mock_llm_generator.generate_patch.return_value = mock_patch_result

        mock_git_tool = MagicMock()
        mock_git_tool.create_branch.return_value = None  # Success
        mock_git_tool.apply_patch.side_effect = PatchApplicationError(
            "Patch validation failed"
        )

        mock_config = {
            "max_iterations": 5,
            "test_command": "pytest --maxfail=1",
            "git": {"branch_prefix": "dev-agent/fix"},
        }
        monkeypatch.setattr("dev_agent._load_config", lambda: mock_config)
        monkeypatch.setattr("dev_agent.TestRunner", lambda x: mock_test_runner)
        monkeypatch.setattr("dev_agent.LLMPatchGenerator", lambda x: mock_llm_generator)
        monkeypatch.setattr("dev_agent.GitTool", lambda: mock_git_tool)

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            dev_agent.main()

        assert exc_info.value.code == 2

        # Assert git operations stopped after patch application failed
        mock_git_tool.create_branch.assert_called_once()
        mock_git_tool.apply_patch.assert_called_once()
        mock_git_tool.commit.assert_not_called()
        mock_git_tool.push.assert_not_called()

    def test_branch_name_sanitization(self, monkeypatch: MonkeyPatch) -> None:
        """Test that branch names are properly sanitized."""
        # Arrange
        test_failure = {
            "test_name": "tests/test_mod.py::Test::test feature",
            "file_path": "tests/test_mod.py",
            "error_output": "AssertionError: test failed",
        }

        mock_test_runner = MagicMock()
        mock_test_runner.run_tests.side_effect = [
            {"passed": False, "failures": [test_failure]},
            {"passed": True, "failures": []},
        ]

        mock_llm_generator = MagicMock()
        mock_patch_result = MagicMock()
        mock_patch_result.diff_content = "diff --git a/example.py b/example.py\n"
        mock_llm_generator.generate_patch.return_value = mock_patch_result

        mock_git_tool = MagicMock()

        mock_config = {
            "max_iterations": 5,
            "test_command": "pytest --maxfail=1",
            "git": {"branch_prefix": "dev-agent/fix"},
        }
        monkeypatch.setattr("dev_agent._load_config", lambda: mock_config)
        monkeypatch.setattr("dev_agent.TestRunner", lambda x: mock_test_runner)
        monkeypatch.setattr("dev_agent.LLMPatchGenerator", lambda x: mock_llm_generator)
        monkeypatch.setattr("dev_agent.GitTool", lambda: mock_git_tool)

        # Act
        with pytest.raises(SystemExit):
            dev_agent.main()

        # Assert branch name is properly sanitized
        # "tests/test_mod.py::Test::test feature" should become "dev-agent/fix_tests_test_mod_py__Test__test_feature"
        expected_branch = "dev-agent/fix_tests_test_mod_py__Test__test_feature"
        mock_git_tool.create_branch.assert_called_once_with(expected_branch)

    def test_no_tests_discovered_exits_zero(self, monkeypatch: MonkeyPatch) -> None:
        """Test exit code 0 when no tests are discovered."""
        # Arrange
        mock_test_runner = MagicMock()
        mock_test_runner.run_tests.side_effect = NoTestsFoundError("No tests found")

        mock_llm_generator = MagicMock()
        mock_git_tool = MagicMock()

        mock_config = {
            "max_iterations": 5,
            "test_command": "pytest --maxfail=1",
            "git": {"branch_prefix": "dev-agent/fix"},
        }
        monkeypatch.setattr("dev_agent._load_config", lambda: mock_config)
        monkeypatch.setattr("dev_agent.TestRunner", lambda x: mock_test_runner)
        monkeypatch.setattr("dev_agent.LLMPatchGenerator", lambda x: mock_llm_generator)
        monkeypatch.setattr("dev_agent.GitTool", lambda: mock_git_tool)

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            dev_agent.main()

        assert exc_info.value.code == 0

        # Assert LLM and Git tools are never called
        mock_llm_generator.generate_patch.assert_not_called()
        mock_git_tool.create_branch.assert_not_called()

    def test_invalid_config_fails_fast(self, monkeypatch: MonkeyPatch) -> None:
        """Test exit code 1 when configuration is invalid or missing."""
        # Arrange
        monkeypatch.setattr(
            "dev_agent._load_config",
            lambda: exec('raise ConfigError("Invalid config")'),
        )

        # Mock components (though they shouldn't be called)
        mock_test_runner = MagicMock()
        mock_llm_generator = MagicMock()
        mock_git_tool = MagicMock()

        monkeypatch.setattr("dev_agent.TestRunner", lambda x: mock_test_runner)
        monkeypatch.setattr("dev_agent.LLMPatchGenerator", lambda x: mock_llm_generator)
        monkeypatch.setattr("dev_agent.GitTool", lambda: mock_git_tool)

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            dev_agent.main()

        assert exc_info.value.code == 1

        # Assert no components are called when config fails
        mock_test_runner.run_tests.assert_not_called()
        mock_llm_generator.generate_patch.assert_not_called()
        mock_git_tool.create_branch.assert_not_called()
