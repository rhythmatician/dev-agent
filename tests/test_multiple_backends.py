"""Tests for the multiple backend support in dev_agent.py.

This test suite covers the functions related to handling multiple
LLM backend integrations, particularly for the Phase 5 requirement
of supporting both llama-cpp and Ollama backends.
"""

import pytest

import dev_agent


class TestMultipleBackendSupport:
    """Test suite for multiple LLM backend support."""

    @pytest.mark.parametrize(
        "model_path,expected_backend,expected_model",
        [
            ("llama-cpp:codellama-13b.gguf", "llama-cpp", "codellama-13b"),
            ("ollama:phi", "ollama", "phi"),
            ("models/codellama.gguf", "llama-cpp", "codellama"),
            ("/path/to/models/mistral.gguf", "llama-cpp", "mistral"),
            (
                "llama-cpp:/models/codellama-13b.Q4_K_M.gguf",
                "llama-cpp",
                "codellama-13b.Q4_K_M",
            ),
        ],
    )
    def test_parse_model_path(
        self, model_path: str, expected_backend: str, expected_model: str
    ) -> None:
        """Test parsing model paths with different formats."""
        backend, model_name = dev_agent._parse_model_path(model_path)
        assert backend == expected_backend
        assert model_name == expected_model
