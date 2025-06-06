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
from pathlib import Path
from typing import Any, Dict, NoReturn

from agent_lib.llm_patch_generator import LLMPatchGenerator
from agent_lib.test_runner import run_tests


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
        "git": {"branch_prefix": "dev-agent/fix"},
        "llm": {"model_path": "models/codellama.gguf"},
    }


def _sanitize_branch_name(name: str) -> str:
    """Sanitize branch name to follow git naming conventions."""
    # Replace invalid characters with dashes
    sanitized = re.sub(r"[^a-zA-Z0-9\-_./]", "-", name)
    # Remove consecutive dashes
    sanitized = re.sub(r"-+", "-", sanitized)
    # Remove leading/trailing dashes
    sanitized = sanitized.strip("-")
    return sanitized


def main() -> NoReturn:
    """Main entry point for dev-agent CLI.

    Orchestrates the test-fix iteration loop until tests pass
    or max iterations is reached.

    Exits:
        0: Successfully processed (tests pass)
        1: General error or max iterations reached
        2: Patch validation/application failure
    """
    try:
        config = _load_config()
    except ConfigError:
        sys.exit(1)  # Initialize components
    repo_path = "."  # Current directory for now
    test_runner = TestRunner(repo_path)
    model_path: str = config["llm"]["model_path"]
    llm_generator = LLMPatchGenerator(model_path)
    git_tool = GitTool()

    max_iterations: int = config["max_iterations"]
    test_command: str = config["test_command"]

    for iteration in range(max_iterations):
        # Run tests
        try:
            test_result = test_runner.run_tests(test_command)
        except NoTestsFoundError:
            sys.exit(0)

        # If tests pass, we're done
        if test_result["passed"]:
            sys.exit(0)

        # If no failures detected but tests didn't pass, treat as no tests found
        if not test_result["failures"]:
            raise NoTestsFoundError("No test failures detected")

        # Generate patch for the first failure
        failure = test_result["failures"][0]
        patch_result = llm_generator.generate_patch(failure, Path(repo_path))

        # Create branch for this fix attempt
        branch_name = _sanitize_branch_name(
            f"{config['git']['branch_prefix']}_{failure['test_name']}"
        )

        # If not first iteration, add iteration number
        if iteration > 0:
            branch_name = f"{branch_name}_{iteration + 1}"

        git_tool.create_branch(branch_name)

        try:
            # Validate and apply patch
            if not llm_generator.validate_patch(
                patch_result.diff_content, Path(repo_path)
            ):
                sys.exit(2)

            # Apply patch
            if not git_tool.apply_patch(patch_result.diff_content):
                sys.exit(2)

            # Commit the changes
            commit_msg = f"TDD: fix {failure['test_name']}"
            git_tool.commit(commit_msg)

            # Only push if tests pass after this fix
            retest_result = test_runner.run_tests(test_command)
            if retest_result["passed"]:
                git_tool.push()
                sys.exit(0)
        except PatchApplicationError:
            sys.exit(2)

    # If we reach here, max iterations was reached
    sys.exit(1)


if __name__ == "__main__":
    main()
