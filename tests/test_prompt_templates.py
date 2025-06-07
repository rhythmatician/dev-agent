"""Tests for the prompt_templates module."""

from agent_lib.prompt_templates import (
    format_discovery_error_prompt,
    format_syntax_error_retry_prompt,
    format_test_failure_prompt,
)


def test_format_discovery_error_prompt_includes_all_parameters():
    """Test that format_discovery_error_prompt includes all provided parameters."""
    error_excerpt = "ImportError: No module named 'missing_module'"
    file_path = "path/to/file.py"
    full_context = "def some_function():\n    import missing_module"
    patch_history = "Previous patch content"

    result = format_discovery_error_prompt(
        error_excerpt=error_excerpt,
        file_path=file_path,
        full_context=full_context,
        patch_history=patch_history,
    )

    # Check that all parameters are included in the formatted prompt
    assert error_excerpt in result
    assert file_path in result
    assert full_context in result
    assert patch_history in result


def test_format_discovery_error_prompt_with_empty_patch_history():
    """Test that format_discovery_error_prompt handles empty patch history."""
    error_excerpt = "SyntaxError: invalid syntax"
    file_path = "path/to/file.py"
    full_context = "def broken_function():\n    if True print('error')"

    result = format_discovery_error_prompt(
        error_excerpt=error_excerpt,
        file_path=file_path,
        full_context=full_context,
    )

    # Check that default "None" is used for empty patch history
    assert "Previous attempts to fix `path/to/file.py`:\nNone" in result


def test_format_test_failure_prompt_includes_all_parameters():
    """Test that format_test_failure_prompt includes all provided parameters."""
    test_name = "test_my_feature"
    file_path = "path/to/implementation.py"
    error_output = "AssertionError: Expected 42, got 24"
    full_context = "def my_feature():\n    return 24  # should be 42"
    patch_history = "Previous fix attempt"

    result = format_test_failure_prompt(
        test_name=test_name,
        file_path=file_path,
        error_output=error_output,
        full_context=full_context,
        patch_history=patch_history,
    )

    # Check that all parameters are included in the formatted prompt
    assert test_name in result
    assert file_path in result
    assert error_output in result
    assert full_context in result
    assert patch_history in result


def test_format_test_failure_prompt_with_empty_patch_history():
    """Test that format_test_failure_prompt handles empty patch history."""
    test_name = "test_another_feature"
    file_path = "path/to/implementation.py"
    error_output = "TypeError: expected str, got int"
    full_context = "def another_feature(param):\n    return param + 5"

    result = format_test_failure_prompt(
        test_name=test_name,
        file_path=file_path,
        error_output=error_output,
        full_context=full_context,
    )

    # Check that default "None" is used for empty patch history
    assert "Previous attempts to fix `path/to/implementation.py`:\nNone" in result


def test_format_syntax_error_retry_prompt_includes_all_parameters():
    """Test that format_syntax_error_retry_prompt includes all provided parameters."""
    original_prompt = "Original prompt content"
    previous_patch = "Previous patch with syntax errors"

    result = format_syntax_error_retry_prompt(
        original_prompt=original_prompt,
        previous_patch=previous_patch,
    )

    # Check that all parameters are included in the formatted prompt
    assert original_prompt in result
    assert previous_patch in result
    assert "IMPORTANT: Your previous patch had syntax errors." in result
