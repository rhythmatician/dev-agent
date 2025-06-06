"""Tests for agent_lib.test_runner module.

Following TDD approach for Phase 1: Test-Runner Module.
These tests validate the run_tests function that executes project tests
and returns structured results.
"""

from pathlib import Path

from agent_lib.test_runner import run_tests


def test_run_tests_pass(tmp_path: Path) -> None:
    """Test run_tests with a passing test case."""
    # Create a tiny Python project with one passing test
    project = tmp_path / "toy_pass"
    project.mkdir()
    (project / "test_sample.py").write_text("def test_always_passes(): assert 1 == 1\n")

    result = run_tests("pytest --maxfail=1 --disable-warnings", repo_path=project)

    assert result.passed is True
    assert result.failures == []
    assert "test_always_passes" in result.raw_output


def test_run_tests_fail(tmp_path: Path) -> None:
    """Test run_tests with a failing test case."""
    project = tmp_path / "toy_fail"
    project.mkdir()
    (project / "test_sample.py").write_text("def test_always_fails(): assert 2 == 3\n")

    result = run_tests("pytest --maxfail=1 --disable-warnings", repo_path=project)

    assert result.passed is False
    assert len(result.failures) == 1
    assert "test_always_fails" in result.failures[0].test_name
    assert "test_sample.py" in result.failures[0].file_path
    assert "assert 2 == 3" in result.failures[0].error_output


def test_run_tests_multiple_failures(tmp_path: Path) -> None:
    """Test run_tests with multiple failing tests."""
    project = tmp_path / "toy_multi_fail"
    project.mkdir()
    (project / "test_multiple.py").write_text(
        """
def test_fail_one(): assert False, "First failure"
def test_fail_two(): assert 1 == 2, "Second failure"
"""
    )
    result = run_tests("pytest --disable-warnings", repo_path=project)

    assert result.passed is False
    # Without --maxfail=1, pytest runs all tests, so expect exactly 2 failures
    assert len(result.failures) == 2
    failure_names = [f.test_name for f in result.failures]
    assert "test_fail_one" in failure_names
    assert "test_fail_two" in failure_names
    assert all(f.file_path == "test_multiple.py" for f in result.failures)


def test_run_tests_mixed_results(tmp_path: Path) -> None:
    """Test run_tests with mix of passing and failing tests."""
    project = tmp_path / "toy_mixed"
    project.mkdir()
    (project / "test_mixed.py").write_text(
        """
def test_passes(): assert True
def test_fails(): assert False, "This test fails"
"""
    )

    result = run_tests("pytest --disable-warnings", repo_path=project)

    assert result.passed is False  # Should fail due to one failing test
    assert len(result.failures) == 1  # Exactly one failure expected
    assert result.failures[0].test_name == "test_fails"
    assert result.failures[0].file_path == "test_mixed.py"


def test_run_tests_no_tests(tmp_path: Path) -> None:
    """Test run_tests with no test files."""
    project = tmp_path / "toy_empty"
    project.mkdir()
    # Create a non-test file
    (project / "not_a_test.py").write_text("print('hello')")

    result = run_tests("pytest --disable-warnings", repo_path=project)

    # pytest should pass when no tests are collected
    assert result.passed is True
    assert result.failures == []


def test_run_tests_invalid_command(tmp_path: Path) -> None:
    """Test run_tests with invalid command."""
    project = tmp_path / "toy_invalid"
    project.mkdir()

    result = run_tests("invalid_command_that_does_not_exist", repo_path=project)

    assert result.passed is False
    assert result.raw_output  # Should contain error output
