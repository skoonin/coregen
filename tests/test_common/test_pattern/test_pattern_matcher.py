"""Tests for pattern matcher factory."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from coregen.common.pattern.matchers import (
    ComponentMatcher,
    ContextMatcher,
    WorkspaceMatcher,
)
from coregen.common.pattern.pattern_matcher import PatternMatcherFactory


@pytest.fixture
def setup_factory() -> Any:
    """Set up test environment."""
    mock_config_access = MagicMock()
    mock_console = MagicMock()
    mock_logger = MagicMock()
    root_path = Path("/tmp/test")

    factory = PatternMatcherFactory(
        config_access=mock_config_access,
        root_path=root_path,
        console=mock_console,
        logger=mock_logger,
    )

    return {
        "mock_config_access": mock_config_access,
        "mock_console": mock_console,
        "mock_logger": mock_logger,
        "root_path": root_path,
        "factory": factory,
    }


class TestPatternMatcherFactory:
    """Tests for PatternMatcherFactory."""

    def test_create_workspace_matcher(self, setup_factory):
        """Test creating a WorkspaceMatcher."""
        factory = setup_factory["factory"]
        mock_config_access = setup_factory["mock_config_access"]

        matcher = factory.create_matcher("workspace/aws")

        assert isinstance(matcher, WorkspaceMatcher)
        assert matcher.config_access == mock_config_access

    def test_create_context_matcher(self, setup_factory):
        """Test creating a ContextMatcher."""
        factory = setup_factory["factory"]
        mock_config_access = setup_factory["mock_config_access"]

        matcher = factory.create_matcher("context/aws-cluster-dev")

        assert isinstance(matcher, ContextMatcher)
        assert matcher.config_access == mock_config_access

    def test_create_component_matcher(self, setup_factory):
        """Test creating a ComponentMatcher."""
        factory = setup_factory["factory"]
        mock_config_access = setup_factory["mock_config_access"]

        matcher = factory.create_matcher("component/prometheus")

        assert isinstance(matcher, ComponentMatcher)
        assert matcher.config_access == mock_config_access

    def test_create_matcher_invalid_pattern(self, setup_factory):
        """Test creating a matcher with an invalid pattern."""
        factory = setup_factory["factory"]

        with pytest.raises(ValueError):
            factory.create_matcher("")

    def test_logging(self, setup_factory):
        """Test that appropriate logging happens."""
        factory = setup_factory["factory"]
        mock_logger = setup_factory["mock_logger"]

        # Testing with real implementation but invalid pattern type
        factory.parser = MagicMock()
        mock_spec = MagicMock()
        mock_spec.pattern_type = "INVALID"  # This is not a valid PatternType enum value
        factory.parser.parse.return_value = mock_spec

        # Test that ValueError is raised and logged
        with pytest.raises(ValueError):
            factory.create_matcher("invalid_pattern")

        # Verify debug and error logging
        assert mock_logger.debug.call_count >= 1
        assert mock_logger.error.call_count >= 1
        assert mock_logger.error.call_count == 1
