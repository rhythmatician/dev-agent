"""Tests for expanded prompt context functionality.

This test suite validates the enhanced LLM patch generator capability to
include full function/file scope in prompts for better context.
Following TDD principles for V1 enhancements.
"""

from pathlib import Path
from unittest.mock import patch

from agent_lib.llm_patch_generator import LLMPatchGenerator
from agent_lib.test_runner import TestFailure


class TestPromptContextExpansion:
    """Test suite for prompt context expansion functionality."""

    def test_build_prompt_includes_full_file_context(self) -> None:
        """Test that prompts include full file content for context."""
        generator = LLMPatchGenerator(model_path="test_model.gguf")

        test_failure = TestFailure(
            test_name="test_example",
            file_path="example.py",
            error_output="AssertionError: assert 1 == 2",
        )

        # Mock file content
        file_content = """def example_function():
    '''A simple example function.'''
    return 1

def other_function():
    '''Another function for context.'''
    return "hello"

def test_example():
    assert example_function() == 2
"""

        with patch("pathlib.Path.read_text", return_value=file_content):

            prompt = generator._build_prompt(test_failure, Path("/test/repo"))

            # Should include the full file content
            assert "def example_function():" in prompt
            assert "def other_function():" in prompt
            assert "def test_example():" in prompt
            assert "A simple example function." in prompt

    def test_build_prompt_includes_function_scope_context(self) -> None:
        """Test that prompts identify and highlight the specific function."""
        generator = LLMPatchGenerator(model_path="test_model.gguf")

        test_failure = TestFailure(
            test_name="test_calculation",
            file_path="calculator.py",
            error_output="AssertionError: Expected 10, got 5",
        )

        # Mock file content with multiple functions
        file_content = """def add(a, b):
    '''Add two numbers.'''
    return a + b

def multiply(a, b):
    '''Multiply two numbers.'''
    return a + b  # BUG: should be a * b

def subtract(a, b):
    '''Subtract two numbers.'''
    return a - b
"""

        with patch("pathlib.Path.read_text", return_value=file_content):
            prompt = generator._build_prompt(test_failure, Path("/test/repo"))

            # Should include all functions for context
            assert "def add(a, b):" in prompt
            assert "def multiply(a, b):" in prompt
            assert "def subtract(a, b):" in prompt

            # Should include docstrings and comments
            assert "Add two numbers." in prompt
            assert "BUG: should be a * b" in prompt

    def test_build_prompt_handles_missing_file_gracefully(self) -> None:
        """Test that prompt building handles missing files gracefully."""
        generator = LLMPatchGenerator(model_path="test_model.gguf")

        test_failure = TestFailure(
            test_name="test_nonexistent",
            file_path="nonexistent.py",
            error_output="ModuleNotFoundError",
        )

        with patch("pathlib.Path.read_text", side_effect=FileNotFoundError()):
            prompt = generator._build_prompt(test_failure, Path("/test/repo"))

            # Should still include basic test information
            assert "test_nonexistent" in prompt
            assert "nonexistent.py" in prompt
            assert "ModuleNotFoundError" in prompt

            # Should include a note about missing file
            assert "file content not available" in prompt.lower()
