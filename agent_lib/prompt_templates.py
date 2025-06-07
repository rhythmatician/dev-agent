"""Prompt templates for dev-agent LLM interactions.

This module contains all the prompt templates used by the LLM patch generator
for different types of errors and contexts. Following the architecture
specified in docs/AGENT-ARCHITECTURE.md.

Templates support variable substitution and are optimized for code generation
tasks with local LLMs.
"""

# Discovery error prompt template
DISCOVERY_ERROR_TEMPLATE = """Pytest failed during discovery with this error:
{error_excerpt}

Task:
1. Fix the above syntax/import issue in {file_path}.
2. Do not change any other files.
3. Return a unified diff only.

Previous attempts to fix `{file_path}`:
{patch_history}

Context from {file_path}:
{full_context}

Instructions:
- Ensure the patch compiles without syntax errors
- Follow black formatting and flake8 linting standards
- Only change what's still broken
- If no changes are needed, respond with "NO_PATCH_NEEDED"

Generate a unified diff patch:"""

# Regular test failure prompt template
TEST_FAILURE_TEMPLATE = """Test failure detected:

Test: {test_name}
File: {file_path}
Error: {error_output}

Previous attempts to fix `{file_path}`:
{patch_history}

Full context from {file_path}:
{full_context}

Task:
1. Analyze the test failure and identify the root cause
2. Generate a minimal unified diff patch to fix the issue
3. Ensure the patch compiles without syntax errors
4. Follow black formatting and flake8 linting standards
5. Only change what's necessary to fix the failing test

If no changes are needed, respond with "NO_PATCH_NEEDED"

Generate a unified diff patch:"""

# Retry prompt for syntax errors
SYNTAX_ERROR_RETRY_TEMPLATE = """{original_prompt}

IMPORTANT: Your previous patch had syntax errors.
Please ensure the patch compiles without syntax errors.

Previous invalid patch:
{previous_patch}

Generate a corrected unified diff patch:"""

# Retry prompt for format/lint errors
FORMAT_LINT_RETRY_TEMPLATE = """{original_prompt}

IMPORTANT: Your patch broke formatting or linting.
Please adjust so that it passes `black` and `flake8` without changing style elsewhere.

Format/lint errors:
{format_lint_errors}

Previous patch that failed checks:
{previous_patch}

Generate a corrected unified diff patch:"""


def format_discovery_error_prompt(
    error_excerpt: str, file_path: str, full_context: str, patch_history: str = ""
) -> str:
    """Format a discovery error prompt with the given parameters."""
    return DISCOVERY_ERROR_TEMPLATE.format(
        error_excerpt=error_excerpt,
        file_path=file_path,
        full_context=full_context,
        patch_history=patch_history or "None",
    )


def format_test_failure_prompt(
    test_name: str,
    file_path: str,
    error_output: str,
    full_context: str,
    patch_history: str = "",
) -> str:
    """Format a test failure prompt with the given parameters."""
    return TEST_FAILURE_TEMPLATE.format(
        test_name=test_name,
        file_path=file_path,
        error_output=error_output,
        full_context=full_context,
        patch_history=patch_history or "None",
    )


def format_syntax_error_retry_prompt(original_prompt: str, previous_patch: str) -> str:
    """Format a retry prompt for syntax errors."""
    return SYNTAX_ERROR_RETRY_TEMPLATE.format(
        original_prompt=original_prompt, previous_patch=previous_patch
    )


def format_format_lint_retry_prompt(
    original_prompt: str, format_lint_errors: str, previous_patch: str
) -> str:
    """Format a retry prompt for format/lint errors."""
    return FORMAT_LINT_RETRY_TEMPLATE.format(
        original_prompt=original_prompt,
        format_lint_errors=format_lint_errors,
        previous_patch=previous_patch,
    )
