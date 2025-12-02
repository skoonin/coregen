"""Unit tests for TypeFilterService.

This module tests the TypeFilterService which handles filtering of configuration
data by entity type (workspace, context, component) with hierarchical rules.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from coregen.common.logger import Logger
from coregen.common.type_filter_service import TypeFilterService


class TestTypeFilterService:
    """Test suite for TypeFilterService."""

    @pytest.fixture
    def service(self) -> TypeFilterService:
        """Create a TypeFilterService instance for testing.

        Returns:
            TypeFilterService: Fresh service instance with mocked logger
        """
        mock_logger = MagicMock(spec=Logger)
        return TypeFilterService(logger=mock_logger)

    @pytest.fixture
    def sample_data(self) -> dict[str, Any]:
        """Create sample data dictionary for filtering tests.

        Returns:
            dict: Sample data with workspaces, contexts, and components
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
                "component1": {"name": "component1"},
                "component2": {"name": "component2"},
            },
        }

    @pytest.fixture
    def flat_data(self) -> dict[str, Any]:
        """Create sample flat format data for filtering tests.

        Returns:
            dict: Sample data with lists as values (flat format)
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

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_init_with_logger(self):
        """Test TypeFilterService initialization with provided logger."""
        mock_logger = MagicMock(spec=Logger)
        service = TypeFilterService(logger=mock_logger)

        assert service.logger is mock_logger

    def test_init_without_logger(self):
        """Test TypeFilterService initialization creates default logger."""
        service = TypeFilterService()

        assert service.logger is not None
        assert hasattr(service.logger, "debug")

    # ========================================================================
    # get_included_types Tests
    # ========================================================================

    def test_get_included_types_workspace(self, service: TypeFilterService):
        """Test get_included_types returns all types for workspace."""
        result = service.get_included_types("workspace")

        assert result == ["workspaces", "contexts", "components"]

    def test_get_included_types_context(self, service: TypeFilterService):
        """Test get_included_types returns contexts and components."""
        result = service.get_included_types("context")

        assert result == ["contexts", "components"]

    def test_get_included_types_component(self, service: TypeFilterService):
        """Test get_included_types returns only components."""
        result = service.get_included_types("component")

        assert result == ["components"]

    def test_get_included_types_case_insensitive(self, service: TypeFilterService):
        """Test get_included_types handles uppercase input."""
        result = service.get_included_types("WORKSPACE")

        assert result == ["workspaces", "contexts", "components"]

    def test_get_included_types_unknown_type(self, service: TypeFilterService):
        """Test get_included_types defaults to workspace for unknown types."""
        result = service.get_included_types("unknown_type")

        assert result == ["workspaces", "contexts", "components"]
        service.logger.warning.assert_called_once()

    # ========================================================================
    # filter_by_type Tests
    # ========================================================================

    def test_filter_by_type_workspace(
        self, service: TypeFilterService, sample_data: dict[str, Any]
    ):
        """Test filter_by_type includes all entity types for workspace."""
        result = service.filter_by_type(sample_data, "workspace")

        assert "workspaces" in result
        assert "contexts" in result
        assert "components" in result
        assert len(result["workspaces"]) == 2
        assert len(result["contexts"]) == 2
        assert len(result["components"]) == 2

    def test_filter_by_type_context(
        self, service: TypeFilterService, sample_data: dict[str, Any]
    ):
        """Test filter_by_type includes contexts and components only."""
        result = service.filter_by_type(sample_data, "context")

        assert "workspaces" in result
        assert "contexts" in result
        assert "components" in result
        # Workspaces should be empty dict when filtering by context
        assert result["workspaces"] == {}
        assert len(result["contexts"]) == 2
        assert len(result["components"]) == 2

    def test_filter_by_type_component(
        self, service: TypeFilterService, sample_data: dict[str, Any]
    ):
        """Test filter_by_type includes only components."""
        result = service.filter_by_type(sample_data, "component")

        assert "workspaces" in result
        assert "contexts" in result
        assert "components" in result
        assert result["workspaces"] == {}
        assert result["contexts"] == {}
        assert len(result["components"]) == 2

    def test_filter_by_type_none_defaults_to_workspace(
        self, service: TypeFilterService, sample_data: dict[str, Any]
    ):
        """Test filter_by_type with None entity_type defaults to workspace."""
        result = service.filter_by_type(sample_data, None)

        assert len(result["workspaces"]) == 2
        assert len(result["contexts"]) == 2
        assert len(result["components"]) == 2

    def test_filter_by_type_empty_string_defaults_to_workspace(
        self, service: TypeFilterService, sample_data: dict[str, Any]
    ):
        """Test filter_by_type with empty string defaults to workspace."""
        result = service.filter_by_type(sample_data, "")

        assert len(result["workspaces"]) == 2
        assert len(result["contexts"]) == 2
        assert len(result["components"]) == 2

    # ========================================================================
    # apply_hierarchy_filter Tests
    # ========================================================================

    def test_apply_hierarchy_filter_preserves_structure(
        self, service: TypeFilterService, sample_data: dict[str, Any]
    ):
        """Test apply_hierarchy_filter maintains consistent structure."""
        included_types = ["contexts", "components"]
        result = service.apply_hierarchy_filter(sample_data, included_types)

        # All keys should be present
        assert "workspaces" in result
        assert "contexts" in result
        assert "components" in result

    def test_apply_hierarchy_filter_handles_list_format(
        self, service: TypeFilterService
    ):
        """Test apply_hierarchy_filter handles list format data."""
        data = {
            "workspaces": [],
            "contexts": [],
            "components": ["comp1", "comp2"],
        }
        included_types = ["components"]
        result = service.apply_hierarchy_filter(data, included_types)

        assert isinstance(result["workspaces"], list)
        assert isinstance(result["contexts"], list)
        assert isinstance(result["components"], list)
        assert len(result["components"]) == 2

    def test_apply_hierarchy_filter_missing_entity_types(
        self, service: TypeFilterService
    ):
        """Test apply_hierarchy_filter handles missing entity types."""
        data = {"workspaces": {"ws1": {}}}  # Missing contexts and components
        included_types = ["workspaces", "contexts", "components"]
        result = service.apply_hierarchy_filter(data, included_types)

        # Should create empty dicts for missing types
        assert "contexts" in result
        assert "components" in result
        assert result["contexts"] == {}
        assert result["components"] == {}

    # ========================================================================
    # get_entity_type_counts Tests
    # ========================================================================

    def test_get_entity_type_counts_with_dicts(
        self, service: TypeFilterService, sample_data: dict[str, Any]
    ):
        """Test get_entity_type_counts returns correct counts for dict format."""
        result = service.get_entity_type_counts(sample_data)

        assert result["workspaces"] == 2
        assert result["contexts"] == 2
        assert result["components"] == 2

    def test_get_entity_type_counts_with_lists(
        self, service: TypeFilterService, flat_data: dict[str, Any]
    ):
        """Test get_entity_type_counts returns correct counts for list format."""
        result = service.get_entity_type_counts(flat_data)

        assert result["workspaces"] == 2
        assert result["contexts"] == 2
        assert result["components"] == 2

    def test_get_entity_type_counts_empty_data(self, service: TypeFilterService):
        """Test get_entity_type_counts handles empty data."""
        result = service.get_entity_type_counts({})

        assert result["workspaces"] == 0
        assert result["contexts"] == 0
        assert result["components"] == 0

    def test_get_entity_type_counts_mixed_formats(self, service: TypeFilterService):
        """Test get_entity_type_counts handles mixed dict/list formats."""
        data = {
            "workspaces": {"ws1": {}, "ws2": {}},
            "contexts": ["ctx1", "ctx2", "ctx3"],
            "components": {},
        }
        result = service.get_entity_type_counts(data)

        assert result["workspaces"] == 2
        assert result["contexts"] == 3
        assert result["components"] == 0

    # ========================================================================
    # filter_exclusive Tests
    # ========================================================================

    def test_filter_exclusive_workspace_flat(
        self, service: TypeFilterService, flat_data: dict[str, Any]
    ):
        """Test filter_exclusive returns only workspaces for flat format."""
        result = service.filter_exclusive(flat_data, "workspace")

        assert "workspaces" in result
        assert "contexts" not in result
        assert "components" not in result
        assert len(result["workspaces"]) == 2

    def test_filter_exclusive_context_flat(
        self, service: TypeFilterService, flat_data: dict[str, Any]
    ):
        """Test filter_exclusive returns only contexts for flat format."""
        result = service.filter_exclusive(flat_data, "context")

        assert "contexts" in result
        assert "workspaces" not in result
        assert "components" not in result
        assert len(result["contexts"]) == 2

    def test_filter_exclusive_component_flat(
        self, service: TypeFilterService, flat_data: dict[str, Any]
    ):
        """Test filter_exclusive returns only components for flat format."""
        result = service.filter_exclusive(flat_data, "component")

        assert "components" in result
        assert "workspaces" not in result
        assert "contexts" not in result
        assert len(result["components"]) == 2

    def test_filter_exclusive_workspace_nested(
        self, service: TypeFilterService, sample_data: dict[str, Any]
    ):
        """Test filter_exclusive removes child data for workspace."""
        # Add nested contexts to workspace
        nested_data = {
            "workspaces": {
                "ws1": {
                    "name": "ws1",
                    "contexts": {
                        "cluster": {"ctx1": {"name": "ctx1"}},
                    },
                }
            }
        }
        result = service.filter_exclusive(nested_data, "workspace")

        assert "workspaces" in result
        assert "ws1" in result["workspaces"]
        # Contexts should be removed from workspace
        assert "contexts" not in result["workspaces"]["ws1"]

    def test_filter_exclusive_context_nested(self, service: TypeFilterService):
        """Test filter_exclusive extracts contexts from nested structure."""
        nested_data = {
            "workspaces": {
                "ws1": {
                    "name": "ws1",
                    "contexts": {
                        "cluster": {
                            "ctx1": {
                                "name": "ctx1",
                                "components": {"app": {"comp1": {}}},
                            }
                        },
                    },
                }
            }
        }
        result = service.filter_exclusive(nested_data, "context")

        assert "contexts" in result
        assert "ctx1" in result["contexts"]
        # Components should be removed from context
        assert "components" not in result["contexts"]["ctx1"]

    def test_filter_exclusive_component_nested(self, service: TypeFilterService):
        """Test filter_exclusive extracts components from nested structure."""
        nested_data = {
            "workspaces": {
                "ws1": {
                    "contexts": {
                        "cluster": {
                            "ctx1": {
                                "components": {
                                    "app": {"comp1": {"name": "comp1"}},
                                }
                            }
                        }
                    }
                }
            }
        }
        result = service.filter_exclusive(nested_data, "component")

        assert "components" in result
        # Component should be extracted with full path
        assert "ctx1/comp1" in result["components"]

    def test_filter_exclusive_unknown_type(
        self, service: TypeFilterService, flat_data: dict[str, Any]
    ):
        """Test filter_exclusive handles unknown entity type."""
        service.filter_exclusive(flat_data, "unknown")

        # Should log warning and return empty result
        service.logger.warning.assert_called()

    def test_filter_exclusive_context_removes_nested_data(
        self, service: TypeFilterService, flat_data: dict[str, Any]
    ):
        """Test filter_exclusive removes nested data from contexts."""
        # Add nested data to contexts
        data_with_nested = {
            "contexts": [
                {
                    "name": "ctx1",
                    "app": {"nested": "data"},
                    "component": {"nested": "data"},
                    "components": {"nested": "data"},
                }
            ]
        }
        result = service.filter_exclusive(data_with_nested, "context")

        assert "contexts" in result
        assert len(result["contexts"]) == 1
        # Nested keys should be removed
        assert "app" not in result["contexts"][0]
        assert "component" not in result["contexts"][0]
        assert "components" not in result["contexts"][0]

    # ========================================================================
    # _is_flat_structure Tests
    # ========================================================================

    def test_is_flat_structure_with_lists(
        self, service: TypeFilterService, flat_data: dict[str, Any]
    ):
        """Test _is_flat_structure detects flat format with lists."""
        result = service._is_flat_structure(flat_data)

        assert result is True

    def test_is_flat_structure_with_dicts(
        self, service: TypeFilterService, sample_data: dict[str, Any]
    ):
        """Test _is_flat_structure detects nested format with dicts."""
        result = service._is_flat_structure(sample_data)

        assert result is False

    def test_is_flat_structure_empty_data(self, service: TypeFilterService):
        """Test _is_flat_structure handles empty data."""
        result = service._is_flat_structure({})

        assert result is False

    # ========================================================================
    # _filter_orphaned_workspaces Tests
    # ========================================================================

    def test_filter_orphaned_workspaces_removes_empty(self, service: TypeFilterService):
        """Test _filter_orphaned_workspaces removes workspaces without contexts."""
        data = {
            "workspaces": {
                "ws1": {"name": "ws1"},
                "ws2": {"name": "ws2"},
            },
            "contexts": {
                "ctx1": {"name": "ctx1", "workspace": "ws1"},
            },
        }
        service._filter_orphaned_workspaces(data)

        # ws2 should be removed (no matching contexts)
        assert "ws1" in data["workspaces"]
        assert "ws2" not in data["workspaces"]

    def test_filter_orphaned_workspaces_preserves_with_contexts(
        self, service: TypeFilterService
    ):
        """Test _filter_orphaned_workspaces preserves workspaces with contexts."""
        data = {
            "workspaces": {
                "ws1": {"name": "ws1"},
            },
            "contexts": {
                "ctx1": {"name": "ctx1", "workspace": "ws1"},
                "ctx2": {"name": "ctx2", "workspace": "ws1"},
            },
        }
        service._filter_orphaned_workspaces(data)

        # ws1 should be preserved (has contexts)
        assert "ws1" in data["workspaces"]

    def test_filter_orphaned_workspaces_handles_non_dict(
        self, service: TypeFilterService
    ):
        """Test _filter_orphaned_workspaces handles non-dict workspaces."""
        data = {
            "workspaces": [],
            "contexts": {"ctx1": {"name": "ctx1", "workspace": "ws1"}},
        }
        # Should not raise error
        service._filter_orphaned_workspaces(data)

    def test_filter_orphaned_workspaces_handles_missing_contexts(
        self, service: TypeFilterService
    ):
        """Test _filter_orphaned_workspaces handles missing contexts key."""
        data = {
            "workspaces": {"ws1": {"name": "ws1"}},
        }
        service._filter_orphaned_workspaces(data)

        # All workspaces should be removed (no contexts)
        assert len(data["workspaces"]) == 0

    # ========================================================================
    # Additional Coverage Tests for Nested Structures
    # ========================================================================

    def test_filter_exclusive_context_with_model_objects(
        self, service: TypeFilterService
    ):
        """Test filter_exclusive handles model objects with model_dump."""
        # Create mock object with model_dump method
        mock_context = MagicMock()
        mock_context.model_dump.return_value = {
            "name": "ctx1",
            "components": {"app": {"comp1": {}}},
            "app": {"nested": "data"},
            "component": {"single": "data"},
        }

        nested_data = {
            "workspaces": {
                "ws1": {
                    "contexts": {
                        "cluster": {"ctx1": mock_context},
                    }
                }
            }
        }
        result = service.filter_exclusive(nested_data, "context")

        assert "contexts" in result
        # model_dump should have been called
        mock_context.model_dump.assert_called()

    def test_filter_exclusive_workspace_with_model_objects(
        self, service: TypeFilterService
    ):
        """Test filter_exclusive handles workspace model objects."""
        # Create mock workspace with model_dump
        mock_workspace = MagicMock()
        mock_workspace.model_dump.return_value = {
            "name": "ws1",
            "contexts": {"cluster": {"ctx1": {}}},
        }

        nested_data = {"workspaces": {"ws1": mock_workspace}}
        result = service.filter_exclusive(nested_data, "workspace")

        assert "workspaces" in result
        mock_workspace.model_dump.assert_called()
        # Contexts should be removed
        assert "contexts" not in result["workspaces"]["ws1"]

    def test_filter_exclusive_component_from_root_contexts(
        self, service: TypeFilterService
    ):
        """Test filter_exclusive extracts components from root-level contexts."""
        nested_data = {
            "contexts": {
                "ctx1": {
                    "components": {
                        "app": {
                            "comp1": {"name": "comp1"},
                            "comp2": {"name": "comp2"},
                        }
                    }
                }
            }
        }
        result = service.filter_exclusive(nested_data, "component")

        assert "components" in result
        assert "ctx1/comp1" in result["components"]
        assert "ctx1/comp2" in result["components"]

    def test_filter_exclusive_component_from_root_components(
        self, service: TypeFilterService
    ):
        """Test filter_exclusive handles root-level components."""
        nested_data = {
            "components": {
                "comp1": {"name": "comp1"},
                "comp2": {"name": "comp2"},
            }
        }
        result = service.filter_exclusive(nested_data, "component")

        assert "components" in result
        assert result["components"] == nested_data["components"]

    def test_filter_exclusive_context_from_root_contexts(
        self, service: TypeFilterService
    ):
        """Test filter_exclusive extracts contexts from root-level."""
        nested_data = {
            "contexts": {
                "ctx1": {
                    "name": "ctx1",
                    "components": {"app": {"comp1": {}}},
                },
                "ctx2": {
                    "name": "ctx2",
                    "app": {"data": "value"},
                },
            }
        }
        result = service.filter_exclusive(nested_data, "context")

        assert "contexts" in result
        assert "ctx1" in result["contexts"]
        assert "ctx2" in result["contexts"]
        # Components and app should be removed
        assert "components" not in result["contexts"]["ctx1"]
        assert "app" not in result["contexts"]["ctx2"]

    def test_filter_flat_structure_context_with_model_dump(
        self, service: TypeFilterService
    ):
        """Test _filter_flat_structure handles context models with model_dump."""
        # Create mock context with model_dump
        mock_context = MagicMock()
        mock_context.model_dump.return_value = {
            "name": "ctx1",
            "app": {"nested": "data"},
            "component": {"single": "data"},
            "components": {"multiple": "data"},
        }

        data = {"contexts": [mock_context]}
        result = service.filter_exclusive(data, "context")

        assert "contexts" in result
        mock_context.model_dump.assert_called()
        # Nested data should be removed
        assert "app" not in result["contexts"][0]
        assert "component" not in result["contexts"][0]
        assert "components" not in result["contexts"][0]

    def test_filter_flat_structure_context_non_dict_passthrough(
        self, service: TypeFilterService
    ):
        """Test _filter_flat_structure handles non-dict/non-model contexts."""
        # String or other non-dict object (edge case)
        data = {"contexts": ["string_context", 123]}
        result = service.filter_exclusive(data, "context")

        assert "contexts" in result
        # Non-dict items should pass through
        assert "string_context" in result["contexts"]
        assert 123 in result["contexts"]

    def test_filter_nested_structure_workspace_non_dict_entity(
        self, service: TypeFilterService
    ):
        """Test _filter_nested_structure handles non-dict workspace entities."""
        data = {"workspaces": {"ws1": "string_value"}}
        result = service.filter_exclusive(data, "workspace")

        assert "workspaces" in result
        assert result["workspaces"]["ws1"] == "string_value"

    def test_filter_nested_structure_context_non_dict_entity(
        self, service: TypeFilterService
    ):
        """Test _filter_nested_structure handles non-dict context entities."""
        nested_data = {
            "workspaces": {
                "ws1": {
                    "contexts": {
                        "cluster": {"ctx1": "string_context"},
                    }
                }
            }
        }
        result = service.filter_exclusive(nested_data, "context")

        assert "contexts" in result
        assert result["contexts"]["ctx1"] == "string_context"

    def test_filter_nested_structure_workspace_non_dict_value(
        self, service: TypeFilterService
    ):
        """Test _filter_nested_structure handles non-dict top-level values."""
        data = {"workspaces": "not_a_dict"}
        result = service.filter_exclusive(data, "workspace")

        assert result["workspaces"] == "not_a_dict"

    def test_filter_nested_structure_context_with_model_at_root(
        self, service: TypeFilterService
    ):
        """Test _filter_nested_structure handles model objects at root contexts."""
        mock_context = MagicMock()
        mock_context.model_dump.return_value = {
            "name": "ctx1",
            "components": {"app": {"comp1": {}}},
        }

        data = {"contexts": {"ctx1": mock_context}}
        result = service.filter_exclusive(data, "context")

        assert "contexts" in result
        mock_context.model_dump.assert_called()
        # Components should be removed
        assert "components" not in result["contexts"]["ctx1"]
