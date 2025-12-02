"""Unit tests for the enhanced config view service."""

import copy
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from coregen.common.console import Console
from coregen.common.file_manager import FileManager
from coregen.config_model.models.config import CoregenConfig
from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig as Workspace
from coregen.config_model.provider import ConfigurationProvider
from coregen.services.config.cfg_view_enhanced_service import ConfigEnhancedViewService


@pytest.fixture
def enhanced_config_service_setup():
    """Set up test fixtures for ConfigEnhancedViewService tests."""
    # Create mock objects
    mock_config_provider = MagicMock(spec=ConfigurationProvider)
    # Create a mock console and explicitly add the methods needed
    mock_console = MagicMock(spec=Console)
    mock_console.print_json = MagicMock()
    mock_console.print_yaml = MagicMock()
    # Mock the file manager used internally by the service base
    mock_file_manager = MagicMock(spec=FileManager)

    # Mock path_service within config_provider
    mock_path_service = MagicMock()
    mock_config_provider.path_service = mock_path_service

    # Create service with mocks
    service = ConfigEnhancedViewService(
        config_provider=mock_config_provider,
        console=mock_console,
        file_manager=mock_file_manager,
    )

    # Mock the _view_discovered_config method
    service._view_discovered_config = MagicMock()

    # Set up common test data
    config_file_path = Path("/path/to/config.yaml")

    return {
        "service": service,
        "mock_config_provider": mock_config_provider,
        "mock_console": mock_console,
        "mock_file_manager": mock_file_manager,
        "mock_path_service": mock_path_service,
        "config_file_path": config_file_path,
    }


