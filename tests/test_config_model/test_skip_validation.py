"""Test skip_validation behavior for backward compatibility."""

import pytest

from coregen.config_model.models.components import (
    Component,
    ComponentConfig,
    ComponentDependency,
)
from coregen.config_model.models.context import Context
from coregen.config_model.processor import ConfigProcessor


class TestSkipValidation:
    """Test that skip_validation properly bypasses Pydantic validation."""

    def test_skip_validation_allows_old_field_names(self):
        """Test that old field names like 'generated' are allowed with skip_validation=True."""
        processor = ConfigProcessor(skip_validation=True)

        # Component with old field name that would normally fail validation
        comp_dict = {
            "name": "test-component",
            "config": {
                "generated": True,  # Old field name (now called for_commit)
                "active": True,
                "priority": 0,
            },
        }

        # Should not raise validation error
        component = processor._process_component(comp_dict, "test-context")

        assert component.name == "test-component"
        assert component.config.active is True
        assert component.config.priority == 0

    def test_normal_validation_rejects_old_field_names(self):
        """Test that old field names are rejected with normal validation."""
        processor = ConfigProcessor(skip_validation=False)

        # Component with old field name
        comp_dict = {
            "name": "test-component",
            "config": {
                "generated": True,  # Old field name should fail
                "active": True,
                "priority": 0,
            },
        }

        # Should raise validation error
        with pytest.raises(
            ValueError, match="Extra inputs are not permitted|generated"
        ):
            processor._process_component(comp_dict, "test-context")

    def test_skip_validation_allows_invalid_priority_dependency_combo(self):
        """Test that invalid combinations are allowed with skip_validation=True."""
        processor = ConfigProcessor(skip_validation=True)

        # Component with priority 0 AND dependencies (normally invalid)
        comp_dict = {
            "name": "test-component",
            "config": {
                "active": True,
                "priority": 0,
                "dependencies": [{"name": "dep1"}],  # Not allowed for priority 0
            },
        }

        # Should not raise validation error when skipping
        component = processor._process_component(comp_dict, "test-context")

        assert component.name == "test-component"
        assert component.config.priority == 0
        assert len(component.config.dependencies) == 1

    def test_normal_validation_rejects_invalid_priority_dependency_combo(self):
        """Test that invalid combinations are rejected with normal validation."""
        processor = ConfigProcessor(skip_validation=False)

        # Component with priority 0 AND dependencies (invalid)
        comp_dict = {
            "name": "test-component",
            "config": {
                "active": True,
                "priority": 0,
                "dependencies": [{"name": "dep1"}],
            },
        }

        # Should raise validation error
        with pytest.raises(
            ValueError, match="Priority 0 component cannot have dependencies"
        ):
            processor._process_component(comp_dict, "test-context")

    def test_skip_validation_uses_model_construct(self):
        """Test that skip_validation actually uses model_construct."""
        processor = ConfigProcessor(skip_validation=True)

        # Component with multiple unknown fields
        comp_dict = {
            "name": "test-component",
            "config": {
                "generated": True,  # Old field
                "some_other_old_field": "value",  # Another unknown field
                "active": True,
            },
        }

        # Should construct without validation
        component = processor._process_component(comp_dict, "test-context")

        assert component.name == "test-component"
        assert isinstance(component, Component)

    def test_current_field_names_work_in_both_modes(self):
        """Test that current field names work with both validation modes."""
        comp_dict = {
            "name": "test-component",
            "config": {
                "for_commit": True,  # New field name
                "active": True,
                "priority": 2,
            },
        }

        # Should work with skip_validation=True
        processor_skip = ConfigProcessor(skip_validation=True)
        component_skip = processor_skip._process_component(comp_dict, "test-context")
        assert component_skip.name == "test-component"

        # Should also work with normal validation
        processor_normal = ConfigProcessor(skip_validation=False)
        component_normal = processor_normal._process_component(
            comp_dict.copy(), "test-context"
        )
        assert component_normal.name == "test-component"

    def test_skip_validation_with_dependencies(self):
        """Test that dependencies are properly handled with skip_validation=True."""
        processor = ConfigProcessor(skip_validation=True)

        # Component with dependencies (including old field names and invalid paths)
        comp_dict = {
            "name": "test-component",
            "config": {
                "active": True,
                "priority": 2,
                "dependencies": [
                    {"name": "dep1", "path": "/nonexistent/path"},  # Invalid path
                    {"name": "dep2"},  # No path
                ],
            },
        }

        # Should not raise validation error
        component = processor._process_component(comp_dict, "test-context")

        assert component.name == "test-component"
        assert len(component.config.dependencies) == 2

        # get_dependencies() should work (called by detect-changes)
        deps = component.get_dependencies()
        assert len(deps) == 2
        assert deps[0]["name"] == "dep1"
        assert deps[1]["name"] == "dep2"

    def test_skip_validation_skips_context_dependency_validation(self):
        """Test that Context dependency validation is skipped with skip_validation=True."""
        # Create components where one depends on a missing component
        # This would normally fail validation

        # Create component A that depends on component B (which doesn't exist)
        dep = ComponentDependency.model_construct(name="component-b")
        config_a = ComponentConfig.model_construct(
            active=True, priority=2, dependencies=[dep]
        )
        component_a = Component.model_construct(name="component-a", config=config_a)

        # Create context with skip_validation=True
        # This should NOT raise error about missing dependency
        context = Context(
            name="test-context",
            environment="test",
            components={
                "app": {
                    "component-a": component_a,
                }
            },
            skip_validation=True,
        )

        assert context.name == "test-context"
        assert "component-a" in context.components["app"]

    def test_normal_validation_catches_missing_dependencies(self):
        """Dependency validation catches missing dependencies post-attachment.

        Mirrors the production flow: the processor runs
        _validate_component_dependencies after attaching components (the
        model's after-validator no longer runs it against a partial set).
        """
        # Create component A that depends on component B (which doesn't exist)
        dep = ComponentDependency(name="component-b")
        config_a = ComponentConfig(active=True, priority=2, dependencies=[dep])
        component_a = Component(name="component-a", config=config_a)

        context = Context(
            name="test-context",
            environment="test",
            components={
                "app": {
                    "component-a": component_a,
                }
            },
            skip_validation=False,
        )

        with pytest.raises(
            ValueError, match="depends on missing component 'component-b'"
        ):
            context._validate_component_dependencies()

    def test_skip_validation_coerces_priority_strings(self):
        """Test that quoted priority strings are properly coerced to integers."""
        processor = ConfigProcessor(skip_validation=True)

        # Component with string priority (common in YAML with quotes)
        comp_dict = {
            "name": "test-component",
            "config": {
                "priority": "5",  # String from YAML
                "active": True,
            },
        }

        component = processor._process_component(comp_dict, "test-context")

        # Priority should be coerced to int
        assert component.config.priority == 5
        assert isinstance(component.config.priority, int)

    def test_skip_validation_coerces_boolean_strings(self):
        """Test that string booleans are coerced properly."""
        processor = ConfigProcessor(skip_validation=True)

        # Component with string boolean values (common in YAML with quotes)
        comp_dict = {
            "name": "test-component",
            "config": {
                "priority": 0,
                "active": "true",  # String from YAML
                "required": "false",  # String from YAML
                "for_commit": "yes",  # String from YAML
            },
        }

        component = processor._process_component(comp_dict, "test-context")

        # Booleans should be coerced from strings
        assert component.config.active is True
        assert component.config.required is False
        assert component.config.for_commit is True
        assert isinstance(component.config.active, bool)
        assert isinstance(component.config.required, bool)
        assert isinstance(component.config.for_commit, bool)

    def test_skip_validation_handles_invalid_priority(self):
        """Test that invalid priority values are coerced to None."""
        processor = ConfigProcessor(skip_validation=True)

        # Component with invalid priority
        comp_dict = {
            "name": "test-component",
            "config": {
                "priority": "invalid",  # Invalid string
                "active": True,
            },
        }

        component = processor._process_component(comp_dict, "test-context")

        # Invalid priority should be coerced to None
        assert component.config.priority is None

    def test_skip_validation_handles_negative_priority(self):
        """Test that negative priority values are coerced to None."""
        processor = ConfigProcessor(skip_validation=True)

        # Component with negative priority
        comp_dict = {
            "name": "test-component",
            "config": {
                "priority": "-5",  # Negative number as string
                "active": True,
            },
        }

        component = processor._process_component(comp_dict, "test-context")

        # Negative priority should be coerced to None
        assert component.config.priority is None
