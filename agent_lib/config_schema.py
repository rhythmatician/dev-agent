"""Configuration schema definitions for dev-agent.

This module provides typed configuration schemas for the dev-agent
using TypedDict for better type checking and linting.
"""

from typing import TypedDict


class GitConfig(TypedDict):
    """Git configuration schema."""

    branch_prefix: str


class LLMConfig(TypedDict):
    """LLM configuration schema."""

    model_path: str


class AgentConfig(TypedDict):
    """Dev-agent configuration schema."""

    max_iterations: int
    test_command: str
    git: GitConfig
    llm: LLMConfig
