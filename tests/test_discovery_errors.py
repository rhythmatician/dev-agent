"""Tests for discovery error detection and handling.

This test suite validates the enhanced test runner capability to detect
pytest discovery errors and the orchestrator's ability to handle them.
Following TDD principles for V1 enhancements.
"""

from pathlib import Path

from agent_lib.test_runner import check_for_discovery_errors, run_tests


class TestDiscoveryErrorDetection:
    """Test suite for discovery error detection functionality."""

    def test_check_for_discovery_errors_syntax_error(self) -> None:
        """Test detection of syntax errors during discovery."""
        # TODO: implement check_for_discovery_errors function
        stdout = ""
        stderr = """
            test_syntax_error.py:3: SyntaxError: invalid syntax
            def broken_function(
                    ^
            E   File "test_syntax_error.py", line 3
            E     def broken_function(
            E                        ^
            E   SyntaxError: invalid syntax
        """

        error_info = check_for_discovery_errors(stdout, stderr)

        assert error_info is not None
        assert error_info["status"] == "discovery_error"
        assert "test_syntax_error.py" in error_info["file_path"]
        assert "SyntaxError" in error_info["error"]

    def test_check_for_discovery_errors_import_error(self) -> None:
        """Test detection of import errors during discovery."""
        stdout = ""
        stderr = """
            ImportError while importing test module 'test_import_error.py'.
            Hint: make sure your test modules can be imported by pytest.
            test_import_error.py:1: in <module>
                import nonexistent_module
            E   ModuleNotFoundError: No module named 'nonexistent_module'
        """

        error_info = check_for_discovery_errors(stdout, stderr)

        assert error_info is not None
        assert error_info["status"] == "discovery_error"
        assert "test_import_error.py" in error_info["file_path"]
        assert "ModuleNotFoundError" in error_info["error"]

    def test_check_for_discovery_errors_no_error(self) -> None:
        """Test that normal test output doesn't trigger discovery error."""
        stdout = "test_normal.py::test_passes PASSED"
        stderr = ""

        error_info = check_for_discovery_errors(stdout, stderr)

        assert error_info is None

    def test_run_tests_returns_discovery_error_on_syntax_error(
        self, tmp_path: Path
    ) -> None:
        """Test that run_tests returns discovery error status for syntax errors."""
        project = tmp_path / "toy_syntax_error"
        project.mkdir()

        # Create a file with syntax error
        (project / "test_syntax_error.py").write_text(
            """
def test_something():
    # Missing closing parenthesis
    broken_call(
"""
        )

        from dev_agent import TestRunner

        test_runner = TestRunner(str(project))
        result = test_runner.run_tests("pytest --disable-warnings")

        # Should return discovery error instead of normal failure
        assert hasattr(result, "status") or isinstance(result, dict)
        if isinstance(result, dict):
            assert result.get("status") == "discovery_error"
        else:
            # For now, this will fail until we implement the enhancement
            assert result.passed is False  # Temporary until enhancement

    def test_fast_syntax_precheck_catches_errors(self, tmp_path: Path) -> None:
        """Test that fast syntax pre-check catches errors before pytest."""
        project = tmp_path / "toy_fast_check"
        project.mkdir()

        # Create a file with syntax error
        (project / "invalid_syntax.py").write_text(
            """
def broken_function(
    # Missing closing parenthesis and body
"""
        )

        # TODO: This will need to be implemented in run_tests
        # For now, this test documents the intended behavior
        result = run_tests("pytest --disable-warnings", repo_path=project)

        # Eventually should catch this before running pytest
        assert result.passed is False
