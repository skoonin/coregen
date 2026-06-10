"""Unit tests for WorkspaceInitializer with settings-based defaults."""

from unittest.mock import MagicMock, patch

from coregen.common.file_manager import FileManager
from coregen.common.path_service import PathService
from coregen.common.workspace_initializer import WorkspaceInitializer


class TestWorkspaceInitializerSettings:
    """Test the WorkspaceInitializer class with settings integration."""

    def test_workspace_initializer_uses_settings_defaults(self, mock_settings):
        """Test that WorkspaceInitializer uses settings for default values."""
        # Configure mock_settings for this test - default dry_run=True
        mock_settings.options.global_options.dry_run = True

        # Patch get_settings at the point of use (where WorkspaceInitializer imports it)
        # This is necessary because get_settings() is called during __init__
        with patch(
            "coregen.common.workspace_initializer.get_settings",
            return_value=mock_settings,
        ):
            # Create mocks for dependencies
            mock_path_service = MagicMock(spec=PathService)
            mock_file_manager = MagicMock(spec=FileManager)

            # Create WorkspaceInitializer with None for dry_run parameter
            initializer = WorkspaceInitializer(
                path_service=mock_path_service,
                file_manager=mock_file_manager,
                dry_run=None,  # Should use settings default
            )

            # Verify that dry_run is set to settings value
            assert initializer.dry_run is True
            assert initializer.dry_run == mock_settings.options.global_options.dry_run

    def test_workspace_initializer_parameter_overrides(self, mock_settings):
        """Test that explicit parameters override settings defaults."""
        # Configure mock_settings with dry_run=True so we can test override with False
        mock_settings.options.global_options.dry_run = True

        # Patch get_settings at the point of use
        with patch(
            "coregen.common.workspace_initializer.get_settings",
            return_value=mock_settings,
        ):
            # Create mocks for dependencies
            mock_path_service = MagicMock(spec=PathService)
            mock_file_manager = MagicMock(spec=FileManager)

            # Create WorkspaceInitializer with explicit dry_run parameter
            explicit_dry_run = False  # Different from settings default
            initializer = WorkspaceInitializer(
                path_service=mock_path_service,
                file_manager=mock_file_manager,
                dry_run=explicit_dry_run,  # Should override settings
            )

            # Verify that dry_run is set to explicit value, not settings value
            assert initializer.dry_run is False
            assert initializer.dry_run == explicit_dry_run
            assert initializer.dry_run != mock_settings.options.global_options.dry_run

    def test_new_file_manager_creation_with_settings(self, mock_settings):
        """Test that a newly created FileManager uses settings-based defaults."""
        # Patch get_settings to return our mocked settings
        with patch(
            "coregen.common.workspace_initializer.get_settings",
            return_value=mock_settings,
        ):
            # Create mock for path_service but let file_manager be created
            mock_path_service = MagicMock(spec=PathService)

            # Also patch FileManager constructor to verify it receives the right values
            with patch(
                "coregen.common.workspace_initializer.FileManager"
            ) as mock_file_manager_class:
                # Create a fake instance to return
                mock_file_manager = MagicMock(spec=FileManager)
                mock_file_manager_class.return_value = mock_file_manager

                # Create WorkspaceInitializer with None for dry_run parameter
                # This should create a new FileManager with settings-based defaults
                WorkspaceInitializer(
                    path_service=mock_path_service,
                    file_manager=None,  # Let it create a new FileManager
                    dry_run=None,  # Should use settings default
                )

                # Verify that FileManager constructor was called with settings-based dry_run
                mock_file_manager_class.assert_called_once()
                kwargs = mock_file_manager_class.call_args.kwargs
                assert kwargs["dry_run"] == mock_settings.options.global_options.dry_run
