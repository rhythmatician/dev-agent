"""AutoGen orchestrator loop implementation.

This module implements the main AutoGen conversation loop between
Supervisor, DevAgent, ShellTool, and GitTool agents according to
AGENT-ARCHITECTURE.md.
"""

import logging
from typing import Any, Dict

import yaml

from agent_lib.message import Message, send_message

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    """Load agent configuration from YAML file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Validate required sections
        if "agents" not in config:
            raise ValueError("Config must contain 'agents' section")

        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in configuration file: {e}")
        raise


def run_autogen_loop(config_path: str = "agent.config.yaml") -> bool:
    """Run the main AutoGen conversation loop.

    This implements the conversation flow specified in AGENT-ARCHITECTURE.md:
    1. Load configuration and initialize agents
    2. Run test command via ShellTool
    3. If tests fail, DevAgent generates patches
    4. Supervisor reviews patches
    5. If approved, GitTool applies changes
    6. Repeat until tests pass or max_iterations reached

    Args:
        config_path: Path to agent configuration file

    Returns:
        True if tests pass, False if max iterations reached
    """
    logger.info(f"Starting AutoGen loop with config: {config_path}")

    try:
        # Load configuration
        config = load_config(config_path)

        # Extract settings with defaults
        max_iterations = config.get("max_iterations", 5)
        test_command = config.get("test_command", "pytest --maxfail=1")

        logger.info(
            f"Max iterations: {max_iterations}, Test command: {test_command}"
        )  # Initialize agents (placeholder - will be proper AutoGen agents later)
        _initialize_agents(config)

        # Main conversation loop
        iteration = 0
        tests_passing = False

        while iteration < max_iterations and not tests_passing:
            iteration += 1
            logger.info(f"AutoGen loop iteration {iteration}/{max_iterations}")

            # Step 1: Run tests via ShellTool
            test_result = _run_tests(test_command)

            if test_result.get("exit_code") == 0:
                logger.info("All tests passing - loop complete")
                tests_passing = True
                break

            logger.info(f"Tests failed with exit code {test_result.get('exit_code')}")

            # Step 2: DevAgent generates patch
            patch_message = _generate_patch(test_result, iteration)
            send_message(patch_message)
            logger.debug(f"DevAgent emitted patch: {patch_message.type}")

            # Step 3: Supervisor reviews patch
            supervisor_response = _supervisor_review(patch_message)
            send_message(supervisor_response)

            approved = supervisor_response.metadata.get("approved", False)
            logger.info(f"Supervisor {'approved' if approved else 'rejected'} patch")

            # Step 4: If approved, apply via GitTool
            if approved:
                git_result = _apply_patch(patch_message.content)
                send_message(git_result)
                logger.debug(
                    f"GitTool applied patch: {git_result.metadata.get('success')}"
                )
            else:
                logger.info("Patch rejected - continuing to next iteration")

        if not tests_passing:
            logger.warning(
                f"Max iterations ({max_iterations}) reached without passing tests"
            )

        return tests_passing

    except Exception as e:
        logger.error(f"AutoGen loop failed: {e}")
        raise


def _initialize_agents(config: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize AutoGen agents based on configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary of initialized agents
    """
    # Placeholder - will create actual AutoGen agents later
    logger.debug("Initializing agents with mock implementations")

    return {
        "supervisor": config["agents"]["supervisor"],
        "dev_agent": config["agents"]["dev_agent"],
        "shell_tool": {"type": "shell"},
        "git_tool": {"type": "git"},
    }


def _run_tests(test_command: str) -> Dict[str, Any]:
    """Run tests via ShellTool.

    Args:
        test_command: Command to run tests

    Returns:
        Test results with exit_code and output
    """
    # Placeholder - in real implementation, this would use ShellTool agent
    logger.debug(f"Running test command: {test_command}")

    return {
        "exit_code": 1,  # Simulate failing tests
        "stdout": "FAILED tests/test_foo.py::test_bar",
        "stderr": "AssertionError: Expected 2, got 1",
    }


def _generate_patch(test_result: Dict[str, Any], iteration: int) -> Message:
    """Generate patch via DevAgent.

    Args:
        test_result: Results from test run
        iteration: Current iteration number

    Returns:
        Message containing the generated patch
    """
    logger.debug(f"Generating patch for iteration {iteration}")

    # Simulate DevAgent response
    patch_content = """```diff
--- a/file.py
+++ b/file.py
@@
+ fix
```"""

    return Message(
        role="DevAgent",
        type="patch",
        content=patch_content,
        metadata={
            "iteration": iteration,
            "test_name": "tests/test_foo.py::test_bar",
            "approved": None,
        },
    )


def _supervisor_review(patch_message: Message) -> Message:
    """Get Supervisor review of patch.

    Args:
        patch_message: Message containing patch to review    Returns:
        Message containing Supervisor's decision
    """
    logger.debug(
        f"Supervisor reviewing patch from iteration "
        f"{patch_message.metadata.get('iteration')}"
    )

    # Simulate Supervisor approval
    return Message(
        role="Supervisor",
        type="review",
        content="Patch looks good - minimal fix addressing the failing test.",
        metadata={"approved": True, "iteration": patch_message.metadata["iteration"]},
    )


def _apply_patch(patch_content: str) -> Message:
    """Apply patch via GitTool.

    Args:
        patch_content: The patch content to apply

    Returns:
        Message indicating success/failure of patch application
    """
    logger.debug("Applying patch via GitTool")

    return Message(
        role="GitTool",
        type="status",
        content="Patch applied successfully",
        metadata={"action": "apply_patch", "success": True},
    )
