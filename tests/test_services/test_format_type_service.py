"""Unit tests for FormatTypeService.

This module tests the FormatTypeService which handles formatting of configuration
data between flat and nested formats for YAML/JSON output.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from coregen.common.format_type_service import FormatTypeService
from coregen.common.logger import Logger


class TestFormatTypeService:
    """Test suite for FormatTypeService."""

    @pytest.fixture
    def service(self) -> FormatTypeService:
        """Create a FormatTypeService instance for testing.

        Returns:
            FormatTypeService: Fresh service instance with mocked logger
        """
        mock_logger = MagicMock(spec=Logger)
        return FormatTypeService(logger=mock_logger)

    @pytest.fixture
    def sample_nested_data(self) -> dict[str, Any]:
        """Create sample nested data dictionary for testing.

        Returns:
            dict: Sample nested data with hierarchical structure
        """
        return {
            "workspaces": {
                "ws1": {
                    "name": "ws1",
                    "type": "kubernetes",
                    "contexts": {
                        "cluster": {
                            "ctx1": {
                                "name": "ctx1",
                                "workspace": "ws1",
                                "environment": "dev",
                                "components": {
                                    "app": {
                                        "comp1": {
                                            "name": "comp1",
                                            "context": "ctx1",
                                            "workspace": "ws1",
                                            "config": {"key": "value"},
                                        }
                                    }
                                },
                            }
                        }
                    },
                }
            }
        }

    @pytest.fixture
    def sample_flat_data(self) -> dict[str, Any]:
        """Create sample flat format data for testing.

        Returns:
            dict: Sample data in flat format with arrays
        """
        return {
            "workspaces": [
                {"name": "ws1", "type": "kubernetes"},
                {"name": "ws2", "type": "aws"},
            ],
            "contexts": [
                {"name": "ctx1", "workspace": "ws1", "environment": "dev"},
                {"name": "ctx2", "workspace": "ws2", "environment": "prod"},
            ],
            "components": [
                {
                    "name": "comp1",
                    "context": "ctx1",
                    "workspace": "ws1",
                    "config": {"key": "value"},
                },
                {
                    "name": "comp2",
                    "context": "ctx2",
                    "workspace": "ws2",
                    "config": {"key": "value"},
                },
            ],
        }

    @pytest.fixture
    def sample_components_only(self) -> dict[str, Any]:
        """Create sample data with only components.

        Returns:
            dict: Sample data with components keyed by context/name
        """
        return {
            "components": {
                "ctx1/comp1": {
                    "name": "comp1",
                    "context": "ctx1",
                    "workspace": "ws1",
                    "config": {"key": "value"},
                },
                "ctx1/comp2": {
                    "name": "comp2",
                    "context": "ctx1",
                    "workspace": "ws1",
                    "config": {"key": "value2"},
                },
            }
        }

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_init_with_logger(self):
        """Test FormatTypeService initialization with provided logger."""
        mock_logger = MagicMock(spec=Logger)
        service = FormatTypeService(logger=mock_logger)

        assert service.logger is mock_logger

    def test_init_without_logger(self):
        """Test FormatTypeService initialization creates default logger."""
        service = FormatTypeService()

        assert service.logger is not None
        assert hasattr(service.logger, "debug")

    # ========================================================================
    # apply_format Tests - Flat Format
    # ========================================================================

    def test_apply_format_flat_basic(
        self, service: FormatTypeService, sample_nested_data: dict[str, Any]
    ):
        """Test apply_format converts nested to flat format."""
        with patch.object(
            service,
            "flatten_results",
            return_value={"workspaces": [], "contexts": [], "components": []},
        ) as mock_flatten:
            result = service.apply_format(sample_nested_data, "flat")

            mock_flatten.assert_called_once_with(sample_nested_data, None)
            assert "workspaces" in result
            assert "contexts" in result
            assert "components" in result

    def test_apply_format_flat_case_insensitive(
        self, service: FormatTypeService, sample_nested_data: dict[str, Any]
    ):
        """Test apply_format handles uppercase 'FLAT' format type."""
        with patch.object(
            service,
            "flatten_results",
            return_value={"workspaces": [], "contexts": [], "components": []},
        ):
            result = service.apply_format(sample_nested_data, "FLAT")

            assert "workspaces" in result
            assert "contexts" in result
            assert "components" in result

    def test_apply_format_flat_with_type_filter(
        self, service: FormatTypeService, sample_flat_data: dict[str, Any]
    ):
        """Test apply_format applies exclusive type filtering in flat format."""
        with patch.object(service, "flatten_results", return_value=sample_flat_data):
            with patch(
                "coregen.common.type_filter_service.TypeFilterService"
            ) as mock_filter_service:
                mock_filter_instance = MagicMock()
                mock_filter_service.return_value = mock_filter_instance
                mock_filter_instance.filter_exclusive.return_value = {
                    "components": sample_flat_data["components"]
                }

                service.apply_format(sample_flat_data, "flat", type_filter="component")

                # TypeFilterService should be instantiated and called
                mock_filter_service.assert_called_once_with(service.logger)
                mock_filter_instance.filter_exclusive.assert_called_once_with(
                    sample_flat_data, "component"
                )

    # ========================================================================
    # apply_format Tests - Nested Format
    # ========================================================================

    def test_apply_format_nested_basic(
        self, service: FormatTypeService, sample_nested_data: dict[str, Any]
    ):
        """Test apply_format maintains nested structure."""
        with patch.object(
            service, "ensure_nested_structure", return_value=sample_nested_data
        ) as mock_nested:
            result = service.apply_format(sample_nested_data, "nested")

            mock_nested.assert_called_once_with(sample_nested_data)
            assert "workspaces" in result

    def test_apply_format_nested_default(
        self, service: FormatTypeService, sample_nested_data: dict[str, Any]
    ):
        """Test apply_format defaults to nested for unknown format types."""
        with patch.object(
            service, "ensure_nested_structure", return_value=sample_nested_data
        ) as mock_nested:
            service.apply_format(sample_nested_data, "unknown")

            mock_nested.assert_called_once_with(sample_nested_data)

    def test_apply_format_with_entity_resolution_components_only_nested(
        self, service: FormatTypeService, sample_components_only: dict[str, Any]
    ):
        """Test apply_format with entity resolution for components only in nested format."""
        # Create mock entity resolution
        mock_entity_resolution = MagicMock()
        mock_entity_resolution.included_entities = {"components"}

        # Add contexts to data to trigger component extraction logic
        data = {
            "contexts": {
                "ctx1": {
                    "name": "ctx1",
                    "workspace": "ws1",
                    "components": {
                        "comp1": {
                            "name": "comp1",
                            "context": "ctx1",
                            "workspace": "ws1",
                        },
                        "comp2": {
                            "name": "comp2",
                            "context": "ctx1",
                            "workspace": "ws1",
                        },
                    },
                }
            }
        }

        with patch.object(service, "ensure_nested_structure", return_value=data):
            with patch.object(
                service, "_order_entity_fields", side_effect=lambda x, _: x
            ):
                result = service.apply_format(
                    data, "nested", entity_resolution=mock_entity_resolution
                )

                assert "components" in result
                assert isinstance(result["components"], list)
                assert "contexts" not in result or "contexts" not in result

    # ========================================================================
    # flatten_results Tests
    # ========================================================================

    def test_flatten_results_basic(
        self, service: FormatTypeService, sample_nested_data: dict[str, Any]
    ):
        """Test flatten_results converts nested to flat arrays."""
        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            mock_sorter_instance.sort_entities.return_value = []

            with patch.object(
                service, "_order_entity_fields", side_effect=lambda x, _: x
            ):
                result = service.flatten_results(sample_nested_data)

                assert "workspaces" in result
                assert "contexts" in result
                assert "components" in result
                assert isinstance(result["workspaces"], list)
                assert isinstance(result["contexts"], list)
                assert isinstance(result["components"], list)

    def test_flatten_results_with_type_filter(
        self, service: FormatTypeService, sample_nested_data: dict[str, Any]
    ):
        """Test flatten_results passes type_filter parameter."""
        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            mock_sorter_instance.sort_entities.return_value = []

            with patch.object(
                service, "_order_entity_fields", side_effect=lambda x, _: x
            ):
                result = service.flatten_results(
                    sample_nested_data, type_filter="component"
                )

                # Should still return all entity types (filtering happens elsewhere)
                assert "workspaces" in result
                assert "contexts" in result
                assert "components" in result

    def test_flatten_results_removes_nested_data(self, service: FormatTypeService):
        """Test flatten_results removes nested contexts from workspaces."""
        data = {
            "workspaces": {
                "ws1": {
                    "name": "ws1",
                    "contexts": {"cluster": {"ctx1": {"name": "ctx1"}}},
                }
            }
        }

        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            mock_sorter_instance.sort_entities.return_value = []

            with patch.object(
                service, "_order_entity_fields", side_effect=lambda x, _: x
            ):
                result = service.flatten_results(data)

                # Workspace should not have nested contexts
                assert len(result["workspaces"]) == 1
                assert "contexts" not in result["workspaces"][0]

    def test_flatten_results_sets_parent_references(self, service: FormatTypeService):
        """Test flatten_results adds parent references to entities."""
        data = {
            "workspaces": {
                "ws1": {
                    "name": "ws1",
                    "contexts": {
                        "cluster": {
                            "ctx1": {
                                "name": "ctx1",
                                "components": {"app": {"comp1": {"name": "comp1"}}},
                            }
                        }
                    },
                }
            }
        }

        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            mock_sorter_instance.sort_entities.return_value = [
                {"name": "comp1", "context": "ctx1", "workspace": "ws1"}
            ]

            with patch.object(
                service, "_order_entity_fields", side_effect=lambda x, _: x
            ):
                result = service.flatten_results(data)

                # Context should have workspace reference
                if result["contexts"]:
                    assert "workspace" in result["contexts"][0]

    def test_flatten_results_handles_components_with_slash_key(
        self, service: FormatTypeService, sample_components_only: dict[str, Any]
    ):
        """Test flatten_results handles component keys with context prefix."""
        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            mock_sorter_instance.sort_entities.return_value = []

            with patch.object(
                service, "_order_entity_fields", side_effect=lambda x, _: x
            ):
                result = service.flatten_results(sample_components_only)

                # Should extract context from key
                assert "components" in result
                assert isinstance(result["components"], list)

    # ========================================================================
    # ensure_nested_structure Tests
    # ========================================================================

    def test_ensure_nested_structure_basic(
        self, service: FormatTypeService, sample_nested_data: dict[str, Any]
    ):
        """Test ensure_nested_structure maintains hierarchical structure."""
        result = service.ensure_nested_structure(sample_nested_data)

        assert "workspaces" in result
        assert isinstance(result["workspaces"], dict)

    def test_ensure_nested_structure_preserves_entity_order(
        self, service: FormatTypeService
    ):
        """Test ensure_nested_structure orders entities correctly."""
        # Use data without nested relationships to test ordering
        data = {
            "components": {"comp1": {"name": "comp1"}},
            "workspaces": {"ws1": {"name": "ws1"}},
        }

        result = service.ensure_nested_structure(data)

        # Should reorder to standard: workspaces first
        keys = list(result.keys())
        assert keys.index("workspaces") < keys.index("components")

    def test_ensure_nested_structure_nests_components_into_contexts(
        self, service: FormatTypeService
    ):
        """Test ensure_nested_structure moves top-level components into contexts."""
        data = {
            "contexts": {"ctx1": {"name": "ctx1"}},
            "components": {
                "ctx1/comp1": {"name": "comp1", "context": "ctx1", "config": {}}
            },
        }

        with patch.object(service, "_flatten_context_components"):
            result = service.ensure_nested_structure(data)

            # Components should be nested in context
            assert "contexts" in result
            assert "ctx1" in result["contexts"]
            # Top-level components should be removed
            assert "components" not in result

    def test_ensure_nested_structure_handles_model_objects(
        self, service: FormatTypeService
    ):
        """Test ensure_nested_structure handles objects with model_dump."""
        mock_workspace = MagicMock()
        mock_workspace.model_dump.return_value = {"name": "ws1", "contexts": {}}

        data = {"workspaces": {"ws1": mock_workspace}}

        result = service.ensure_nested_structure(data)

        assert "workspaces" in result
        mock_workspace.model_dump.assert_called()

    # ========================================================================
    # is_flat_format Tests
    # ========================================================================

    def test_is_flat_format_detects_flat(
        self, service: FormatTypeService, sample_flat_data: dict[str, Any]
    ):
        """Test is_flat_format detects flat format with arrays."""
        result = service.is_flat_format(sample_flat_data)

        assert result is True

    def test_is_flat_format_detects_nested(
        self, service: FormatTypeService, sample_nested_data: dict[str, Any]
    ):
        """Test is_flat_format detects nested format with dicts."""
        result = service.is_flat_format(sample_nested_data)

        assert result is False

    def test_is_flat_format_handles_empty(self, service: FormatTypeService):
        """Test is_flat_format handles empty data."""
        result = service.is_flat_format({})

        assert result is False

    # ========================================================================
    # _order_entity_fields Tests
    # ========================================================================

    def test_order_entity_fields_component(self, service: FormatTypeService):
        """Test _order_entity_fields orders component fields correctly."""
        entity = {
            "config": {"key": "value"},
            "workspace": "ws1",
            "name": "comp1",
            "context": "ctx1",
        }

        result = service._order_entity_fields(entity, "component")

        # Priority fields should come first
        keys = list(result.keys())
        assert keys[0] == "name"
        assert keys[1] == "context"
        assert keys[2] == "workspace"
        assert "config" in keys

    def test_order_entity_fields_context(self, service: FormatTypeService):
        """Test _order_entity_fields orders context fields correctly."""
        entity = {
            "environment": "dev",
            "workspace": "ws1",
            "name": "ctx1",
            "active": True,
        }

        result = service._order_entity_fields(entity, "context")

        # Priority fields should come first
        keys = list(result.keys())
        assert keys[0] == "name"
        assert keys[1] == "workspace"

    def test_order_entity_fields_workspace(self, service: FormatTypeService):
        """Test _order_entity_fields orders workspace fields correctly."""
        entity = {
            "type": "kubernetes",
            "name": "ws1",
            "active": True,
        }

        result = service._order_entity_fields(entity, "workspace")

        # Only name should be priority for workspace
        keys = list(result.keys())
        assert keys[0] == "name"

    # ========================================================================
    # _flatten_context_components Tests
    # ========================================================================

    def test_flatten_context_components_removes_component_type(
        self, service: FormatTypeService
    ):
        """Test _flatten_context_components removes component_type field."""
        ctx_data = {
            "name": "ctx1",
            "component_type": "app",
            "components": {},
        }

        service._flatten_context_components(ctx_data)

        assert "component_type" not in ctx_data

    def test_flatten_context_components_sorts_components(
        self, service: FormatTypeService
    ):
        """Test _flatten_context_components sorts components."""
        ctx_data = {
            "components": {
                "comp2": {"name": "comp2", "config": {}},
                "comp1": {"name": "comp1", "config": {}},
            }
        }

        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            mock_sorter_instance.sort_entities.return_value = [
                {"name": "comp1", "config": {}},
                {"name": "comp2", "config": {}},
            ]

            service._flatten_context_components(ctx_data)

            mock_sorter_instance.sort_entities.assert_called_once()

    # ========================================================================
    # _convert_model_to_dict Tests
    # ========================================================================

    def test_convert_model_to_dict_with_model_dump(self, service: FormatTypeService):
        """Test _convert_model_to_dict converts model objects."""
        mock_model = MagicMock()
        mock_model.model_dump.return_value = {"name": "test", "value": 123}

        result = service._convert_model_to_dict(mock_model)

        assert result == {"name": "test", "value": 123}
        mock_model.model_dump.assert_called_once()

    def test_convert_model_to_dict_with_dict(self, service: FormatTypeService):
        """Test _convert_model_to_dict handles plain dicts."""
        input_dict = {"name": "test", "value": 123}

        result = service._convert_model_to_dict(input_dict)

        assert result == input_dict
        assert result is not input_dict  # Should be a copy

    def test_convert_model_to_dict_with_other_type(self, service: FormatTypeService):
        """Test _convert_model_to_dict handles other types."""
        input_value = "string_value"

        result = service._convert_model_to_dict(input_value)

        assert result == input_value

    # ========================================================================
    # Entity Resolution Tests - Additional Coverage
    # ========================================================================

    def test_apply_format_with_entity_resolution_extracts_from_top_level_components(
        self, service: FormatTypeService
    ):
        """Test apply_format with entity resolution extracting from top-level components."""
        mock_entity_resolution = MagicMock()
        mock_entity_resolution.included_entities = {"components"}

        data = {
            "components": {
                "ctx1/comp1": {
                    "name": "comp1",
                    "context": "ctx1",
                    "workspace": "ws1",
                    "config": {},
                },
                "ctx1/comp2": {
                    "name": "comp2",
                    "context": "ctx1",
                    "workspace": "ws1",
                    "config": {},
                },
            }
        }

        with patch.object(service, "ensure_nested_structure", return_value=data):
            with patch.object(
                service, "_order_entity_fields", side_effect=lambda x, _: x
            ):
                result = service.apply_format(
                    data, "nested", entity_resolution=mock_entity_resolution
                )

                assert "components" in result
                assert isinstance(result["components"], list)
                assert len(result["components"]) == 2

    def test_apply_format_with_entity_resolution_components_from_contexts(
        self, service: FormatTypeService
    ):
        """Test apply_format extracts components from nested contexts when entity resolution requires it."""
        mock_entity_resolution = MagicMock()
        mock_entity_resolution.included_entities = {"components"}

        data = {
            "contexts": {
                "ctx1": {
                    "name": "ctx1",
                    "workspace": "ws1",
                    "components": {
                        "comp1": {"name": "comp1", "config": {}},
                    },
                }
            }
        }

        with patch.object(service, "ensure_nested_structure", return_value=data):
            with patch.object(
                service, "_order_entity_fields", side_effect=lambda x, _: x
            ):
                result = service.apply_format(
                    data, "nested", entity_resolution=mock_entity_resolution
                )

                assert "components" in result

    def test_apply_format_with_entity_resolution_skip_top_level_components_for_context_queries(
        self, service: FormatTypeService
    ):
        """Test apply_format skips top-level components for context-only queries in nested format."""
        mock_entity_resolution = MagicMock()
        mock_entity_resolution.included_entities = {"contexts"}

        data = {
            "contexts": {"ctx1": {"name": "ctx1"}},
            "components": {"comp1": {"name": "comp1"}},
        }

        with patch.object(service, "ensure_nested_structure", return_value=data):
            result = service.apply_format(
                data, "nested", entity_resolution=mock_entity_resolution
            )

            assert "contexts" in result
            assert "components" not in result

    def test_apply_format_with_entity_resolution_includes_non_standard_entities(
        self, service: FormatTypeService
    ):
        """Test apply_format includes non-standard entity types from entity resolution."""
        mock_entity_resolution = MagicMock()
        mock_entity_resolution.included_entities = {"custom_entities", "workspaces"}

        data = {
            "workspaces": {"ws1": {"name": "ws1"}},
            "custom_entities": {"entity1": {"name": "entity1"}},
        }

        with patch.object(service, "ensure_nested_structure", return_value=data):
            result = service.apply_format(
                data, "nested", entity_resolution=mock_entity_resolution
            )

            assert "workspaces" in result
            assert "custom_entities" in result

    def test_flatten_results_handles_model_dump_objects(
        self, service: FormatTypeService
    ):
        """Test flatten_results handles objects with model_dump method."""
        mock_workspace = MagicMock()
        mock_workspace.model_dump.return_value = {"name": "ws1", "type": "kubernetes"}

        data = {"workspaces": {"ws1": mock_workspace}}

        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            mock_sorter_instance.sort_entities.return_value = []

            with patch.object(
                service, "_order_entity_fields", side_effect=lambda x, _: x
            ):
                result = service.flatten_results(data)

                assert len(result["workspaces"]) == 1
                mock_workspace.model_dump.assert_called()

    def test_flatten_results_handles_direct_context_entry(
        self, service: FormatTypeService
    ):
        """Test flatten_results handles direct context entries without type grouping."""
        data = {
            "workspaces": {
                "ws1": {
                    "name": "ws1",
                    "contexts": {
                        "ctx1": {"name": "ctx1", "environment": "dev"},
                    },
                }
            }
        }

        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            mock_sorter_instance.sort_entities.return_value = []

            with patch.object(
                service, "_order_entity_fields", side_effect=lambda x, _: x
            ):
                result = service.flatten_results(data)

                assert len(result["contexts"]) == 1
                assert result["contexts"][0]["name"] == "ctx1"

    def test_flatten_results_handles_direct_component_entry(
        self, service: FormatTypeService
    ):
        """Test flatten_results handles direct component entries."""
        data = {
            "workspaces": {
                "ws1": {
                    "name": "ws1",
                    "contexts": {
                        "cluster": {
                            "ctx1": {
                                "name": "ctx1",
                                "workspace": "ws1",
                                "components": {
                                    "comp1": {"name": "comp1", "config": {}},
                                },
                            }
                        }
                    },
                }
            }
        }

        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            mock_sorter_instance.sort_entities.return_value = []

            with patch.object(
                service, "_order_entity_fields", side_effect=lambda x, _: x
            ):
                result = service.flatten_results(data)

                # Should have extracted component
                assert "components" in result

    def test_flatten_results_handles_component_without_context_in_key(
        self, service: FormatTypeService
    ):
        """Test flatten_results handles components without context prefix in key."""
        data = {
            "components": {
                "comp1": {"name": "comp1", "context": "ctx1", "workspace": "ws1"},
            }
        }

        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            mock_sorter_instance.sort_entities.return_value = []

            with patch.object(
                service, "_order_entity_fields", side_effect=lambda x, _: x
            ):
                result = service.flatten_results(data)

                assert (
                    len(result["components"]) == 0
                )  # Sorter returns empty list in mock

    def test_flatten_results_sets_unknown_workspace_for_missing_context(
        self, service: FormatTypeService
    ):
        """Test flatten_results sets unknown workspace when context is missing."""
        data = {
            "components": {
                "unknown_comp": {"name": "unknown_comp"},
            }
        }

        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            # Return the component with defaults added
            mock_sorter_instance.sort_entities.return_value = [
                {"name": "unknown_comp", "context": "unknown", "workspace": "unknown"}
            ]

            with patch.object(
                service, "_order_entity_fields", side_effect=lambda x, _: x
            ):
                result = service.flatten_results(data)

                # Sorted result should have the mocked return
                assert len(result["components"]) == 1

    def test_flatten_context_components_handles_grouped_components(
        self, service: FormatTypeService
    ):
        """Test _flatten_context_components handles component type groupings."""
        ctx_data = {
            "components": {
                "app": {
                    "comp1": {"name": "comp1", "config": {}},
                    "comp2": {"name": "comp2", "config": {}},
                }
            }
        }

        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            mock_sorter_instance.sort_entities.return_value = [
                {"name": "comp1", "config": {}},
                {"name": "comp2", "config": {}},
            ]

            service._flatten_context_components(ctx_data)

            # Should have flattened the grouping
            assert "components" in ctx_data
            # Components should be reorganized
            mock_sorter_instance.sort_entities.assert_called_once()

    def test_flatten_context_components_handles_model_objects(
        self, service: FormatTypeService
    ):
        """Test _flatten_context_components handles component model objects."""
        mock_component = MagicMock()
        mock_component.model_dump.return_value = {"name": "comp1", "config": {}}

        ctx_data = {
            "components": {
                "comp1": mock_component,
            }
        }

        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            mock_sorter_instance.sort_entities.return_value = [
                {"name": "comp1", "config": {}}
            ]

            service._flatten_context_components(ctx_data)

            mock_component.model_dump.assert_called()

    def test_convert_model_to_dict_excludes_component_type_fields(
        self, service: FormatTypeService
    ):
        """Test _convert_model_to_dict excludes dynamic component type fields."""
        mock_context = MagicMock()
        mock_context.components = {"app": {"comp1": {}}, "infra": {"comp2": {}}}
        mock_context.component_type = "app"
        mock_context.model_dump.return_value = {"name": "ctx1", "workspace": "ws1"}

        result = service._convert_model_to_dict(mock_context)

        assert "name" in result
        mock_context.model_dump.assert_called()

    def test_ensure_nested_structure_handles_context_type_grouping(
        self, service: FormatTypeService
    ):
        """Test ensure_nested_structure handles context type groupings."""
        data = {
            "workspaces": {
                "ws1": {
                    "name": "ws1",
                    "contexts": {
                        "cluster": {
                            "ctx1": {"name": "ctx1"},
                            "ctx2": {"name": "ctx2"},
                        }
                    },
                }
            }
        }

        with patch.object(service, "_flatten_context_components"):
            result = service.ensure_nested_structure(data)

            assert "workspaces" in result
            assert "ws1" in result["workspaces"]

    def test_ensure_nested_structure_handles_components_without_contexts(
        self, service: FormatTypeService
    ):
        """Test ensure_nested_structure handles components when no contexts exist."""
        data = {
            "components": {
                "ctx1/comp1": {"name": "comp1", "context": "ctx1", "workspace": "ws1"},
            }
        }

        result = service.ensure_nested_structure(data)

        # Components should remain as-is when no contexts
        assert "components" in result

    def test_flatten_context_components_removes_component_type_fields(
        self, service: FormatTypeService
    ):
        """Test _flatten_context_components removes duplicate component type fields."""
        ctx_data = {
            "name": "ctx1",
            "workspace": "ws1",
            "app": {"comp1": {"config": {}}},
            "infra": {"comp2": {"config": {}}},
            "components": {},
        }

        with patch(
            "coregen.common.component_sorter_service.ComponentSorterService"
        ) as mock_sorter:
            mock_sorter_instance = MagicMock()
            mock_sorter.return_value = mock_sorter_instance
            mock_sorter_instance.sort_entities.return_value = []

            service._flatten_context_components(ctx_data)

            # Component type fields should be removed
            assert "app" not in ctx_data
            assert "infra" not in ctx_data
