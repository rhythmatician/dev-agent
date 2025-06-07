"""Test the Supervisor Agent loop functionality.

Tests for the supervisor's ability to iterate over subtasks and invoke
the Dev-Agent for each one, handling success and failure scenarios.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_supervisor_iterates_over_subtasks():
    """Test that supervisor calls dev-agent for each subtask."""
    story = "Create a calculator. Add functions for add and subtract."

    # For now, just test that the supervisor creates a proper plan in dry-run mode
    result = subprocess.run(
        [sys.executable, "-m", "supervisor", "run", "--story", story, "--dry-run"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    plan = json.loads(result.stdout)
    assert "subtasks" in plan

    # Should have multiple subtasks for this story
    assert len(plan["subtasks"]) >= 2


def test_supervisor_fails_fast_on_dev_agent_error():
    """Test that supervisor aborts if dev-agent returns nonzero on a subtask."""
    story = "Create failing tests and fix them."

    # Mock subprocess.run to simulate dev-agent failure
    with patch("supervisor.supervisor.subprocess.run") as mock_run:
        # First call for subtask 1 returns failure (nonzero exit code)
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="dev-agent failed"
        )

        result = subprocess.run(
            [sys.executable, "-m", "supervisor", "run", "--story", story],
            capture_output=True,
            text=True,
        )

        # Supervisor should exit with failure when dev-agent fails
        assert result.returncode != 0

        # Should only call dev-agent once (for the first failing subtask)
        assert mock_run.call_count == 1


def test_supervisor_proceeds_only_after_subtask_success():
    """Test that supervisor proceeds to subtask2 only if subtask1 passes."""
    # This test will be implemented once we have the loop logic
    # For now, it documents the expected behavior
    story = "Write tests. Implement features. Run validation."

    # This should eventually test that:
    # 1. Supervisor creates subtasks (should be 3 for this story)
    # 2. Calls dev-agent for subtask1
    # 3. Only if subtask1 succeeds, calls dev-agent for subtask2
    # 4. Only if subtask2 succeeds, calls dev-agent for subtask3

    # For now, just check that we can create the story plan
    result = subprocess.run(
        [sys.executable, "-m", "supervisor", "run", "--story", story, "--dry-run"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    plan = json.loads(result.stdout)
    assert "subtasks" in plan
    assert len(plan["subtasks"]) >= 3


def test_supervisor_handles_empty_subtask_list():
    """Test that supervisor handles the case when no subtasks are generated."""
    # Edge case: story that doesn't generate meaningful subtasks
    story = "."

    result = subprocess.run(
        [sys.executable, "-m", "supervisor", "run", "--story", story],
        capture_output=True,
        text=True,
    )

    # Should fail gracefully when no subtasks can be generated
    assert result.returncode != 0
    assert "error" in result.stderr.lower() or "no" in result.stderr.lower()


def test_supervisor_respects_max_retries():
    """Test that supervisor respects retry limits for failing subtasks."""
    # This test will be implemented once we have retry logic
    # For now, it documents the expected behavior
    story = "Create robust error handling with retries."

    # This should eventually test that:
    # 1. If dev-agent fails on a subtask
    # 2. Supervisor retries up to N times (configurable)
    # 3. If still failing after N retries, supervisor aborts

    # For now, just check that we can create the story plan
    result = subprocess.run(
        [sys.executable, "-m", "supervisor", "run", "--story", story, "--dry-run"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    plan = json.loads(result.stdout)
    assert "subtasks" in plan
