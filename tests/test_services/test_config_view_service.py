"""
Unit tests for the ConfigViewService class.

This test file focuses on comprehensive testing of the ConfigViewService class,
with particular attention to the view_config and filter_config_data methods.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coregen.common.console import Console
from coregen.common.file_manager import FileManager
from coregen.common.workspace_initializer import WorkspaceInitializer
from coregen.config_model.models.config import CoregenConfig
from coregen.config_model.provider import ConfigurationProvider
from coregen.services.config.cfg_view_service import ConfigViewService


@pytest.fixture
def config_view_setup():
    """Set up test fixtures for ConfigViewService tests."""
    # Create mock objects
    mock_console = MagicMock(spec=Console)
    mock_file_manager = MagicMock(spec=FileManager)
    mock_workspace_initializer = MagicMock(spec=WorkspaceInitializer)
    mock_config_provider = MagicMock(spec=ConfigurationProvider)

    # Create service with mocks
    service = ConfigViewService(
        console=mock_console,
        file_manager=mock_file_manager,
        workspace_initializer=mock_workspace_initializer,
        config_provider=mock_config_provider,
    )

    # Common test data
    sample_config = {
        "version": "1.0",
        "workspaces": [
            {
                "name": "workspace1",
                "contexts": [
                    {
                        "name": "context1",
                        "environment": "dev",
                        "components": [
                            {
                                "name": "component1",
                                "type": "service",
                                "active": True,
                            },
                            {
                                "name": "component2",
                                "type": "database",
                                "active": False,
                            },
                        ],
                    },
                    {
                        "name": "context2",
                        "environment": "prod",
                        "components": [
                            {
                                "name": "component3",
                                "type": "service",
                                "active": True,
                            },
                        ],
                    },
                ],
            },
            {
                "name": "workspace2",
                "contexts": [
                    {
                        "name": "context3",
                        "environment": "dev",
                        "components": [
                            {
                                "name": "component4",
                                "type": "network",
                                "active": True,
                            },
                        ],
                    },
                ],
            },
        ],
    }

    return {
        "mock_console": mock_console,
        "mock_file_manager": mock_file_manager,
        "mock_workspace_initializer": mock_workspace_initializer,
        "mock_config_provider": mock_config_provider,
        "service": service,
        "sample_config": sample_config,
    }


class TestConfigViewService:
    """Comprehensive tests for the ConfigViewService class."""

    def test_view_config_file_not_found(self, config_view_setup):
        """Test view_config with a non-existent file."""
        service = config_view_setup["service"]
        # Mock Path.exists to return False
        with patch("pathlib.Path.exists", return_value=False):
            # Expect FileNotFoundError when file doesn't exist
            with pytest.raises(FileNotFoundError):
                service.view_config(config_file_path=Path("nonexistent.yaml"))

    def test_view_config_default_path(self, config_view_setup):
        """Test view_config using default path determination."""
        service = config_view_setup["service"]
        # Mock settings and path resolution
        service.settings.system.config_file_name = "default.yaml"

        # Mock Path methods
        with patch("pathlib.Path.is_absolute", return_value=False):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.cwd", return_value=Path("/current/dir")):
                    with patch.object(
                        service, "_view_raw_config", return_value={"test": "data"}
                    ) as mock_view_raw:
                        # Call view_config without specifying a path
                        result = service.view_config()

                        # Verify the correct path was used
                        mock_view_raw.assert_called_once_with(
                            Path("/current/dir/default.yaml")
                        )
                        assert result == {"test": "data"}

    def test_view_config_absolute_path(self, config_view_setup):
        """Test view_config with an absolute path."""
        service = config_view_setup["service"]
        absolute_path = Path("/absolute/path/to/config.yaml")

        # Mock Path methods
        with patch("pathlib.Path.is_absolute", return_value=True):
            with patch("pathlib.Path.exists", return_value=True):
                with patch.object(
                    service, "_view_raw_config", return_value={"test": "data"}
                ) as mock_view_raw:
                    # Call view_config with an absolute path
                    result = service.view_config(config_file_path=absolute_path)

                    # Verify the correct path was used
                    mock_view_raw.assert_called_once_with(absolute_path)
                    assert result == {"test": "data"}

    def test_view_config_invalid_mode(self, config_view_setup):
        """Test view_config with an invalid view mode."""
        service = config_view_setup["service"]
        # Mock Path.exists to return True
        with patch("pathlib.Path.exists", return_value=True):
            # Expect ValueError for invalid mode
            with pytest.raises(ValueError) as excinfo:
                service.view_config(
                    config_file_path=Path("config.yaml"), view_mode="invalid_mode"
                )

            # Verify error message
            assert "Invalid view mode" in str(excinfo.value)

    def test_view_config_all_modes(self, config_view_setup):
        """Test view_config with all supported modes."""
        service = config_view_setup["service"]
        config_path = Path("config.yaml")
        modes = ["raw", "discovered", "resolved", "enhanced"]

        # Mock Path.exists to return True
        with patch("pathlib.Path.exists", return_value=True):
            for mode in modes:
                # Mock the appropriate method based on the mode
                if mode == "raw":
                    mock_method = "_view_raw_config"
                elif mode == "discovered":
                    mock_method = "_view_discovered_config"
                elif mode == "resolved":
                    mock_method = "_view_resolved_config"
                else:  # enhanced
                    # For enhanced mode, we need to mock the ConfigEnhancedViewService
                    with patch(
                        "coregen.services.config.cfg_view_service.ConfigEnhancedViewService"
                    ) as mock_enhanced_class:
                        mock_enhanced = MagicMock()
                        mock_enhanced.view_enhanced_config.return_value = {
                            "enhanced": True
                        }
                        mock_enhanced_class.return_value = mock_enhanced

                        # Call view_config with enhanced mode
                        result = service.view_config(
                            config_file_path=config_path, view_mode=mode
                        )

                        # Verify the result
                        assert result == {"enhanced": True}
                        mock_enhanced.view_enhanced_config.assert_called_once_with(
                            config_path
                        )
                        continue

                # For non-enhanced modes, mock the base method
                with patch.object(
                    service, mock_method, return_value={"mode": mode}
                ) as mock_view_method:
                    # Call view_config with the current mode
                    result = service.view_config(
                        config_file_path=config_path, view_mode=mode
                    )

                    # Verify the result
                    assert result == {"mode": mode}
                    mock_view_method.assert_called_once_with(config_path)

    def test_filter_config_data_no_filters(self, config_view_setup):
        """Test filter_config_data with no filters applied."""
        service = config_view_setup["service"]
        sample_config = config_view_setup["sample_config"]
        # Use CoregenConfig mock
        mock_config = MagicMock(spec=CoregenConfig)
        mock_config.model_dump.return_value = sample_config

        # Filter with no criteria (should return all data, but inactive components are filtered out by default)
        result = service.filter_config_data(mock_config)

        # Verify result
        assert len(result["workspaces"]) == 2
        assert len(result["workspaces"][0]["contexts"]) == 2
        # By default, component2 is filtered out because it's inactive
        assert len(result["workspaces"][0]["contexts"][0]["components"]) == 1
        assert len(result["workspaces"][0]["contexts"][1]["components"]) == 1
        assert len(result["workspaces"][1]["contexts"]) == 1
        assert len(result["workspaces"][1]["contexts"][0]["components"]) == 1

    def test_filter_config_data_with_dict(self, config_view_setup):
        """Test filter_config_data with dictionary instead of CoregenConfig."""
        service = config_view_setup["service"]
        sample_config = config_view_setup["sample_config"]
        # Filter with no criteria using dict input
        result = service.filter_config_data(sample_config)

        # Verify result
        assert len(result["workspaces"]) == 2
        assert len(result["workspaces"][0]["contexts"]) == 2
        # By default, component2 is filtered out because it's inactive
        assert len(result["workspaces"][0]["contexts"][0]["components"]) == 1
        assert len(result["workspaces"][0]["contexts"][1]["components"]) == 1
        assert len(result["workspaces"][1]["contexts"]) == 1
        assert len(result["workspaces"][1]["contexts"][0]["components"]) == 1

    def test_filter_config_data_by_context(self, config_view_setup):
        """Test filter_config_data filtering by context names."""
        service = config_view_setup["service"]
        sample_config = config_view_setup["sample_config"]
        # Filter by context name
        result = service.filter_config_data(sample_config, contexts=["context1"])

        # Verify result
        assert len(result["workspaces"]) == 1  # Only workspace1 has context1
        assert (
            len(result["workspaces"][0]["contexts"]) == 1
        )  # Only context1 should be included
        assert result["workspaces"][0]["contexts"][0]["name"] == "context1"
        # By default, component2 is filtered out because it's inactive
        assert len(result["workspaces"][0]["contexts"][0]["components"]) == 1

    def test_filter_config_data_by_context_type(self, config_view_setup):
        """Test filter_config_data filtering by context type."""
        service = config_view_setup["service"]
        sample_config = config_view_setup["sample_config"]
        # Add type to contexts in sample data
        sample_config = sample_config.copy()
        sample_config["workspaces"][0]["contexts"][0]["type"] = "kubernetes"
        sample_config["workspaces"][0]["contexts"][1]["type"] = "aws"
        sample_config["workspaces"][1]["contexts"][0]["type"] = "kubernetes"

        # Filter by context type
        result = service.filter_config_data(sample_config, context_type="kubernetes")

        # Verify result
        assert (
            len(result["workspaces"]) == 2
        )  # Both workspaces have kubernetes contexts
        assert len(result["workspaces"][0]["contexts"]) == 1  # Only kubernetes contexts
        assert result["workspaces"][0]["contexts"][0]["type"] == "kubernetes"
        assert len(result["workspaces"][1]["contexts"]) == 1  # Only kubernetes contexts
        assert result["workspaces"][1]["contexts"][0]["type"] == "kubernetes"

    def test_filter_config_data_by_environment(self, config_view_setup):
        """Test filter_config_data filtering by environment."""
        service = config_view_setup["service"]
        sample_config = config_view_setup["sample_config"]
        # Filter by environment
        result = service.filter_config_data(sample_config, environments=["dev"])

        # Verify result
        assert len(result["workspaces"]) == 2  # Both workspaces have dev environments
        assert len(result["workspaces"][0]["contexts"]) == 1  # Only dev contexts
        assert result["workspaces"][0]["contexts"][0]["environment"] == "dev"
        assert len(result["workspaces"][1]["contexts"]) == 1  # Only dev contexts
        assert result["workspaces"][1]["contexts"][0]["environment"] == "dev"

    def test_filter_config_data_by_component(self, config_view_setup):
        """Test filter_config_data filtering by component names."""
        service = config_view_setup["service"]
        sample_config = config_view_setup["sample_config"]
        # Filter by component name
        result = service.filter_config_data(sample_config, components=["component1"])

        # Verify result
        # Implementation behavior: both workspaces remain, but only one has context with component1
        assert result["workspaces"][0]["name"] == "workspace1"
        assert (
            len(result["workspaces"][0]["contexts"]) == 1
        )  # Only context1 has component1
        assert (
            len(result["workspaces"][0]["contexts"][0]["components"]) == 1
        )  # Only component1
        assert (
            result["workspaces"][0]["contexts"][0]["components"][0]["name"]
            == "component1"
        )
        # workspace2 is kept in the result but has empty contexts since no matches
        assert result["workspaces"][1]["name"] == "workspace2"
        assert len(result["workspaces"][1]["contexts"]) == 0

    def test_filter_config_data_by_component_type(self, config_view_setup):
        """Test filter_config_data filtering by component type."""
        service = config_view_setup["service"]
        sample_config = config_view_setup["sample_config"]
        # Filter by component type
        result = service.filter_config_data(sample_config, component_type="service")

        # Verify result
        assert len(result["workspaces"]) == 2  # Both workspaces have service components
        assert (
            len(result["workspaces"][0]["contexts"]) == 2
        )  # Both contexts have service components
        # Check component counts
        assert (
            len(result["workspaces"][0]["contexts"][0]["components"]) == 1
        )  # One service component
        assert (
            result["workspaces"][0]["contexts"][0]["components"][0]["type"] == "service"
        )
        assert (
            len(result["workspaces"][0]["contexts"][1]["components"]) == 1
        )  # One service component
        assert (
            result["workspaces"][0]["contexts"][1]["components"][0]["type"] == "service"
        )

    def test_filter_config_data_active_false(self, config_view_setup):
        """Test filter_config_data with include_active_false parameter."""
        service = config_view_setup["service"]
        sample_config = config_view_setup["sample_config"]
        # Default behavior: excludes inactive components
        result_default = service.filter_config_data(sample_config)

        # Count active components in workspace1/context1
        active_count = len(result_default["workspaces"][0]["contexts"][0]["components"])
        assert active_count == 1  # Only active component1

        # Include inactive components
        result_with_inactive = service.filter_config_data(
            sample_config, include_active_false=True
        )

        # Count all components in workspace1/context1
        all_count = len(
            result_with_inactive["workspaces"][0]["contexts"][0]["components"]
        )
        assert all_count == 2  # Both active component1 and inactive component2

    def test_filter_config_data_combined_filters(self, config_view_setup):
        """Test filter_config_data with multiple filters combined."""
        service = config_view_setup["service"]
        sample_config = config_view_setup["sample_config"]
        # Add more data to test multiple filter combinations
        sample_config = sample_config.copy()
        sample_config["workspaces"][0]["contexts"][0]["type"] = "kubernetes"
        sample_config["workspaces"][0]["contexts"][1]["type"] = "aws"
        sample_config["workspaces"][1]["contexts"][0]["type"] = "kubernetes"

        # Apply multiple filters
        result = service.filter_config_data(
            sample_config,
            environments=["dev"],
            context_type="kubernetes",
            component_type="service",
        )

        # Verify result
        # Implementation behavior: Both workspaces with kubernetes contexts remain
        # but only workspace1/context1 has service components that match the filter
        assert len(result["workspaces"]) == 2

        # Check workspace1
        assert result["workspaces"][0]["name"] == "workspace1"
        assert (
            len(result["workspaces"][0]["contexts"]) == 1
        )  # Only context1 satisfies all conditions
        assert result["workspaces"][0]["contexts"][0]["environment"] == "dev"
        assert result["workspaces"][0]["contexts"][0]["type"] == "kubernetes"
        assert (
            len(result["workspaces"][0]["contexts"][0]["components"]) == 1
        )  # Only component1
        assert (
            result["workspaces"][0]["contexts"][0]["components"][0]["type"] == "service"
        )

        # Check workspace2 - it has a context with dev+kubernetes, but no service components
        assert result["workspaces"][1]["name"] == "workspace2"
        assert len(result["workspaces"][1]["contexts"]) == 1
        assert result["workspaces"][1]["contexts"][0]["environment"] == "dev"
        assert result["workspaces"][1]["contexts"][0]["type"] == "kubernetes"
        assert (
            len(result["workspaces"][1]["contexts"][0]["components"]) == 0
        )  # No service components

    def test_filter_config_data_non_matching_filters(self, config_view_setup):
        """Test filter_config_data with filters that don't match anything."""
        service = config_view_setup["service"]
        sample_config = config_view_setup["sample_config"]
        # Filter with criteria that don't match anything
        result = service.filter_config_data(
            sample_config,
            contexts=["nonexistent"],
            environments=["staging"],
            components=["nonexistent"],
        )

        # Verify result has empty workspaces
        assert len(result["workspaces"]) == 0

    def test_filter_config_data_empty_config(self, config_view_setup):
        """Test filter_config_data with an empty configuration."""
        service = config_view_setup["service"]
        # Empty config
        empty_config = {"workspaces": []}

        # Filter empty config
        result = service.filter_config_data(empty_config)

        # Verify result is also empty
        assert len(result["workspaces"]) == 0

    def test_filter_config_data_preserve_global_settings(self, config_view_setup):
        """Test filter_config_data preserves global settings."""
        service = config_view_setup["service"]
        sample_config = config_view_setup["sample_config"]
        # Config with global settings
        config_with_settings = sample_config.copy()
        config_with_settings["version"] = "1.0"
        config_with_settings["settings"] = {"global": True, "debug": False}

        # Filter with criteria that filter out all workspaces
        result = service.filter_config_data(
            config_with_settings, contexts=["nonexistent"]
        )

        # Verify global settings are preserved
        assert result["version"] == "1.0"
        assert result["settings"]["global"] is True
        assert result["settings"]["debug"] is False
        # But workspaces are filtered
        assert len(result["workspaces"]) == 0
