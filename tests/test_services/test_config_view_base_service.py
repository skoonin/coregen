"""Unit tests for ConfigViewBaseService.

This module tests the ConfigViewBaseService which provides base functionality
for viewing configuration data in various formats and processing stages.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coregen.common.console import Console
from coregen.common.file_manager import FileManager
from coregen.common.workspace_initializer import WorkspaceInitializer
from coregen.config_model.loader import ConfigLoader
from coregen.config_model.provider import ConfigurationProvider
from coregen.services.config.cfg_view_base_service import ConfigViewBaseService


class TestConfigViewBaseService:
    """Test suite for ConfigViewBaseService."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for ConfigViewBaseService.

        Returns:
            dict: Dictionary containing all mock objects needed for testing
        """
        return {
            "console": MagicMock(spec=Console),
            "file_manager": MagicMock(spec=FileManager),
            "workspace_initializer": MagicMock(spec=WorkspaceInitializer),
            "config_provider": MagicMock(spec=ConfigurationProvider),
        }

    @pytest.fixture
    def service(self, mock_dependencies: dict) -> ConfigViewBaseService:
        """Create a ConfigViewBaseService instance with mocked dependencies.

        Args:
            mock_dependencies: Dictionary of mock objects

        Returns:
            ConfigViewBaseService: Service instance for testing
        """
        return ConfigViewBaseService(
            console=mock_dependencies["console"],
            file_manager=mock_dependencies["file_manager"],
            workspace_initializer=mock_dependencies["workspace_initializer"],
            config_provider=mock_dependencies["config_provider"],
        )

    @pytest.fixture
    def sample_config_dict(self) -> dict:
        """Create sample configuration dictionary for testing.

        Returns:
            dict: Sample configuration data
        """
        return {
            "version": "1.0",
            "workspaces": [
                {
                    "name": "test-workspace",
                    "contexts": [
                        {
                            "name": "test-context",
                            "environment": "dev",
                            "components": [
                                {
                                    "name": "test-component",
                                    "type": "service",
                                    "active": True,
                                }
                            ],
                        }
                    ],
                }
            ],
        }

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_init_creates_config_loader(self, service: ConfigViewBaseService):
        """Test that initialization creates a ConfigLoader instance."""
        assert hasattr(service, "config_loader")
        assert isinstance(service.config_loader, ConfigLoader)

    def test_init_creates_settings(self, service: ConfigViewBaseService):
        """Test that initialization creates settings instance."""
        assert hasattr(service, "settings")
        assert service.settings is not None

    def test_init_passes_global_options_to_loader(self, mock_dependencies: dict):
        """Test that global options are passed to ConfigLoader."""
        # Create service with specific options
        service = ConfigViewBaseService(
            console=mock_dependencies["console"],
            file_manager=mock_dependencies["file_manager"],
            workspace_initializer=mock_dependencies["workspace_initializer"],
            config_provider=mock_dependencies["config_provider"],
            dry_run=True,
            quiet=True,
            verbose=False,
            no_color=True,
        )

        # Verify options were passed to config_loader
        assert service.config_loader.dry_run is True
        assert service.config_loader.quiet is True
        assert service.config_loader.verbose is False
        assert service.config_loader.no_color is True

    # ========================================================================
    # _view_raw_config Tests
    # ========================================================================

    def test_view_raw_config_success(
        self, service: ConfigViewBaseService, sample_config_dict: dict
    ):
        """Test _view_raw_config successfully loads configuration."""
        config_path = Path("/mock/path/to/config.yaml")

        # Mock the config_loader.load_config method
        with patch.object(
            service.config_loader, "load_config", return_value=sample_config_dict
        ) as mock_load:
            result = service._view_raw_config(config_path)

            # Verify the loader was called with correct path
            mock_load.assert_called_once_with(config_path)
            # Verify result matches expected config
            assert result == sample_config_dict

    def test_view_raw_config_file_not_found(self, service: ConfigViewBaseService):
        """Test _view_raw_config raises FileNotFoundError for missing file."""
        config_path = Path("/nonexistent/config.yaml")

        # Mock the config_loader to raise FileNotFoundError
        with patch.object(
            service.config_loader,
            "load_config",
            side_effect=FileNotFoundError("Config file not found"),
        ):
            with pytest.raises(FileNotFoundError, match="Config file not found"):
                service._view_raw_config(config_path)

    def test_view_raw_config_logs_debug_message(self, service: ConfigViewBaseService):
        """Test _view_raw_config logs debug message with correct path."""
        config_path = Path("/mock/path/to/config.yaml")

        with (
            patch.object(service.config_loader, "load_config", return_value={}),
            patch.object(service.logger, "debug") as mock_debug,
        ):
            service._view_raw_config(config_path)

            # Verify debug logging was called
            mock_debug.assert_called_once()
            call_args = mock_debug.call_args[0][0]
            assert "Viewing raw configuration from" in call_args
            assert str(config_path) in call_args

    def test_view_raw_config_handles_generic_exception(
        self, service: ConfigViewBaseService
    ):
        """Test _view_raw_config handles and re-raises generic exceptions."""
        config_path = Path("/mock/path/to/config.yaml")

        # Mock the config_loader to raise a generic exception
        with patch.object(
            service.config_loader,
            "load_config",
            side_effect=ValueError("Invalid YAML"),
        ):
            with pytest.raises(ValueError, match="Invalid YAML"):
                service._view_raw_config(config_path)

    # ========================================================================
    # _view_discovered_config Tests
    # ========================================================================

    def test_view_discovered_config_success(
        self, service: ConfigViewBaseService, sample_config_dict: dict
    ):
        """Test _view_discovered_config successfully loads and discovers contexts."""
        config_path = Path("/mock/path/to/config.yaml")
        discovered_config = {**sample_config_dict, "discovered": True}

        # Mock both load_config and discover_context_configs
        with (
            patch.object(
                service.config_loader, "load_config", return_value=sample_config_dict
            ) as mock_load,
            patch.object(
                service.config_loader,
                "discover_context_configs",
                return_value=discovered_config,
            ) as mock_discover,
        ):
            result = service._view_discovered_config(config_path)

            # Verify load_config was called
            mock_load.assert_called_once_with(config_path)
            # Verify discover_context_configs was called with correct args
            mock_discover.assert_called_once_with(
                sample_config_dict, root_dir=config_path.parent
            )
            # Verify result includes discovered context
            assert result == discovered_config

    def test_view_discovered_config_logs_debug_message(
        self, service: ConfigViewBaseService, sample_config_dict: dict
    ):
        """Test _view_discovered_config logs debug message."""
        config_path = Path("/mock/path/to/config.yaml")

        with (
            patch.object(
                service.config_loader, "load_config", return_value=sample_config_dict
            ),
            patch.object(
                service.config_loader,
                "discover_context_configs",
                return_value=sample_config_dict,
            ),
            patch.object(service.logger, "debug") as mock_debug,
        ):
            service._view_discovered_config(config_path)

            # Verify debug logging was called
            mock_debug.assert_called_once()
            call_args = mock_debug.call_args[0][0]
            assert "Viewing configuration with discovered contexts" in call_args
            assert str(config_path) in call_args

    def test_view_discovered_config_handles_exception(
        self, service: ConfigViewBaseService
    ):
        """Test _view_discovered_config handles exceptions during discovery."""
        config_path = Path("/mock/path/to/config.yaml")

        # Mock load_config to succeed but discover_context_configs to fail
        with (
            patch.object(service.config_loader, "load_config", return_value={}),
            patch.object(
                service.config_loader,
                "discover_context_configs",
                side_effect=RuntimeError("Discovery failed"),
            ),
        ):
            with pytest.raises(RuntimeError, match="Discovery failed"):
                service._view_discovered_config(config_path)

    # ========================================================================
    # _view_resolved_config Tests
    # ========================================================================

    def test_view_resolved_config_success(
        self, service: ConfigViewBaseService, sample_config_dict: dict
    ):
        """Test _view_resolved_config successfully loads and resolves configuration."""
        config_path = Path("/mock/path/to/config.yaml")

        # Create mock config object with model_dump method
        mock_config = MagicMock()
        mock_config.model_dump.return_value = sample_config_dict

        # Mock ConfigurationProvider and its load_config method
        with patch(
            "coregen.config_model.provider.ConfigurationProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.load_config.return_value = mock_config
            mock_provider_class.return_value = mock_provider

            result = service._view_resolved_config(config_path)

            # Verify ConfigurationProvider was created with correct settings
            mock_provider_class.assert_called_once_with(
                config_mode=False,
                lenient_validation=False,
                root_path=config_path.parent,
            )
            # Verify load_config was called
            mock_provider.load_config.assert_called_once_with(config_path)
            # Verify model_dump was called with mode="json"
            mock_config.model_dump.assert_called_once_with(mode="json")
            # Verify result
            assert result == sample_config_dict

    def test_view_resolved_config_logs_debug_message(
        self, service: ConfigViewBaseService
    ):
        """Test _view_resolved_config logs debug message."""
        config_path = Path("/mock/path/to/config.yaml")

        # Create mock config object
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {}

        with (
            patch(
                "coregen.config_model.provider.ConfigurationProvider"
            ) as mock_provider_class,
            patch.object(service.logger, "debug") as mock_debug,
        ):
            mock_provider = MagicMock()
            mock_provider.load_config.return_value = mock_config
            mock_provider_class.return_value = mock_provider

            service._view_resolved_config(config_path)

            # Verify debug logging was called
            mock_debug.assert_called_once()
            call_args = mock_debug.call_args[0][0]
            assert "Viewing fully processed configuration" in call_args
            assert str(config_path) in call_args

    def test_view_resolved_config_handles_validation_error(
        self, service: ConfigViewBaseService
    ):
        """Test _view_resolved_config handles validation errors."""
        config_path = Path("/mock/path/to/config.yaml")

        # Mock ConfigurationProvider to raise exception
        with patch(
            "coregen.config_model.provider.ConfigurationProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.load_config.side_effect = ValueError("Validation failed")
            mock_provider_class.return_value = mock_provider

            with pytest.raises(ValueError, match="Validation failed"):
                service._view_resolved_config(config_path)

    def test_view_resolved_config_uses_correct_provider_settings(
        self, service: ConfigViewBaseService
    ):
        """Test _view_resolved_config creates provider with strict validation."""
        config_path = Path("/mock/path/to/config.yaml")

        # Create mock config object
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {}

        with patch(
            "coregen.config_model.provider.ConfigurationProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.load_config.return_value = mock_config
            mock_provider_class.return_value = mock_provider

            service._view_resolved_config(config_path)

            # Verify provider was created with strict validation settings
            call_kwargs = mock_provider_class.call_args[1]
            assert call_kwargs["config_mode"] is False
            assert call_kwargs["lenient_validation"] is False
            assert call_kwargs["root_path"] == config_path.parent

    # ========================================================================
    # Integration and Edge Case Tests
    # ========================================================================

    def test_config_loader_inherits_global_options(self, mock_dependencies: dict):
        """Test that ConfigLoader receives all global options from service."""
        # Create service with all options set
        service = ConfigViewBaseService(
            console=mock_dependencies["console"],
            file_manager=mock_dependencies["file_manager"],
            workspace_initializer=mock_dependencies["workspace_initializer"],
            config_provider=mock_dependencies["config_provider"],
            dry_run=True,
            quiet=False,
            verbose=True,
            no_color=False,
        )

        # Verify all options were passed to config_loader
        assert service.config_loader.dry_run is True
        assert service.config_loader.quiet is False
        assert service.config_loader.verbose is True
        assert service.config_loader.no_color is False
        assert service.dry_run is True
        assert service.verbose is True

    def test_view_raw_config_logs_error_on_failure(
        self, service: ConfigViewBaseService
    ):
        """Test _view_raw_config logs error message when loading fails."""
        config_path = Path("/mock/path/to/config.yaml")

        with (
            patch.object(
                service.config_loader,
                "load_config",
                side_effect=RuntimeError("Load failed"),
            ),
            patch.object(service.logger, "error") as mock_error,
        ):
            with pytest.raises(RuntimeError):
                service._view_raw_config(config_path)

            # Verify error logging was called
            mock_error.assert_called_once()
            call_args = mock_error.call_args[0][0]
            assert "Error loading raw configuration" in call_args
            assert "Load failed" in call_args

    def test_view_discovered_config_logs_error_on_failure(
        self, service: ConfigViewBaseService
    ):
        """Test _view_discovered_config logs error message when discovery fails."""
        config_path = Path("/mock/path/to/config.yaml")

        with (
            patch.object(service.config_loader, "load_config", return_value={}),
            patch.object(
                service.config_loader,
                "discover_context_configs",
                side_effect=RuntimeError("Discovery failed"),
            ),
            patch.object(service.logger, "error") as mock_error,
        ):
            with pytest.raises(RuntimeError):
                service._view_discovered_config(config_path)

            # Verify error logging was called
            mock_error.assert_called_once()
            call_args = mock_error.call_args[0][0]
            assert "Error loading discovered configuration" in call_args
            assert "Discovery failed" in call_args

    def test_view_resolved_config_logs_error_on_failure(
        self, service: ConfigViewBaseService
    ):
        """Test _view_resolved_config logs error message when resolution fails."""
        config_path = Path("/mock/path/to/config.yaml")

        with (
            patch(
                "coregen.config_model.provider.ConfigurationProvider"
            ) as mock_provider_class,
            patch.object(service.logger, "error") as mock_error,
        ):
            mock_provider = MagicMock()
            mock_provider.load_config.side_effect = RuntimeError("Resolution failed")
            mock_provider_class.return_value = mock_provider

            with pytest.raises(RuntimeError):
                service._view_resolved_config(config_path)

            # Verify error logging was called
            mock_error.assert_called_once()
            call_args = mock_error.call_args[0][0]
            assert "Error loading resolved configuration" in call_args
            assert "Resolution failed" in call_args
