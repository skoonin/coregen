"""
Unit tests for FilterService field discovery integration.

Tests the integration between FilterService and FieldDiscovery for
field validation and suggestion functionality.
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from coregen.common.filter_service import FilterService
from coregen.common.logger import Logger
from coregen.config_model.access import ConfigAccess


class TestFilterServiceFieldIntegration:
    """Test cases for FilterService field discovery integration."""

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

    def test_filter_service_has_field_discovery(self, filter_service):
        """Test that FilterService initializes with FieldDiscovery."""
        assert hasattr(filter_service, "field_discovery")
        assert filter_service.field_discovery is not None

    @patch("coregen.common.filter_service.FieldDiscovery")
    def test_validate_filter_fields_valid_fields(
        self, mock_field_discovery_class, filter_service
    ):
        """Test field validation with valid fields."""
        # Setup mock
        mock_field_discovery = mock_field_discovery_class.return_value
        mock_field_discovery.validate_field_exists.return_value = True
        filter_service.field_discovery = mock_field_discovery

        # Test with valid filters
        filters = [
            {"property": "name", "operator": "=", "value": "test"},
            {"property": "active", "operator": "=", "value": True},
        ]

        errors = filter_service.validate_filter_fields(filters, "context")

        # Should have no errors
        assert errors == []

        # Verify validation was called for each field
        assert mock_field_discovery.validate_field_exists.call_count == 2
        mock_field_discovery.validate_field_exists.assert_any_call("name", "context")
        mock_field_discovery.validate_field_exists.assert_any_call("active", "context")

    @patch("coregen.common.filter_service.FieldDiscovery")
    def test_validate_filter_fields_invalid_fields(
        self, mock_field_discovery_class, filter_service
    ):
        """Test field validation with invalid fields."""
        # Setup mock
        mock_field_discovery = mock_field_discovery_class.return_value
        mock_field_discovery.validate_field_exists.side_effect = (
            lambda field, entity: field != "invalid_field"
        )
        mock_field_discovery.get_field_suggestions.return_value = ["name", "active"]
        filter_service.field_discovery = mock_field_discovery

        # Test with invalid filter
        filters = [{"property": "invalid_field", "operator": "=", "value": "test"}]

        errors = filter_service.validate_filter_fields(filters, "context")

        # Should have error with suggestions
        assert len(errors) == 1
        assert "invalid_field" in errors[0]
        assert "Did you mean" in errors[0]
        assert "name, active" in errors[0]

    @patch("coregen.common.filter_service.FieldDiscovery")
    def test_validate_filter_fields_no_suggestions(
        self, mock_field_discovery_class, filter_service
    ):
        """Test field validation with invalid field but no suggestions."""
        # Setup mock
        mock_field_discovery = mock_field_discovery_class.return_value
        mock_field_discovery.validate_field_exists.return_value = False
        mock_field_discovery.get_field_suggestions.return_value = []
        filter_service.field_discovery = mock_field_discovery

        # Test with invalid filter
        filters = [{"property": "completely_invalid", "operator": "=", "value": "test"}]

        errors = filter_service.validate_filter_fields(filters, "context")

        # Should have error without suggestions
        assert len(errors) == 1
        assert "completely_invalid" in errors[0]
        assert "Did you mean" not in errors[0]

    @patch("coregen.common.filter_service.FieldDiscovery")
    def test_validate_filter_fields_mixed_validity(
        self, mock_field_discovery_class, filter_service
    ):
        """Test field validation with mix of valid and invalid fields."""
        # Setup mock
        mock_field_discovery = mock_field_discovery_class.return_value

        def mock_validate(field, entity):
            return field in ["name", "active"]

        mock_field_discovery.validate_field_exists.side_effect = mock_validate
        mock_field_discovery.get_field_suggestions.return_value = ["name", "active"]
        filter_service.field_discovery = mock_field_discovery

        # Test with mix of valid and invalid filters
        filters = [
            {"property": "name", "operator": "=", "value": "test"},  # Valid
            {"property": "invalid1", "operator": "=", "value": "test"},  # Invalid
            {"property": "active", "operator": "=", "value": True},  # Valid
            {"property": "invalid2", "operator": "=", "value": "test"},  # Invalid
        ]

        errors = filter_service.validate_filter_fields(filters, "context")

        # Should have errors only for invalid fields
        assert len(errors) == 2
        assert any("invalid1" in error for error in errors)
        assert any("invalid2" in error for error in errors)

    @patch("coregen.common.filter_service.FieldDiscovery")
    def test_validate_filter_fields_empty_property(
        self, mock_field_discovery_class, filter_service
    ):
        """Test field validation handles filters with empty property names."""
        # Setup mock
        mock_field_discovery = mock_field_discovery_class.return_value
        filter_service.field_discovery = mock_field_discovery

        # Test with filter missing property
        filters = [
            {"operator": "=", "value": "test"},  # No property
            {"property": "", "operator": "=", "value": "test"},  # Empty property
            {"property": None, "operator": "=", "value": "test"},  # None property
        ]

        errors = filter_service.validate_filter_fields(filters, "context")

        # Should have no errors (empty properties are skipped)
        assert errors == []

        # Validation should not be called for empty properties
        assert mock_field_discovery.validate_field_exists.call_count == 0

    @patch("coregen.common.filter_service.FieldDiscovery")
    def test_get_available_fields(self, mock_field_discovery_class, filter_service):
        """Test getting available fields for entity type."""
        # Setup mock
        mock_field_discovery = mock_field_discovery_class.return_value
        mock_field_discovery.discover_fields.return_value = {
            "name": Mock(),
            "active": Mock(),
            "environment": Mock(),
            "account_id": Mock(),
        }
        filter_service.field_discovery = mock_field_discovery

        # Get available fields
        fields = filter_service.get_available_fields("context")

        # Should return sorted field names
        assert fields == ["account_id", "active", "environment", "name"]
        mock_field_discovery.discover_fields.assert_called_once_with("context")

    def test_parse_filter_expression_unchanged(self, filter_service):
        """Test that parse_filter_expression behavior is unchanged."""
        # Test basic filter parsing still works
        filter_spec = filter_service.parse_filter_expression("name=test")

        assert filter_spec["property"] == "name"
        assert filter_spec["operator"] == "="
        assert filter_spec["value"] == "test"

        # Test boolean conversion still works
        filter_spec = filter_service.parse_filter_expression("active=true")

        assert filter_spec["property"] == "active"
        assert filter_spec["operator"] == "="
        assert filter_spec["value"] is True

    def test_apply_filters_unchanged(self, filter_service, mock_config_access):
        """Test that apply_filters behavior is unchanged."""
        # Setup test data
        elements = {
            "workspaces": {"ws1": {"name": "workspace1"}},
            "contexts": {"ctx1": {"name": "context1", "active": True}},
            "components": {"comp1": {"name": "component1"}},
        }

        filters = []  # No filters

        # Apply filters (should be unchanged)
        result = filter_service.apply_filters(elements, filters)

        # Should return elements unchanged when no filters
        assert result == elements
