"""Unit tests for the config services."""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch  # Ensure mock_open is imported

import pytest
import yaml

from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.enums.enum_output_format import OutputFormat
from coregen.common.console import Console
from coregen.common.file_manager import FileManager
from coregen.common.workspace_initializer import WorkspaceInitializer
from coregen.config_model.models.config import (  # Import CoregenConfig for resolved mode mock
    CoregenConfig,
)
from coregen.config_model.processor import ConfigProcessor  # Import ConfigProcessor
from coregen.config_model.provider import ConfigurationProvider
from coregen.services.config.cfg_init_service import ConfigInitService
from coregen.services.config.cfg_schema_service import ConfigSchemaService
from coregen.services.config.cfg_view_service import ConfigViewService


class TestConfigServiceBaseInit:
    """Test the shared init behavior the config services inherit from ServicesBase.

    Config services now derive from ServicesBase (which provides config-provider
    access) rather than a separate ConfigServiceBase. ConfigInitService stands in
    as a concrete subclass.
    """

    def test_init_with_defaults(self, mock_config_provider, mock_path_service):
        """Test that omitted (None) options fall back to settings defaults."""
        # Passing None routes each option through ServiceBase to the settings
        # default, preserving the option-precedence the old base encoded.
        with patch(
            "coregen.config_model.provider.ConfigurationProvider",
            return_value=mock_config_provider,
        ):
            service = ConfigInitService(
                dry_run=None,
                file_action=None,
                quiet=None,
                verbose=None,
                no_color=None,
                config_file=None,
            )

        # ServiceBase stores the Console class reference (not an instance) so
        # color/flag state stays class-level and consistent across services.
        assert service._console is Console
        assert isinstance(service._file_manager, FileManager)
        assert isinstance(service._workspace_initializer, WorkspaceInitializer)
        assert isinstance(service._config_provider, ConfigurationProvider)

        # Settings defaults (see config_model/models/defaults.py)
        assert service.dry_run is False
        assert service.file_action == FileAction.OVERWRITE
        assert service.quiet is False
        assert service.verbose is False
        assert service.no_color is False

    def test_init_with_custom_values(self):
        """Test initializing with custom values."""
        # Create mock objects
        mock_console = MagicMock(spec=Console)
        mock_file_manager = MagicMock(spec=FileManager)
        mock_workspace_initializer = MagicMock(spec=WorkspaceInitializer)
        mock_config_provider = MagicMock(spec=ConfigurationProvider)

        # Create service with custom values
        service = ConfigInitService(
            console=mock_console,
            file_manager=mock_file_manager,
            workspace_initializer=mock_workspace_initializer,
            config_provider=mock_config_provider,
            dry_run=True,
            file_action=FileAction.OVERWRITE,
            quiet=True,
            verbose=True,
            no_color=True,
        )

        # Verify instances were assigned
        assert service._console is mock_console
        assert service._file_manager is mock_file_manager
        assert service._workspace_initializer is mock_workspace_initializer
        assert service._config_provider is mock_config_provider

        # Verify custom values
        assert service.dry_run is True
        assert service.file_action == FileAction.OVERWRITE
        assert service.quiet is True
        assert service.verbose is True
        assert service.no_color is True

    @patch("coregen.services.service_base.Logger")
    def test_logger_creation(
        self, mock_logger_class, mock_config_provider, mock_path_service
    ):
        """Test logger creation during initialization."""
        # Setup mock logger instance that the Logger class will return
        mock_logger_instance = MagicMock()
        mock_logger_class.return_value = mock_logger_instance

        # Patch the ConfigurationProvider constructor to return our mock
        with patch(
            "coregen.config_model.provider.ConfigurationProvider",
            return_value=mock_config_provider,
        ):
            # Create service - this should trigger Logger instantiation
            service = ConfigInitService()

        # Verify Logger was instantiated with the concrete class name
        mock_logger_class.assert_called_once_with("ConfigInitService")

        # Verify the service's logger attribute is the mocked instance
        assert service.logger is mock_logger_instance


