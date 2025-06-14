"""Test runner module for dev-agent.

This module provides functionality to run tests in a target project
and return structured results including failures and error information.
Following the architecture specified in docs/AGENT-ARCHITECTURE.md.

The main function `run_tests()` executes test commands (typically pytest)
in a subprocess and parses the output to extract failure information.
This is used by the AutoGen DevAgent to understand which tests are failing
and need to be fixed.

Typical usage:
    from agent_lib.test_runner import run_tests
    from pathlib import Path

    result = run_tests("pytest --maxfail=1", Path("/path/to/project"))
    if not result.passed:
        for failure in result.failures:
            print(f"Failed: {failure.test_name} in {failure.file_path}")
"""

import py_compile
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Constants for magic numbers and configuration
DEFAULT_TIMEOUT_SECONDS = 30
PYTEST_NO_TESTS_EXIT_CODE = 5


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
                print(f"Failed: {failure.test_name} in {failure.file_path}")"""

    # Fast syntax pre-check before running pytest
    syntax_error = fast_syntax_precheck(repo_path)
    if syntax_error:
        return TestResult(
            passed=False,
            failures=[
                TestFailure(
                    test_name=syntax_error["error"],
                    file_path=syntax_error["file_path"],
                    error_output=syntax_error["error"],
                )
            ],
            raw_output=f"Syntax error detected: {syntax_error['error']}",
        )

    # For cross-platform compatibility, detect if pytest is available
    # and use appropriate command format
    # Tokenize the command using shlex for robust parsing

    command_tokens = shlex.split(command)

    if command_tokens and command_tokens[0] == "pytest":
        # Replace "pytest" with "python -m pytest" for reliability
        command_tokens = ["python", "-m", "pytest"] + command_tokens[1:]
        # Add verbose output if not already present to capture test names
        if "-v" not in command_tokens and "--verbose" not in command_tokens:
            command_tokens.append("-v")

    try:
        proc = subprocess.run(
            command_tokens,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT_SECONDS,  # Prevent hanging tests
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
        return TestResult(
            passed=True, failures=[], raw_output=output
        )  # pytest exit code 5 means "no tests were collected"

    # This should be treated as success for our purposes

    if proc.returncode == PYTEST_NO_TESTS_EXIT_CODE:
        return TestResult(passed=True, failures=[], raw_output=output)

    # Check for discovery errors like syntax or import errors
    discovery_error = check_for_discovery_errors(proc.stdout, proc.stderr)
    if discovery_error:
        return TestResult(
            passed=False,
            failures=[
                TestFailure(
                    test_name=discovery_error["error"],
                    file_path=discovery_error["file_path"],
                    error_output=discovery_error["error"],
                )
            ],
            raw_output=output,
        )

    # Parse failures from pytest output
    failures = _parse_pytest_failures(output)

    return TestResult(passed=False, failures=failures, raw_output=output)


def check_for_discovery_errors(stdout: str, stderr: str) -> Optional[Dict[str, Any]]:
    """Check pytest output for discovery errors like syntax or import errors.

    Args:
        stdout: Standard output from pytest command
        stderr: Standard error from pytest command

    Returns:
        Dict with discovery error info if found, None otherwise.
        Dict contains: status, file_path, error
    """
    combined_output = stdout + stderr

    # Check for syntax errors
    syntax_error_pattern = r"(\S+\.py):(\d+): SyntaxError: (.+)"
    syntax_match = re.search(syntax_error_pattern, combined_output)
    if syntax_match:
        file_path, line_num, error_msg = syntax_match.groups()
        return {
            "status": "discovery_error",
            "file_path": file_path,
            "error": f"SyntaxError: {error_msg} (line {line_num})",
        }

    # Check for import errors
    import_error_pattern = r"ImportError while importing test module '([^']+)'"
    import_match = re.search(import_error_pattern, combined_output)
    if import_match:
        file_path = import_match.group(1)
        # Extract the actual import error details
        module_error_pattern = r"(ModuleNotFoundError|ImportError): (.+)"
        module_match = re.search(module_error_pattern, combined_output)
        if module_match:
            error_type, error_msg = module_match.groups()
            return {
                "status": "discovery_error",
                "file_path": file_path,
                "error": f"{error_type}: {error_msg}",
            }
        else:
            return {
                "status": "discovery_error",
                "file_path": file_path,
                "error": "Import error during test discovery",
            }

    return None


def fast_syntax_precheck(repo_path: Path) -> Optional[Dict[str, Any]]:
    """Perform fast syntax-only pre-check on all Python files.

    Args:
        repo_path: Path to the repository to check

    Returns:
        Dict with discovery error info if syntax error found, None otherwise
    """
    for py_file in repo_path.rglob("*.py"):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            return {
                "status": "discovery_error",
                "file_path": str(py_file.relative_to(repo_path)),
                "error": str(e),
            }
    return None


def _extract_error_message(output: str, test_nodeid: str) -> str:
    """Extract relevant error message for a specific test failure.

    Args:
        output: Full pytest output
        test_nodeid: Test identifier (e.g., "test_file.py::test_name")

    Returns:
        Extracted error message or full output if extraction fails
    """

    lines = output.splitlines()

    # Find the failure section for this specific test
    in_failure_section = False
    error_lines: List[str] = []

    for line in lines:
        if f"FAILED {test_nodeid}" in line:
            in_failure_section = True
            error_lines.append(line)

        elif in_failure_section:
            if line.startswith("FAILED ") or line.startswith("="):
                # We've reached the next failure or end section
                break

            error_lines.append(line)

    if error_lines:
        return "\n".join(error_lines).strip()

    # Fallback to full output if we can't extract specific error
    return output


def _parse_pytest_failures(output: str) -> List[TestFailure]:
    """Parse pytest output to extract test failure information.

    Args:
        output: Raw pytest output containing failure information

    Returns:
        List of TestFailure objects with parsed failure details
    """

    failures: List[TestFailure] = []

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
                        error_output=_extract_error_message(output, test_nodeid),
                    )

                    failures.append(failure)

    # If no FAILED lines found but we have a non-zero exit code,
    # create a generic failure entry

    if not failures:
        failures.append(
            TestFailure(test_name="unknown", file_path="unknown", error_output=output)
        )

    return failures