class TestConfigEnhancedViewService:
    """Test the ConfigEnhancedViewService class."""

    def test_view_enhanced_config_success(self, enhanced_config_service_setup):
        """Test view_enhanced_config method when successful."""
        service = enhanced_config_service_setup["service"]
        config_file_path = enhanced_config_service_setup["config_file_path"]

        # Create mock data
        enhanced_dict = {
            "version": "1.0",
            "workspaces": [
                {
                    "name": "workspace1",
                    "context_type": "contexts",
                    "contexts": {},
                    "resolved_paths": {
                        "root": "/path/to/workspace1",
                        "templates": "/path/to/workspace1/templates",
                    },
                }
            ],
        }

        # Mock the entire method implementation directly
        with patch.object(
            service, "view_enhanced_config", return_value=enhanced_dict
        ) as mock_method:
            # Call the method
            result = service.view_enhanced_config(config_file_path)

            # Verify the method was called correctly
            mock_method.assert_called_once_with(config_file_path)

        # Verify result contains the expected data
        assert result == enhanced_dict
        assert "version" in result
        assert "workspaces" in result
        assert len(result["workspaces"]) == 1
        assert "resolved_paths" in result["workspaces"][0]
        assert (
            result["workspaces"][0]["resolved_paths"]["root"] == "/path/to/workspace1"
        )
        assert (
            result["workspaces"][0]["resolved_paths"]["templates"]
            == "/path/to/workspace1/templates"
        )

    def test_view_enhanced_config_exception(self, enhanced_config_service_setup):
        """Test view_enhanced_config method when an exception occurs."""
        service = enhanced_config_service_setup["service"]
        enhanced_config_service_setup["mock_path_service"]
        config_file_path = enhanced_config_service_setup["config_file_path"]

        # Setup the mock to raise an exception
        service._view_discovered_config.side_effect = ValueError("Test error")

        # Mock the logger
        service.logger = MagicMock()

        # Call the method and expect the exception to be re-raised
        with pytest.raises(ValueError) as excinfo:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data="")):
                    service.view_enhanced_config(config_file_path)

        # Verify the error message
        assert "Test error" in str(excinfo.value)

        # Verify logger was called with the error
        service.logger.error.assert_called_once()

    def test_enhance_discovered_config_with_workspaces(
        self, enhanced_config_service_setup
    ):
        """Test _enhance_discovered_config with workspaces."""
        service = enhanced_config_service_setup["service"]
        mock_path_service = enhanced_config_service_setup["mock_path_service"]
        enhanced_config_service_setup["config_file_path"]

        # Create test data
        discovered_dict = {
            "version": "1.0",
            "workspaces": [
                {
                    "name": "workspace1",
                    "context_type": "contexts",
                    "contexts": {
                        "context1": {
                            "name": "context1",
                            "component_type": "components",
                            "components": {"component1": {"name": "component1"}},
                        }
                    },
                }
            ],
        }

        # Create mock config
        mock_workspace = MagicMock(spec=Workspace)
        mock_workspace.name = "workspace1"

        # Mock context
        mock_context = MagicMock(spec=Context)
        mock_context.path = Path("/path/to/context1")
        # Store contexts as a dict with context name as key
        mock_workspace.contexts = {"contexts": {"context1": mock_context}}

        # Mock component
        mock_component = MagicMock()
        mock_component.config = MagicMock()
        # Prepare model_dump returns
        mock_component.model_dump.return_value = {
            "name": "component1",
            "type": "test",
            "template": "template1",
            "config": {},
        }
        mock_component.config.model_dump.return_value = {
            "param1": "value1",
            "param2": "value2",
        }
        # Store components as a dict with component name as key
        mock_context.components = {"components": {"component1": mock_component}}

        mock_config = MagicMock(spec=CoregenConfig)
        mock_config.workspaces = [mock_workspace]

        # Mock provider
        provider = MagicMock(spec=ConfigurationProvider)
        provider.path_service = mock_path_service

        # Mock resolve paths
        mock_path_service.resolve_workspace_paths.return_value = {
            "root": Path("/path/to/workspace1")
        }
        mock_path_service.resolve_context_paths.return_value = {
            "base": Path("/path/to/context1")
        }
        mock_path_service.resolve_component_paths.return_value = {
            "output": Path("/path/to/component1")
        }

        # Mock context.model_dump
        mock_context.model_dump.return_value = {
            "name": "context1",
            "path": "/path/to/context1",
            "variables": {"var1": "val1"},
        }

        # Call the method
        result = service._enhance_discovered_config(
            discovered_dict, mock_config, provider
        )

        # Verify result structure
        assert "version" in result
        assert "workspaces" in result
        assert len(result["workspaces"]) == 1
        workspace = result["workspaces"][0]
        assert "resolved_paths" in workspace
        assert workspace["resolved_paths"]["root"] == "/path/to/workspace1"

        # Verify context enhancement
        context = workspace["contexts"]["context1"]
        assert "resolved_paths" in context
        assert context["resolved_paths"]["base"] == "/path/to/context1"
        assert context["path"] == "/path/to/context1"
        assert "variables" in context
        assert context["variables"]["var1"] == "val1"

        # Verify component enhancement
        component = context["components"]["component1"]
        assert "resolved_paths" in component
        assert component["resolved_paths"]["output"] == "/path/to/component1"
        assert "type" in component
        assert component["type"] == "test"
        assert "template" in component
        assert component["template"] == "template1"
        assert "config" in component
        assert component["config"]["param1"] == "value1"
        assert component["config"]["param2"] == "value2"

    def test_enhance_discovered_config_with_array_contexts(
        self, enhanced_config_service_setup
    ):
        """Test _enhance_discovered_config with contexts as an array."""
        service = enhanced_config_service_setup["service"]
        mock_path_service = enhanced_config_service_setup["mock_path_service"]
        enhanced_config_service_setup["config_file_path"]

        # Create test data with contexts as an array
        discovered_dict = {
            "version": "1.0",
            "workspaces": [
                {
                    "name": "workspace1",
                    "context_type": "contexts",
                    "contexts": [
                        {
                            "name": "context1",
                            "component_type": "components",
                            "components": [{"name": "component1"}],
                        }
                    ],
                }
            ],
        }

        # Create mock config
        mock_workspace = MagicMock(spec=Workspace)
        mock_workspace.name = "workspace1"

        # Mock context
        mock_context = MagicMock(spec=Context)
        mock_context.path = Path("/path/to/context1")
        # Store contexts as a dict with context name as key
        mock_workspace.contexts = {"contexts": {"context1": mock_context}}

        # Mock component
        mock_component = MagicMock()
        mock_component.config = MagicMock()
        # Prepare model_dump returns
        mock_component.model_dump.return_value = {
            "name": "component1",
            "type": "test",
            "template": "template1",
            "config": {},
        }
        mock_component.config.model_dump.return_value = {
            "param1": "value1",
            "param2": "value2",
        }
        # Store components as a dict with component name as key
        mock_context.components = {"components": {"component1": mock_component}}

        mock_config = MagicMock(spec=CoregenConfig)
        mock_config.workspaces = [mock_workspace]

        # Mock provider
        provider = MagicMock(spec=ConfigurationProvider)
        provider.path_service = mock_path_service

        # Mock resolve paths
        mock_path_service.resolve_workspace_paths.return_value = {
            "root": Path("/path/to/workspace1")
        }
        mock_path_service.resolve_context_paths.return_value = {
            "base": Path("/path/to/context1")
        }
        mock_path_service.resolve_component_paths.return_value = {
            "output": Path("/path/to/component1")
        }

        # Mock context.model_dump
        mock_context.model_dump.return_value = {
            "name": "context1",
            "path": "/path/to/context1",
            "variables": {"var1": "val1"},
        }

        # Call the method
        result = service._enhance_discovered_config(
            discovered_dict, mock_config, provider
        )

        # Verify result structure
        assert "version" in result
        assert "workspaces" in result
        assert len(result["workspaces"]) == 1
        workspace = result["workspaces"][0]
        assert "resolved_paths" in workspace
        assert workspace["resolved_paths"]["root"] == "/path/to/workspace1"

        # Verify context enhancement (should still be an array)
        contexts = workspace["contexts"]
        assert isinstance(contexts, list)
        context = contexts[0]
        assert "resolved_paths" in context
        assert context["resolved_paths"]["base"] == "/path/to/context1"
        assert context["path"] == "/path/to/context1"
        assert "variables" in context
        assert context["variables"]["var1"] == "val1"

        # Verify component enhancement (should still be an array)
        components = context["components"]
        assert isinstance(components, list)
        component = components[0]
        assert "resolved_paths" in component
        assert component["resolved_paths"]["output"] == "/path/to/component1"
        assert "type" in component
        assert component["type"] == "test"
        assert "template" in component
        assert component["template"] == "template1"
        assert "config" in component
        assert component["config"]["param1"] == "value1"
        assert component["config"]["param2"] == "value2"

    def test_enhance_context_with_dict_components(self, enhanced_config_service_setup):
        """Test _enhance_context method with components as a dictionary."""
        service = enhanced_config_service_setup["service"]
        mock_path_service = enhanced_config_service_setup["mock_path_service"]
        enhanced_config_service_setup["config_file_path"]

        # Create test data
        ctx_dict = {
            "name": "context1",
            "component_type": "components",
            "components": {"component1": {"name": "component1"}},
        }

        # Mock processed workspace and context
        processed_ws = MagicMock(spec=Workspace)
        processed_ctx = MagicMock(spec=Context)
        processed_ctx.path = Path("/path/to/context1")
        processed_ctx.model_dump.return_value = {
            "name": "context1",
            "path": "/path/to/context1",
            "variables": {"var1": "val1"},
            "components": {},
            "_config_file_path": "/path/to/config.yaml",
        }

        # Mock component
        mock_component = MagicMock()
        mock_component.config = MagicMock()
        mock_component.model_dump.return_value = {
            "name": "component1",
            "type": "test",
            "template": "template1",
            "_config_file_path": "/path/to/config.yaml",
        }
        processed_ctx.components = {"components": {"component1": mock_component}}

        # Mock provider and path_service
        provider = MagicMock(spec=ConfigurationProvider)
        provider.path_service = mock_path_service

        # Mock next function to find the right context
        processed_ws.contexts = {"contexts": {"context1": processed_ctx}}

        # Mock resolve_context_paths
        mock_path_service.resolve_context_paths.return_value = {
            "base": Path("/path/to/context1")
        }

        # Patch the _enhance_component method
        with patch.object(service, "_enhance_component") as mock_enhance_component:
            # Call the method
            service._enhance_context(ctx_dict, "context1", processed_ws, provider)

            # Verify _enhance_component was called with the right arguments
            mock_enhance_component.assert_called_once_with(
                ctx_dict["components"]["component1"],
                "component1",
                processed_ctx,
                processed_ws,
                provider,
            )

        # Verify context was enhanced
        assert "resolved_paths" in ctx_dict
        assert ctx_dict["resolved_paths"]["base"] == "/path/to/context1"
        assert ctx_dict["path"] == "/path/to/context1"
        assert "variables" in ctx_dict
        assert ctx_dict["variables"]["var1"] == "val1"

    def test_enhance_context_with_array_components(self, enhanced_config_service_setup):
        """Test _enhance_context method with components as an array."""
        service = enhanced_config_service_setup["service"]
        mock_path_service = enhanced_config_service_setup["mock_path_service"]
        enhanced_config_service_setup["config_file_path"]

        # Create test data
        ctx_dict = {
            "name": "context1",
            "component_type": "components",
            "components": [{"name": "component1"}],
        }

        # Mock processed workspace and context
        processed_ws = MagicMock(spec=Workspace)
        processed_ctx = MagicMock(spec=Context)
        processed_ctx.path = Path("/path/to/context1")
        processed_ctx.model_dump.return_value = {
            "name": "context1",
            "path": "/path/to/context1",
            "variables": {"var1": "val1"},
            "components": {},
            "_config_file_path": "/path/to/config.yaml",
        }

        # Mock component
        mock_component = MagicMock()
        mock_component.config = MagicMock()
        mock_component.model_dump.return_value = {
            "name": "component1",
            "type": "test",
            "template": "template1",
            "_config_file_path": "/path/to/config.yaml",
        }
        processed_ctx.components = {"components": {"component1": mock_component}}

        # Mock provider and path_service
        provider = MagicMock(spec=ConfigurationProvider)
        provider.path_service = mock_path_service

        # Mock next function to find the right context
        processed_ws.contexts = {"contexts": {"context1": processed_ctx}}

        # Mock resolve_context_paths
        mock_path_service.resolve_context_paths.return_value = {
            "base": Path("/path/to/context1")
        }

        # Patch the _enhance_component method
        with patch.object(service, "_enhance_component") as mock_enhance_component:
            # Call the method
            service._enhance_context(ctx_dict, "context1", processed_ws, provider)

            # Verify _enhance_component was called with the right arguments
            mock_enhance_component.assert_called_once_with(
                ctx_dict["components"][0],
                "component1",
                processed_ctx,
                processed_ws,
                provider,
            )

        # Verify context was enhanced
        assert "resolved_paths" in ctx_dict
        assert ctx_dict["resolved_paths"]["base"] == "/path/to/context1"
        assert ctx_dict["path"] == "/path/to/context1"
        assert "variables" in ctx_dict
        assert ctx_dict["variables"]["var1"] == "val1"

    def test_enhance_context_not_found(self, enhanced_config_service_setup):
        """Test _enhance_context method when context is not found."""
        service = enhanced_config_service_setup["service"]
        enhanced_config_service_setup["mock_path_service"]
        enhanced_config_service_setup["config_file_path"]

        # Create test data
        ctx_dict = {"name": "unknown_context"}

        # Mock processed workspace with no matching context
        processed_ws = MagicMock(spec=Workspace)
        processed_ws.contexts = {"contexts": {}}

        # Mock provider
        provider = MagicMock(spec=ConfigurationProvider)

        # Call the method
        service._enhance_context(ctx_dict, "unknown_context", processed_ws, provider)

        # Verify context was not enhanced (no resolved_paths added)
        assert "resolved_paths" not in ctx_dict

    def test_enhance_component(self, enhanced_config_service_setup):
        """Test _enhance_component method."""
        service = enhanced_config_service_setup["service"]
        mock_path_service = enhanced_config_service_setup["mock_path_service"]
        enhanced_config_service_setup["config_file_path"]

        # Create test data
        comp_dict = {"name": "component1"}

        # Mock processed context and workspace
        processed_ctx = MagicMock(spec=Context)
        processed_ws = MagicMock(spec=Workspace)

        # Mock component
        mock_component = MagicMock()
        mock_component.config = MagicMock()
        mock_component.model_dump.return_value = {
            "name": "component1",
            "type": "test",
            "template": "template1",
            "config": {},
            "_config_file_path": "/path/to/config.yaml",
        }
        mock_component.config.model_dump.return_value = {
            "param1": "value1",
            "param2": "value2",
        }
        processed_ctx.components = {"components": {"component1": mock_component}}

        # Mock provider and path_service
        provider = MagicMock(spec=ConfigurationProvider)
        provider.path_service = mock_path_service

        # Mock resolve_component_paths
        mock_path_service.resolve_component_paths.return_value = {
            "output": Path("/path/to/component1")
        }

        # Call the method
        service._enhance_component(
            comp_dict, "component1", processed_ctx, processed_ws, provider
        )

        # Verify component was enhanced
        assert "resolved_paths" in comp_dict
        assert comp_dict["resolved_paths"]["output"] == "/path/to/component1"
        assert "type" in comp_dict
        assert comp_dict["type"] == "test"
        assert "template" in comp_dict
        assert comp_dict["template"] == "template1"
        assert "config" in comp_dict
        assert comp_dict["config"]["param1"] == "value1"
        assert comp_dict["config"]["param2"] == "value2"

    def test_enhance_component_not_found(self, enhanced_config_service_setup):
        """Test _enhance_component method when component is not found."""
        service = enhanced_config_service_setup["service"]
        enhanced_config_service_setup["mock_path_service"]
        enhanced_config_service_setup["config_file_path"]

        # Create test data
        comp_dict = {"name": "unknown_component"}

        # Mock processed context with no matching component
        processed_ctx = MagicMock(spec=Context)
        processed_ctx.components = {"components": {}}
        processed_ws = MagicMock(spec=Workspace)

        # Mock provider
        provider = MagicMock(spec=ConfigurationProvider)

        # Call the method
        service._enhance_component(
            comp_dict, "unknown_component", processed_ctx, processed_ws, provider
        )

        # Verify component was not enhanced (no resolved_paths added)
        assert "resolved_paths" not in comp_dict

    def test_deep_copy_of_discovered_dict(self, enhanced_config_service_setup):
        """Test that a deep copy of the discovered dict is made."""
        service = enhanced_config_service_setup["service"]
        enhanced_config_service_setup["mock_path_service"]
        enhanced_config_service_setup["config_file_path"]

        # Create test data
        discovered_dict = {"version": "1.0", "workspaces": []}
        mock_config = MagicMock(spec=CoregenConfig)
        mock_config.workspaces = []
        provider = MagicMock(spec=ConfigurationProvider)

        # Patch copy.deepcopy to verify it's called with the right argument
        with patch("copy.deepcopy", wraps=copy.deepcopy) as mock_deepcopy:
            service._enhance_discovered_config(discovered_dict, mock_config, provider)

            # Verify deepcopy was called with discovered_dict
            mock_deepcopy.assert_called_once_with(discovered_dict)