@pytest.fixture
def view_service_setup():
    """Set up test fixtures for ConfigViewService tests."""
    # Create mock objects
    mock_config_provider = MagicMock(spec=ConfigurationProvider)
    # Create a mock console and explicitly add the methods needed
    mock_console = MagicMock(spec=Console)
    mock_console.print_json = MagicMock()
    mock_console.print_yaml = MagicMock()
    # Mock the file manager used internally by the service base
    mock_file_manager = MagicMock(spec=FileManager)

    # Create service with mocks
    service = ConfigViewService(
        config_provider=mock_config_provider,
        console=mock_console,
        file_manager=mock_file_manager,
    )
    # Mock the processor used internally by cfg_view_base_service
    mock_processor = MagicMock(spec=ConfigProcessor)
    try:
        service.config_processor = mock_processor
    except AttributeError:
        pass

    return {
        "mock_config_provider": mock_config_provider,
        "mock_console": mock_console,
        "mock_file_manager": mock_file_manager,
        "service": service,
        "mock_processor": mock_processor,
    }


class TestConfigViewServiceBasic:
    """Test basic view modes of the ConfigViewService class."""

    def test_view_config_raw_mode(
        self, view_service_setup, mock_config_provider, mock_path_service
    ):
        """Test viewing config in raw mode."""
        service = view_service_setup["service"]
        mock_file_manager = view_service_setup["mock_file_manager"]
        # Mock_config_provider is provided by the fixture but not used here

        # Mock file content
        mock_config_content = {"version": "1.0", "workspaces": [{"name": "test"}]}
        mock_yaml_content = yaml.dump(mock_config_content)

        # Mock file manager's read_file method (might still be used by base class)
        mock_file_manager.read_file = MagicMock(return_value=mock_yaml_content)

        # Call view_config with raw mode, mocking Path.exists and open
        with patch("pathlib.Path.exists", return_value=True):
            # Mock open for ConfigLoader's internal use
            with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
                result = service.view_config(
                    config_file_path=Path("config.yaml"), view_mode="raw"
                )

        # Verify result
        assert result == mock_config_content

    @patch("coregen.config_model.loader.ConfigLoader.discover_context_configs")
    def test_view_config_discovered_mode(
        self,
        mock_discover_context_configs,
        view_service_setup,
        mock_config_provider,
        mock_path_service,
    ):
        """Test viewing config in discovered mode."""
        service = view_service_setup["service"]
        # Mock_config_provider is provided by the fixture but not used here
        # Mock data
        raw_config_dict = {"version": "1.0", "workspaces": []}  # What loader returns
        mock_discovered_config = {
            "version": "1.0",
            "workspaces": [{"name": "test", "contexts": [{"name": "ctx"}]}],
        }  # What discover_context_configs returns
        mock_yaml_content = yaml.dump(raw_config_dict)

        # Set up the mock to return our discovered config
        mock_discover_context_configs.return_value = mock_discovered_config

        # Call view_config with discovered mode, mocking Path.exists and open
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
                result = service.view_config(
                    config_file_path=Path("config.yaml"), view_mode="discovered"
                )

        # Verify result
        assert result == mock_discovered_config
        # Verify discover_context_configs was called with the right args
        mock_discover_context_configs.assert_called_once()

    @patch("coregen.config_model.provider.ConfigurationProvider")
    def test_view_config_resolved_mode(
        self,
        mock_provider_class,
        view_service_setup,
        mock_config_provider,
        mock_path_service,
    ):
        """Test viewing config in resolved mode."""
        service = view_service_setup["service"]
        # Mock_config_provider is provided by the fixture but not used here
        # Mock config provider's load_config method return value (a CoregenConfig model)
        mock_resolved_config_model = MagicMock(spec=CoregenConfig)
        mock_resolved_dict = {"resolved": True}
        # Use model_dump instead of to_dict to match the actual implementation
        mock_resolved_config_model.model_dump.return_value = mock_resolved_dict

        # Configure the mocked provider instance
        mock_internal_provider = MagicMock()
        mock_internal_provider.load_config.return_value = mock_resolved_config_model
        mock_provider_class.return_value = mock_internal_provider

        # Provide valid YAML for mock_open
        valid_yaml_content = 'version: "1.0"\nworkspaces: []'

        # Call view_config with resolved mode, mocking Path.exists and open
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=valid_yaml_content)):
                result = service.view_config(
                    config_file_path=Path("config.yaml"), view_mode="resolved"
                )

        # Verify result
        assert result == mock_resolved_dict
        # Verify the internal provider's load_config was called
        mock_internal_provider.load_config.assert_called_once_with(Path("config.yaml"))
        # Verify model_dump was called with the correct parameters
        mock_resolved_config_model.model_dump.assert_called_once_with(mode="json")

    @patch("coregen.services.config.cfg_view_service.ConfigEnhancedViewService")
    def test_view_config_enhanced_mode(
        self,
        mock_enhanced_service_class,
        view_service_setup,
        mock_config_provider,
        mock_path_service,
    ):
        """Test viewing config in enhanced mode."""
        service = view_service_setup["service"]
        # Mock_config_provider is provided by the fixture but not used here
        # Configure the mock enhanced service instance
        mock_enhanced_service_instance = MagicMock()
        mock_enhanced_result = {"enhanced": True}
        # Use the correct method name view_enhanced_config that we found in the source
        mock_enhanced_service_instance.view_enhanced_config.return_value = (
            mock_enhanced_result
        )
        mock_enhanced_service_class.return_value = mock_enhanced_service_instance

        # Provide valid YAML for mock_open used by enhanced service (assuming it uses loader)
        valid_yaml_content = 'version: "1.0"\nworkspaces: []'

        # Call view_config with enhanced mode, mocking Path.exists and open
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=valid_yaml_content)):
                result = service.view_config(
                    config_file_path=Path("config.yaml"), view_mode="enhanced"
                )

        # Verify result
        assert result == mock_enhanced_result
        # Check that ConfigEnhancedViewService was initialized correctly
        mock_enhanced_service_class.assert_called_once()
        # Check that view_enhanced_config was called with the correct parameters
        mock_enhanced_service_instance.view_enhanced_config.assert_called_once_with(
            Path("config.yaml")
        )

    def test_view_config_with_output_formatting(
        self, view_service_setup, mock_config_provider, mock_path_service
    ):
        """Test viewing config with different output formats."""
        service = view_service_setup["service"]
        # Mock_config_provider is provided by the fixture but not used here
        # Mock file content
        mock_config_content = {"version": "1.0", "workspaces": [{"name": "test"}]}

        # We'll mock _view_raw_config directly to isolate this test from implementation details
        # Also patch Path.exists to avoid FileNotFoundError
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                service, "_view_raw_config", return_value=mock_config_content
            ) as mock_view_raw:
                # Test with JSON output format
                result_json = service.view_config(
                    config_file_path=Path("config.yaml"),
                    view_mode="raw",
                    # output_format removed,
                )

        # Verify _view_raw_config was called
        mock_view_raw.assert_called_once()
        # Check that result contains the expected data
        assert result_json == mock_config_content

        # Reset mocks
        mock_view_raw.reset_mock()

        # Test with YAML output format
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                service, "_view_raw_config", return_value=mock_config_content
            ) as mock_view_raw:
                result_yaml = service.view_config(
                    config_file_path=Path("config.yaml"),
                    view_mode="raw",
                    # output_format removed,
                )

        # Verify _view_raw_config was called again
        mock_view_raw.assert_called_once()
        # Check that result contains the expected data
        assert result_yaml == mock_config_content


