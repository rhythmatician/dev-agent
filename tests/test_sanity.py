"""Sanity test to mark RED phase for Phase 0 TDD cycle."""

import pytest


@pytest.mark.xfail(reason="Phase 0 scaffold - intentionally marked as expected failure")
def test_sanity_check():
    """This test intentionally fails to mark the RED phase of TDD."""
    assert True is False  # Intentionally failing test for RED phase
