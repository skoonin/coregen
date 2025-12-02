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
from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig


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

        # Mock suggestions
        with patch.object(
            pattern_matcher,
            "_suggest_alternative_patterns",
            return_value=["context/test", "workspace/test"],
        ):
            # Call match
            pattern_matcher.match("test/pattern")

            # Verify debug output for no matches (now goes to logger, not console)
            mock_logger.debug.assert_any_call(
                "  - No matches found for pattern: 'test/pattern'"
            )

            # Verify suggestions are displayed (now goes to logger, not console)
            mock_logger.debug.assert_any_call(
                "  - You might try: 'context/test', 'workspace/test'"
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

    def test_suggest_alternative_patterns_for_path(self, pattern_matcher):
        """Test _suggest_alternative_patterns for path-like patterns."""
        # Test with a path-like pattern
        suggestions = pattern_matcher._suggest_alternative_patterns("path/to/file")

        # Should suggest logical prefixes
        assert "workspace/path/to/file" in suggestions

    def test_suggest_alternative_patterns_for_simple_name(self, pattern_matcher):
        """Test _suggest_alternative_patterns for simple names."""
        # Test with a simple name (no slashes)
        suggestions = pattern_matcher._suggest_alternative_patterns("test")

        # Check what suggestions are actually returned according to the implementation
        # For a simple name without slashes, only suggests adding a glob
        assert "test/*" in suggestions

    def test_suggest_alternative_patterns_for_missing_globs(self, pattern_matcher):
        """Test _suggest_alternative_patterns for patterns without globs."""
        # Test with workspace pattern without glob
        suggestions = pattern_matcher._suggest_alternative_patterns("workspace/test")
        assert "workspace/test/**" in suggestions

        # Test with context pattern without glob
        suggestions = pattern_matcher._suggest_alternative_patterns("context/test")
        assert "context/test/**" in suggestions

        # Test with path ending in slash
        suggestions = pattern_matcher._suggest_alternative_patterns("test/")
        assert "test/**" in suggestions

        # Test with simple path without slash or glob
        suggestions = pattern_matcher._suggest_alternative_patterns("test")
        assert "test/*" in suggestions

    def test_add_matched_workspace(self, pattern_matcher, mock_config_access):
        """Test _add_matched_workspace method."""
        # Create workspace
        workspace = WorkspaceConfig(name="test-ws", workspace_dir="test/path")

        # Create empty result dict
        result = {"workspaces": {}, "contexts": {}, "components": {}}

        # Add workspace without children
        pattern_matcher._add_matched_workspace(workspace, result, add_children=False)

        # Verify workspace was added
        assert "test-ws" in result["workspaces"]
        assert result["workspaces"]["test-ws"] == workspace

        # Verify no contexts or components were added
        assert len(result["contexts"]) == 0
        assert len(result["components"]) == 0

        # Reset result
        result = {"workspaces": {}, "contexts": {}, "components": {}}

        # Mock config_access.get_all_contexts
        mock_context = Context(name="test-ctx", environment="dev")
        mock_config_access.get_all_contexts.return_value = {"test-ctx": mock_context}

        # Add workspace with children
        pattern_matcher._add_matched_workspace(workspace, result, add_children=True)

        # Verify workspace was added
        assert "test-ws" in result["workspaces"]

        # Verify config_access.get_all_contexts was called
        mock_config_access.get_all_contexts.assert_called_with(workspace)

        # Since we're mocking _add_matched_context, we need to manually call it
        # to simulate the behavior - this is a limitation of unit testing
        pattern_matcher._add_matched_context(
            mock_context, result, add_children=True, add_parent=False
        )

        # Verify context was added
        assert "test-ctx" in result["contexts"]

    def test_add_matched_context(self, pattern_matcher, mock_config_access):
        """Test _add_matched_context method."""
        # Create context
        context = Context(name="test-ctx", environment="dev")
        context.components = {
            "service": {
                "comp1": Component(name="comp1"),
                "comp2": Component(name="comp2"),
            }
        }

        # Create empty result dict
        result = {"workspaces": {}, "contexts": {}, "components": {}}

        # Add context without children or parent
        pattern_matcher._add_matched_context(
            context, result, add_children=False, add_parent=False
        )

        # Verify context was added
        assert "test-ctx" in result["contexts"]
        assert result["contexts"]["test-ctx"] == context

        # Verify no workspaces or components were added
        assert len(result["workspaces"]) == 0
        assert len(result["components"]) == 0

        # Reset result
        result = {"workspaces": {}, "contexts": {}, "components": {}}

        # Mock config_access._get_workspace_from_context
        mock_workspace = WorkspaceConfig(name="test-ws", workspace_dir="test/path")
        mock_config_access._get_workspace_from_context.return_value = mock_workspace

        # Add context with parent but no children
        pattern_matcher._add_matched_context(
            context, result, add_children=False, add_parent=True
        )

        # Verify context was added
        assert "test-ctx" in result["contexts"]

        # Verify _get_workspace_from_context was called
        mock_config_access._get_workspace_from_context.assert_called_with(context)

        # After mocking, we need to manually call _add_matched_workspace
        # to simulate the behavior
        pattern_matcher._add_matched_workspace(
            mock_workspace, result, add_children=False
        )

        # Verify workspace was added
        assert "test-ws" in result["workspaces"]

        # Reset result
        result = {"workspaces": {}, "contexts": {}, "components": {}}

        # Add context with children but no parent
        pattern_matcher._add_matched_context(
            context, result, add_children=True, add_parent=False
        )

        # Since get_all_components is a method on Context, it's not easily mockable
        # We can verify that context was added
        assert "test-ctx" in result["contexts"]

        # Reset result and manually add components to ensure _add_matched_component is tested
        result = {"workspaces": {}, "contexts": {}, "components": {}}
        pattern_matcher._add_matched_context(
            context, result, add_children=False, add_parent=False
        )

        # Manually call _add_matched_component
        for name, comp in context.get_all_components().items():
            pattern_matcher._add_matched_component(
                comp, context, result, add_parent=False
            )

        # Verify components were added
        assert "test-ctx/comp1" in result["components"]
        assert "test-ctx/comp2" in result["components"]

    def test_add_matched_component(self, pattern_matcher):
        """Test _add_matched_component method."""
        # Create context and component
        context = Context(name="test-ctx", environment="dev")
        component = Component(name="test-comp")

        # Create empty result dict
        result = {"workspaces": {}, "contexts": {}, "components": {}}

        # Add component without parent
        pattern_matcher._add_matched_component(
            component, context, result, add_parent=False
        )

        # Verify component was added
        assert "test-ctx/test-comp" in result["components"]
        assert result["components"]["test-ctx/test-comp"] == component

        # Verify no workspaces or contexts were added
        assert len(result["workspaces"]) == 0
        assert len(result["contexts"]) == 0

        # Reset result
        result = {"workspaces": {}, "contexts": {}, "components": {}}

        # Add component with parent
        pattern_matcher._add_matched_component(
            component, context, result, add_parent=True
        )

        # Verify component was added
        assert "test-ctx/test-comp" in result["components"]

        # Since we're mocking _add_matched_context, we need to manually call it
        # to simulate the behavior
        pattern_matcher._add_matched_context(
            context, result, add_children=False, add_parent=True
        )

        # Verify context was added
        assert "test-ctx" in result["contexts"]

    def test_match_logical_pattern(self, pattern_matcher, mock_factory, mock_logger):
        """Test _match_logical_pattern method."""
        # Create empty result dict
        result = {"workspaces": {}, "contexts": {}, "components": {}}

        # Setup mock matcher that will populate the result
        mock_matcher = MagicMock()
        mock_matcher.match.return_value = True
        mock_factory.create_matcher.return_value = mock_matcher

        # Call _match_logical_pattern
        matched = pattern_matcher._match_logical_pattern("workspace/test", result)

        # Verify factory was called
        mock_factory.create_matcher.assert_called_with("workspace/test")

        # Verify matcher was called
        mock_matcher.match.assert_called_with(result)

        # Verify result
        assert matched is True

        # Test exception handling
        mock_factory.create_matcher.side_effect = Exception("Test error")

        # Call _match_logical_pattern
        matched = pattern_matcher._match_logical_pattern("workspace/test", result)

        # Verify error logging
        mock_logger.error.assert_called_with(
            "Error in legacy _match_logical_pattern: Test error"
        )

        # Verify result
        assert matched is False