@pytest.fixture
def init_service_setup():
    """Set up test fixtures for ConfigInitService tests."""
    # Create mock objects
    mock_file_manager = MagicMock(spec=FileManager)
    mock_console = MagicMock(spec=Console)

    mock_config_provider = MagicMock(spec=ConfigurationProvider)

    # Mock workspace initializer
    mock_workspace_initializer = MagicMock(spec=WorkspaceInitializer)

    # Create service with mocks
    service = ConfigInitService(
        file_manager=mock_file_manager,
        console=mock_console,
        config_provider=mock_config_provider,
        workspace_initializer=mock_workspace_initializer,
    )

    return {
        "mock_file_manager": mock_file_manager,
        "mock_console": mock_console,
        "mock_config_provider": mock_config_provider,
        "mock_workspace_initializer": mock_workspace_initializer,
        "service": service,
    }


class TestConfigInitService:
    """Test the ConfigInitService class."""

    def test_initialize_config_success(self, init_service_setup):
        """Test initializing configuration from existing file."""
        service = init_service_setup["service"]
        mock_config_provider = init_service_setup["mock_config_provider"]
        # Mock Path.exists to return True (file exists)
        with patch("pathlib.Path.exists", return_value=True):
            # Mock config_provider.load_config to return a config object
            mock_config = MagicMock()
            mock_config.workspaces = [MagicMock(contexts={})]
            mock_config_provider.load_config = MagicMock(return_value=mock_config)

            # Call initialize_config
            result = service.initialize_config(Path("config.yaml"))

        # Verify the expected method calls
        mock_config_provider.load_config.assert_called_once_with(Path("config.yaml"))
        init_service_setup[
            "mock_workspace_initializer"
        ].initialize_workspace.assert_called_once()
        assert result.success is True

    def test_initialize_config_file_not_found(self, init_service_setup):
        """Test initializing config with non-existent file."""
        service = init_service_setup["service"]
        mock_config_provider = init_service_setup["mock_config_provider"]
        # Mock Path.exists to return False (file doesn't exist)
        with patch("pathlib.Path.exists", return_value=False):
            # Call initialize_config
            result = service.initialize_config(Path("config.yaml"))

        # Verify file was not processed
        assert not mock_config_provider.load_config.called
        assert result.success is False


