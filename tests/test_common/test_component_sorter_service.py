"""Comprehensive unit tests for ComponentSorterService.

Tests cover:
- Basic sorting by priority (workspace → context → priority → name)
- Workspace and context grouping
- Alphabetical tie-breaking
- Validation rules (duplicate priorities, priority conflicts, circular dependencies)
- Legacy method compatibility
"""

from typing import Any

import pytest

from coregen.common.component_sorter_service import (
    ComponentSorterService,
    ComponentValidationError,
)


@pytest.fixture
def sorter() -> Any:
    """Create ComponentSorterService instance with default configuration."""
    return ComponentSorterService()


class TestComponentSorterService:
    """Test the ComponentSorterService class."""

    # ---- Basic Priority Sorting Tests ----

    def test_sort_by_priority_basic(self, sorter):
        """Test components are sorted by priority (lower numbers first)."""
        components = [
            {"name": "comp3", "priority": 3},
            {"name": "comp1", "priority": 1},
            {"name": "comp2", "priority": 2},
        ]

        result = sorter.sort_entities(components, "component")

        assert [c["name"] for c in result] == ["comp1", "comp2", "comp3"]

    def test_sort_priority_with_none_last(self, sorter):
        """Test components with None priority come after prioritized ones."""
        components = [
            {"name": "comp_none1", "priority": None, "workspace": "", "context": ""},
            {"name": "comp2", "priority": 2, "workspace": "", "context": ""},
            {"name": "comp1", "priority": 1, "workspace": "", "context": ""},
            {"name": "comp_none2", "priority": None, "workspace": "", "context": ""},
        ]

        result = sorter.sort_entities(components, "component")

        names = [c["name"] for c in result]
        # Prioritized first (by priority)
        assert names[:2] == ["comp1", "comp2"]
        # Non-prioritized last (alphabetical)
        assert names[2:] == ["comp_none1", "comp_none2"]

    def test_alphabetical_tie_breaking_with_validation_error(self, sorter):
        """Test components with same priority trigger validation error.

        Note: In the new validation rules, duplicate priorities within a context
        are not allowed and will raise ComponentValidationError.
        """
        components = [
            {"name": "zebra", "priority": 1, "workspace": "ws1", "context": "ctx1"},
            {"name": "alpha", "priority": 1, "workspace": "ws1", "context": "ctx1"},
            {"name": "beta", "priority": 1, "workspace": "ws1", "context": "ctx1"},
        ]

        with pytest.raises(ComponentValidationError) as exc_info:
            sorter.sort_entities(components, "component")

        error_msg = str(exc_info.value)
        assert "Duplicate priority values" in error_msg
        assert "Priority 1" in error_msg

    # ---- Workspace and Context Grouping Tests ----

    def test_workspace_grouping(self, sorter):
        """Test components are grouped by workspace first."""
        components = [
            {
                "name": "comp_b1",
                "workspace": "workspace_b",
                "context": "",
                "priority": 1,
            },
            {
                "name": "comp_a1",
                "workspace": "workspace_a",
                "context": "",
                "priority": 1,
            },
            {
                "name": "comp_b2",
                "workspace": "workspace_b",
                "context": "",
                "priority": 2,
            },
            {
                "name": "comp_a2",
                "workspace": "workspace_a",
                "context": "",
                "priority": 2,
            },
        ]

        result = sorter.sort_entities(components, "component")

        names = [c["name"] for c in result]
        # workspace_a comes before workspace_b
        assert names == ["comp_a1", "comp_a2", "comp_b1", "comp_b2"]

    def test_context_grouping_within_workspace(self, sorter):
        """Test components are grouped by context within workspace."""
        components = [
            {"name": "comp1", "workspace": "ws1", "context": "ctx_b", "priority": 1},
            {"name": "comp2", "workspace": "ws1", "context": "ctx_a", "priority": 1},
            {"name": "comp3", "workspace": "ws2", "context": "ctx_a", "priority": 1},
            {"name": "comp4", "workspace": "ws1", "context": "ctx_a", "priority": 2},
        ]

        result = sorter.sort_entities(components, "component")

        names = [c["name"] for c in result]
        # ws1/ctx_a, then ws1/ctx_b, then ws2/ctx_a
        assert names == ["comp2", "comp4", "comp1", "comp3"]

    def test_dependencies_only_within_context(self, sorter):
        """Test validation only checks dependencies within same context."""
        components = [
            {
                "name": "app",
                "workspace": "ws1",
                "context": "ctx1",
                "priority": 1,
                "config": {"dependencies": [{"name": "lib"}]},
            },
            {
                "name": "lib",
                "workspace": "ws1",
                "context": "ctx2",  # Different context
                "priority": 2,
            },
        ]

        # Should not raise error because dependency is in different context
        result = sorter.sort_entities(components, "component")

        names = [c["name"] for c in result]
        # Components sorted by context then priority
        assert names == ["app", "lib"]

    # ---- Configuration Tests ----

    def test_custom_none_priority_value(self, sorter):
        """Test custom value for None priority affects sort order."""
        sorter = ComponentSorterService(none_priority_value=500)

        components = [
            {"name": "app1", "priority": 1, "workspace": "", "context": ""},
            {"name": "lib_none", "priority": None, "workspace": "", "context": ""},
        ]

        result = sorter.sort_entities(components, "component")

        # app1 comes first (priority 1), lib_none last (treated as 500)
        assert result[0]["name"] == "app1"
        assert result[1]["name"] == "lib_none"

    def test_configuration_via_kwargs(self, sorter):
        """Test passing configuration via kwargs."""
        sorter = ComponentSorterService(
            none_priority_value=500,
            cycle_break_strategy="stable",
        )

        assert sorter.none_priority_value == 500
        assert sorter.cycle_break_strategy == "stable"

    # ---- Edge Cases and Error Handling ----

    def test_empty_input(self, sorter):
        """Test handling of empty input."""
        assert sorter.sort_entities([], "component") == []

    def test_missing_dependencies(self, sorter):
        """Test handling of dependencies that don't exist."""
        components = [
            {
                "name": "app",
                "workspace": "",
                "context": "",
                "priority": 1,
                "config": {"dependencies": [{"name": "missing"}]},
            },
        ]

        # Should not raise, missing dependency is ignored
        result = sorter.sort_entities(components, "component")
        assert len(result) == 1
        assert result[0]["name"] == "app"

    def test_large_dataset_performance(self, sorter):
        """Test performance with larger dataset."""
        # Create 100 components with various priorities
        components = []
        for i in range(100):
            components.append(
                {
                    "name": f"comp{i:03d}",
                    "workspace": f"ws{i // 20}",
                    "context": f"ctx{i // 10}",
                    "priority": i % 5 if i % 2 == 0 else None,
                    "config": {},
                }
            )

        # Should complete without issues
        result = sorter.sort_entities(components, "component")
        assert len(result) == 100

        # Verify workspace grouping is maintained
        ws_order = []
        for comp in result:
            ws = comp["workspace"]
            if not ws_order or ws_order[-1] != ws:
                ws_order.append(ws)
        assert ws_order == sorted(ws_order)


