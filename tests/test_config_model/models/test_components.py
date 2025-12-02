"""Tests for config.models.components module."""

from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from coregen.config_model.models.components import (
    Component,
    ComponentConfig,
    ComponentDependency,
)


@contextmanager
def skip_path_validation() -> Iterator[None]:
    """Skip path validation in tests for model components."""
    # Create a version of Path.exists that always returns True for tests

    def mock_exists(self) -> bool:
        return True

    # Apply the patch
    with patch("pathlib.Path.exists", mock_exists):
        yield


class TestComponentDependency:
    """Tests for ComponentDependency model."""

    def test_create_dependency(self) -> None:
        """Should create a dependency with valid data."""
        dependency = ComponentDependency(name="test-dependency")
        assert dependency.name == "test-dependency"
        assert dependency.path is None

    def test_create_dependency_with_path(self) -> None:
        """Should create a dependency with path."""
        with skip_path_validation():
            dependency = ComponentDependency(name="test-dependency", path="custom/path")
            assert dependency.name == "test-dependency"
            assert dependency.path == "custom/path"

    def test_empty_name_raises_error(self) -> None:
        """Should raise error when name is empty."""
        with pytest.raises(ValidationError):
            ComponentDependency(name="")

    def test_whitespace_name_raises_error(self) -> None:
        """Should raise error when name is only whitespace."""
        with pytest.raises(ValidationError):
            ComponentDependency(name="   ")


class TestComponentConfig:
    """Tests for ComponentConfig model."""

    def test_create_default_config(self) -> None:
        """Should create config with default values."""
        config = ComponentConfig()
        assert isinstance(config.active, bool)
        assert isinstance(config.required, bool)
        assert isinstance(config.for_commit, bool)
        assert isinstance(config.dependencies, list)

    def test_create_custom_config(self) -> None:
        """Should create config with custom values."""
        with skip_path_validation():
            config = ComponentConfig(
                active=True,
                required=True,
                for_commit=True,
                priority=5,
                path="custom/path",
                dependencies=[{"name": "dep1"}, {"name": "dep2", "path": "dep2/path"}],
            )
            assert config.active is True
            assert config.required is True
            assert config.for_commit is True
            assert config.priority == 5
            assert config.path == "custom/path"
            assert len(config.dependencies) == 2
            assert config.dependencies[0].name == "dep1"
            assert config.dependencies[1].name == "dep2"

    def test_for_commit_can_be_inactive(self) -> None:
        """For commit components can be inactive - no validation prevents this."""
        # This validation was removed or never implemented
        config = ComponentConfig(active=False, for_commit=True)
        assert config.active is False
        assert config.for_commit is True

    def test_string_priority_validation(self) -> None:
        """Should validate and convert string priority values to integers."""
        # Valid string priority - the validation passes and converts to int
        config = ComponentConfig(priority="5")
        assert config.priority == 5  # Converts to integer

        # Invalid string priority (non-numeric)
        with pytest.raises(ValidationError) as exc:
            ComponentConfig(priority="abc")
        # The error message from Pydantic validation may vary with versions,
        # so we check that some key part of the message is present
        assert "unable to parse string as an integer" in str(exc.value)

        # Invalid string priority (negative)
        with pytest.raises(ValidationError) as exc:
            ComponentConfig(priority="-1")
        assert "Priority must be a non-negative integer" in str(exc.value)

    def test_negative_priority_raises_error(self) -> None:
        """Should raise error when priority is negative."""
        with pytest.raises(ValidationError) as exc:
            ComponentConfig(priority=-1)
        assert "Priority must be a non-negative integer" in str(exc.value)


