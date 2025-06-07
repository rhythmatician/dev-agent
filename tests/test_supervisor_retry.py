"""Test the Supervisor Agent retry functionality.

Tests for the supervisor's ability to retry failed subtasks according to
configuration and handle retry exhaustion gracefully.
"""

import json
from unittest.mock import MagicMock, patch


def test_supervisor_retries_failed_subtasks():
    """Test that supervisor retries failed subtasks up to max_retries limit."""
    story = "Create a function that initially fails."

    # Test the supervisor directly with mocking
    with patch("supervisor.supervisor.subprocess.run") as mock_run:
        # Configure mock to fail first time, succeed second time
        mock_run.side_effect = [
            MagicMock(returncode=2, stdout="", stderr="First attempt failed"),
            MagicMock(
                returncode=1,
                stdout="",
                stderr="NoTestsFoundError: No test failures detected",
            ),
        ]

        from supervisor.supervisor import Supervisor

        # Test with max_retries=1
        supervisor = Supervisor(max_retries=1)

        # Capture stdout to check the JSON output
        import io
        from contextlib import redirect_stdout

        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            exit_code = supervisor.run(story, dry_run=False)

        assert exit_code == 0
        output = captured_output.getvalue()
        plan = json.loads(output)

        # Should be approved after retry
        assert plan["approval"]["status"] == "approved"
        # Should have made 2 subprocess calls (initial + 1 retry)
        assert mock_run.call_count == 2


def test_supervisor_respects_max_retries_limit():
    """Test that supervisor stops retrying after max_retries is exceeded."""
    story = "Create a function that always fails."

    # Test the supervisor directly with mocking
    with patch("supervisor.supervisor.subprocess.run") as mock_run:
        # Configure mock to always fail
        mock_run.return_value = MagicMock(
            returncode=2, stdout="", stderr="Always fails"
        )

        from supervisor.supervisor import Supervisor

        # Test with max_retries=2
        supervisor = Supervisor(max_retries=2)

        # Capture stderr to check failure messages
        import io
        from contextlib import redirect_stderr

        captured_error = io.StringIO()
        with redirect_stderr(captured_error):
            exit_code = supervisor.run(story, dry_run=False)

        # Should fail after exhausting retries
        assert exit_code != 0
        stderr_output = captured_error.getvalue()
        assert (
            "exhausted retries" in stderr_output.lower()
            or "retry" in stderr_output.lower()
        )
        # Should have made 3 subprocess calls (initial + 2 retries)
        assert mock_run.call_count == 3


def test_supervisor_default_retry_behavior():
    """Test that supervisor has sensible default retry behavior."""
    story = "Simple task."

    # Test the supervisor directly with mocking
    with patch("supervisor.supervisor.subprocess.run") as mock_run:
        # Configure mock to succeed on first try
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="NoTestsFoundError: No test failures detected",
        )

        from supervisor.supervisor import Supervisor

        # Test with default settings (no max_retries specified)
        supervisor = Supervisor()

        # Check that supervisor has a reasonable default for max_retries
        assert hasattr(supervisor, "max_retries")
        assert supervisor.max_retries >= 0  # Should be 0 or positive integer
        assert supervisor.max_retries <= 5  # Should be reasonable (not too high)


def test_supervisor_retry_preserves_subtask_order():
    """Test that retrying subtasks doesn't affect the order of execution."""
    story = "First task. Second task."

    # Test the supervisor directly with mocking
    with patch("supervisor.supervisor.subprocess.run") as mock_run:
        # Configure mock: first subtask fails then succeeds, second subtask succeeds
        mock_run.side_effect = [
            MagicMock(returncode=2, stdout="", stderr="First subtask fails"),
            MagicMock(
                returncode=1,
                stdout="",
                stderr="NoTestsFoundError: No test failures detected",
            ),  # First subtask retry succeeds
            MagicMock(
                returncode=1,
                stdout="",
                stderr="NoTestsFoundError: No test failures detected",
            ),  # Second subtask succeeds
        ]

        from supervisor.supervisor import Supervisor

        supervisor = Supervisor(max_retries=1)

        # Capture stderr to check execution order
        import io
        from contextlib import redirect_stderr

        captured_error = io.StringIO()
        with redirect_stderr(captured_error):
            exit_code = supervisor.run(story, dry_run=False)

        assert exit_code == 0
        stderr_output = captured_error.getvalue()

        # Check that subtasks were executed in correct order
        assert "subtask 1/2" in stderr_output  # First subtask
        assert "subtask 2/2" in stderr_output  # Second subtask
        # Should have made 3 subprocess calls total
        assert mock_run.call_count == 3


def test_supervisor_no_test_failures_not_retried():
    """Test that 'No test failures detected' case is not retried."""
    story = "Task that has no test failures."

    # Test the supervisor directly with mocking
    with patch("supervisor.supervisor.subprocess.run") as mock_run:
        # Configure mock to return "No test failures detected" (which is success)
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="NoTestsFoundError: No test failures detected",
        )

        from supervisor.supervisor import Supervisor

        supervisor = Supervisor(max_retries=3)

        exit_code = supervisor.run(story, dry_run=False)

        assert exit_code == 0
        # Should have made only 1 subprocess call (no retries for success)
        assert mock_run.call_count == 1
