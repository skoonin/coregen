"""Unit tests for InactiveFilterService.

This module tests the InactiveFilterService which handles filtering of configuration
data based on active/inactive status, with support for hierarchical filtering and
parent-child awareness.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from coregen.common.inactive_filter_service import InactiveFilterService
from coregen.common.logger import Logger


class TestInactiveFilterService:
    """Test suite for InactiveFilterService."""

    @pytest.fixture
    def service(self) -> InactiveFilterService:
        """Create an InactiveFilterService instance for testing.

        Returns:
            InactiveFilterService: Fresh service instance with mocked logger
        """
        mock_logger = MagicMock(spec=Logger)
        return InactiveFilterService(logger=mock_logger)

    @pytest.fixture
    def sample_data_dict(self) -> dict[str, Any]:
        """Create sample dict-format data with active/inactive items.

        Returns:
            dict: Sample data with workspaces, contexts, and components
        """
        return {
            "workspaces": {
                "ws1": {"name": "ws1", "active": True},
                "ws2": {"name": "ws2", "active": False},
            },
            "contexts": {
                "ctx1": {"name": "ctx1", "active": True},
                "ctx2": {"name": "ctx2", "active": False},
            },
            "components": {
                "comp1": {"name": "comp1", "active": True},
                "comp2": {"name": "comp2", "active": False},
            },
        }

    @pytest.fixture
    def sample_data_list(self) -> dict[str, Any]:
        """Create sample list-format data with active/inactive items.

        Returns:
            dict: Sample data with lists as values (flat format)
        """
        return {
            "workspaces": [
                {"name": "ws1", "active": True},
                {"name": "ws2", "active": False},
            ],
            "contexts": [
                {"name": "ctx1", "active": True},
                {"name": "ctx2", "active": False},
            ],
            "components": [
                {"name": "comp1", "active": True},
                {"name": "comp2", "active": False},
            ],
        }

    @pytest.fixture
    def nested_config_data(self) -> dict[str, Any]:
        """Create sample data with active field in config object.

        Returns:
            dict: Sample data with config.active pattern
        """
        return {
            "components": {
                "comp1": {
                    "name": "comp1",
                    "config": {"active": True, "path": "/path1"},
                },
                "comp2": {
                    "name": "comp2",
                    "config": {"active": False, "path": "/path2"},
                },
            }
        }

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_init_with_logger(self):
        """Test InactiveFilterService initialization with provided logger."""
        mock_logger = MagicMock(spec=Logger)
        service = InactiveFilterService(logger=mock_logger)

        assert service.logger is mock_logger

    def test_init_without_logger(self):
        """Test InactiveFilterService initialization creates default logger."""
        service = InactiveFilterService()

        assert service.logger is not None
        assert hasattr(service.logger, "debug")

    # ========================================================================
    # filter_inactive Tests - Basic Functionality
    # ========================================================================

    def test_filter_inactive_excludes_inactive_items_dict_format(
        self, service: InactiveFilterService, sample_data_dict: dict[str, Any]
    ):
        """Test filter_inactive excludes items with active=false in dict format."""
        result = service.filter_inactive(sample_data_dict, include_inactive=False)

        # Active items should be present
        assert "ws1" in result["workspaces"]
        assert "ctx1" in result["contexts"]
        assert "comp1" in result["components"]

        # Inactive items should be filtered out
        assert "ws2" not in result["workspaces"]
        assert "ctx2" not in result["contexts"]
        assert "comp2" not in result["components"]

    def test_filter_inactive_excludes_inactive_items_list_format(
        self, service: InactiveFilterService, sample_data_list: dict[str, Any]
    ):
        """Test filter_inactive excludes items with active=false in list format."""
        result = service.filter_inactive(sample_data_list, include_inactive=False)

        # Should have only 1 active item per entity type
        assert len(result["workspaces"]) == 1
        assert len(result["contexts"]) == 1
        assert len(result["components"]) == 1

        # Verify the active items are present
        assert result["workspaces"][0]["name"] == "ws1"
        assert result["contexts"][0]["name"] == "ctx1"
        assert result["components"][0]["name"] == "comp1"

    def test_filter_inactive_includes_all_when_flag_true(
        self, service: InactiveFilterService, sample_data_dict: dict[str, Any]
    ):
        """Test filter_inactive returns all items when include_inactive=True."""
        result = service.filter_inactive(sample_data_dict, include_inactive=True)

        # All items should be present (both active and inactive)
        assert "ws1" in result["workspaces"]
        assert "ws2" in result["workspaces"]
        assert "ctx1" in result["contexts"]
        assert "ctx2" in result["contexts"]
        assert "comp1" in result["components"]
        assert "comp2" in result["components"]

    def test_filter_inactive_handles_empty_data(self, service: InactiveFilterService):
        """Test filter_inactive handles empty data gracefully."""
        empty_data = {}
        result = service.filter_inactive(empty_data, include_inactive=False)

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_filter_inactive_handles_missing_active_field(
        self, service: InactiveFilterService
    ):
        """Test filter_inactive treats missing active field as active=True."""
        data = {
            "components": {
                "comp1": {"name": "comp1"},  # No active field
                "comp2": {"name": "comp2", "active": False},
            }
        }
        result = service.filter_inactive(data, include_inactive=False)

        # comp1 should be included (defaults to active)
        assert "comp1" in result["components"]
        # comp2 should be excluded (active=false)
        assert "comp2" not in result["components"]

    def test_filter_inactive_handles_config_active_field(
        self, service: InactiveFilterService, nested_config_data: dict[str, Any]
    ):
        """Test filter_inactive handles active field in config object."""
        result = service.filter_inactive(nested_config_data, include_inactive=False)

        # comp1 should be present (config.active=true)
        assert "comp1" in result["components"]
        # comp2 should be filtered (config.active=false)
        assert "comp2" not in result["components"]

    # ========================================================================
    # filter_complete_model Tests - Parent-Child Awareness
    # ========================================================================

    def test_filter_complete_model_filters_inactive_contexts(
        self, service: InactiveFilterService
    ):
        """Test filter_complete_model filters out inactive contexts."""
        # Create mock objects with active attribute
        mock_ctx1 = MagicMock()
        mock_ctx1.active = True
        mock_ctx1.name = "ctx1"

        mock_ctx2 = MagicMock()
        mock_ctx2.active = False
        mock_ctx2.name = "ctx2"

        complete_model = {
            "workspaces": {"ws1": {"name": "ws1"}},
            "contexts": {"ctx1": mock_ctx1, "ctx2": mock_ctx2},
            "components": {},
        }

        result = service.filter_complete_model(complete_model, include_inactive=False)

        # Active context should be present
        assert "ctx1" in result["contexts"]
        # Inactive context should be filtered
        assert "ctx2" not in result["contexts"]

    def test_filter_complete_model_filters_components_of_inactive_context(
        self, service: InactiveFilterService
    ):
        """Test filter_complete_model filters components when parent context is inactive."""
        # Create mock context objects
        mock_ctx1 = MagicMock()
        mock_ctx1.active = True

        mock_ctx2 = MagicMock()
        mock_ctx2.active = False

        # Create mock components
        mock_comp1 = MagicMock()
        mock_comp1.config.active = True

        mock_comp2 = MagicMock()
        mock_comp2.config.active = True

        complete_model = {
            "workspaces": {"ws1": {}},
            "contexts": {"ctx1": mock_ctx1, "ctx2": mock_ctx2},
            "components": {
                "ctx1/comp1": mock_comp1,  # Active context, active component
                "ctx2/comp2": mock_comp2,  # Inactive context, active component
            },
        }

        result = service.filter_complete_model(complete_model, include_inactive=False)

        # Component from active context should be present
        assert "ctx1/comp1" in result["components"]
        # Component from inactive context should be filtered
        assert "ctx2/comp2" not in result["components"]

    def test_filter_complete_model_includes_all_when_flag_true(
        self, service: InactiveFilterService
    ):
        """Test filter_complete_model returns all items when include_inactive=True."""
        mock_ctx = MagicMock()
        mock_ctx.active = False

        complete_model = {
            "workspaces": {"ws1": {}},
            "contexts": {"ctx1": mock_ctx},
            "components": {},
        }

        result = service.filter_complete_model(complete_model, include_inactive=True)

        # Should return unchanged data
        assert result == complete_model

    # ========================================================================
    # _has_active_false Tests - Helper Method
    # ========================================================================

    def test_has_active_false_with_dict_active_true(
        self, service: InactiveFilterService
    ):
        """Test _has_active_false returns False for dict with active=True."""
        data = {"name": "test", "active": True}
        result = service._has_active_false(data)

        assert result is False

    def test_has_active_false_with_dict_active_false(
        self, service: InactiveFilterService
    ):
        """Test _has_active_false returns True for dict with active=False."""
        data = {"name": "test", "active": False}
        result = service._has_active_false(data)

        assert result is True

    def test_has_active_false_with_model_object(self, service: InactiveFilterService):
        """Test _has_active_false works with model objects (config.active)."""
        mock_obj = MagicMock()
        mock_obj.config.active = False

        result = service._has_active_false(mock_obj)

        assert result is True

    def test_has_active_false_with_config_active(self, service: InactiveFilterService):
        """Test _has_active_false checks config.active field."""
        data = {"name": "test", "config": {"active": False}}
        result = service._has_active_false(data)

        assert result is True

    def test_has_active_false_missing_active_field(
        self, service: InactiveFilterService
    ):
        """Test _has_active_false returns False when active field is missing."""
        data = {"name": "test"}
        result = service._has_active_false(data)

        assert result is False

    # ========================================================================
    # _has_content Tests - Helper Method
    # ========================================================================

    def test_has_content_with_non_empty_dict(self, service: InactiveFilterService):
        """Test _has_content returns True for non-empty dict."""
        data = {"key": "value"}
        result = service._has_content(data)

        assert result is True

    def test_has_content_with_empty_dict(self, service: InactiveFilterService):
        """Test _has_content returns False for empty dict."""
        data = {}
        result = service._has_content(data)

        assert result is False

    def test_has_content_with_non_empty_list(self, service: InactiveFilterService):
        """Test _has_content returns True for non-empty list."""
        data = ["item1", "item2"]
        result = service._has_content(data)

        assert result is True

    def test_has_content_with_empty_list(self, service: InactiveFilterService):
        """Test _has_content returns False for empty list."""
        data = []
        result = service._has_content(data)

        assert result is False

    def test_has_content_with_none(self, service: InactiveFilterService):
        """Test _has_content returns False for None."""
        result = service._has_content(None)

        assert result is False

    def test_has_content_with_string(self, service: InactiveFilterService):
        """Test _has_content returns True for non-None string."""
        result = service._has_content("test")

        assert result is True

    # ========================================================================
    # _get_name Tests - Helper Method
    # ========================================================================

    def test_get_name_from_dict(self, service: InactiveFilterService):
        """Test _get_name extracts name from dict."""
        data = {"name": "test-item"}
        result = service._get_name(data)

        assert result == "test-item"

    def test_get_name_from_model_object(self, service: InactiveFilterService):
        """Test _get_name extracts name from model object."""
        mock_obj = MagicMock()
        mock_obj.name = "test-object"

        result = service._get_name(mock_obj)

        assert result == "test-object"

    def test_get_name_returns_unknown_when_missing(
        self, service: InactiveFilterService
    ):
        """Test _get_name returns 'unknown' when name field is missing."""
        data = {"other_field": "value"}
        result = service._get_name(data)

        assert result == "unknown"

    # ========================================================================
    # Edge Cases and Complex Scenarios
    # ========================================================================

    def test_filter_inactive_recursive_filtering_nested_dict(
        self, service: InactiveFilterService
    ):
        """Test filter_inactive recursively filters nested structures."""
        data = {
            "workspaces": {
                "ws1": {
                    "name": "ws1",
                    "nested": {
                        "item1": {"active": True, "value": "a"},
                        "item2": {"active": False, "value": "b"},
                    },
                }
            }
        }
        result = service.filter_inactive(data, include_inactive=False)

        # ws1 should be present
        assert "ws1" in result["workspaces"]
        # Nested item1 should be present
        assert "item1" in result["workspaces"]["ws1"]["nested"]
        # Nested item2 should be filtered
        assert "item2" not in result["workspaces"]["ws1"]["nested"]

    def test_filter_inactive_handles_model_objects(
        self, service: InactiveFilterService
    ):
        """Test filter_inactive preserves model objects when active."""
        mock_obj = MagicMock()
        mock_obj.model_dump = MagicMock(return_value={"name": "test", "active": True})
        # Configure the mock to not have active=false
        type(mock_obj).active = MagicMock(return_value=True)

        data = {"components": {"comp1": mock_obj}}

        result = service.filter_inactive(data, include_inactive=False)

        # Model object should be preserved (not converted to dict)
        assert "comp1" in result["components"]
        # Should be the same object reference
        assert result["components"]["comp1"] is mock_obj

    def test_filter_inactive_filters_model_objects_when_inactive(
        self, service: InactiveFilterService
    ):
        """Test filter_inactive filters out inactive model objects.

        When all items in a collection are inactive, the collection itself
        may be removed from the result.
        """
        mock_obj = MagicMock()
        # Model objects check config.active first
        mock_obj.config.active = False
        mock_obj.name = "inactive-obj"

        data = {"components": {"comp1": mock_obj}}

        result = service.filter_inactive(data, include_inactive=False)

        # If components key exists, comp1 should not be in it
        # If all components were filtered, the key might be removed entirely
        if "components" in result:
            assert "comp1" not in result["components"]
        else:
            # All components were filtered, so the key was removed (acceptable)
            assert "components" not in result

    def test_filter_complete_model_filters_component_with_inactive_flag(
        self, service: InactiveFilterService
    ):
        """Test filter_complete_model filters components with active=False."""
        mock_ctx = MagicMock()
        mock_ctx.active = True

        mock_comp = MagicMock()
        mock_comp.config.active = False

        complete_model = {
            "workspaces": {},
            "contexts": {"ctx1": mock_ctx},
            "components": {"ctx1/comp1": mock_comp},
        }

        result = service.filter_complete_model(complete_model, include_inactive=False)

        # Component should be filtered (component.config.active=False)
        assert "ctx1/comp1" not in result["components"]

    def test_filter_complete_model_defaults_missing_active_to_true(
        self, service: InactiveFilterService
    ):
        """Test filter_complete_model treats missing active attribute as True."""
        mock_ctx = MagicMock(spec=[])  # No active attribute
        mock_ctx.name = "ctx1"

        complete_model = {
            "workspaces": {},
            "contexts": {"ctx1": mock_ctx},
            "components": {},
        }

        result = service.filter_complete_model(complete_model, include_inactive=False)

        # Context without active field should be included (defaults to active)
        assert "ctx1" in result["contexts"]

    def test_filter_inactive_returns_dict_for_invalid_input(
        self, service: InactiveFilterService
    ):
        """Test filter_inactive returns empty dict for invalid input."""
        # Test with non-dict input after filtering
        # This shouldn't happen in practice but ensures robustness
        result = service.filter_inactive({"test": "value"}, include_inactive=False)

        assert isinstance(result, dict)

    def test_filter_inactive_handles_boolean_and_numeric_active_values(
        self, service: InactiveFilterService
    ):
        """Test filter_inactive handles boolean and numeric active values.

        Note: bool() is used, so truthy/falsy evaluation applies:
        - 0, False, None, "", [] are falsy
        - Non-zero numbers, True, non-empty strings are truthy
        """
        data = {
            "items": {
                "item1": {"active": True},  # Boolean True
                "item2": {"active": False},  # Boolean False
                "item3": {"active": 0},  # Falsy number
                "item4": {"active": 1},  # Truthy number
                "item5": {"active": None},  # None is falsy
            }
        }
        result = service.filter_inactive(data, include_inactive=False)

        # item1 and item4 should be present (truthy values)
        assert "item1" in result["items"]
        assert "item4" in result["items"]
        # item2, item3, and item5 should be filtered (falsy values)
        assert "item2" not in result["items"]
        assert "item3" not in result["items"]
        assert "item5" not in result["items"]
