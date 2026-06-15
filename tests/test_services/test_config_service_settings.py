"""Unit tests for config-service settings integration.

Config services derive from ServicesBase (which inherits the option/settings
precedence from ServiceBase). ConfigInitService stands in as a concrete subclass
to exercise that shared behavior.

In the documented hierarchy, individual flag options (dry_run, file_action,
quiet, verbose, no_color) fall back to settings when passed as None, while the
config file is resolved through GlobalOptions (the path the CLI always uses).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.global_options import GlobalOptions
from coregen.common.console import Console
from coregen.common.file_manager import FileManager
from coregen.common.workspace_initializer import WorkspaceInitializer
from coregen.config_model.provider import ConfigurationProvider
from coregen.services.config.cfg_init_service import ConfigInitService

# ServiceBase imports get_settings from this module inside __init__.
SETTINGS_TARGET = "coregen.config_model.models.settings.get_settings"


class TestConfigServiceSettings:
    """Settings integration for config services via ServicesBase."""

    def test_settings_defaults(self, mock_settings):
        """Omitted (None) flag options fall back to settings defaults."""
        with patch(SETTINGS_TARGET, return_value=mock_settings):
            mock_console = MagicMock(spec=Console)
            mock_file_manager = MagicMock(spec=FileManager)
            mock_provider = MagicMock(spec=ConfigurationProvider)
            mock_workspace_init = MagicMock(spec=WorkspaceInitializer)

            # All None parameters => settings defaults are used
            service = ConfigInitService(
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

            assert service.dry_run == mock_settings.options.global_options.dry_run
            assert (
                service.file_action == mock_settings.options.global_options.file_action
            )
            assert service.quiet == mock_settings.options.global_options.quiet
            assert service.verbose == mock_settings.options.global_options.verbose
            assert service.no_color == mock_settings.options.global_options.no_color

    def test_parameter_overrides(self, mock_settings):
        """Explicit parameters override settings defaults; None still falls back."""
        explicit_dry_run = True
        explicit_file_action = FileAction.SKIP

        with patch(SETTINGS_TARGET, return_value=mock_settings):
            mock_console = MagicMock(spec=Console)
            mock_file_manager = MagicMock(spec=FileManager)
            mock_provider = MagicMock(spec=ConfigurationProvider)
            mock_workspace_init = MagicMock(spec=WorkspaceInitializer)

            service = ConfigInitService(
                console=mock_console,
                file_manager=mock_file_manager,
                config_provider=mock_provider,
                workspace_initializer=mock_workspace_init,
                dry_run=explicit_dry_run,
                file_action=explicit_file_action,
                quiet=None,
                verbose=None,
                no_color=None,
                config_file=None,
            )

            mock_console.setup.assert_not_called()

            # Explicit values win
            assert service.dry_run == explicit_dry_run
            assert service.file_action == explicit_file_action
            # None falls back to settings
            assert service.quiet == mock_settings.options.global_options.quiet
            assert service.verbose == mock_settings.options.global_options.verbose
            assert service.no_color == mock_settings.options.global_options.no_color

    def test_config_file_from_global_options(self):
        """config_file is taken from GlobalOptions when provided."""
        test_config_path = Path("/test/path/custom-config.yaml")
        global_options = GlobalOptions(config_file=test_config_path)

        service = ConfigInitService(global_options=global_options)

        assert service.config_file == test_config_path
        assert isinstance(service.config_file, Path)

    def test_config_file_global_options_precedence(self):
        """The GlobalOptions config_file wins over an individual config_file param."""
        global_config_path = Path("/global/config.yaml")
        individual_config_path = Path("/individual/config.yaml")
        global_options = GlobalOptions(config_file=global_config_path)

        # GlobalOptions takes precedence over individual options
        service = ConfigInitService(
            global_options=global_options,
            config_file=individual_config_path,
        )

        assert service.config_file == global_config_path
        assert service.config_file != individual_config_path