class TestComponentSorterValidation:
    """Test strict validation features."""

    def test_duplicate_priority_validation(self, sorter):
        """Test that duplicate priorities are detected."""
        sorter = ComponentSorterService()
        components = [
            {
                "name": "comp1",
                "workspace": "test",
                "context": "prod",
                "priority": 1,
                "config": {"dependencies": []},
            },
            {
                "name": "comp2",
                "workspace": "test",
                "context": "prod",
                "priority": 1,  # Duplicate!
                "config": {"dependencies": []},
            },
        ]

        with pytest.raises(ComponentValidationError) as exc_info:
            sorter.sort_entities(components, "component")

        error_msg = str(exc_info.value)
        assert "Duplicate priority values" in error_msg
        assert "comp1" in error_msg and "comp2" in error_msg

    def test_priority_conflict_validation(self, sorter):
        """Test that priority conflicts are detected.

        When a component depends on another, the dependency must have
        equal or better priority (lower number).
        """
        sorter = ComponentSorterService()
        components = [
            {
                "name": "low",
                "workspace": "test",
                "context": "prod",
                "priority": 5,
                "config": {"dependencies": []},
            },
            {
                "name": "high",
                "workspace": "test",
                "context": "prod",
                "priority": 1,
                "config": {
                    "dependencies": [{"name": "low"}]
                },  # Depends on higher priority number
            },
        ]

        with pytest.raises(ComponentValidationError) as exc_info:
            sorter.sort_entities(components, "component")

        error_msg = str(exc_info.value)
        assert "Priority conflict" in error_msg
        assert "high" in error_msg and "low" in error_msg

    def test_circular_dependency_validation(self, sorter):
        """Test that circular dependencies are detected."""
        sorter = ComponentSorterService()
        components = [
            {
                "name": "a",
                "workspace": "test",
                "context": "prod",
                "priority": None,
                "config": {"dependencies": [{"name": "b"}]},
            },
            {
                "name": "b",
                "workspace": "test",
                "context": "prod",
                "priority": None,
                "config": {"dependencies": [{"name": "c"}]},
            },
            {
                "name": "c",
                "workspace": "test",
                "context": "prod",
                "priority": None,
                "config": {"dependencies": [{"name": "a"}]},  # Cycle: a -> b -> c -> a
            },
        ]

        with pytest.raises(ComponentValidationError) as exc_info:
            sorter.sort_entities(components, "component")

        error_msg = str(exc_info.value)
        assert "Circular dependencies" in error_msg
        # Should mention the cycle components
        assert "a" in error_msg and "b" in error_msg and "c" in error_msg

    def test_priority_component_cannot_depend_on_null_priority(self, sorter):
        """Test that priority components cannot depend on null priority components."""
        sorter = ComponentSorterService()
        components = [
            {
                "name": "app",
                "workspace": "test",
                "context": "prod",
                "priority": 1,
                "config": {"dependencies": [{"name": "lib"}]},
            },
            {
                "name": "lib",
                "workspace": "test",
                "context": "prod",
                "priority": None,
                "config": {"dependencies": []},
            },
        ]

        with pytest.raises(ComponentValidationError) as exc_info:
            sorter.sort_entities(components, "component")

        error_msg = str(exc_info.value)
        assert "Invalid priority configuration" in error_msg
        assert "cannot depend on" in error_msg
        assert "priority=null" in error_msg

    def test_null_priority_cannot_depend_on_null_priority(self, sorter):
        """Test that null priority components cannot depend on other null priority components."""
        sorter = ComponentSorterService()
        components = [
            {
                "name": "app",
                "workspace": "test",
                "context": "prod",
                "priority": None,
                "config": {"dependencies": [{"name": "lib"}]},
            },
            {
                "name": "lib",
                "workspace": "test",
                "context": "prod",
                "priority": None,
                "config": {"dependencies": []},
            },
        ]

        with pytest.raises(ComponentValidationError) as exc_info:
            sorter.sort_entities(components, "component")

        error_msg = str(exc_info.value)
        assert "Invalid priority configuration" in error_msg
        assert "priority=null" in error_msg

    def test_validation_collects_all_errors(self, sorter):
        """Test that all validation errors are collected before failing."""
        sorter = ComponentSorterService()
        components = [
            {
                "name": "comp1",
                "workspace": "test",
                "context": "prod",
                "priority": 1,
                "config": {"dependencies": []},
            },
            {
                "name": "comp2",
                "workspace": "test",
                "context": "prod",
                "priority": 1,  # Duplicate priority (error 1)
                "config": {"dependencies": []},
            },
            {
                "name": "comp3",
                "workspace": "test",
                "context": "prod",
                "priority": 2,
                "config": {
                    "dependencies": [{"name": "comp4"}]
                },  # Priority conflict (error 2)
            },
            {
                "name": "comp4",
                "workspace": "test",
                "context": "prod",
                "priority": 5,
                "config": {"dependencies": []},
            },
        ]

        with pytest.raises(ComponentValidationError) as exc_info:
            sorter.sort_entities(components, "component")

        error_msg = str(exc_info.value)
        # Should contain BOTH errors
        assert "Duplicate priority values" in error_msg
        assert "Priority conflict" in error_msg

    def test_priority_ordering_rule(self, sorter):
        """Test that components are sorted in strict priority order: 0 → 1 → 2 → ... → null."""
        sorter = ComponentSorterService()
        components = [
            {"name": "comp_null", "workspace": "", "context": "", "priority": None},
            {"name": "comp5", "workspace": "", "context": "", "priority": 5},
            {"name": "comp0", "workspace": "", "context": "", "priority": 0},
            {"name": "comp2", "workspace": "", "context": "", "priority": 2},
        ]

        result = sorter.sort_entities(components, "component")
        names = [c["name"] for c in result]

        # Should be ordered: 0 → 2 → 5 → null
        assert names == ["comp0", "comp2", "comp5", "comp_null"]

    def test_skip_validation_bypasses_all_rules(self, sorter):
        """Test that skip_validation=True bypasses all validation rules.

        This is critical for detect-changes to work with invalid base branch configs.
        """
        sorter = ComponentSorterService()

        # Create components that violate multiple validation rules
        invalid_components = [
            {
                "name": "comp1",
                "workspace": "test",
                "context": "prod",
                "priority": 1,
                "config": {"dependencies": []},
            },
            {
                "name": "comp2",
                "workspace": "test",
                "context": "prod",
                "priority": 1,  # Duplicate priority - normally fails
                "config": {"dependencies": []},
            },
            {
                "name": "comp3",
                "workspace": "test",
                "context": "prod",
                "priority": 2,
                "config": {"dependencies": [{"name": "comp4"}]},  # Priority conflict
            },
            {
                "name": "comp4",
                "workspace": "test",
                "context": "prod",
                "priority": 5,
                "config": {"dependencies": []},
            },
        ]

        # Should fail without skip_validation
        with pytest.raises(ComponentValidationError) as exc:
            sorter.sort_entities(invalid_components, "component", skip_validation=False)
        assert "Duplicate priority" in str(exc.value)

        # Should succeed with skip_validation=True
        result = sorter.sort_entities(
            invalid_components, "component", skip_validation=True
        )
        assert len(result) == 4
        # Components should still be sorted by priority and name
        names = [c["name"] for c in result]
        assert names == ["comp1", "comp2", "comp3", "comp4"]


class TestComponentSorterIntegration:
    """Integration tests for ComponentSorterService with real-world scenarios."""

    def test_simple_microservices_architecture(self, sorter):
        """Test sorting a simple microservices architecture with strict priority ordering."""
        sorter = ComponentSorterService()

        components = [
            # Different contexts, ordered by priority within each
            {
                "name": "web-ui",
                "workspace": "prod",
                "context": "frontend",
                "priority": 10,
                "config": {"dependencies": []},
            },
            {
                "name": "api-gateway",
                "workspace": "prod",
                "context": "api",
                "priority": 20,
                "config": {"dependencies": []},
            },
            {
                "name": "auth-service",
                "workspace": "prod",
                "context": "services",
                "priority": 30,
                "config": {"dependencies": []},
            },
            {
                "name": "user-service",
                "workspace": "prod",
                "context": "services",
                "priority": 31,
                "config": {"dependencies": []},
            },
        ]

        result = sorter.sort_entities(components, "component")
        names = [c["name"] for c in result]

        # Components ordered by context (alphabetically), then priority
        # api < frontend < services (alphabetical)
        # Within services: 30 < 31
        assert names == ["api-gateway", "web-ui", "auth-service", "user-service"]
