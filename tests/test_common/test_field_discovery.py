"""
Unit tests for field discovery service.

Tests the field discovery system's ability to introspect Pydantic models
and discover both base model fields and custom user-defined fields.
"""

from typing import Any
from unittest.mock import Mock

import pytest

from coregen.common.field_discovery import FieldDiscovery
from coregen.common.field_types import FieldInfo, FieldType
from coregen.common.logger import Logger
from coregen.config_model.access import ConfigAccess
from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig


class TestFieldDiscovery:
    """Test cases for the FieldDiscovery service."""

    @pytest.fixture
    def mock_config_access(self) -> Any:
        """Create a mock ConfigAccess instance."""
        return Mock(spec=ConfigAccess)

    @pytest.fixture
    def mock_logger(self) -> Any:
        """Create a mock Logger instance."""
        return Mock(spec=Logger)

    @pytest.fixture
    def field_discovery(self, mock_config_access, mock_logger) -> Any:
        """Create a FieldDiscovery instance with mocked dependencies."""
        return FieldDiscovery(mock_config_access, mock_logger)

    @pytest.fixture
    def sample_workspace(self) -> Any:
        """Create a sample workspace with custom fields."""
        # Create workspace with custom fields via constructor
        workspace_data = {
            "name": "test-workspace",
            "workspace_dir": "workspaces",
            "context_type": "cluster",
            # Custom fields
            "cloud_provider": "aws",
            "cost_center": "engineering",
            "region": "us-west-2",
        }
        workspace = WorkspaceConfig(**workspace_data)
        return workspace

    @pytest.fixture
    def sample_context(self) -> Any:
        """Create a sample context with custom fields."""
        # Create context with custom fields via constructor
        context_data = {
            "name": "test-context",
            "environment": "dev",
            # Custom fields
            "account_id": "123456789",
            "region_short": "usw2",
            "cloud": "aws",
        }
        context = Context(**context_data)
        return context

    @pytest.fixture
    def sample_component(self) -> Any:
        """Create a sample component with custom fields."""
        # Create component with custom fields via constructor
        component_data = {
            "name": "test-component",
            "config": {"active": True, "priority": 10},
            # Custom fields
            "team": "platform",
            "vars": {"helm_chart_version": "1.2.3", "replicas": 3},
        }
        component = Component(**component_data)
        return component

    def test_discover_workspace_fields(
        self, field_discovery, mock_config_access, sample_workspace
    ):
        """Test discovering fields from workspace entities."""
        # Setup mock to return sample workspace
        mock_config_access.find_workspaces.return_value = [sample_workspace]

        # Discover fields
        fields = field_discovery.discover_fields("workspace")

        # Verify model fields are discovered
        assert "name" in fields
        assert fields["name"].field_type == FieldType.STRING
        assert fields["name"].source == "model"

        assert "context_type" in fields
        assert fields["context_type"].field_type == FieldType.STRING
        assert fields["context_type"].source == "model"

        # Verify custom fields are discovered
        assert "cloud_provider" in fields
        assert fields["cloud_provider"].field_type == FieldType.STRING
        assert fields["cloud_provider"].source == "custom"

        assert "cost_center" in fields
        assert fields["cost_center"].field_type == FieldType.STRING
        assert fields["cost_center"].source == "custom"

    def test_discover_context_fields(
        self, field_discovery, mock_config_access, sample_context
    ):
        """Test discovering fields from context entities."""
        # Setup mock to return sample context
        sample_workspace = Mock()
        mock_config_access.find_workspaces.return_value = [sample_workspace]
        mock_config_access.get_all_contexts.return_value = {
            "test-context": sample_context
        }

        # Discover fields
        fields = field_discovery.discover_fields("context")

        # Verify model fields are discovered
        assert "name" in fields
        assert fields["name"].field_type == FieldType.STRING
        assert fields["name"].source == "model"

        assert "environment" in fields
        assert fields["environment"].field_type == FieldType.STRING
        assert fields["environment"].source == "model"

        assert "active" in fields
        assert fields["active"].field_type == FieldType.BOOLEAN
        assert fields["active"].source == "model"

        # Verify custom fields are discovered
        assert "account_id" in fields
        assert fields["account_id"].field_type == FieldType.STRING
        assert fields["account_id"].source == "custom"

        assert "cloud" in fields
        assert fields["cloud"].field_type == FieldType.STRING
        assert fields["cloud"].source == "custom"

    def test_discover_component_fields(
        self, field_discovery, mock_config_access, sample_component
    ):
        """Test discovering fields from component entities including nested config fields."""
        # Setup mock to return sample component
        sample_workspace = Mock()
        sample_context = Mock()
        sample_context.get_all_components.return_value = {
            "test-component": sample_component
        }

        mock_config_access.find_workspaces.return_value = [sample_workspace]
        mock_config_access.get_all_contexts.return_value = {
            "test-context": sample_context
        }

        # Discover fields
        fields = field_discovery.discover_fields("component")

        # Verify model fields are discovered
        assert "name" in fields
        assert fields["name"].field_type == FieldType.STRING
        assert fields["name"].source == "model"

        # Verify nested config fields are discovered
        assert "config.active" in fields
        assert fields["config.active"].field_type == FieldType.BOOLEAN
        assert fields["config.active"].source == "nested"
        assert fields["config.active"].nested_path == "config"

        assert "config.priority" in fields
        assert fields["config.priority"].field_type == FieldType.INTEGER
        assert fields["config.priority"].source == "nested"

        # Verify custom fields are discovered
        assert "team" in fields
        assert fields["team"].field_type == FieldType.STRING
        assert fields["team"].source == "custom"

        # Verify nested vars fields are discovered
        assert "vars.helm_chart_version" in fields
        assert fields["vars.helm_chart_version"].field_type == FieldType.STRING
        assert fields["vars.helm_chart_version"].source == "nested"
        assert fields["vars.helm_chart_version"].nested_path == "vars"

        assert "vars.replicas" in fields
        assert fields["vars.replicas"].field_type == FieldType.INTEGER
        assert fields["vars.replicas"].source == "nested"

    def test_field_type_detection_from_value(self, field_discovery):
        """Test field type detection from actual values."""
        # Test different value types
        assert (
            field_discovery._detect_field_type_from_value("string") == FieldType.STRING
        )
        assert field_discovery._detect_field_type_from_value(True) == FieldType.BOOLEAN
        assert field_discovery._detect_field_type_from_value(42) == FieldType.INTEGER
        assert field_discovery._detect_field_type_from_value(3.14) == FieldType.FLOAT
        assert field_discovery._detect_field_type_from_value({}) == FieldType.DICT
        assert field_discovery._detect_field_type_from_value([]) == FieldType.LIST

    def test_get_field_suggestions(
        self, field_discovery, mock_config_access, sample_context
    ):
        """Test field name suggestions for typos."""
        # Setup mock
        sample_workspace = Mock()
        mock_config_access.find_workspaces.return_value = [sample_workspace]
        mock_config_access.get_all_contexts.return_value = {
            "test-context": sample_context
        }

        # Test suggestions for typo
        suggestions = field_discovery.get_field_suggestions("activ", "context")
        assert "active" in suggestions

        # Test suggestions for partial match
        suggestions = field_discovery.get_field_suggestions("environ", "context")
        assert "environment" in suggestions

        # Test suggestions for custom field typo
        suggestions = field_discovery.get_field_suggestions("accont_id", "context")
        assert "account_id" in suggestions

    def test_validate_field_exists(
        self, field_discovery, mock_config_access, sample_context
    ):
        """Test field existence validation."""
        # Setup mock
        sample_workspace = Mock()
        mock_config_access.find_workspaces.return_value = [sample_workspace]
        mock_config_access.get_all_contexts.return_value = {
            "test-context": sample_context
        }

        # Test existing model field
        assert field_discovery.validate_field_exists("name", "context") is True
        assert field_discovery.validate_field_exists("environment", "context") is True

        # Test existing custom field
        assert field_discovery.validate_field_exists("account_id", "context") is True

        # Test non-existing field
        assert field_discovery.validate_field_exists("nonexistent", "context") is False

    def test_unsupported_entity_type(self, field_discovery):
        """Test error handling for unsupported entity types."""
        with pytest.raises(ValueError, match="Unsupported entity type"):
            field_discovery.discover_fields("invalid_type")

    def test_no_entities_found(self, field_discovery, mock_config_access, mock_logger):
        """Test handling when no entities are found."""
        # Setup mock to return empty results
        mock_config_access.find_workspaces.return_value = []

        fields = field_discovery.discover_fields("workspace")

        # Should return empty dict and log info message
        assert fields == {}
        mock_logger.info.assert_called()

    def test_exception_handling_during_sampling(
        self, field_discovery, mock_config_access, mock_logger
    ):
        """Test exception handling during entity sampling."""
        # Setup mock to raise exception
        mock_config_access.find_workspaces.side_effect = Exception("Test error")

        fields = field_discovery.discover_fields("workspace")

        # Should handle exception gracefully
        assert fields == {}
        # Should have at least one info call (may have multiple)
        assert mock_logger.info.call_count >= 1


class TestFieldInfo:
    """Test cases for the FieldInfo dataclass."""

    def test_field_info_creation(self):
        """Test creating FieldInfo instances."""
        field_info = FieldInfo(
            name="test_field",
            field_type=FieldType.STRING,
            source="model",
            description="Test field description",
        )

        assert field_info.name == "test_field"
        assert field_info.field_type == FieldType.STRING
        assert field_info.source == "model"
        assert field_info.description == "Test field description"

    def test_field_info_string_representation(self):
        """Test string representation of FieldInfo."""
        field_info = FieldInfo(
            name="test_field", field_type=FieldType.STRING, source="model"
        )

        str_repr = str(field_info)
        assert "test_field" in str_repr
        assert "string" in str_repr
        assert "model" in str_repr

    def test_field_info_with_nested_path(self):
        """Test FieldInfo with nested path information."""
        field_info = FieldInfo(
            name="config.active",
            field_type=FieldType.BOOLEAN,
            source="nested",
            nested_path="config",
        )

        str_repr = str(field_info)
        assert "config.active" in str_repr
        assert "boolean" in str_repr
        assert "nested" in str_repr
        assert "config" in str_repr