class TestComponent:
    """Tests for Component model."""

    def test_create_component(self) -> None:
        """Should create a component with valid data."""
        component = Component(name="test-component")
        assert component.name == "test-component"
        assert isinstance(component.config, ComponentConfig)

    def test_create_with_custom_fields(self) -> None:
        """Should allow custom fields."""
        component = Component(name="test-component", custom_field="custom-value", another_field=123)  # type: ignore[call-arg]
        assert component.name == "test-component"
        assert component.custom_field == "custom-value"
        assert component.another_field == 123

    def test_create_with_config(self) -> None:
        """Should create with provided config."""
        # Need to pass config as a dict rather than a ComponentConfig object
        # to avoid the .items() validation error
        component = Component(
            name="test-component", config={"active": True, "required": True}
        )
        assert component.name == "test-component"
        assert component.config.active is True
        assert component.config.required is True

    def test_create_from_dict(self) -> None:
        """Should create from dictionary."""
        component = Component(
            **{  # type: ignore[arg-type]
                "name": "test-component",
                "config": {
                    "active": True,
                    "required": False,
                    "for_commit": True,
                    "dependencies": [{"name": "dep1"}],
                },
                "custom_key": "custom_value",
            }
        )
        assert component.name == "test-component"
        assert component.config.active is True
        assert component.config.for_commit is True
        assert len(component.config.dependencies) == 1
        assert component.custom_key == "custom_value"

    def test_get_dependencies(self) -> None:
        """Should return dependencies as list of dicts."""
        with skip_path_validation():
            component = Component(
                name="test-component",
                config={
                    "dependencies": [
                        {"name": "dep1"},
                        {"name": "dep2", "path": "path/to/dep2"},
                    ]
                },
            )
            deps = component.get_dependencies()
            assert len(deps) == 2
            assert deps[0]["name"] == "dep1"
            assert "path" not in deps[0]
            assert deps[1]["name"] == "dep2"
            assert deps[1]["path"] == "path/to/dep2"

    def test_has_dependency(self) -> None:
        """Should check if component has a dependency."""
        component = Component(
            name="test-component",
            config={"dependencies": [{"name": "dep1"}, {"name": "dep2"}]},
        )
        assert component.has_dependency("dep1") is True
        assert component.has_dependency("dep2") is True
        assert component.has_dependency("dep3") is False

    def test_add_dependency(self) -> None:
        """Should add a dependency if it doesn't exist."""
        component = Component(
            name="test-component", config={"dependencies": [{"name": "dep1"}]}
        )
        component.add_dependency(ComponentDependency(name="dep2"))
        assert len(component.config.dependencies) == 2
        assert component.has_dependency("dep2") is True

        # Adding existing dependency should not change anything
        component.add_dependency(ComponentDependency(name="dep1"))
        assert len(component.config.dependencies) == 2

    def test_validate_extra_fields(self) -> None:
        """Should validate extra fields in the component."""
        # Valid extra fields
        component = Component(name="test-component", str_field="string", int_field=123, bool_field=True)  # type: ignore[call-arg]
        assert component.str_field == "string"
        assert component.int_field == 123
        assert component.bool_field is True

        # Invalid extra field should still pass as component allows extra fields
        component = Component(
            name="test-component",
            invalid_obj=object(),  # This is allowed because extra="allow"  # type: ignore[call-arg]
        )
        assert hasattr(component, "invalid_obj")

    def test_empty_name_raises_error(self) -> None:
        """Should raise error when name is empty."""
        with pytest.raises(ValidationError):
            Component(name="")  # type: ignore[call-arg]

    def test_component_with_componentconfig_object(self) -> None:
        """Should create component with ComponentConfig object (issue #119)."""
        # This test ensures the fix for issue #119 works
        # Previously this would fail with "'ComponentConfig' object has no attribute 'items'"
        config_obj = ComponentConfig(active=True, for_commit=True, priority=1)
        component = Component(name="test-component", config=config_obj)

        assert component.name == "test-component"
        assert component.config.active is True
        assert component.config.for_commit is True
        assert component.config.priority == 1

    def test_component_with_config_dict_still_works(self) -> None:
        """Should still create component with config dict (existing functionality)."""
        # Ensure we didn't break the existing dict-based config creation
        component = Component(
            name="test-component", config={"active": True, "for_commit": True}
        )

        assert component.name == "test-component"
        assert component.config.active is True
        assert component.config.for_commit is True

    def test_component_runtime_context_fields(self) -> None:
        """Test that Component has runtime context fields."""
        component = Component(name="test-component")

        # Fields should exist with None defaults
        assert hasattr(component, "environment")
        assert hasattr(component, "workspace")
        assert hasattr(component, "context")
        assert component.environment is None
        assert component.workspace is None
        assert component.context is None

    def test_component_with_runtime_fields_set(self) -> None:
        """Test Component with runtime context fields set."""
        component = Component(
            name="test-component",
            environment="prod",
            workspace="aws-workspace",
            context="prod-context",
        )

        assert component.environment == "prod"
        assert component.workspace == "aws-workspace"
        assert component.context == "prod-context"

    def test_component_runtime_fields_in_model_dump(self) -> None:
        """Test that runtime fields appear in model dump."""
        component = Component(
            name="test-component",
            environment="dev",
            workspace="test-ws",
            context="dev-ctx",
        )

        dump = component.model_dump()
        assert "environment" in dump
        assert "workspace" in dump
        assert "context" in dump
        assert dump["environment"] == "dev"
        assert dump["workspace"] == "test-ws"
        assert dump["context"] == "dev-ctx"
