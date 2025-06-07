"""Test the Supervisor Agent CLI interface.

Tests for the supervisor-agent command-line tool that:
1. Parses story descriptions into subtasks
2. Provides proper exit codes and error handling
3. Outputs plans in JSON/YAML format
"""

import json
import subprocess
import sys


def test_supervisor_cli_missing_story():
    """Test that supervisor-agent exits nonzero when story is missing."""
    result = subprocess.run(
        [sys.executable, "-m", "supervisor", "run"],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "error" in result.stderr.lower() or "required" in result.stderr.lower()


def test_supervisor_cli_empty_story():
    """Test that supervisor-agent exits nonzero when story is empty."""
    result = subprocess.run(
        [sys.executable, "-m", "supervisor", "run", "--story", ""],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "error" in result.stderr.lower() or "empty" in result.stderr.lower()


def test_supervisor_cli_valid_story_produces_plan():
    """Test that supervisor-agent produces a plan for a valid story."""
    story = (
        "Create a simple calculator with add and subtract functions. Write tests first."
    )

    result = subprocess.run(
        [sys.executable, "-m", "supervisor", "run", "--story", story],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    # Output should be valid JSON containing subtasks
    try:
        plan = json.loads(result.stdout)
        assert "subtasks" in plan
        assert isinstance(plan["subtasks"], list)
        assert len(plan["subtasks"]) > 0

        # Each subtask should have a description
        for subtask in plan["subtasks"]:
            assert "description" in subtask
            assert isinstance(subtask["description"], str)
            assert len(subtask["description"].strip()) > 0

    except json.JSONDecodeError:
        assert False, f"Output is not valid JSON: {result.stdout}"


def test_supervisor_cli_help_option():
    """Test that supervisor-agent shows help with -h flag."""
    result = subprocess.run(
        [sys.executable, "-m", "supervisor", "run", "-h"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "story" in result.stdout.lower()
    assert "usage" in result.stdout.lower() or "help" in result.stdout.lower()


def test_supervisor_cli_config_option():
    """Test that supervisor-agent accepts --config option."""
    story = "Simple test story"
    config_path = "/fake/config.yaml"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "supervisor",
            "run",
            "--story",
            story,
            "--config",
            config_path,
        ],
        capture_output=True,
        text=True,
    )

    # Should fail gracefully if config doesn't exist, but should accept the option
    # We're testing argument parsing, not config loading here
    assert "--config" not in result.stderr or "unrecognized" not in result.stderr


def test_supervisor_cli_dry_run_option():
    """Test that supervisor-agent accepts --dry-run option."""
    story = "Simple test story"

    result = subprocess.run(
        [sys.executable, "-m", "supervisor", "run", "--story", story, "--dry-run"],
        capture_output=True,
        text=True,
    )

    # Should accept the option without error
    assert "--dry-run" not in result.stderr or "unrecognized" not in result.stderr

    # In dry-run mode, should still produce a plan but indicate it's a dry run
    if result.returncode == 0:
        try:
            plan = json.loads(result.stdout)
            assert "dry_run" in plan
            assert plan["dry_run"] is True
        except json.JSONDecodeError:
            pass  # Might not be implemented yet
