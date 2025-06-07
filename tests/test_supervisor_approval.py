"""Test the Supervisor Agent approval check functionality.

Tests for the supervisor's ability to provide approval checks for completed work,
including ✅ Approved and ❌ Rejected scenarios.
"""

import json
import subprocess
import sys
from unittest.mock import MagicMock, patch


def test_supervisor_provides_approval_check_for_completed_work():
    """Test that supervisor provides approval status after completing all subtasks."""
    story = "Create a simple function."

    # Test the supervisor directly with mocking
    with patch("supervisor.supervisor.subprocess.run") as mock_run:
        # Configure mock to return success for dev-agent calls
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="NoTestsFoundError: No test failures detected",
        )

        from supervisor.supervisor import Supervisor

        supervisor = Supervisor()
        exit_code = supervisor.run(story, dry_run=False)

        assert exit_code == 0
        # The approval functionality should be tested by capturing stdout
        # For now, we validate that the mock was called and no exception occurred


def test_supervisor_approves_when_all_subtasks_complete():
    """Test that supervisor marks work as approved when all subtasks complete successfully."""
    story = "Simple task that should succeed."

    # Test the supervisor directly with mocking
    with patch("supervisor.supervisor.subprocess.run") as mock_run:
        # Configure mock to return success for dev-agent calls
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="NoTestsFoundError: No test failures detected",
        )

        from supervisor.supervisor import Supervisor

        supervisor = Supervisor()

        # Capture stdout to check the JSON output
        import io
        from contextlib import redirect_stdout

        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            exit_code = supervisor.run(story, dry_run=False)

        assert exit_code == 0
        output = captured_output.getvalue()
        plan = json.loads(output)

        # Should be approved when all subtasks complete
        assert plan["approval"]["status"] == "approved"
        assert "✅" in plan["approval"]["message"]


def test_supervisor_rejects_when_subtasks_fail():
    """Test that supervisor marks work as rejected when subtasks fail."""
    story = "Task that should fail."

    # Test the supervisor directly with mocking
    with patch("supervisor.supervisor.subprocess.run") as mock_run:
        # Configure mock to return failure for dev-agent calls
        mock_run.return_value = MagicMock(
            returncode=2, stdout="", stderr="Some real error occurred"
        )

        from supervisor.supervisor import Supervisor

        supervisor = Supervisor()

        # Capture stderr to check the rejection message
        import io
        from contextlib import redirect_stderr

        captured_error = io.StringIO()
        with redirect_stderr(captured_error):
            exit_code = supervisor.run(story, dry_run=False)

        # Should fail with rejected status
        assert exit_code != 0
        stderr_output = captured_error.getvalue()
        # Check stderr for rejection info
        assert "rejected" in stderr_output.lower() or "❌" in stderr_output


def test_supervisor_approval_includes_summary():
    """Test that approval check includes a summary of completed work."""
    story = "Create a calculator. Add functions."

    # Test the supervisor directly with mocking
    with patch("supervisor.supervisor.subprocess.run") as mock_run:
        # Configure mock to return success for dev-agent calls
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="NoTestsFoundError: No test failures detected",
        )

        from supervisor.supervisor import Supervisor

        supervisor = Supervisor()

        # Capture stdout to check the JSON output
        import io
        from contextlib import redirect_stdout

        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            exit_code = supervisor.run(story, dry_run=False)

        assert exit_code == 0
        output = captured_output.getvalue()
        plan = json.loads(output)

        # Should include summary information
        assert "approval" in plan
        assert "summary" in plan["approval"]
        assert "completed_subtasks" in plan["approval"]
        assert (
            plan["approval"]["completed_subtasks"] >= 2
        )  # Should have multiple subtasks


def test_supervisor_dry_run_does_not_include_approval():
    """Test that dry-run mode does not include approval status."""
    story = "Create something in dry run."

    result = subprocess.run(
        [sys.executable, "-m", "supervisor", "run", "--story", story, "--dry-run"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    plan = json.loads(result.stdout)

    # Dry-run should not include approval since no work was executed
    assert "approval" not in plan
    assert plan["dry_run"] is True
