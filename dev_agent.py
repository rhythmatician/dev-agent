"""Dev Agent - AutoGen-based multi-agent system for automated test fixing.

This is the main entry point for the dev-agent CLI tool.
The tool implements a multi-agent system using AutoGen that:
1. Runs the target project's tests
2. Generates minimal unified-diff patches via a local LLM
3. Iterates until the tests pass
4. Commits/pushes fixes and optionally opens a PR

Usage:
    dev-agent [options] <project-path>

For full documentation, see: docs/PROJECT-OUTLINE.md
"""

import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, NoReturn, Optional, Tuple

from agent_lib.llm_patch_generator import LLMPatchGenerator
from agent_lib.metrics import (
    DevAgentMetrics,
    MetricsStorage,
    PatchMetrics,
    generate_metrics_report,
)
from agent_lib.test_runner import TestFailure, run_tests


# Custom exceptions for orchestrator error handling
class NoTestsFoundError(Exception):
    """Raised when no tests are discovered."""

    pass


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


class PatchApplicationError(Exception):
    """Raised when patch cannot be applied."""

    pass


class TestRunner:
    """Wrapper class for the functional test runner interface."""

    def __init__(self, repo_path: str):
        """Initialize TestRunner with repository path."""
        self.repo_path = Path(repo_path)

    def run_tests(self, command: str) -> Dict[str, Any]:
        """Run tests and return results in dict format."""
        result = run_tests(command, self.repo_path)

        # Check if this is a discovery error by examining the failure content
        if (
            not result.passed
            and len(result.failures) == 1
            and result.failures[0].test_name == result.failures[0].error_output
        ):
            # This indicates a discovery error (test_name == error_output)
            return {
                "status": "discovery_error",
                "file_path": result.failures[0].file_path,
                "error": result.failures[0].error_output,
                "passed": result.passed,
                "failures": [
                    {
                        "test_name": f.test_name,
                        "file_path": f.file_path,
                        "error_output": f.error_output,
                    }
                    for f in result.failures
                ],
                "raw_output": result.raw_output,
            }

        return {
            "passed": result.passed,
            "failures": [
                {
                    "test_name": f.test_name,
                    "file_path": f.file_path,
                    "error_output": f.error_output,
                }
                for f in result.failures
            ],
            "raw_output": result.raw_output,
        }


