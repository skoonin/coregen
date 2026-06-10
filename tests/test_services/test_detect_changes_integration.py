"""Integration tests for detect-changes command using isolated temp repos.

These tests use fixture-based temporary repositories with subprocess calls
to test the full CLI workflow that users experience.
"""

import pytest

# Subprocess-driven integration tests: real git repos, real CLI runs.
# Marked so unit-only selections exclude them and coverage attribution is clear.
pytestmark = pytest.mark.integration
