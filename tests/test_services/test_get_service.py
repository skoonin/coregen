"""Unit tests for the GetService class."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig
from coregen.services.get.get_service import GetService


@pytest.fixture
def get_service_setup():
    """Set up test fixtures for GetService tests."""
    # Create mock configuration elements
    mock_workspace = MagicMock(spec=WorkspaceConfig)
    mock_workspace.name = "test-workspace"
    mock_workspace.context_type = "cluster"
    mock_workspace.get = MagicMock(side_effect=lambda key, default=None: default)

    mock_context = MagicMock(spec=Context)
    mock_context.name = "test-context"
    mock_context.environment = "dev"
    mock_context.workspace_name = "test-workspace"
    mock_context.active = True
    mock_context.model_dump = MagicMock(return_value={"name": "test-context"})
    mock_context.get = MagicMock(side_effect=lambda key, default=None: default)

    mock_component = MagicMock(spec=Component)
    mock_component.name = "test-component"
    # Create mock config
    mock_config = MagicMock()
    mock_config.active = True
    mock_component.config = mock_config
    mock_component.context_name = "test-context"
    mock_component.workspace_name = "test-workspace"
    mock_component.model_dump = MagicMock(return_value={"name": "test-component"})

    # Mock get_all_components to return components
    mock_contexts = {"test-context": mock_context}
    mock_workspace.contexts = {"cluster": mock_contexts}
    mock_context.components = {"app": {"test-component": mock_component}}

    # Create mock config provider
    mock_config_provider = MagicMock()
    mock_config_provider.path_service = MagicMock()
    mock_config_provider.path_service.resolver = MagicMock()
    mock_config_provider.path_service.resolver.root_path = Path("/mock/root/path")

    # Initialize service with config provider
    service = GetService(config_provider=mock_config_provider)

    # Set up mocks for service - patch internal attributes
    service._config_access = MagicMock()
    service._filter_service = MagicMock()

    # These services are initialized in GetService.__init__, so we can just mock them
    service.inactive_filter_service = MagicMock()
    service.entity_resolution_service = MagicMock()
    service.format_type_service = MagicMock()
    service.name_filter_service = MagicMock()
    service.type_filter_service = MagicMock()
    service.parse_filter_expression = MagicMock()

    return {
        "service": service,
        "mock_workspace": mock_workspace,
        "mock_context": mock_context,
        "mock_component": mock_component,
        "mock_config_provider": mock_config_provider,
    }


class TestGetService:
    """Test the GetService class."""

    def test_get_elements_with_patterns(self, get_service_setup):
        """Test getting elements using patterns."""
        service = get_service_setup["service"]
        mock_workspace = get_service_setup["mock_workspace"]
        mock_context = get_service_setup["mock_context"]
        mock_component = get_service_setup["mock_component"]

        # Mock the complete model and pattern selector
        mock_complete_model = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {"test-context": mock_context},
            "components": {"test-context/test-component": mock_component},
        }

        with patch.object(
            service._config_access,
            "get_complete_model",
            return_value=mock_complete_model,
        ):
            # Mock inactive filter to return the same model
            service.inactive_filter_service.filter_complete_model.return_value = (
                mock_complete_model
            )

            with patch(
                "coregen.services.get.get_service.PatternSelector"
            ) as mock_pattern_selector:
                # Mock the pattern selector to return our component
                mock_selector_instance = MagicMock()
                mock_selector_instance.select_by_pattern.return_value = {
                    "workspaces": {},
                    "contexts": {},
                    "components": {"test-context/test-component": mock_component},
                }
                mock_pattern_selector.return_value = mock_selector_instance

                # Call get_elements with a component pattern
                result = service.get_elements(
                    patterns=["component/test-workspace/test-context/test-component"],
                    include_inactive=True,
                )

                # Verify pattern selector was used
                mock_pattern_selector.assert_called()
                mock_selector_instance.select_by_pattern.assert_called_once()

                # Verify results - components are returned as a dict
                assert "components" in result
                assert len(result["components"]) == 1
                # Components are keyed by their path
                component_key = list(result["components"].keys())[0]
                component = result["components"][component_key]
                assert component.name == "test-component"

    def test_get_elements_with_multiple_patterns(self, get_service_setup):
        """Test getting elements with multiple patterns."""
        service = get_service_setup["service"]
        mock_workspace = get_service_setup["mock_workspace"]
        mock_context = get_service_setup["mock_context"]
        mock_component = get_service_setup["mock_component"]

        # Mock the complete model
        mock_complete_model = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {"test-context": mock_context},
            "components": {"test-context/test-component": mock_component},
        }

        with patch.object(
            service._config_access,
            "get_complete_model",
            return_value=mock_complete_model,
        ):
            # Mock inactive filter to return the same model
            service.inactive_filter_service.filter_complete_model.return_value = (
                mock_complete_model
            )

            with patch(
                "coregen.services.get.get_service.PatternSelector"
            ) as mock_pattern_selector:
                # Mock the pattern selector to return different results for each pattern
                mock_selector_instance = MagicMock()
                mock_selector_instance.select_by_pattern.side_effect = [
                    # First pattern returns workspace
                    {
                        "workspaces": {"test-workspace": mock_workspace},
                        "contexts": {},
                        "components": {},
                    },
                    # Second pattern returns context
                    {
                        "workspaces": {},
                        "contexts": {"test-context": mock_context},
                        "components": {},
                    },
                    # Third pattern returns component
                    {
                        "workspaces": {},
                        "contexts": {},
                        "components": {"test-context/test-component": mock_component},
                    },
                ]
                mock_pattern_selector.return_value = mock_selector_instance

                # Call get_elements with multiple patterns
                result = service.get_elements(
                    patterns=[
                        "workspace/test-workspace",
                        "context/test-workspace/test-context",
                        "component/test-workspace/test-context/test-component",
                    ],
                    include_inactive=True,
                )

                # Verify pattern selector was called 3 times
                assert mock_selector_instance.select_by_pattern.call_count == 3

                # Verify results
                assert "workspaces" in result
                assert "contexts" in result
                assert "components" in result
                assert len(result["workspaces"]) == 1
                assert len(result["contexts"]) == 1
                assert len(result["components"]) == 1

    def test_get_elements_with_filters(self, get_service_setup):
        """Test getting elements with filters."""
        service = get_service_setup["service"]
        mock_workspace = get_service_setup["mock_workspace"]
        mock_context = get_service_setup["mock_context"]
        mock_component = get_service_setup["mock_component"]

        # Mock the complete model
        mock_complete_model = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {"test-context": mock_context},
            "components": {"test-context/test-component": mock_component},
        }

        with patch.object(
            service._config_access,
            "get_complete_model",
            return_value=mock_complete_model,
        ):
            # Mock filter service to return filtered model
            service._filter_service.apply_filters_complete.return_value = {
                "workspaces": {},
                "contexts": {},
                "components": {},
            }

            # Mock inactive filter to return the same model
            service.inactive_filter_service.filter_complete_model.return_value = {
                "workspaces": {},
                "contexts": {},
                "components": {},
            }

            # Set up parse_filter_expression mock
            service.parse_filter_expression = MagicMock(
                return_value=("environment", "=", "prod")
            )

            with patch(
                "coregen.services.get.get_service.PatternSelector"
            ) as mock_pattern_selector:
                # Mock pattern selector to return empty (everything filtered out)
                mock_selector_instance = MagicMock()
                mock_selector_instance.select_by_pattern.return_value = {
                    "workspaces": {},
                    "contexts": {},
                    "components": {},
                }
                mock_pattern_selector.return_value = mock_selector_instance

                # Call get_elements with filters
                result = service.get_elements(
                    patterns=["context/test-workspace/test-context"],
                    filters=["environment=prod"],
                )

                # Verify parse_filter_expression was called
                service.parse_filter_expression.assert_called_once_with(
                    "environment=prod"
                )

                # Verify filter service was called
                service._filter_service.apply_filters_complete.assert_called_once()

                # Verify results reflect filtering (empty results)
                assert "components" in result
                assert len(result["components"]) == 0

    def test_get_elements_from_json_string(self, get_service_setup):
        """Test getting elements from JSON string."""
        service = get_service_setup["service"]
        mock_workspace = get_service_setup["mock_workspace"]
        mock_context = get_service_setup["mock_context"]
        mock_component = get_service_setup["mock_component"]

        # Set up mock for _process_json_input to return new architecture format
        mock_json_result = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {"test-context": mock_context},
            "components": {"test-context/test-component": mock_component},
        }

        service._process_json_input = MagicMock(return_value=mock_json_result)

        # Create JSON input
        json_input = json.dumps(
            [
                {
                    "workspace": "test-workspace",
                    "context": "test-context",
                    "component": "test-component",
                }
            ]
        )

        # Call get_elements with JSON input
        result = service.get_elements(from_json=json_input)

        # Verify _process_json_input was called with the right arguments
        service._process_json_input.assert_called_once_with(
            json_input, None, None, False, None
        )

        # Verify results
        assert "components" in result
        assert "test-context/test-component" in result["components"]

    def test_get_elements_from_json_file(self, get_service_setup):
        """Test getting elements from JSON file."""
        service = get_service_setup["service"]
        mock_workspace = get_service_setup["mock_workspace"]
        mock_context = get_service_setup["mock_context"]
        mock_component = get_service_setup["mock_component"]

        # Set up mock for _process_json_input to return new architecture format
        mock_json_result = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {"test-context": mock_context},
            "components": {"test-context/test-component": mock_component},
        }

        service._process_json_input = MagicMock(return_value=mock_json_result)

        # Create mock JSON file path
        json_file_path = Path("/mock/path/components.json")

        # Call get_elements with JSON file
        result = service.get_elements(json_file=json_file_path)

        # Verify _process_json_input was called
        service._process_json_input.assert_called_once_with(
            None, json_file_path, None, False, None
        )

        # Verify results
        assert "components" in result
        assert "test-context/test-component" in result["components"]

    def test_name_only_flag(self, get_service_setup):
        """Test get_elements with name_only flag."""
        service = get_service_setup["service"]
        mock_workspace = get_service_setup["mock_workspace"]
        mock_context = get_service_setup["mock_context"]
        mock_component = get_service_setup["mock_component"]

        # Mock the complete model
        mock_complete_model = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {"test-context": mock_context},
            "components": {"test-context/test-component": mock_component},
        }

        with patch.object(
            service._config_access,
            "get_complete_model",
            return_value=mock_complete_model,
        ):
            # Mock inactive filter to return the same model
            service.inactive_filter_service.filter_complete_model.return_value = (
                mock_complete_model
            )

            with patch(
                "coregen.services.get.get_service.PatternSelector"
            ) as mock_pattern_selector:
                # Mock pattern selector
                mock_selector_instance = MagicMock()
                mock_selector_instance.select_by_pattern.return_value = {
                    "workspaces": {},
                    "contexts": {},
                    "components": {"test-context/test-component": mock_component},
                }
                mock_pattern_selector.return_value = mock_selector_instance

                # Mock name filter service to return names only
                service.name_filter_service.filter_names_only.return_value = {
                    "workspaces": [],
                    "contexts": [],
                    "components": ["test-component"],
                }

                # Call get_elements with name_only flag
                result = service.get_elements(
                    patterns=["component/**"],
                    name_only=True,
                )

                # Verify name filter service was called
                service.name_filter_service.filter_names_only.assert_called_once()

                # Verify results contain only names
                assert "components" in result
                assert result["components"] == ["test-component"]

    def test_input_validation(self, get_service_setup):
        """Test input validation for get_elements."""
        service = get_service_setup["service"]

        # Test that ValueError is raised when no patterns or JSON input is provided
        with pytest.raises(ValueError) as exc_info:
            service.get_elements()

        assert "Either patterns or JSON input" in str(exc_info.value)

    def test_filter_order(self, get_service_setup):
        """Test that filters are applied in the correct order."""
        service = get_service_setup["service"]
        mock_workspace = get_service_setup["mock_workspace"]
        mock_context = get_service_setup["mock_context"]
        mock_component = get_service_setup["mock_component"]

        # Mock the complete model
        mock_complete_model = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {"test-context": mock_context},
            "components": {"test-context/test-component": mock_component},
        }

        with patch.object(
            service._config_access,
            "get_complete_model",
            return_value=mock_complete_model,
        ):
            # Track call order
            call_order = []

            # Mock filter service
            def mock_apply_filters_complete(*args, **kwargs):
                call_order.append("filters")
                return mock_complete_model

            service._filter_service.apply_filters_complete.side_effect = (
                mock_apply_filters_complete
            )

            # Mock inactive filter
            def mock_filter_complete_model(*args, **kwargs):
                call_order.append("inactive")
                return mock_complete_model

            service.inactive_filter_service.filter_complete_model.side_effect = (
                mock_filter_complete_model
            )

            # Set up parse_filter_expression mock
            service.parse_filter_expression = MagicMock(
                return_value=("active", "=", "true")
            )

            with patch(
                "coregen.services.get.get_service.PatternSelector"
            ) as mock_pattern_selector:
                # Mock pattern selector
                def mock_select_by_pattern(*args, **kwargs):
                    call_order.append("pattern")
                    return {
                        "workspaces": {},
                        "contexts": {},
                        "components": {"test-context/test-component": mock_component},
                    }

                mock_selector_instance = MagicMock()
                mock_selector_instance.select_by_pattern.side_effect = (
                    mock_select_by_pattern
                )
                mock_pattern_selector.return_value = mock_selector_instance

                # Call get_elements with filters
                service.get_elements(
                    patterns=["component/**"],
                    filters=["active=true"],
                    include_inactive=False,
                )

                # Verify order: filters, inactive, pattern
                assert call_order == ["filters", "inactive", "pattern"]

    def test_pattern_filter_mismatch_raises_error(self, get_service_setup):
        """Test that pattern/filter entity type mismatches raise ValueError."""
        service = get_service_setup["service"]

        with patch.object(service, "_config_access") as mock_config_access:
            # Set up mock config_access
            mock_config_access.get_complete_model.return_value = {
                "workspaces": {},
                "contexts": {},
                "components": {},
            }

            # Test c/* with component.* filter raises error
            with pytest.raises(
                ValueError, match="Pattern/filter mismatch.*component fields"
            ):
                service.get_elements(
                    patterns=["c/*"],
                    filters=["component.config.priority=none"],
                )

            # Test cm/* with context.* filter raises error
            with pytest.raises(
                ValueError, match="Pattern/filter mismatch.*context fields"
            ):
                service.get_elements(
                    patterns=["cm/*"],
                    filters=["context.environment=prod"],
                )

            # Test w/* with nested entity filters raises error
            with pytest.raises(
                ValueError, match="Pattern/filter mismatch.*component fields"
            ):
                service.get_elements(
                    patterns=["w/*"],
                    filters=["component.config.active=true"],
                )
