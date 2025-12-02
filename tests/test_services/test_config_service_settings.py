"""Unit tests for ConfigServiceBase with settings integration."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from coregen.cli.enums.enum_file_action import FileAction

# OutputFormat import removed - no longer used in services
from coregen.common.console import Console
from coregen.common.file_manager import FileManager
from coregen.common.workspace_initializer import WorkspaceInitializer
from coregen.config_model.provider import ConfigurationProvider
from coregen.services.config.cfg_base_service import ConfigServiceBase


class TestConfigServiceBaseSettings:
    """Test the ConfigServiceBase class with settings integration."""

    def test_settings_defaults(self, mock_settings):
        """Test ConfigServiceBase using settings for defaults."""
        # Need to use patch objects to avoid affecting original classes
        with patch(
            "coregen.config_model.models.settings.get_settings",
            return_value=mock_settings,
        ):
            # Create mocks for each component so we can check what's passed to them
            mock_console = MagicMock(spec=Console)
            mock_file_manager = MagicMock(spec=FileManager)
            mock_provider = MagicMock(spec=ConfigurationProvider)
            mock_workspace_init = MagicMock(spec=WorkspaceInitializer)

            # Create service with all None parameters to test settings defaults
            service = ConfigServiceBase(
                console=mock_console,
                file_manager=mock_file_manager,
                config_provider=mock_provider,
                workspace_initializer=mock_workspace_init,
                dry_run=None,
                file_action=None,
                quiet=None,
                verbose=None,
                no_color=None,
                config_file=None,
            )

            # Services no longer call Console.setup() - verify it wasn't called
            mock_console.setup.assert_not_called()

            # Verify service attributes match settings defaults
            assert service.dry_run == mock_settings.options.global_options.dry_run
            assert (
                service.file_action == mock_settings.options.global_options.file_action
            )
            assert service.quiet == mock_settings.options.global_options.quiet
            assert service.verbose == mock_settings.options.global_options.verbose
            # output_format removed from services
            assert service.no_color == mock_settings.options.global_options.no_color
            assert (
                service.config_file == mock_settings.options.global_options.config_file
            )

    def test_parameter_overrides(self, mock_settings):
        """Test explicit parameters overriding settings defaults."""
        # Create explicit parameters different from settings defaults
        explicit_dry_run = (
            True  # Different from mock_settings.options.global_options.dry_run
        )
        explicit_file_action = (
            FileAction.SKIP
        )  # Different from mock_settings default of OVERWRITE

        with patch(
            "coregen.config_model.models.settings.get_settings",
            return_value=mock_settings,
        ):
            # Create mocks for each component
            mock_console = MagicMock(spec=Console)
            mock_file_manager = MagicMock(spec=FileManager)
            mock_provider = MagicMock(spec=ConfigurationProvider)
            mock_workspace_init = MagicMock(spec=WorkspaceInitializer)

            # Create service with mix of explicit and None parameters
            service = ConfigServiceBase(
                console=mock_console,
                file_manager=mock_file_manager,
                config_provider=mock_provider,
                workspace_initializer=mock_workspace_init,
                dry_run=explicit_dry_run,  # Explicit value different from settings
                file_action=explicit_file_action,  # Explicit value different from settings
                # output_format removed
                quiet=None,  # Use settings default
                verbose=None,  # Use settings default
                no_color=None,  # Use settings default
                config_file=None,  # Use settings default
            )

            # Services no longer call Console.setup() - verify it wasn't called
            mock_console.setup.assert_not_called()

            # Verify service attributes match the mixed parameters
            assert service.dry_run == explicit_dry_run  # Should use explicit value
            assert (
                service.file_action == explicit_file_action
            )  # Should use explicit value
            assert (
                service.quiet == mock_settings.options.global_options.quiet
            )  # Should use settings
            assert (
                service.verbose == mock_settings.options.global_options.verbose
            )  # Should use settings
            # output_format removed from services  # Should use settings
            assert (
                service.no_color == mock_settings.options.global_options.no_color
            )  # Should use settings
            assert (
                service.config_file == mock_settings.options.global_options.config_file
            )  # Should use settings

    def test_config_file_from_settings(self):
        """Test that config_file is properly read from settings when specified."""
        # Create a fresh mock settings with a specific config file path
        test_config_path = Path("/test/path/custom-config.yaml")

        mock_settings = MagicMock()
        mock_settings.options.global_options.dry_run = False
        mock_settings.options.global_options.file_action = FileAction.OVERWRITE
        # output_format removed from services
        mock_settings.options.global_options.quiet = False
        mock_settings.options.global_options.verbose = False
        mock_settings.options.global_options.no_color = False
        mock_settings.options.global_options.config_file = test_config_path

        with patch(
            "coregen.services.config.cfg_base_service.get_settings",
            return_value=mock_settings,
        ):
            # Create service without explicit config_file parameter
            service = ConfigServiceBase()

            # Verify that the service reads config_file from settings
            assert service.config_file == test_config_path
            assert isinstance(service.config_file, Path)

    def test_config_file_parameter_overrides_settings(self):
        """Test that explicit config_file parameter overrides settings."""
        # Create mock settings with one config file path
        settings_config_path = Path("/settings/config.yaml")

        mock_settings = MagicMock()
        mock_settings.options.global_options.dry_run = False
        mock_settings.options.global_options.file_action = FileAction.OVERWRITE
        # output_format removed from services
        mock_settings.options.global_options.quiet = False
        mock_settings.options.global_options.verbose = False
        mock_settings.options.global_options.no_color = False
        mock_settings.options.global_options.config_file = settings_config_path

        # Specify a different config file explicitly
        explicit_config_path = Path("/explicit/config.yaml")

        with patch(
            "coregen.services.config.cfg_base_service.get_settings",
            return_value=mock_settings,
        ):
            # Create service with explicit config_file parameter
            service = ConfigServiceBase(config_file=explicit_config_path)

            # Verify that explicit parameter takes precedence
            assert service.config_file == explicit_config_path
            assert service.config_file != settings_config_path