class GitTool:
    """Git operations for patch application and branch management."""

    def __init__(self) -> None:
        """Initialize GitTool."""
        pass

    def create_branch(self, branch_name: str) -> bool:
        """Create a new git branch."""
        try:
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def apply_patch(self, patch_content: str) -> bool:
        """Apply a unified diff patch."""
        try:
            # First validate the patch can be applied
            proc = subprocess.run(
                ["git", "apply", "--check"],
                input=patch_content,
                text=True,
                capture_output=True,
            )
            if proc.returncode != 0:
                raise PatchApplicationError("Patch validation failed")

            # Apply the patch
            subprocess.run(["git", "apply"], input=patch_content, text=True, check=True)
            return True
        except subprocess.CalledProcessError:
            raise PatchApplicationError("Failed to apply patch")

    def commit(self, message: str) -> bool:
        """Commit current changes."""
        try:
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", message], check=True, capture_output=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def push(self) -> bool:
        """Push current branch to remote."""
        try:
            subprocess.run(["git", "push"], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def open_pr(self, title: str, body: str) -> bool:
        """Open a pull request using GitHub CLI.

        Args:
            title: The title of the pull request
            body: The body/description of the pull request

        Returns:
            True if PR was created successfully, False otherwise
        """
        try:
            # Use GitHub CLI (gh) to create a PR
            # --fill will use the commit message if title is not provided
            subprocess.run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--title",
                    title,
                    "--body",
                    body,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except Exception:
            # Catch any errors during PR creation
            # This includes subprocess.CalledProcessError and any others
            # that might occur if gh CLI is not installed or configured
            return False

    def check_format_and_lint(self, file_path: str) -> Dict[str, Any]:
        """Check format and lint compliance for a file.

        Args:
            file_path: Path to the file to check

        Returns:
            Dict with 'passed' bool and optional 'error' string
        """
        try:
            # Check formatting with black (dry run)
            black_result = subprocess.run(
                ["black", "--check", "--diff", file_path],
                capture_output=True,
                text=True,
            )

            if black_result.returncode != 0:
                return {
                    "passed": False,
                    "error": f"Format check failed: {black_result.stdout}",
                }

            # Check linting with flake8
            flake8_result = subprocess.run(
                ["flake8", "--max-line-length=88", "--extend-ignore=E203", file_path],
                capture_output=True,
                text=True,
            )

            if flake8_result.returncode != 0:
                return {
                    "passed": False,
                    "error": f"Lint check failed: {flake8_result.stdout}",
                }

            # Both checks passed
            return {"passed": True}

        except subprocess.CalledProcessError as e:
            return {
                "passed": False,
                "error": f"Failed to run format/lint checks: {e}",
            }


def _sanitize_branch_name(name: str) -> str:
    """Sanitize branch name to follow git naming conventions."""
    # Preserve the branch prefix structure (e.g., "dev-agent/fix")
    prefix_parts = name.split("_", 1)
    if len(prefix_parts) < 2:
        return name  # No underscore found

    prefix, rest = prefix_parts

    # Replace colons and double colons with hyphens
    rest = re.sub(r"::", "-", rest)
    rest = re.sub(r":", "-", rest)

    # Replace spaces with hyphens
    rest = rest.replace(" ", "-")

    # Return with original prefix structure intact
    return f"{prefix}_{rest}"


def _parse_model_path(model_path: str) -> Tuple[str, str]:
    """Parse model path into backend and model name.

    Args:
        model_path: Path to model in format "backend:/path/to/model.gguf"
                   or "backend:model_name"

    Returns:
        Tuple of (backend, model_name)
    """
    if ":" in model_path:
        backend, model_path_part = model_path.split(":", 1)
        # Extract model name from path
        model_name = Path(model_path_part).stem
        return backend, model_name
    else:
        # Default to llama-cpp if no prefix
        return "llama-cpp", Path(model_path).stem


def _load_config() -> Dict[str, Any]:
    """Load configuration for the dev-agent orchestrator.

    Returns:
        Configuration dictionary with orchestrator settings.

    Raises:
        ConfigError: If configuration is invalid or missing.
    """
    # For now, return default configuration
    # Future versions will load from config file
    return {
        "max_iterations": 5,
        "test_command": "pytest --maxfail=1",
        "git": {
            "branch_prefix": "dev-agent/fix",
            "remote": "origin",
            "auto_pr": True,
        },
        "llm": {"model_path": "llama-cpp:models/codellama.gguf"},
        "metrics": {
            "enabled": True,
            "storage_path": None,  # Use default path
        },
    }


def main() -> NoReturn:
    """Main entry point for dev-agent CLI.

    Orchestrates the test-fix iteration loop until tests pass
    or max iterations is reached.

    Exits:
        0: Successfully processed (tests pass)
        1: General error or max iterations reached
        2: Patch validation/application failure
    """
    # Setup metrics
    metrics_storage = MetricsStorage()
    metrics = DevAgentMetrics()
    start_time = time.time()

    try:
        config = _load_config()
    except ConfigError:
        sys.exit(1)  # Initialize components
    repo_path = "."  # Current directory for now
    test_runner = TestRunner(repo_path)
    model_path: str = config["llm"]["model_path"]
    llm_backend, model_name = _parse_model_path(model_path)
    llm_generator = LLMPatchGenerator(model_path)
    git_tool = GitTool()

    max_iterations: int = config["max_iterations"]
    test_command: str = config["test_command"]
    # Auto PR configuration
    auto_pr_enabled: bool = config["git"].get("auto_pr", False)

    # Track if we have a failure object for metrics
    current_failure: Optional[TestFailure] = None

    for iteration in range(max_iterations):
        # Start timing for this iteration
        iteration_start_time = time.time()

        # Run tests
        try:
            test_result = test_runner.run_tests(test_command)
        except NoTestsFoundError:
            sys.exit(0)

        # Check for discovery errors (syntax/import errors) - treat as special case
        if test_result.get("status") == "discovery_error":
            # For discovery errors, create a special failure info for LLM
            current_failure = TestFailure(
                test_name="discovery_error",
                file_path=test_result["file_path"],
                error_output=test_result["error"],
            )
            # Continue with normal patch generation process
        elif test_result["passed"]:
            sys.exit(0)
        elif not test_result["failures"]:
            # If no failures detected but tests didn't pass, treat as no tests found
            raise NoTestsFoundError("No test failures detected")
        else:  # Normal test failure
            failure_dict = test_result["failures"][0]
            # Convert dictionary to TestFailure object
            current_failure = TestFailure(
                test_name=failure_dict["test_name"],
                file_path=failure_dict["file_path"],
                error_output=failure_dict["error_output"],
            )
        patch_result = llm_generator.generate_patch(
            current_failure, Path(repo_path)
        )  # Create branch for this fix attempt
        branch_name = _sanitize_branch_name(
            f"{config['git']['branch_prefix']}_{current_failure.test_name}"
        )

        # If not first iteration, add iteration number
        if iteration > 0:
            branch_name = f"{branch_name}_{iteration + 1}"

        if not git_tool.create_branch(branch_name):
            sys.exit(2)  # Exit with error if branch creation fails

        try:
            # Validate and apply patch
            if not llm_generator.validate_patch(
                patch_result.diff_content, Path(repo_path)
            ):
                sys.exit(2)

            # Apply patch
            if not git_tool.apply_patch(patch_result.diff_content):
                sys.exit(2)  # Commit the changes
            commit_msg = f"TDD: fix {current_failure.test_name}"
            git_tool.commit(commit_msg)

            # Only push if tests pass after this fix
            retest_result = test_runner.run_tests(test_command)
            if retest_result["passed"]:
                # Record successful metrics
                iteration_end_time = time.time()
                duration_ms = round((iteration_end_time - iteration_start_time) * 1000)
                patch_metrics = PatchMetrics(
                    test_name=current_failure.test_name,
                    llm_backend=llm_backend,
                    model_name=model_name,
                    iterations=iteration + 1,
                    success=True,
                    duration_ms=duration_ms,
                )
                metrics.add_patch_result(patch_metrics)
                metrics_storage.save_metrics(metrics)

                # Generate and print report
                report = generate_metrics_report(metrics)
                print("\n" + report)

                # Push changes
                if git_tool.push():
                    # Create PR if enabled
                    if auto_pr_enabled:
                        pr_title = f"Fix {current_failure.test_name}"
                        pr_body = (
                            f"This PR was automatically generated by Dev Agent to "
                            f"fix failing test: {current_failure.test_name}.\n\n"
                            f"The fix was applied after {iteration + 1} "
                            f"iteration(s).\n\n"
                            f"LLM Backend: {llm_backend}\n"
                            f"Model: {model_name}"
                        )
                        git_tool.open_pr(pr_title, pr_body)

                sys.exit(0)
        except PatchApplicationError:
            sys.exit(2)

    # If we reach here, max iterations was reached
    # Record failure metrics
    final_end_time = time.time()
    total_duration_ms = round((final_end_time - start_time) * 1000)

    # Make sure we have a failure object to record metrics for
    if current_failure:
        test_name = current_failure.test_name
    else:
        test_name = "unknown_failure"

    patch_metrics = PatchMetrics(
        test_name=test_name,
        llm_backend=llm_backend,
        model_name=model_name,
        iterations=max_iterations,
        success=False,
        duration_ms=total_duration_ms,
    )
    metrics.add_patch_result(patch_metrics)
    metrics_storage.save_metrics(metrics)

    # Generate and print failure report
    report = generate_metrics_report(metrics)
    print("\n" + report)

    sys.exit(1)


if __name__ == "__main__":
    main()
