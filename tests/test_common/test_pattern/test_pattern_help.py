"""Unit tests for pattern help functionality."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from coregen.common.pattern.pattern_help import (
    PatternHelpProvider,
    provide_pattern_help,
)


@pytest.fixture
def setup_pattern_help() -> Any:
    """Set up test fixtures."""
    mock_console = MagicMock()
    provider = PatternHelpProvider(mock_console)
    return {
        "mock_console": mock_console,
        "provider": provider,
    }


class TestPatternHelpProvider:
    """Test the PatternHelpProvider class."""

    def test_init(self, setup_pattern_help):
        """Test provider initialization."""

        mock_console = setup_pattern_help["mock_console"]

        provider = setup_pattern_help["provider"]

        assert provider.console == mock_console

    def test_show_pattern_tips(self, setup_pattern_help):
        """Test showing pattern tips."""

        mock_console = setup_pattern_help["mock_console"]

        provider = setup_pattern_help["provider"]

        provider._show_general_pattern_tips()

        # Verify console methods were called
        assert mock_console.info.called
        # Check that tips contain expected content
        calls = mock_console.info.call_args_list
        call_text = " ".join([str(call) for call in calls])
        assert "Quote patterns with wildcards" in call_text

    def test_show_pattern_examples(self, setup_pattern_help):
        """Test showing pattern examples."""

        mock_console = setup_pattern_help["mock_console"]

        provider = setup_pattern_help["provider"]

        provider.show_pattern_examples()

        # Verify examples were shown
        assert mock_console.info.called

        # Check that examples contain expected patterns
        calls = mock_console.info.call_args_list
        call_text = " ".join([str(call) for call in calls])
        assert "w/" in call_text or "workspace" in call_text

    def test_show_common_issues(self, setup_pattern_help):
        """Test showing common issues."""

        mock_console = setup_pattern_help["mock_console"]

        provider = setup_pattern_help["provider"]

        provider._show_general_pattern_tips()

        # Verify issues were shown
        assert mock_console.info.called

        # Check content includes common problems
        calls = mock_console.info.call_args_list
        call_text = " ".join([str(call) for call in calls])
        assert "Quote patterns" in call_text

    def test_show_pattern_help_comprehensive(self, setup_pattern_help):
        """Test comprehensive pattern help display."""

        mock_console = setup_pattern_help["mock_console"]

        provider = setup_pattern_help["provider"]

        patterns = ["aws"]

        provider.provide_pattern_help(patterns, "Test context")

        # Verify error and info messages were called
        assert mock_console.error.called  # For error messages
        assert mock_console.info.called  # For tips

    def test_show_pattern_help_no_matches(self, setup_pattern_help):
        """Test pattern help display when no patterns match."""

        mock_console = setup_pattern_help["mock_console"]

        provider = setup_pattern_help["provider"]

        provider.provide_pattern_help(["w/nonexistent"], "Test context")

        # Should still show tips and error message
        assert mock_console.info.called
        assert mock_console.error.called


class TestProvidePatternHelpFunction:
    """Test the module-level provide_pattern_help function."""

    @patch("coregen.common.pattern.pattern_help.Console.error")
    @patch("coregen.common.pattern.pattern_help.Console.info")
    def test_provide_pattern_help_basic(self, mock_info, mock_error):
        """Test providing basic pattern help."""
        patterns = ["w/aws"]
        provide_pattern_help(patterns, additional_context="Test context")

        # Verify console methods were called
        assert mock_error.called or mock_info.called

    def test_provide_pattern_help_empty_patterns(self, setup_pattern_help):
        """Test providing pattern help with empty patterns list."""

        setup_pattern_help["mock_console"]

        setup_pattern_help["provider"]

        patterns = []
        provide_pattern_help(patterns)

        # Should return early and not crash

    @patch("coregen.common.pattern.pattern_help.Console")
    def test_provide_pattern_help_with_custom_console(self, mock_console_class):
        """Test providing pattern help with custom console."""
        custom_console = MagicMock()

        patterns = ["test-pattern"]
        provide_pattern_help(patterns, console=custom_console)

        # Should use the provided console, not create a new one
        assert not mock_console_class.called
        assert custom_console.info.called


class TestPatternHelpProviderEdgeCases:
    """Test edge cases and error conditions."""

    def test_show_pattern_help_with_none_console(self, setup_pattern_help):
        """Test pattern help provider with None console."""

        setup_pattern_help["mock_console"]

        provider = setup_pattern_help["provider"]

        with pytest.raises(AttributeError):
            provider = PatternHelpProvider(None)
            provider.show_pattern_tips()

    def test_show_pattern_help_with_long_pattern_list(self, setup_pattern_help):
        """Test pattern help with many patterns."""

        mock_console = setup_pattern_help["mock_console"]

        provider = setup_pattern_help["provider"]

        many_patterns = [f"w/pattern-{i}" for i in range(20)]

        provider.provide_pattern_help(many_patterns, "Long list test")

        # Should handle long lists gracefully
        assert mock_console.info.called


class TestPatternHelpProviderContent:
    """Test the content and formatting of help messages."""

    def test_pattern_tips_content(self, setup_pattern_help):
        """Test that pattern tips contain expected content."""

        mock_console = setup_pattern_help["mock_console"]

        provider = setup_pattern_help["provider"]

        provider._show_general_pattern_tips()

        # Get all the calls to info method
        info_calls = mock_console.info.call_args_list
        all_text = " ".join([str(call) for call in info_calls])

        # Check for key tip content
        expected_content = ["Quote patterns", "check-pattern", "*"]
        # Note: ** pattern was deprecated

        for content in expected_content:
            assert content in all_text, f"Expected '{content}' in tips"

    def test_pattern_examples_content(self, setup_pattern_help):
        """Test that pattern examples contain expected patterns."""

        mock_console = setup_pattern_help["mock_console"]

        provider = setup_pattern_help["provider"]

        provider.show_pattern_examples()

        # Get all the calls to info method
        info_calls = mock_console.info.call_args_list
        all_text = " ".join([str(call) for call in info_calls])

        # Check for example patterns with new prefix system
        expected_patterns = ["w/", "c/", "cm/", "/*"]
        # Note: /** pattern was deprecated

        for pattern in expected_patterns:
            assert pattern in all_text, f"Expected pattern '{pattern}' in examples"

    def test_common_issues_content(self, setup_pattern_help):
        """Test that common issues contain expected problems."""

        mock_console = setup_pattern_help["mock_console"]

        provider = setup_pattern_help["provider"]

        provider._show_general_pattern_tips()

        # Get all the calls to info method
        info_calls = mock_console.info.call_args_list
        all_text = " ".join([str(call) for call in info_calls])

        # Check for common issue content
        expected_issues = ["quote", "pattern", "wildcard"]

        for issue in expected_issues:
            assert (
                issue.lower() in all_text.lower()
            ), f"Expected issue '{issue}' in common issues"

    def test_prefix_system_content(self, setup_pattern_help):
        """Test that help mentions the new prefix system."""

        mock_console = setup_pattern_help["mock_console"]

        provider = setup_pattern_help["provider"]

        provider._show_general_pattern_tips()

        # Get all the calls to info method
        info_calls = mock_console.info.call_args_list
        all_text = " ".join([str(call) for call in info_calls])

        # Check for prefix system content
        expected_prefixes = ["w/", "c/", "cm/", "prefix"]

        for prefix in expected_prefixes:
            assert prefix in all_text, f"Expected prefix '{prefix}' in help content"
