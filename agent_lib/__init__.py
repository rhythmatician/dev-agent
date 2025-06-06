"""Agent library for dev-agent multi-agent system.

This package contains the core modules for the AutoGen-based
multi-agent system that automatically fixes failing tests.

Modules (to be implemented in future phases):
    test_runner: Executes project tests and parses results
    llm_patch_generator: Generates code patches via local LLM
    orchestrator: Coordinates the multi-agent conversation flow
    git_tools: Handles git operations (branch, commit, push, PR)
    shell_tools: Safely executes whitelisted shell commands

For architecture details, see: docs/AGENT-ARCHITECTURE.md
"""

__version__ = "0.1.0"
__author__ = "Dev Agent Team"
