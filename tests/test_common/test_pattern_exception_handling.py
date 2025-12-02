"""Test coverage for pattern system exception handling scenarios."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.common.pattern.facade import PatternMatcher


@pytest.fixture
def setup_pattern_exception() -> Any:
    """Set up test environment."""
    return {
        "mock_config_access": MagicMock(),
        "mock_console": MagicMock(spec=Console),
        "mock_logger": MagicMock(spec=Logger),
        "root_path": Path("/test/root"),
    }


class TestPatternExceptionHandling:
    """Test specific exception handling scenarios in pattern system."""

    def test_pattern_matcher_general_exception_handling(self, setup_pattern_exception):
        """Test general exception handling in PatternMatcher."""
        mock_config_access = setup_pattern_exception["mock_config_access"]
        mock_console = setup_pattern_exception["mock_console"]
        mock_logger = setup_pattern_exception["mock_logger"]
        root_path = setup_pattern_exception["root_path"]

        pattern_matcher = PatternMatcher(
            config_access=mock_config_access,
            root_path=root_path,
            console=mock_console,
            logger=mock_logger,
            verbose=False,
        )

        # Test that exceptions during pattern matching are caught and logged
        with patch.object(
            pattern_matcher.factory,
            "create_matcher",
            side_effect=Exception("Test error"),
        ):
            result = pattern_matcher.match("workspace/test")

            # Should return empty result on error
            assert result == {"workspaces": {}, "contexts": {}, "components": {}}

            # Should log the error
            mock_logger.error.assert_called_with(
                "Error matching pattern 'workspace/test': Test error"
            )
