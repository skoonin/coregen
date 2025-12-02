"""Tests for config.models.context module."""

import pytest
from pydantic import ValidationError

from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context


class TestContext:
    """Tests for Context model."""

    def test_create_context(self):
        """Should create a context with valid data."""
        context = Context(name="test-context", environment="dev")
        assert context.name == "test-context"
        assert context.environment == "dev"
        assert context.active is False  # default value
        assert context.commit_dir == "for-commit"  # default value

    def test_create_context_with_custom_values(self):
        """Should create a context with custom values."""
        context = Context(
            name="test-context",
            environment="prod",
            active=True,
            commit_dir="gen-files",
            component_type="service",
        )
        assert context.name == "test-context"
        assert context.environment == "prod"
        assert context.active is True
        assert context.commit_dir == "gen-files"
        assert context.component_type == "service"

    def test_create_with_custom_fields(self):
        """Should allow custom fields."""
        context = Context(
            name="test-context", environment="dev", custom_field="custom-value"
        )
        assert context.name == "test-context"
        assert context.custom_field == "custom-value"

    def test_empty_name_raises_error(self):
        """Should raise error when name is empty."""
        with pytest.raises(ValidationError):
            Context(name="", environment="dev")

    def test_active_context_needs_active_component(self):
        """
        Should raise error when context is active but has no active components.
        This only applies when components exist and context is not in bypass_validation mode.
        """
        # Create context with inactive component
        with pytest.raises(ValidationError) as exc:
            Context(
                name="test-context",
                environment="dev",
                active=True,
                components={
                    "component": {
                        "test-component": Component(
                            name="test-component", config={"active": False}
                        )
                    }
                },
            )

        assert "Active context must have at least one active component" in str(
            exc.value
        )

    def test_skip_validation_allows_active_context_without_active_component(self):
        """Should allow active context without active components when skip_validation is True."""
        context = Context(
            name="test-context",
            environment="dev",
            active=True,
            skip_validation=True,
            components={
                "component": {
                    "test-component": Component(
                        name="test-component", config={"active": False}
                    )
                }
            },
        )
        # This should not raise an exception
        assert context.active is True

    def test_get_all_components(self):
        """Should return all components from all component types as a flattened dictionary."""
        context = Context(
            name="test-context",
            environment="dev",
            components={
                "service": {
                    "service1": Component(name="service1"),
                    "service2": Component(name="service2"),
                },
                "app": {"app1": Component(name="app1")},
            },
        )

        all_components = context.get_all_components()
        assert len(all_components) == 3
        assert "service1" in all_components
        assert "service2" in all_components
        assert "app1" in all_components

    def test_path_property(self):
        """Should expose internal_path via path property."""
        context = Context(name="test-context", environment="dev")
        # Initial path should be empty
        assert context.path == ""

        # Set internal path
        context.set_internal_path("/test/path")
        assert context.path == "/test/path"
        assert context.internal_path == "/test/path"

    def test_path_property_returns_internal_path(self):
        """Path property returns internal_path value."""
        # Path is a read-only property that returns internal_path
        context = Context(
            name="test-context",
            environment="dev",
        )
        # Initially internal_path is empty
        assert context.path == ""  # Property returns internal_path
        assert context.internal_path == ""

        # Set internal_path
        context.set_internal_path("/test/path")
        assert context.path == "/test/path"  # Property returns internal_path
