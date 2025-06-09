"""LLM client for agent communication.

This module provides a simple LLM client interface that can be used
by different agents to communicate with language models.
"""


class LLMClient:
    """Simple LLM client for agent communication."""

    def __init__(self, backend: str, model: str) -> None:
        """Initialize the LLM client.

        Args:
            backend: The backend to use (e.g., 'ollama', 'llama-cpp')
            model: The model name
        """
        self.backend = backend
        self.model = model

    def complete(self, prompt: str) -> str:
        """Generate a completion for the given prompt.

        Args:
            prompt: The input prompt

        Returns:
            The generated completion
        """
        # This will be properly implemented later
        return "Mock response"
