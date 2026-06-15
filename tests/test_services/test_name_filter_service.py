"""Unit tests for NameFilterService.

This module tests the NameFilterService which handles filtering and extracting
entity names from configuration data, with support for deduplication and
format detection.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from coregen.common.logger import Logger
from coregen.common.name_filter_service import NameFilterService


class TestNameFilterService:
    """Test suite for NameFilterService."""

    @pytest.fixture
    def service(self) -> NameFilterService:
        """Create a NameFilterService instance for testing.

        Returns:
            NameFilterService: Fresh service instance with mocked logger
        """
        mock_logger = MagicMock(spec=Logger)
        return NameFilterService(logger=mock_logger)

    @pytest.fixture
    def nested_data(self) -> dict[str, Any]:
        """Create sample nested format data.

        Returns:
            dict: Sample data with nested dict structure
        """
        return {
            "workspaces": {
                "workspace1": {"name": "workspace1", "type": "kubernetes"},
                "workspace2": {"name": "workspace2", "type": "aws"},
            },
            "contexts": {
                "context1": {"name": "context1", "workspace": "workspace1"},
                "context2": {"name": "context2", "workspace": "workspace2"},
            },
            "components": {
                "context1/component1": {"name": "component1"},
                "context2/component2": {"name": "component2"},
            },
        }

    @pytest.fixture
    def flat_data(self) -> dict[str, Any]:
        """Create sample flat format data.

        Returns:
            dict: Sample data with flat list structure
        """
        return {
            "workspaces": [
                {"name": "workspace1", "type": "kubernetes"},
                {"name": "workspace2", "type": "aws"},
            ],
            "contexts": [
                {"name": "context1", "workspace": "workspace1"},
                {"name": "context2", "workspace": "workspace2"},
            ],
            "components": [
                {"name": "component1"},
                {"name": "component2"},
            ],
        }

    @pytest.fixture
    def name_only_data(self) -> dict[str, Any]:
        """Create sample name-only format data.

        Returns:
            dict: Sample data with arrays of name strings
        """
        return {
            "workspaces": ["workspace1", "workspace2"],
            "contexts": ["context1", "context2"],
            "components": ["component1", "component2"],
        }

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_init_with_logger(self):
        """Test NameFilterService initialization with provided logger."""
        mock_logger = MagicMock(spec=Logger)
        service = NameFilterService(logger=mock_logger)

        assert service.logger is mock_logger

    def test_init_without_logger(self):
        """Test NameFilterService initialization creates default logger."""
        service = NameFilterService()

        assert service.logger is not None
        assert hasattr(service.logger, "debug")

    # ========================================================================
    # filter_names_only Tests
    # ========================================================================

    def test_filter_names_only_nested_format(
        self, service: NameFilterService, nested_data: dict[str, Any]
    ):
        """Test filter_names_only extracts names from nested dict format."""
        result = service.filter_names_only(nested_data)

        assert isinstance(result["workspaces"], list)
        assert isinstance(result["contexts"], list)
        assert isinstance(result["components"], list)
        assert result["workspaces"] == ["workspace1", "workspace2"]
        assert result["contexts"] == ["context1", "context2"]
        assert result["components"] == ["component1", "component2"]

    def test_filter_names_only_flat_format(
        self, service: NameFilterService, flat_data: dict[str, Any]
    ):
        """Test filter_names_only extracts names from flat list format."""
        result = service.filter_names_only(flat_data)

        assert result["workspaces"] == ["workspace1", "workspace2"]
        assert result["contexts"] == ["context1", "context2"]
        assert result["components"] == ["component1", "component2"]

    def test_filter_names_only_deduplicates_components(
        self, service: NameFilterService
    ):
        """Test filter_names_only deduplicates component names across contexts."""
        data = {
            "components": {
                "context1/component1": {"name": "component1"},
                "context2/component1": {"name": "component1"},  # Duplicate name
                "context1/component2": {"name": "component2"},
            }
        }
        result = service.filter_names_only(data)

        # Should have only 2 unique component names
        assert len(result["components"]) == 2
        assert "component1" in result["components"]
        assert "component2" in result["components"]

    def test_filter_names_only_handles_empty_data(self, service: NameFilterService):
        """Test filter_names_only handles empty data gracefully."""
        result = service.filter_names_only({})

        assert result["workspaces"] == []
        assert result["contexts"] == []
        assert result["components"] == []

    def test_filter_names_only_handles_string_components(
        self, service: NameFilterService
    ):
        """Test filter_names_only handles string component keys in list format."""
        data = {
            "components": [
                "context1/component1",
                "context2/component2",
                "context1/component3",
            ]
        }
        result = service.filter_names_only(data)

        # Should extract component names from "context/component" format
        assert len(result["components"]) == 3
        assert "component1" in result["components"]
        assert "component2" in result["components"]
        assert "component3" in result["components"]

    def test_filter_names_only_already_name_format(
        self, service: NameFilterService, name_only_data: dict[str, Any]
    ):
        """Test filter_names_only handles data already in name-only format."""
        result = service.filter_names_only(name_only_data)

        # Should return sorted arrays (same content, possibly reordered)
        assert set(result["workspaces"]) == set(name_only_data["workspaces"])
        assert set(result["contexts"]) == set(name_only_data["contexts"])
        assert set(result["components"]) == set(name_only_data["components"])

    # ========================================================================
    # is_name_only_format Tests
    # ========================================================================

    def test_is_name_only_format_true(
        self, service: NameFilterService, name_only_data: dict[str, Any]
    ):
        """Test is_name_only_format returns True for name-only data."""
        result = service.is_name_only_format(name_only_data)

        assert result is True

    def test_is_name_only_format_false_nested(
        self, service: NameFilterService, nested_data: dict[str, Any]
    ):
        """Test is_name_only_format returns False for nested dict format."""
        result = service.is_name_only_format(nested_data)

        assert result is False

    def test_is_name_only_format_false_flat(
        self, service: NameFilterService, flat_data: dict[str, Any]
    ):
        """Test is_name_only_format returns False for flat format with dicts."""
        result = service.is_name_only_format(flat_data)

        assert result is False

    def test_is_name_only_format_partial_match(self, service: NameFilterService):
        """Test is_name_only_format handles partial name-only data."""
        data = {
            "workspaces": ["ws1", "ws2"],  # Name-only
            "contexts": [{"name": "ctx1"}],  # Not name-only
            "components": ["comp1"],
        }
        result = service.is_name_only_format(data)

        # Should return False if any entity type is not name-only
        assert result is False

    # ========================================================================
    # _extract_component_name Tests
    # ========================================================================

    def test_extract_component_name_with_context(self, service: NameFilterService):
        """Test _extract_component_name extracts from 'context/component' format."""
        result = service._extract_component_name("context1/component1")

        assert result == "component1"

    def test_extract_component_name_without_context(self, service: NameFilterService):
        """Test _extract_component_name handles plain component name."""
        result = service._extract_component_name("component1")

        assert result == "component1"

    def test_extract_component_name_multiple_slashes(self, service: NameFilterService):
        """Test _extract_component_name handles multiple slashes correctly."""
        result = service._extract_component_name("workspace/context/component")

        # Should split on first slash and return everything after
        assert result == "context/component"

    # ========================================================================
    # transform_for_output Tests
    # ========================================================================

    def test_transform_for_output_workspace_type(
        self, service: NameFilterService, name_only_data: dict[str, Any]
    ):
        """Test transform_for_output returns workspaces array for workspace type."""
        result = service.transform_for_output(name_only_data, entity_type="workspace")

        assert isinstance(result, list)
        assert result == name_only_data["workspaces"]

    def test_transform_for_output_context_type(
        self, service: NameFilterService, name_only_data: dict[str, Any]
    ):
        """Test transform_for_output returns contexts array for context type."""
        result = service.transform_for_output(name_only_data, entity_type="context")

        assert isinstance(result, list)
        assert result == name_only_data["contexts"]

    def test_transform_for_output_component_type(
        self, service: NameFilterService, name_only_data: dict[str, Any]
    ):
        """Test transform_for_output returns components array for component type."""
        result = service.transform_for_output(name_only_data, entity_type="component")

        assert isinstance(result, list)
        assert result == name_only_data["components"]

    def test_transform_for_output_from_patterns_workspace(
        self, service: NameFilterService, name_only_data: dict[str, Any]
    ):
        """Test transform_for_output infers workspace from patterns."""
        patterns = ["w/workspace1", "workspace/workspace2"]
        result = service.transform_for_output(name_only_data, patterns=patterns)

        assert isinstance(result, list)
        assert result == name_only_data["workspaces"]

    def test_transform_for_output_from_patterns_context(
        self, service: NameFilterService, name_only_data: dict[str, Any]
    ):
        """Test transform_for_output infers context from patterns."""
        patterns = ["c/context1", "context/context2"]
        result = service.transform_for_output(name_only_data, patterns=patterns)

        assert isinstance(result, list)
        assert result == name_only_data["contexts"]

    def test_transform_for_output_from_patterns_component(
        self, service: NameFilterService, name_only_data: dict[str, Any]
    ):
        """Test transform_for_output infers component from patterns."""
        patterns = ["cm/component1", "component/component2"]
        result = service.transform_for_output(name_only_data, patterns=patterns)

        assert isinstance(result, list)
        assert result == name_only_data["components"]

    def test_transform_for_output_not_name_only_format(
        self, service: NameFilterService, nested_data: dict[str, Any]
    ):
        """Test transform_for_output returns data as-is if not name-only format."""
        result = service.transform_for_output(nested_data, entity_type="workspace")

        # Should return the original dict since it's not name-only format
        assert result == nested_data

    def test_transform_for_output_type_all(
        self, service: NameFilterService, name_only_data: dict[str, Any]
    ):
        """Test transform_for_output with entity_type='all' returns primary type."""
        result = service.transform_for_output(name_only_data, entity_type="all")

        # Should return the type with most items, or full dict
        # In this case, all have 2 items, so it should pick one or return dict
        assert isinstance(result, (list, dict))

    def test_transform_for_output_no_entity_type_or_patterns(
        self, service: NameFilterService, name_only_data: dict[str, Any]
    ):
        """Test transform_for_output without entity_type or patterns."""
        result = service.transform_for_output(name_only_data)

        # Should analyze data and return primary type or full dict
        assert isinstance(result, (list, dict))

    def test_transform_for_output_selects_type_with_most_items(
        self, service: NameFilterService
    ):
        """Test transform_for_output selects entity type with most items."""
        data = {
            "workspaces": ["ws1"],
            "contexts": ["ctx1", "ctx2"],
            "components": ["comp1", "comp2", "comp3"],
        }
        result = service.transform_for_output(data)

        # Should return components (has 3 items, most of all)
        assert isinstance(result, list)
        assert result == data["components"]
