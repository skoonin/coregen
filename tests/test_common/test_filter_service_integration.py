"""
Integration tests for filter service with Pydantic models.

Tests filtering workspaces, contexts, and components using raw Pydantic models
with nested properties, custom fields, and field inheritance.
"""

from typing import Any
from unittest.mock import Mock

import pytest

from coregen.common.filter_service import FilterService
from coregen.common.logger import Logger
from coregen.config_model.access import ConfigAccess
from coregen.config_model.models.components import Component, ComponentConfig
from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig


class TestFilterServiceIntegration:
    """Integration tests for filter service with Pydantic models."""

    @pytest.fixture
    def mock_config_access(self) -> Any:
        """Create a mock ConfigAccess instance."""
        return Mock(spec=ConfigAccess)

    @pytest.fixture
    def mock_logger(self) -> Any:
        """Create a mock Logger instance."""
        return Mock(spec=Logger)

    @pytest.fixture
    def filter_service(self, mock_config_access, mock_logger) -> Any:
        """Create a FilterService instance with mocked dependencies."""
        # Mock the find_workspaces method for workspace lookup
        mock_workspace = Mock()
        mock_workspace.name = "test-workspace"
        mock_config_access.find_workspaces.return_value = [mock_workspace]
        mock_config_access.get_all_contexts.return_value = {"test-context": Mock()}

        return FilterService(mock_config_access, mock_logger)

    @pytest.fixture
    def sample_elements(self) -> Any:
        """Create sample configuration elements as raw Pydantic models."""
        # Create workspace
        workspace = WorkspaceConfig(
            name="test-workspace",
            archive_dir="workspace-archive",
            cloud_provider="aws",  # Custom field
        )

        # Create contexts with field inheritance
        prod_context = Context(
            name="prod-context",
            environment="production",
            archive_dir="prod-archive",  # Override workspace
            workspace_ref=workspace,
        )

        dev_context = Context(
            name="dev-context",
            environment="development",
            # archive_dir will be inherited from workspace
            workspace_ref=workspace,
        )
        # Apply field inheritance
        dev_context.inherit_workspace_fields()

        # Create components
        nginx_config = ComponentConfig(active=True, priority=10)
        nginx_component = Component(name="nginx", config=nginx_config)

        redis_config = ComponentConfig(active=False, priority=5)
        redis_component = Component(name="redis", config=redis_config)

        return {
            "workspaces": {"test-workspace": workspace},
            "contexts": {
                "prod-context": prod_context,
                "dev-context": dev_context,
            },
            "components": {
                "prod-context/nginx": nginx_component,
                "prod-context/redis": redis_component,
                "dev-context/nginx": nginx_component,
            },
        }

    def test_filter_workspace_by_name(self, filter_service, sample_elements):
        """Test filtering workspaces by name using raw Pydantic models."""
        # Parse filter for workspace name
        filter_spec = filter_service.parse_filter_expression(
            "workspace.name=test-workspace"
        )

        # Apply filter
        result = filter_service.apply_filters(sample_elements, [filter_spec])

        # Should keep the workspace
        assert "test-workspace" in result["workspaces"]
        assert len(result["workspaces"]) == 1

    def test_filter_workspace_by_custom_field(self, filter_service, sample_elements):
        """Test filtering workspaces by custom field using raw Pydantic models."""
        # Parse filter for custom field
        filter_spec = filter_service.parse_filter_expression(
            "workspace.cloud_provider=aws"
        )

        # Apply filter
        result = filter_service.apply_filters(sample_elements, [filter_spec])

        # Should keep the workspace with matching custom field
        assert "test-workspace" in result["workspaces"]
        assert len(result["workspaces"]) == 1

    def test_filter_context_by_environment(self, filter_service, sample_elements):
        """Test filtering contexts by environment using raw Pydantic models."""
        # Parse filter for production environment
        filter_spec = filter_service.parse_filter_expression(
            "context.environment=production"
        )

        # Apply filter
        result = filter_service.apply_filters(sample_elements, [filter_spec])

        # Should only keep production context
        assert "prod-context" in result["contexts"]
        assert "dev-context" not in result["contexts"]
        assert len(result["contexts"]) == 1

        # Should only keep components from production context
        assert "prod-context/nginx" in result["components"]
        assert "prod-context/redis" in result["components"]
        assert "dev-context/nginx" not in result["components"]

    def test_filter_context_by_inherited_field(self, filter_service, sample_elements):
        """Test filtering contexts by inherited field from workspace."""
        # The dev context should inherit workspace-archive from workspace
        # Parse filter for inherited archive_dir
        filter_spec = filter_service.parse_filter_expression(
            "context.archive_dir=workspace-archive"
        )

        # Apply filter
        result = filter_service.apply_filters(sample_elements, [filter_spec])

        # Should only keep dev context (which inherited workspace-archive)
        assert "dev-context" in result["contexts"]
        assert "prod-context" not in result["contexts"]  # Has prod-archive override
        assert len(result["contexts"]) == 1

    def test_filter_component_by_nested_property(self, filter_service, sample_elements):
        """Test filtering components by nested config property using raw Pydantic models."""
        # Parse filter for active components
        filter_spec = filter_service.parse_filter_expression(
            "component.config.active=true"
        )

        # Apply filter
        result = filter_service.apply_filters(sample_elements, [filter_spec])

        # Should only keep active components (nginx)
        assert "prod-context/nginx" in result["components"]
        assert "dev-context/nginx" in result["components"]
        assert "prod-context/redis" not in result["components"]  # inactive
        assert len(result["components"]) == 2

    def test_filter_component_by_priority(self, filter_service, sample_elements):
        """Test filtering components by priority using raw Pydantic models."""
        # Parse filter for high priority components
        filter_spec = filter_service.parse_filter_expression(
            "component.config.priority>=10"
        )

        # Apply filter
        result = filter_service.apply_filters(sample_elements, [filter_spec])

        # Should only keep components with priority >= 10 (nginx has priority 10)
        assert "prod-context/nginx" in result["components"]
        assert "dev-context/nginx" in result["components"]
        assert "prod-context/redis" not in result["components"]  # priority 5
        assert len(result["components"]) == 2

    def test_no_filter_returns_all_elements(self, filter_service, sample_elements):
        """Test that no filters returns all elements unchanged."""
        # Apply no filters
        result = filter_service.apply_filters(sample_elements, [])

        # Should return all elements
        assert len(result["workspaces"]) == 1
        assert len(result["contexts"]) == 2
        assert len(result["components"]) == 3

    def test_nested_attr_access_with_missing_property(self, filter_service):
        """Test that _get_nested_attr handles missing properties gracefully."""
        # Create a simple component
        component = Component(name="test")

        # Try to access a non-existent nested property
        result = filter_service._get_nested_attr(component, "nonexistent.property")

        # Should return None for missing properties
        assert result is None

    def test_nested_attr_access_with_valid_property(self, filter_service):
        """Test that _get_nested_attr works with valid nested properties."""
        # Create a component with config
        config = ComponentConfig(active=True, priority=5)
        component = Component(name="test", config=config)

        # Access nested property
        result = filter_service._get_nested_attr(component, "config.active")
        assert result is True

        result = filter_service._get_nested_attr(component, "config.priority")
        assert result == 5

        # Access simple property
        result = filter_service._get_nested_attr(component, "name")
        assert result == "test"

    @pytest.mark.parametrize(
        "entity_type,entity_class,entity_key,filter_expr,match_key,no_match_keys",
        [
            (
                "context",
                Context,
                "contexts",
                "context.versions.helmfile=v0.144.0",
                "cluster-01",
                ["cluster-02", "cluster-03"],
            ),
            (
                "workspace",
                WorkspaceConfig,
                "workspaces",
                "workspace.tool_versions.terraform=1.5.0",
                "workspace-01",
                ["workspace-02", "workspace-03"],
            ),
        ],
    )
    def test_filter_by_nested_custom_field(
        self,
        filter_service,
        mock_config_access,
        entity_type,
        entity_class,
        entity_key,
        filter_expr,
        match_key,
        no_match_keys,
    ):
        """Test filtering contexts and workspaces by nested custom fields."""
        if entity_type == "context":
            # Create contexts with nested custom fields
            entity_with_nested = Context(
                name=match_key,
                environment="production",
                versions={
                    "helmfile": "v0.144.0",
                    "helm": "v3.11.3",
                    "kubectl": "v1.27.3",
                },
            )
            entity_without_nested = Context(
                name=no_match_keys[0], environment="production"
            )
            entity_different_value = Context(
                name=no_match_keys[1],
                environment="production",
                versions={"helmfile": "v0.140.0", "helm": "v3.10.0"},
            )

            # Mock setup
            mock_workspace = Mock()
            mock_config_access.find_workspaces.return_value = [mock_workspace]
            mock_config_access.get_all_contexts.return_value = {
                match_key: entity_with_nested
            }
        else:  # workspace
            # Create workspaces with nested custom fields
            entity_with_nested = WorkspaceConfig(
                name=match_key,
                workspace_dir="workspaces",
                context_type="cluster",
                tool_versions={"terraform": "1.5.0", "ansible": "2.15.0"},
            )
            entity_without_nested = WorkspaceConfig(
                name=no_match_keys[0],
                workspace_dir="workspaces",
                context_type="cluster",
            )
            entity_different_value = WorkspaceConfig(
                name=no_match_keys[1],
                workspace_dir="workspaces",
                context_type="cluster",
                tool_versions={"terraform": "1.4.0"},
            )

            # Mock setup
            mock_config_access.find_workspaces.return_value = [entity_with_nested]

        # Build elements dict
        elements = {
            "workspaces": {},
            "contexts": {},
            "components": {},
        }
        elements[entity_key] = {
            match_key: entity_with_nested,
            no_match_keys[0]: entity_without_nested,
            no_match_keys[1]: entity_different_value,
        }

        # Test filtering
        filter_spec = filter_service.parse_filter_expression(filter_expr)
        result = filter_service.apply_filters(elements, [filter_spec])

        # Verify results
        assert match_key in result[entity_key]
        assert no_match_keys[0] not in result[entity_key]
        assert no_match_keys[1] not in result[entity_key]
        assert len(result[entity_key]) == 1

    def test_nested_custom_field_access_with_dict(self, filter_service):
        """Test that _get_nested_attr handles nested dict custom fields correctly."""
        # Create a context with nested custom fields
        context = Context(
            name="test-context",
            environment="dev",
            versions={"helmfile": "v0.144.0", "helm": "v3.11.3"},
        )

        # Access nested custom field (should work via model_extra)
        result = filter_service._get_nested_attr(context, "versions.helmfile")
        assert result == "v0.144.0"

        result = filter_service._get_nested_attr(context, "versions.helm")
        assert result == "v3.11.3"

        # Access non-existent nested field
        result = filter_service._get_nested_attr(context, "versions.nonexistent")
        assert result is None
