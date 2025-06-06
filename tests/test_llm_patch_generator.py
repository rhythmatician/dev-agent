"""Tests for the LLM patch generator module.

This test suite covers the functionality for generating code patches
using a local LLM based on test failure information. Following TDD
principles as outlined in docs/PROJECT-OUTLINE.md Phase 2.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_lib.llm_patch_generator import (
    LLMPatchGenerator,
    PatchGenerationError,
    PatchResult,
)
from agent_lib.test_runner import TestFailure


class TestLLMPatchGenerator:
    """Test suite for LLM patch generator functionality."""

    def test_create_patch_generator_with_model_path(self) -> None:
        """Test creating patch generator with a model path."""

        model_path = "test/model/path.gguf"
        generator = LLMPatchGenerator(model_path=model_path)
        assert generator.model_path == model_path

    def test_generate_patch_from_test_failure(self) -> None:
        """Test generating a patch from a test failure."""
        # Setup
        generator = LLMPatchGenerator(model_path="test_model.gguf")

        test_failure = TestFailure(
            test_name="test_example",
            file_path="test_example.py",
            error_output="AssertionError: assert 1 == 2",
        )

        repo_path = Path("/test/repo")

        # Mock the LLM call to return a sample diff
        with patch.object(generator, "_call_llm") as mock_llm:
            mock_llm.return_value = """diff --git a/example.py b/example.py
index 1234567..abcdefg 100644
--- a/example.py
+++ b/example.py
@@ -1,3 +1,3 @@
 def example_function():
-    return 1
+    return 2
"""

            result = generator.generate_patch(test_failure, repo_path)

            assert isinstance(result, PatchResult)
            assert result.diff_content is not None
            assert "def example_function():" in result.diff_content
            assert "return 2" in result.diff_content

    def test_validate_patch_with_git_apply_check(self) -> None:
        """Test patch validation using git apply --check."""
        generator = LLMPatchGenerator(model_path="test_model.gguf")

        valid_diff = """diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,3 @@
 def test_func():
-    return False
+    return True
"""

        repo_path = Path("/test/repo")

        # Mock successful git apply --check
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            is_valid = generator.validate_patch(valid_diff, repo_path)

            assert is_valid is True
            mock_run.assert_called_once()
            # Verify git apply --check was called
            call_args = mock_run.call_args[0][0]
            assert "git" in call_args
            assert "apply" in call_args
            assert "--check" in call_args

    def test_validate_patch_fails_with_invalid_diff(self) -> None:
        """Test patch validation fails with invalid diff."""
        generator = LLMPatchGenerator(model_path="test_model.gguf")

        invalid_diff = "not a valid diff"
        repo_path = Path("/test/repo")

        # Mock failed git apply --check
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            is_valid = generator.validate_patch(invalid_diff, repo_path)

            assert is_valid is False

    def test_generate_patch_raises_error_on_llm_failure(self) -> None:
        """Test that patch generation raises error when LLM fails."""
        generator = LLMPatchGenerator(model_path="test_model.gguf")

        test_failure = TestFailure(
            test_name="test_example", file_path="test_example.py", error_output="Error"
        )

        # Mock LLM failure
        with patch.object(generator, "_call_llm") as mock_llm:
            mock_llm.side_effect = Exception("LLM connection failed")

            with pytest.raises(PatchGenerationError):
                generator.generate_patch(test_failure, Path("/test/repo"))

    @pytest.mark.parametrize("model_backend", ["llama-cpp", "ollama"])
    def test_supports_different_model_backends(self, model_backend: str) -> None:
        """Test support for different LLM backends."""
        model_path = f"{model_backend}:test-model"
        generator = LLMPatchGenerator(model_path=model_path)

        assert generator.model_path == model_path
        # Should not raise an exception during initialization
