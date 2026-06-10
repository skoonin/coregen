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
