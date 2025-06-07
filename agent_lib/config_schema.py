"""Configuration schema definitions for dev-agent.

This module provides typed configuration schemas for the dev-agent
using TypedDict for better type checking and linting.
"""

from typing import Literal, Optional, TypedDict


class GitConfig(TypedDict):
    """Git configuration schema."""

    branch_prefix: str
    remote: str
    auto_pr: bool


class LLMConfig(TypedDict):
    """LLM configuration schema."""

    model_path: str


class MetricsConfig(TypedDict):
    """Metrics configuration schema."""

    enabled: bool
    storage_path: Optional[str]


class AgentRoleConfig(TypedDict):
    """Configuration for a specific agent role."""

    backend: Literal["ollama", "openai", "llama-cpp", "codellama"]
    model: str


class AgentsConfig(TypedDict):
    """Configuration for all agent roles."""

    supervisor: AgentRoleConfig
    dev_agent: AgentRoleConfig


class AgentConfig(TypedDict):
    """Dev-agent configuration schema."""

    max_iterations: int
    test_command: str
    git: GitConfig
    llm: LLMConfig
    metrics: MetricsConfig
    agents: AgentsConfig
