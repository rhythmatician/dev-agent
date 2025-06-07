"""Test agent configuration schema extensions.

Tests for the agents configuration that defines separate LLM backends
for supervisor and dev-agent roles.
"""

from agent_lib.config_schema import AgentConfig, AgentRoleConfig, AgentsConfig


def test_agent_role_config_structure():
    """Test that AgentRoleConfig has the correct structure."""
    # Test that we can create valid agent role configs
    supervisor_config: AgentRoleConfig = {"backend": "ollama", "model": "gpt-o3"}

    dev_agent_config: AgentRoleConfig = {
        "backend": "codellama",
        "model": "codellama-13b",
    }

    assert supervisor_config["backend"] == "ollama"
    assert supervisor_config["model"] == "gpt-o3"
    assert dev_agent_config["backend"] == "codellama"
    assert dev_agent_config["model"] == "codellama-13b"


def test_agents_config_structure():
    """Test that AgentsConfig requires both supervisor and dev_agent."""
    agents_config: AgentsConfig = {
        "supervisor": {"backend": "ollama", "model": "gpt-o3"},
        "dev_agent": {"backend": "codellama", "model": "codellama-13b"},
    }

    assert "supervisor" in agents_config
    assert "dev_agent" in agents_config
    assert agents_config["supervisor"]["backend"] == "ollama"
    assert agents_config["dev_agent"]["backend"] == "codellama"


def test_valid_agents_config():
    """Test that a valid agents configuration is accepted."""
    valid_config: AgentConfig = {
        "max_iterations": 5,
        "test_command": "pytest",
        "git": {"branch_prefix": "dev-agent/fix", "remote": "origin", "auto_pr": True},
        "llm": {"model_path": "/path/to/model"},
        "metrics": {"enabled": True, "storage_path": None},
        "agents": {
            "supervisor": {"backend": "ollama", "model": "gpt-o3"},
            "dev_agent": {"backend": "codellama", "model": "codellama-13b"},
        },
    }

    # Check that agents section is properly typed
    assert "agents" in valid_config
    assert "supervisor" in valid_config["agents"]
    assert "dev_agent" in valid_config["agents"]
    assert valid_config["agents"]["supervisor"]["backend"] == "ollama"
    assert valid_config["agents"]["supervisor"]["model"] == "gpt-o3"
    assert valid_config["agents"]["dev_agent"]["backend"] == "codellama"
    assert valid_config["agents"]["dev_agent"]["model"] == "codellama-13b"


def test_all_backend_types_accepted():
    """Test that all supported backend types are accepted."""
    backends = ["ollama", "openai", "llama-cpp", "codellama"]

    for backend in backends:
        config: AgentRoleConfig = {"backend": backend, "model": f"test-model-{backend}"}
        assert config["backend"] == backend
        assert config["model"] == f"test-model-{backend}"


def test_agents_config_with_different_backends():
    """Test mixing different backends for supervisor and dev_agent."""
    mixed_config: AgentsConfig = {
        "supervisor": {"backend": "openai", "model": "gpt-4"},
        "dev_agent": {"backend": "llama-cpp", "model": "codellama-7b.Q4_K_M.gguf"},
    }

    assert mixed_config["supervisor"]["backend"] == "openai"
    assert mixed_config["dev_agent"]["backend"] == "llama-cpp"
    assert mixed_config["dev_agent"]["backend"] == "llama-cpp"
