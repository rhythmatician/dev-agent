"""Sanity test to mark Phase 0 completion per TDD cycle.

This module contains the initial failing test that validates the basic
scaffold structure is in place for the dev-agent project.
"""

import pytest


@pytest.mark.xfail(reason="Phase 0 scaffold - intentionally marked as expected failure")
def test_sanity_check() -> None:
    """Test that intentionally fails to mark Phase 0 TDD cycle completion.

    This test will be replaced in Phase 1 with actual functionality tests.
    It serves as a marker that the basic project scaffold is complete.
    """
    assert True is False  # Intentionally failing test for Phase 0 scaffold
