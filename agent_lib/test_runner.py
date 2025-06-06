"""Test runner module for dev-agent.

This module provides functionality to run tests in a target project
and return structured results including failures and error information.
Following the architecture specified in docs/AGENT-ARCHITECTURE.md.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class TestFailure:
    """Represents a single test failure with context information."""

    test_name: str
    file_path: str
    error_output: str


@dataclass
class TestResult:
    """Represents the result of running tests in a project."""

    passed: bool
    failures: List[TestFailure]
    raw_output: str


def run_tests(command: str, repo_path: Path) -> TestResult:
    """Run tests in the specified repository using the given command.

    Args:
        command: The test command to execute (e.g., "pytest --maxfail=1")
        repo_path: Path to the repository where tests should be run

    Returns:
        TestResult containing pass/fail status, failures list, and raw output

    Example:
        result = run_tests("pytest --maxfail=1", Path("/path/to/project"))
        if not result.passed:
            for failure in result.failures:
                print(f"Failed: {failure.test_name} in {failure.file_path}")
    """  # For cross-platform compatibility, detect if pytest is available
    # and use appropriate command format
    if command.startswith("pytest"):
        # Replace "pytest" with "python -m pytest" for reliability
        command = command.replace("pytest", "python -m pytest", 1)
        # Add verbose output if not already present to capture test names
        if "-v" not in command and "--verbose" not in command:
            command += " -v"
    try:
        proc = subprocess.run(
            command.split(),
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,  # Prevent hanging tests
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        # Handle command not found or timeout
        return TestResult(
            passed=False,
            failures=[],
            raw_output=f"Error running command '{command}': {str(e)}",
        )

    output = proc.stdout + proc.stderr

    # If command succeeded (exit code 0), tests passed
    if proc.returncode == 0:
        return TestResult(passed=True, failures=[], raw_output=output)

    # pytest exit code 5 means "no tests were collected"
    # This should be treated as success for our purposes
    if proc.returncode == 5:
        return TestResult(passed=True, failures=[], raw_output=output)

    # Parse failures from pytest output
    failures = _parse_pytest_failures(output)

    return TestResult(passed=False, failures=failures, raw_output=output)


def _parse_pytest_failures(output: str) -> List[TestFailure]:
    """Parse pytest output to extract test failure information.

    Args:
        output: Raw pytest output containing failure information

    Returns:
        List of TestFailure objects with parsed failure details
    """
    failures = []
    lines = output.splitlines()

    for line in lines:
        # Look for "FAILED test_file.py::test_name" pattern
        if line.startswith("FAILED ") and "::" in line:
            # Example: "FAILED test_sample.py::test_always_fails - assert 2 == 3"
            parts = line.split()
            if len(parts) >= 2:
                test_nodeid = parts[1]  # e.g. "test_sample.py::test_always_fails"

                if "::" in test_nodeid:
                    file_part, test_part = test_nodeid.split("::", 1)

                    failure = TestFailure(
                        test_name=test_part,
                        file_path=file_part,
                        error_output=output,  # Include full output for context
                    )
                    failures.append(failure)

    # If no FAILED lines found but we have a non-zero exit code,
    # create a generic failure entry
    if not failures and "FAILED" not in output:
        failures.append(
            TestFailure(test_name="unknown", file_path="unknown", error_output=output)
        )

    return failures
