"""Unit tests for PatternMatcher with settings-based defaults."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from coregen.common.pattern.facade import PatternMatcher
from coregen.config_model.access import ConfigAccess


class TestPatternMatcherSettings:
    """Test the PatternMatcher class with settings integration."""

    def test_pattern_matcher_uses_settings_defaults(self, mock_settings):
        """Test that PatternMatcher uses settings for default values."""
        # Configure mock_settings for this test - verbose=True
        mock_settings.options.global_options.verbose = True

        # Patch get_settings at the point of use (where PatternMatcher imports it)
        # This is necessary because get_settings() is called during __init__
        with patch(
            "coregen.common.pattern.facade.get_settings", return_value=mock_settings
        ):
            # Create mock dependencies
            mock_config_access = MagicMock(spec=ConfigAccess)
            mock_root_path = Path("/mock/root")
            mock_console = MagicMock()
            mock_logger = MagicMock()

            # Create PatternMatcher with None for verbose parameter
            pattern_matcher = PatternMatcher(
                config_access=mock_config_access,
                root_path=mock_root_path,
                console=mock_console,
                logger=mock_logger,
                verbose=None,  # Should use settings default
            )

            # Verify that verbose is set to settings value
            assert pattern_matcher.verbose is True
            assert (
                pattern_matcher.verbose == mock_settings.options.global_options.verbose
            )

    def test_pattern_matcher_parameter_overrides(self, mock_settings):
        """Test that explicit parameters override settings defaults."""
        # Configure mock_settings with verbose=True so we can test override with False
        mock_settings.options.global_options.verbose = True

        # Patch get_settings at the point of use
        with patch(
            "coregen.common.pattern.facade.get_settings", return_value=mock_settings
        ):
            # Create mock dependencies
            mock_config_access = MagicMock(spec=ConfigAccess)
            mock_root_path = Path("/mock/root")
            mock_console = MagicMock()
            mock_logger = MagicMock()

            # Create PatternMatcher with explicit verbose parameter
            explicit_verbose = False  # Different from settings default
            pattern_matcher = PatternMatcher(
                config_access=mock_config_access,
                root_path=mock_root_path,
                console=mock_console,
                logger=mock_logger,
                verbose=explicit_verbose,  # Should override settings
            )

            # Verify that verbose is set to explicit value, not settings value
            assert pattern_matcher.verbose is False
            assert pattern_matcher.verbose == explicit_verbose
            assert (
                pattern_matcher.verbose != mock_settings.options.global_options.verbose
            )
