"""Unit tests for the ServiceBase class."""

from unittest.mock import MagicMock, patch

from coregen.cli.enums.enum_file_action import FileAction

# OutputFormat import removed - no longer used in ServiceBase
from coregen.common.console import Console
from coregen.common.file_manager import FileManager
from coregen.common.workspace_initializer import WorkspaceInitializer
from coregen.services.service_base import ServiceBase


class TestServiceBase:
    """Test the ServiceBase class."""

    def test_init_with_defaults(self):
        """Test initializing with default values."""
        # Mock settings to control the default values
        with patch(
            "coregen.config_model.models.settings.get_settings"
        ) as mock_settings:
            # Setup mock settings with known values
            mock_settings_obj = MagicMock()
            mock_settings_obj.options.global_options.dry_run = False
            mock_settings_obj.options.global_options.file_action = FileAction.SKIP
            # output_format removed from global options
            mock_settings_obj.options.global_options.quiet = False
            mock_settings_obj.options.global_options.verbose = False
            mock_settings_obj.options.global_options.no_color = False
            mock_settings.return_value = mock_settings_obj

            # Also patch GlobalOptions as it's still used in ServiceBase
            with patch("coregen.cli.global_options.GlobalOptions") as mock_go_class:
                # Create service with default values
                service = ServiceBase()

                # Verify default instances were created - now using properties
                assert service.console is Console
                assert isinstance(service.file_manager, FileManager)
                assert isinstance(service.workspace_initializer, WorkspaceInitializer)

                # Verify logger was created
                assert hasattr(service, "logger")

                # Verify default values from settings are used
                assert service.dry_run is False
                assert service.file_action == FileAction.SKIP
                # output_format removed from ServiceBase
                assert service.quiet is False
                assert service.verbose is False
                assert service.no_color is False
                assert service.global_options is None  # No GlobalOptions provided

    def test_init_with_custom_values(self):
        """Test initializing with custom values."""
        # Mock settings to ensure they don't interfere with custom values
        with patch(
            "coregen.config_model.models.settings.get_settings"
        ) as mock_settings:
            # Setup mock settings with different values
            mock_settings_obj = MagicMock()
            mock_settings_obj.options.global_options.dry_run = False
            mock_settings_obj.options.global_options.file_action = FileAction.SKIP
            # output_format removed from global options
            mock_settings_obj.options.global_options.quiet = False
            mock_settings_obj.options.global_options.verbose = False
            mock_settings_obj.options.global_options.no_color = False
            mock_settings.return_value = mock_settings_obj

            # Create mock objects
            mock_console = MagicMock(spec=Console)
            mock_file_manager = MagicMock(spec=FileManager)
            mock_workspace_initializer = MagicMock(spec=WorkspaceInitializer)

            # Create service with custom values
            service = ServiceBase(
                console=mock_console,
                file_manager=mock_file_manager,
                workspace_initializer=mock_workspace_initializer,
                dry_run=True,
                file_action=FileAction.OVERWRITE,
                # output_format removed
                quiet=True,
                verbose=True,
                no_color=True,
                config_file="/path/to/config.yaml",
            )

            # Verify instances were assigned - using properties with underscore
            assert service.console is mock_console
            assert service.file_manager is mock_file_manager
            assert service.workspace_initializer is mock_workspace_initializer

            # Verify custom values are used instead of settings
            assert service.dry_run is True
            assert service.file_action == FileAction.OVERWRITE
            # output_format removed from ServiceBase
            assert service.quiet is True
            assert service.verbose is True
            assert service.no_color is True
            assert service.config_file == "/path/to/config.yaml"
            assert service.global_options is None

    def test_init_with_global_options(self):
        """Test initializing with GlobalOptions."""
        # Mock settings to ensure they don't interfere with global options
        with patch(
            "coregen.config_model.models.settings.get_settings"
        ) as mock_settings:
            # Setup mock settings with different values
            mock_settings_obj = MagicMock()
            mock_settings_obj.options.global_options.dry_run = False
            mock_settings_obj.options.global_options.file_action = FileAction.SKIP
            # output_format removed from global options
            mock_settings_obj.options.global_options.quiet = False
            mock_settings_obj.options.global_options.verbose = False
            mock_settings_obj.options.global_options.no_color = False
            mock_settings.return_value = mock_settings_obj

            # Create mock GlobalOptions
            mock_global_options = MagicMock()
            mock_global_options.dry_run = True
            mock_global_options.file_action = FileAction.OVERWRITE
            # output_format removed from GlobalOptions
            mock_global_options.quiet = True
            mock_global_options.verbose = True
            mock_global_options.no_color = True
            mock_global_options.config_file = "/path/to/config.yaml"

            # Create service with GlobalOptions
            service = ServiceBase(global_options=mock_global_options)

            # Verify values from GlobalOptions were used instead of settings
            assert service.dry_run is True
            assert service.file_action == FileAction.OVERWRITE
            # output_format removed from ServiceBase
            assert service.quiet is True
            assert service.verbose is True
            assert service.no_color is True
            assert service.config_file == "/path/to/config.yaml"
            assert service.global_options is mock_global_options

    def test_global_options_precedence(self):
        """Test that GlobalOptions takes precedence over individual parameters."""
        # Create mock GlobalOptions with specific values
        mock_global_options = MagicMock()
        mock_global_options.dry_run = True
        mock_global_options.file_action = FileAction.OVERWRITE
        # output_format removed from GlobalOptions
        mock_global_options.quiet = True
        mock_global_options.verbose = True
        mock_global_options.no_color = True
        mock_global_options.config_file = "/path/to/global_config.yaml"
        mock_global_options.debug = True

        # Create service with both GlobalOptions and individual parameters
        # Individual parameters should be ignored when GlobalOptions is provided
        service = ServiceBase(
            global_options=mock_global_options,
            dry_run=False,
            file_action=FileAction.SKIP,
            # output_format removed from ServiceBase
            quiet=False,
            verbose=False,
            no_color=False,
            config_file="/path/to/individual_config.yaml",
        )

        # Verify values from GlobalOptions were used, not individual parameters
        assert service.dry_run is True
        assert service.file_action == FileAction.OVERWRITE
        # output_format removed from ServiceBase
        assert service.quiet is True
        assert service.verbose is True
        assert service.no_color is True
        assert service.config_file == "/path/to/global_config.yaml"
        assert service.global_options is mock_global_options

    def test_initialize_workspace(self):
        """Test workspace initializer property."""
        # Create a mock workspace initializer
        mock_workspace_initializer = MagicMock(spec=WorkspaceInitializer)

        # Create service with mock workspace initializer
        service = ServiceBase(workspace_initializer=mock_workspace_initializer)

        # Verify the property returns the right object
        assert service.workspace_initializer is mock_workspace_initializer

    def test_logger_creation(self):
        """Test logger creation."""
        # Just verify the logger attribute exists - the actual Logger class
        # is initialized inline and can't easily be mocked
        with patch(
            "coregen.cli.global_options.GlobalOptions"
        ):  # Add mock to prevent import errors
            service = ServiceBase()

            # Verify logger was created and is a logger instance
            assert hasattr(service, "logger")
            # We can't easily verify it's the right logger object since it's created inline
            # so just check it exists and has expected methods
            assert hasattr(service.logger, "debug")
            assert hasattr(service.logger, "info")
            assert hasattr(service.logger, "warning")
            assert hasattr(service.logger, "error")
