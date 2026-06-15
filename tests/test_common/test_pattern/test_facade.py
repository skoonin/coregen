"""
Tests for the PatternMatcher class in the facade module.

This module tests the PatternMatcher implementation that serves as the facade for
our pattern matching system.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from coregen.common.pattern.facade import PatternMatcher


@pytest.fixture
def root_path() -> Any:
    """Root path for pattern matching."""
    return Path("/test/root")


@pytest.fixture
def mock_factory() -> Any:
    """Mock factory to control matcher creation and behavior."""
    return MagicMock()


@pytest.fixture
def pattern_matcher(
    mock_config_access, root_path, mock_console, mock_logger, mock_factory
) -> Any:
    """Create PatternMatcher instance with non-verbose output."""
    matcher = PatternMatcher(
        config_access=mock_config_access,
        root_path=root_path,
        console=mock_console,
        logger=mock_logger,
        verbose=False,
    )
    matcher.factory = mock_factory
    return matcher


@pytest.fixture
def verbose_pattern_matcher(
    mock_config_access, root_path, mock_console, mock_logger, mock_factory
) -> Any:
    """Create PatternMatcher instance with verbose output enabled."""
    matcher = PatternMatcher(
        config_access=mock_config_access,
        root_path=root_path,
        console=mock_console,
        logger=mock_logger,
        verbose=True,
    )
    matcher.factory = mock_factory
    return matcher


class TestPatternMatcher:
    """Tests for PatternMatcher class."""

    def test_initialization(
        self, mock_config_access, root_path, mock_console, mock_logger
    ):
        """Test PatternMatcher initialization with factory creation."""
        with patch(
            "coregen.common.pattern.facade.PatternMatcherFactory"
        ) as factory_mock:
            # Create instance
            pattern_matcher = PatternMatcher(
                config_access=mock_config_access,
                root_path=root_path,
                console=mock_console,
                logger=mock_logger,
                verbose=False,
            )

            # Verify factory was created with correct parameters
            factory_mock.assert_called_once_with(
                mock_config_access,
                root_path,
                mock_console,
                mock_logger,
            )

            # Verify instance attributes
            assert pattern_matcher.config_access == mock_config_access
            assert pattern_matcher.root_path == root_path
            assert pattern_matcher.console == mock_console
            assert pattern_matcher.logger == mock_logger
            assert pattern_matcher.verbose is False
            assert pattern_matcher.factory == factory_mock.return_value

    def test_match_success(self, pattern_matcher, mock_factory, mock_logger):
        """Test match method with successful match."""
        # Setup mock matcher that will populate the result
        mock_matcher = MagicMock()

        def populate_result(result):
            result["workspaces"]["ws1"] = {"name": "ws1"}
            result["contexts"]["ctx1"] = {"name": "ctx1"}
            result["components"]["ctx1/comp1"] = {"name": "comp1"}
            return True

        mock_matcher.match.side_effect = populate_result
        mock_factory.create_matcher.return_value = mock_matcher

        # Call match
        result = pattern_matcher.match("test/pattern")

        # Verify factory was called
        mock_factory.create_matcher.assert_called_once_with("test/pattern")

        # Verify matcher was called
        mock_matcher.match.assert_called_once()

        # Verify result structure
        assert "workspaces" in result
        assert "contexts" in result
        assert "components" in result
        assert "ws1" in result["workspaces"]
        assert "ctx1" in result["contexts"]
        assert "ctx1/comp1" in result["components"]

        # Verify logging
        mock_logger.debug.assert_any_call(
            "PatternMatcher: Processing pattern: test/pattern"
        )
        mock_logger.debug.assert_any_call(
            "Pattern 'test/pattern' matched successfully."
        )

    def test_match_verbose_output(
        self, verbose_pattern_matcher, mock_factory, mock_logger
    ):
        """Test match method with verbose output."""
        # Setup mock matcher that will populate the result
        mock_matcher = MagicMock()

        def populate_result(result):
            result["workspaces"]["ws1"] = {"name": "ws1"}
            result["workspaces"]["ws2"] = {"name": "ws2"}
            result["contexts"]["ctx1"] = {"name": "ctx1"}
            result["contexts"]["ctx2"] = {"name": "ctx2"}
            result["components"]["ctx1/comp1"] = {"name": "comp1"}
            result["components"]["ctx2/comp2"] = {"name": "comp2"}
            return True

        mock_matcher.match.side_effect = populate_result
        mock_factory.create_matcher.return_value = mock_matcher

        # Call match on verbose pattern matcher
        verbose_pattern_matcher.match("test/pattern")

        # Verify verbose logger output (verbose output now goes to logger, not console)
        mock_logger.debug.assert_any_call("  - Matched 2 workspace(s): ['ws1', 'ws2']")
        mock_logger.debug.assert_any_call("  - Matched 2 context(s): ['ctx1', 'ctx2']")
        mock_logger.debug.assert_any_call("  - Matched 2 component(s)")

    def test_match_no_matches(self, pattern_matcher, mock_factory, mock_logger):
        """Test match method with no matches."""
        # Setup mock matcher that will not populate the result
        mock_matcher = MagicMock()
        mock_matcher.match.return_value = False
        mock_factory.create_matcher.return_value = mock_matcher

        # Call match
        pattern_matcher.match("test/pattern")

        # Verify debug output for no matches (now goes to logger, not console)
        mock_logger.debug.assert_any_call(
            "  - No matches found for pattern: 'test/pattern'"
        )

    def test_match_with_glob_patterns(self, pattern_matcher, mock_logger):
        """Test match method with glob patterns."""
        # Test recursive glob pattern
        pattern_matcher.match("test/**")
        mock_logger.debug.assert_any_call(
            "PatternMatcher: Processing recursive glob pattern: test/**"
        )

        # Test simple glob pattern
        pattern_matcher.match("test/*")
        mock_logger.debug.assert_any_call(
            "PatternMatcher: Processing glob pattern: test/*"
        )

    def test_match_exception_handling(self, pattern_matcher, mock_factory, mock_logger):
        """Test match method with exception handling."""
        # Setup mock factory to raise exception
        mock_factory.create_matcher.side_effect = Exception("Test error")

        # Call match - should catch the exception
        result = pattern_matcher.match("test/pattern")

        # Verify error logging
        mock_logger.error.assert_called_with(
            "Error matching pattern 'test/pattern': Test error"
        )

        # Verify empty result structure
        assert "workspaces" in result
        assert "contexts" in result
        assert "components" in result
        assert len(result["workspaces"]) == 0
        assert len(result["contexts"]) == 0
        assert len(result["components"]) == 0

    def test_match_verbose_exception_handling(
        self, verbose_pattern_matcher, mock_factory, mock_logger
    ):
        """Test verbose match method with exception handling."""
        # Setup mock factory to raise exception
        mock_factory.create_matcher.side_effect = Exception("Test error")

        # Call match on verbose pattern matcher - should catch the exception
        verbose_pattern_matcher.match("test/pattern")

        # Verify verbose error output (now goes to logger, not console)
        mock_logger.debug.assert_called_with("  - Error details: Test error")
