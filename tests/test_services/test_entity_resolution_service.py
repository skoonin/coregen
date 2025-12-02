"""Unit tests for EntityResolutionService.

This module tests the EntityResolutionService which resolves entity inclusion
based on patterns, type filters, and format types. The service determines:
- What entities to include (workspaces, contexts, components)
- Whether to filter parent entities
- Validation of pattern/type combinations
"""

from unittest.mock import MagicMock

import pytest

from coregen.common.entity_resolution_service import (
    EntityResolution,
    EntityResolutionService,
)
from coregen.common.logger import Logger


class TestEntityResolutionService:
    """Test suite for EntityResolutionService."""

    @pytest.fixture
    def service(self) -> EntityResolutionService:
        """Create an EntityResolutionService instance for testing.

        Returns:
            EntityResolutionService: Fresh service instance with mocked logger
        """
        mock_logger = MagicMock(spec=Logger)
        return EntityResolutionService(logger=mock_logger)

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_init_with_logger(self):
        """Test EntityResolutionService initialization with provided logger."""
        mock_logger = MagicMock(spec=Logger)
        service = EntityResolutionService(logger=mock_logger)

        assert service.logger is mock_logger

    def test_init_without_logger(self):
        """Test EntityResolutionService initialization creates default logger."""
        service = EntityResolutionService()

        assert service.logger is not None
        assert hasattr(service.logger, "debug")

    # ========================================================================
    # resolve() Tests - Component Patterns
    # ========================================================================

    def test_resolve_component_pattern_filters_parents(
        self, service: EntityResolutionService
    ):
        """Test cm/* patterns return only components with parent filtering."""
        result = service.resolve(
            patterns=["cm/*"], type_filter=None, format_type="nested"
        )

        assert result.primary_entity == "components"
        assert result.included_entities == {"components"}
        assert result.filter_parents is True

    def test_resolve_component_pattern_with_type_filter(
        self, service: EntityResolutionService
    ):
        """Test cm/* pattern with component type filter returns components."""
        result = service.resolve(
            patterns=["cm/my-component"], type_filter="component", format_type="nested"
        )

        assert result.primary_entity == "components"
        assert result.included_entities == {"components"}
        # Type filter overrides pattern-based filtering
        assert result.filter_parents is True

    def test_resolve_component_pattern_invalid_workspace_type(
        self, service: EntityResolutionService
    ):
        """Test cm/* pattern with workspace type filter raises ValueError."""
        with pytest.raises(ValueError, match="cannot return workspaces"):
            service.resolve(
                patterns=["cm/*"], type_filter="workspace", format_type="nested"
            )

    def test_resolve_component_pattern_invalid_context_type(
        self, service: EntityResolutionService
    ):
        """Test cm/* pattern with context type filter raises ValueError."""
        with pytest.raises(ValueError, match="cannot return contexts"):
            service.resolve(
                patterns=["cm/*"], type_filter="context", format_type="nested"
            )

    # ========================================================================
    # resolve() Tests - Context Patterns
    # ========================================================================

    def test_resolve_context_pattern_includes_contexts_and_components(
        self, service: EntityResolutionService
    ):
        """Test c/* patterns return contexts and components with parent filtering."""
        result = service.resolve(
            patterns=["c/*"], type_filter=None, format_type="nested"
        )

        assert result.primary_entity == "contexts"
        assert result.included_entities == {"contexts", "components"}
        assert result.filter_parents is True

    def test_resolve_context_pattern_with_component_filter(
        self, service: EntityResolutionService
    ):
        """Test c/* pattern with component type filter returns only components."""
        result = service.resolve(
            patterns=["c/my-context"], type_filter="component", format_type="nested"
        )

        assert result.primary_entity == "contexts"
        assert result.included_entities == {"components"}
        assert result.filter_parents is True

    def test_resolve_context_pattern_invalid_workspace_type(
        self, service: EntityResolutionService
    ):
        """Test c/* pattern with workspace type filter raises ValueError."""
        with pytest.raises(ValueError, match="cannot return workspaces"):
            service.resolve(
                patterns=["c/*"], type_filter="workspace", format_type="nested"
            )

    # ========================================================================
    # resolve() Tests - Workspace Patterns
    # ========================================================================

    def test_resolve_workspace_pattern_nested_format(
        self, service: EntityResolutionService
    ):
        """Test w/* pattern in nested format returns only workspaces."""
        result = service.resolve(
            patterns=["w/*"], type_filter=None, format_type="nested"
        )

        assert result.primary_entity == "workspaces"
        assert result.included_entities == {"workspaces"}
        assert result.filter_parents is False

    def test_resolve_workspace_pattern_flat_format(
        self, service: EntityResolutionService
    ):
        """Test w/* pattern in flat format returns only workspaces."""
        result = service.resolve(patterns=["w/*"], type_filter=None, format_type="flat")

        assert result.primary_entity == "workspaces"
        assert result.included_entities == {"workspaces"}
        assert result.filter_parents is False

    def test_resolve_workspace_pattern_with_component_filter(
        self, service: EntityResolutionService
    ):
        """Test w/* pattern with component type filter returns only components."""
        result = service.resolve(
            patterns=["w/my-workspace"], type_filter="component", format_type="nested"
        )

        assert result.primary_entity == "workspaces"
        assert result.included_entities == {"components"}
        assert result.filter_parents is False

    # ========================================================================
    # resolve() Tests - Type Filter Normalization
    # ========================================================================

    def test_resolve_type_filter_normalization_workspace(
        self, service: EntityResolutionService
    ):
        """Test type filter normalization for workspace (singular to plural)."""
        result = service.resolve(
            patterns=["w/*"], type_filter="workspace", format_type="nested"
        )

        assert result.included_entities == {"workspaces"}

    def test_resolve_type_filter_normalization_context(
        self, service: EntityResolutionService
    ):
        """Test type filter normalization for context (singular to plural)."""
        result = service.resolve(
            patterns=["c/*"], type_filter="context", format_type="nested"
        )

        assert result.included_entities == {"contexts"}

    def test_resolve_type_filter_normalization_component(
        self, service: EntityResolutionService
    ):
        """Test type filter normalization for component (singular to plural)."""
        result = service.resolve(
            patterns=["cm/*"], type_filter="component", format_type="nested"
        )

        assert result.included_entities == {"components"}

    # ========================================================================
    # resolve() Tests - No Pattern Edge Cases
    # ========================================================================

    def test_resolve_empty_patterns_all_entities(
        self, service: EntityResolutionService
    ):
        """Test empty patterns return all entities without filtering."""
        result = service.resolve(patterns=[], type_filter=None, format_type="nested")

        assert result.primary_entity is None
        assert result.included_entities == {"workspaces", "contexts", "components"}
        assert result.filter_parents is False

    def test_resolve_filesystem_pattern_all_entities(
        self, service: EntityResolutionService
    ):
        """Test filesystem patterns return all entities without filtering."""
        result = service.resolve(
            patterns=["/some/path/*"], type_filter=None, format_type="nested"
        )

        assert result.primary_entity is None
        assert result.included_entities == {"workspaces", "contexts", "components"}
        assert result.filter_parents is False

    def test_resolve_filesystem_pattern_with_type_filter(
        self, service: EntityResolutionService
    ):
        """Test filesystem pattern with type filter returns only that type."""
        result = service.resolve(
            patterns=["/some/path/*"], type_filter="component", format_type="nested"
        )

        assert result.primary_entity is None
        assert result.included_entities == {"components"}
        assert result.filter_parents is False

    # ========================================================================
    # _get_primary_entity_type() Tests
    # ========================================================================

    def test_get_primary_entity_type_workspace_short_prefix(
        self, service: EntityResolutionService
    ):
        """Test _get_primary_entity_type recognizes w/ prefix as workspace."""
        result = service._get_primary_entity_type(["w/my-workspace"])

        assert result == "workspaces"

    def test_get_primary_entity_type_workspace_long_prefix(
        self, service: EntityResolutionService
    ):
        """Test _get_primary_entity_type recognizes workspace/ prefix."""
        result = service._get_primary_entity_type(["workspace/my-workspace"])

        assert result == "workspaces"

    def test_get_primary_entity_type_context_short_prefix(
        self, service: EntityResolutionService
    ):
        """Test _get_primary_entity_type recognizes c/ prefix as context."""
        result = service._get_primary_entity_type(["c/my-context"])

        assert result == "contexts"

    def test_get_primary_entity_type_context_long_prefix(
        self, service: EntityResolutionService
    ):
        """Test _get_primary_entity_type recognizes context/ prefix."""
        result = service._get_primary_entity_type(["context/my-context"])

        assert result == "contexts"

    def test_get_primary_entity_type_component_short_prefix(
        self, service: EntityResolutionService
    ):
        """Test _get_primary_entity_type recognizes cm/ prefix as component."""
        result = service._get_primary_entity_type(["cm/my-component"])

        assert result == "components"

    def test_get_primary_entity_type_component_long_prefix(
        self, service: EntityResolutionService
    ):
        """Test _get_primary_entity_type recognizes component/ prefix."""
        result = service._get_primary_entity_type(["component/my-component"])

        assert result == "components"

    def test_get_primary_entity_type_empty_patterns(
        self, service: EntityResolutionService
    ):
        """Test _get_primary_entity_type returns None for empty patterns."""
        result = service._get_primary_entity_type([])

        assert result is None

    def test_get_primary_entity_type_filesystem_pattern(
        self, service: EntityResolutionService
    ):
        """Test _get_primary_entity_type returns None for filesystem patterns."""
        result = service._get_primary_entity_type(["/some/path/*"])

        assert result is None

    def test_get_primary_entity_type_multiple_patterns_uses_first(
        self, service: EntityResolutionService
    ):
        """Test _get_primary_entity_type uses first pattern when multiple provided."""
        result = service._get_primary_entity_type(["w/workspace1", "c/context1"])

        # Should use the first pattern
        assert result == "workspaces"

    # ========================================================================
    # _validate_combination() Tests
    # ========================================================================

    def test_validate_combination_valid_workspace_component(
        self, service: EntityResolutionService
    ):
        """Test _validate_combination allows workspace pattern with component type."""
        # Should not raise
        service._validate_combination(
            primary_entity="workspaces", requested_type="components", patterns=["w/*"]
        )

    def test_validate_combination_valid_context_component(
        self, service: EntityResolutionService
    ):
        """Test _validate_combination allows context pattern with component type."""
        # Should not raise
        service._validate_combination(
            primary_entity="contexts", requested_type="components", patterns=["c/*"]
        )

    def test_validate_combination_valid_context_context(
        self, service: EntityResolutionService
    ):
        """Test _validate_combination allows context pattern with context type."""
        # Should not raise
        service._validate_combination(
            primary_entity="contexts", requested_type="contexts", patterns=["c/*"]
        )

    def test_validate_combination_invalid_context_workspace(
        self, service: EntityResolutionService
    ):
        """Test _validate_combination rejects context pattern with workspace type."""
        with pytest.raises(ValueError, match="Context patterns"):
            service._validate_combination(
                primary_entity="contexts", requested_type="workspaces", patterns=["c/*"]
            )

    def test_validate_combination_invalid_component_workspace(
        self, service: EntityResolutionService
    ):
        """Test _validate_combination rejects component pattern with workspace type."""
        with pytest.raises(ValueError, match="Component patterns"):
            service._validate_combination(
                primary_entity="components",
                requested_type="workspaces",
                patterns=["cm/*"],
            )

    def test_validate_combination_invalid_component_context(
        self, service: EntityResolutionService
    ):
        """Test _validate_combination rejects component pattern with context type."""
        with pytest.raises(ValueError, match="Component patterns"):
            service._validate_combination(
                primary_entity="components",
                requested_type="contexts",
                patterns=["cm/*"],
            )

    def test_validate_combination_with_no_primary_entity(
        self, service: EntityResolutionService
    ):
        """Test _validate_combination allows any type when no primary entity."""
        # Should not raise for filesystem patterns with any type
        service._validate_combination(
            primary_entity=None, requested_type="workspaces", patterns=["/path/*"]
        )
        service._validate_combination(
            primary_entity=None, requested_type="contexts", patterns=["/path/*"]
        )
        service._validate_combination(
            primary_entity=None, requested_type="components", patterns=["/path/*"]
        )


class TestEntityResolution:
    """Test suite for EntityResolution dataclass."""

    def test_entity_resolution_dataclass_creation(self):
        """Test EntityResolution dataclass can be created with valid fields."""
        resolution = EntityResolution(
            primary_entity="workspaces",
            included_entities={"workspaces", "contexts"},
            filter_parents=True,
        )

        assert resolution.primary_entity == "workspaces"
        assert resolution.included_entities == {"workspaces", "contexts"}
        assert resolution.filter_parents is True

    def test_entity_resolution_none_primary_entity(self):
        """Test EntityResolution handles None for primary_entity."""
        resolution = EntityResolution(
            primary_entity=None,
            included_entities={"workspaces", "contexts", "components"},
            filter_parents=False,
        )

        assert resolution.primary_entity is None
        assert len(resolution.included_entities) == 3

    def test_entity_resolution_empty_included_entities(self):
        """Test EntityResolution handles empty included_entities set."""
        resolution = EntityResolution(
            primary_entity="components", included_entities=set(), filter_parents=False
        )

        assert resolution.included_entities == set()
        assert len(resolution.included_entities) == 0
