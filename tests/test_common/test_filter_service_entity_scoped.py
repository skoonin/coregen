"""
Test enhanced dot notation filtering with entity-scoped parsing.

Tests the filter service's ability to parse entity-scoped filter expressions
like "context.property=value" and "component.config.active=true".
"""

from typing import Any
from unittest.mock import Mock

import pytest

from coregen.common.filter_service import FilterService
from coregen.common.logger import Logger
from coregen.config_model.access import ConfigAccess


class TestFilterServiceEntityScoped:
    """Test entity-scoped filtering functionality."""

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
        return FilterService(mock_config_access, mock_logger)

    def test_parse_entity_scoped_simple_properties(self, filter_service):
        """Test parsing simple entity-scoped properties."""
        # Workspace properties
        result = filter_service.parse_filter_expression("workspace.name=aws")
        assert result == {
            "entity_type": "workspace",
            "property": "name",
            "operator": "=",
            "value": "aws",
        }

        # Context properties
        result = filter_service.parse_filter_expression(
            "context.environment=production"
        )
        assert result == {
            "entity_type": "context",
            "property": "environment",
            "operator": "=",
            "value": "production",
        }

        # Component properties
        result = filter_service.parse_filter_expression("component.name=nginx")
        assert result == {
            "entity_type": "component",
            "property": "name",
            "operator": "=",
            "value": "nginx",
        }

    def test_parse_entity_scoped_nested_properties(self, filter_service):
        """Test parsing entity-scoped nested properties."""
        # Component nested property
        result = filter_service.parse_filter_expression("component.config.active=true")
        assert result == {
            "entity_type": "component",
            "property": "config.active",
            "operator": "=",
            "value": True,
        }

        # Component vars property
        result = filter_service.parse_filter_expression(
            "component.vars.helm_version=1.2.3"
        )
        assert result == {
            "entity_type": "component",
            "property": "vars.helm_version",
            "operator": "=",
            "value": "1.2.3",
        }

    def test_parse_entity_scoped_with_operators(self, filter_service):
        """Test parsing entity-scoped properties with different operators."""
        # Not equal
        result = filter_service.parse_filter_expression("context.priority!=100")
        assert result == {
            "entity_type": "context",
            "property": "priority",
            "operator": "!=",
            "value": 100,
        }

        # Greater than
        result = filter_service.parse_filter_expression("component.config.priority>50")
        assert result == {
            "entity_type": "component",
            "property": "config.priority",
            "operator": ">",
            "value": 50,
        }

        # Pattern match (regex-style with ~=)
        result = filter_service.parse_filter_expression("workspace.name~=aws")
        assert result == {
            "entity_type": "workspace",
            "property": "name",
            "operator": "~=",
            "value": "aws",
        }

        # Pattern match (bash-style with =~)
        result = filter_service.parse_filter_expression("workspace.name=~aws")
        assert result == {
            "entity_type": "workspace",
            "property": "name",
            "operator": "=~",
            "value": "aws",
        }

    def test_parse_without_entity_scope(self, filter_service):
        """Test parsing filters without entity scope."""
        # Simple property
        result = filter_service.parse_filter_expression("active=true")
        assert result == {
            "entity_type": None,
            "property": "active",
            "operator": "=",
            "value": True,
        }

        # Nested property without entity
        result = filter_service.parse_filter_expression("config.priority=100")
        assert result == {
            "entity_type": None,
            "property": "config.priority",
            "operator": "=",
            "value": 100,
        }

    def test_parse_custom_fields(self, filter_service):
        """Test parsing custom field filters."""
        # Context custom field
        result = filter_service.parse_filter_expression(
            "context.custom_region=us-west-2"
        )
        assert result == {
            "entity_type": "context",
            "property": "custom_region",
            "operator": "=",
            "value": "us-west-2",
        }

        # Workspace custom field
        result = filter_service.parse_filter_expression("workspace.cloud_provider=aws")
        assert result == {
            "entity_type": "workspace",
            "property": "cloud_provider",
            "operator": "=",
            "value": "aws",
        }

    def test_parse_priority_none_with_entity(self, filter_service):
        """Test parsing priority=none with entity scope."""
        result = filter_service.parse_filter_expression(
            "component.config.priority=none"
        )
        assert result == {
            "entity_type": "component",
            "property": "config.priority",
            "operator": "=",
            "value": None,  # Should convert "none" to None for priority
        }

    def test_parse_type_conversions_with_entity(self, filter_service):
        """Test type conversions work with entity-scoped parsing."""
        # Boolean conversion
        result = filter_service.parse_filter_expression(
            "component.config.required=false"
        )
        assert result["value"] is False

        # Integer conversion
        result = filter_service.parse_filter_expression("context.account_id=12345")
        assert result["value"] == 12345

        # Float conversion
        result = filter_service.parse_filter_expression("component.vars.version=3.14")
        assert result["value"] == 3.14

    def test_apply_filter_respects_entity_type(
        self, filter_service, mock_config_access
    ):
        """Test that filters are only applied to specified entity types."""
        # Create test data
        elements = {
            "workspaces": {
                "ws1": {"name": "test", "active": True},
                "ws2": {"name": "prod", "active": False},
            },
            "contexts": {
                "ctx1": {"name": "test", "environment": "dev"},
                "ctx2": {"name": "prod", "environment": "prod"},
            },
            "components": {
                "comp1": {"name": "test", "config": {"active": True}},
                "comp2": {"name": "prod", "config": {"active": False}},
            },
        }

        # Filter for context.name=test - should only affect contexts
        filter_spec = {
            "entity_type": "context",
            "property": "name",
            "operator": "=",
            "value": "test",
        }

        result = filter_service.apply_filters(elements, [filter_spec])

        # Workspaces and components should be unchanged
        assert len(result["workspaces"]) == 2
        assert len(result["components"]) == 2
        # Only contexts should be filtered
        assert len(result["contexts"]) == 1
        assert "ctx1" in result["contexts"]
        assert "ctx2" not in result["contexts"]
