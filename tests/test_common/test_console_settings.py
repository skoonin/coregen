"""Tests for console.py settings integration."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from coregen.cli.enums.enum_output_format import OutputFormat
from coregen.common.console import Console


@pytest.fixture(autouse=True)
def setup_console_settings() -> Any:
    """Set up test environment."""
    # Reset console state before each test
    Console._user_console = None
    Console._log_console = None
    Console.verbose_mode = False
    Console.quiet_mode = False
    Console._no_color = False
    Console.dry_run_mode = False
    Console._default_output_format = OutputFormat.TEXT


class TestConsoleSettings:
    """Tests for Console class settings integration."""

    def test_setup_with_settings_defaults(self):
        """Test that setup uses settings values when parameters are None."""
        with patch(
            "coregen.config_model.models.settings.get_settings"
        ) as mock_settings:
            # Setup mock settings with known values
            mock_settings_obj = MagicMock()
            mock_settings_obj.options.global_options.dry_run = True
            mock_settings_obj.options.global_options.quiet = True
            mock_settings_obj.options.global_options.verbose = True
            mock_settings_obj.options.global_options.no_color = True
            # output_format removed from global options
            mock_settings.return_value = mock_settings_obj

            # Call setup with all None parameters
            Console.setup(
                no_color=None,
                quiet=None,
                verbose=None,
                dry_run=None,
            )

            # Verify settings values were used
            assert Console._no_color is True
            assert Console.quiet_mode is True
            assert Console.verbose_mode is True
            assert Console.dry_run_mode is True
            # output_format is no longer set via setup

    def test_setup_with_explicit_values(self):
        """Test that setup uses explicit values over settings defaults."""
        with patch(
            "coregen.config_model.models.settings.get_settings"
        ) as mock_settings:
            # Setup mock settings with values opposite to what we'll provide
            mock_settings_obj = MagicMock()
            mock_settings_obj.options.global_options.dry_run = True
            mock_settings_obj.options.global_options.quiet = True
            mock_settings_obj.options.global_options.verbose = True
            mock_settings_obj.options.global_options.no_color = True
            # output_format removed from global options
            mock_settings.return_value = mock_settings_obj

            # Call setup with explicit parameters (opposite of settings)
            Console.setup(
                no_color=False,
                quiet=False,
                verbose=False,
                dry_run=False,
            )

            # Verify explicit values were used instead of settings
            assert Console._no_color is False
            assert Console.quiet_mode is False
            assert Console.verbose_mode is False
            assert Console.dry_run_mode is False
            # output_format is no longer set via setup

    def test_setup_with_mixed_values(self):
        """Test that setup correctly handles mix of explicit and settings values."""
        with patch(
            "coregen.config_model.models.settings.get_settings"
        ) as mock_settings:
            # Setup mock settings
            mock_settings_obj = MagicMock()
            mock_settings_obj.options.global_options.dry_run = True
            mock_settings_obj.options.global_options.quiet = True
            mock_settings_obj.options.global_options.verbose = True
            mock_settings_obj.options.global_options.no_color = True
            # output_format removed from global options
            mock_settings.return_value = mock_settings_obj

            # Call setup with some explicit parameters and some None
            Console.setup(
                no_color=False,  # Explicit, different from settings
                quiet=None,  # Use settings
                verbose=False,  # Explicit, different from settings
                dry_run=None,  # Use settings
            )

            # Verify mix of explicit and settings values
            assert Console._no_color is False  # Explicit
            assert Console.quiet_mode is True  # From settings
            assert Console.verbose_mode is False  # Explicit
            assert Console.dry_run_mode is True  # From settings
            # output_format is no longer set via setup