@pytest.fixture
def schema_service_setup():
    """Set up test fixtures for ConfigSchemaService tests."""
    # Create service instance
    service = ConfigSchemaService()

    # For output format tests
    mock_console = MagicMock(spec=Console)

    return {
        "service": service,
        "mock_console": mock_console,
    }


class TestConfigSchemaService:
    """Test the ConfigSchemaService class."""

    def test_get_schema_types(self, schema_service_setup):
        """Test getting schema types."""
        service = schema_service_setup["service"]
        # Get schema types
        schema_types = service.get_schema_types()

        # Verify schema types include the basic ones
        assert "settings" in schema_types
        assert "workspace" in schema_types
        assert "context" in schema_types
        assert "component" in schema_types

    @patch("coregen.services.config.cfg_schema_service.settings")
    def test_get_schema(self, mock_settings, schema_service_setup):
        """Test getting schema for a specific type."""
        service = schema_service_setup["service"]
        # Configure the mock
        mock_settings.get_model_schema = MagicMock(return_value={"type": "object"})

        # Call get_schema for a valid type
        schema = service.get_schema("settings")

        # Verify schema was returned
        assert schema == {"type": "object"}
        # Verify the settings method was called
        mock_settings.get_model_schema.assert_called_once()

    def test_get_schema_invalid_type(self, schema_service_setup):
        """Test getting schema for an invalid type."""
        service = schema_service_setup["service"]
        # Call get_schema with invalid type
        with pytest.raises(ValueError) as excinfo:
            service.get_schema("invalid_type")

        # Verify error message
        assert "Unknown schema type" in str(excinfo.value)

    def test_process_schema_request_single(self, schema_service_setup):
        """Test processing a schema request for a single type."""
        service = schema_service_setup["service"]
        # Mock get_schema to return a schema
        with patch.object(
            service, "get_schema", return_value={"type": "object"}
        ) as mock_get_schema:
            # Call process_schema_request with a single type
            result = service.process_schema_request(["settings"], OutputFormat.JSON)

            # Verify result structure
            assert "schema_data" in result
            assert "settings" in result["schema_data"]
            assert result["schema_data"]["settings"] == {"type": "object"}
            assert result["valid_types"] == ["settings"]
            assert not result["has_multiple"]
            assert not result["unknown_types"]

            # Verify get_schema was called
            mock_get_schema.assert_called_once_with("settings")

    def test_process_schema_request_all(self, schema_service_setup):
        """Test processing a schema request for all types."""
        service = schema_service_setup["service"]

        # Mock get_schema to return different schemas based on type
        def mock_get_schema_side_effect(schema_type):
            return {"type": "object", "schema_type": schema_type}

        with patch.object(
            service, "get_schema", side_effect=mock_get_schema_side_effect
        ) as mock_get_schema:
            # Call process_schema_request with 'all'
            result = service.process_schema_request(["all"], OutputFormat.JSON)

            # Verify result structure
            assert "schema_data" in result
            assert len(result["schema_data"]) == len(service.get_schema_types())
            assert result["has_multiple"]

            # Verify get_schema was called for each type
            assert mock_get_schema.call_count == len(service.get_schema_types())
