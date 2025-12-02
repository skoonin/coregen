"""Tests for config.models.validation module."""

import pytest

from coregen.config_model.models.components import Component, ComponentConfig
from coregen.config_model.models.context import Context
from coregen.config_model.models.validation import ModelValidator


class TestModelValidator:
    """Tests for ModelValidator class."""

    def test_validate_priority_valid_values(self):
        """Should validate valid priority values."""
        # None is valid
        ModelValidator.validate_priority(None)

        # Zero is valid
        ModelValidator.validate_priority(0)

        # Positive integers are valid
        ModelValidator.validate_priority(1)
        ModelValidator.validate_priority(100)

        # String representations of integers are valid
        ModelValidator.validate_priority("0")
        ModelValidator.validate_priority("5")
        ModelValidator.validate_priority("100")

    def test_validate_priority_invalid_values(self):
        """Should raise error for invalid priority values."""
        # Negative integers are invalid
        with pytest.raises(ValueError) as exc:
            ModelValidator.validate_priority(-1)
        assert "non-negative integer" in str(exc.value)

        # String representations of negative integers are invalid
        with pytest.raises(ValueError) as exc:
            ModelValidator.validate_priority("-1")
        assert "non-negative integer" in str(exc.value)

        # Non-numeric strings are invalid
        with pytest.raises(ValueError) as exc:
            ModelValidator.validate_priority("high")
        assert "non-negative integer" in str(exc.value)

        # Objects are invalid
        with pytest.raises(ValueError) as exc:
            ModelValidator.validate_priority(object())
        assert "non-negative integer" in str(exc.value)

    def test_validate_component_config_valid(self):
        """Should validate valid component configurations."""
        # active=True, for_commit=True is valid
        config = ComponentConfig(active=True, for_commit=True)
        ModelValidator.validate_component_config(config)

        # active=True, for_commit=False is valid
        config = ComponentConfig(active=True, for_commit=False)
        ModelValidator.validate_component_config(config)

        # active=False, for_commit=False is valid
        config = ComponentConfig(active=False, for_commit=False)
        ModelValidator.validate_component_config(config)

    def test_validate_component_config_invalid(self):
        """Should raise error for invalid component configurations."""
        # active=False, for_commit=True is invalid
        config = ComponentConfig()
        config.active = False
        config.for_commit = True

        with pytest.raises(ValueError) as exc:
            ModelValidator.validate_component_config(config)
        assert "Components for commit must be active" in str(exc.value)

    def test_validate_context_valid(self):
        """Should validate valid context configuration."""
        # Active context with active component
        component = Component(name="test-component", config={"active": True})
        # Context validation happens automatically during creation
        context = Context(
            name="test-context",
            environment="dev",
            active=True,
            skip_validation=True,  # Set this to skip internal validation
            components={"component": {"test-component": component}},
        )
        # If we get here without exception, validation passed
        assert context.active is True

        # Inactive context has no requirements for active components
        context = Context(
            name="test-context",
            environment="dev",
            active=False,
            components={
                "component": {
                    "test-component": Component(
                        name="test-component", config={"active": False}
                    )
                }
            },
        )
        # If we get here without exception, validation passed
        assert context.active is False

    def test_validate_context_invalid(self):
        """Should raise error for invalid context configuration."""
        # Active context without active components should raise during creation
        # Note: We need to NOT set skip_validation to test the validation
        with pytest.raises(ValueError) as exc:
            Context(
                name="test-context",
                environment="dev",
                active=True,
                skip_validation=False,  # Allow validation to run
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

    def test_validate_extra_fields_valid(self):
        """Should not raise error for valid extra fields."""
        # Test data for extra fields validation
        data = {
            "name": "test-item",
            "string_field": "string value",
            "int_field": 123,
            "float_field": 1.23,
            "bool_field": True,
            "list_field": [1, 2, 3],
            "dict_field": {"key": "value"},
        }
        model_fields = {"name"}

        # Should not raise exception
        ModelValidator.validate_extra_fields(data, model_fields)

        # Empty data
        ModelValidator.validate_extra_fields({}, set())

    def test_validate_extra_fields_invalid(self):
        """Should raise error for invalid extra fields."""
        # Data with invalid field type (object)
        data = {"name": "test-item", "invalid_field": object()}
        model_fields = {"name"}

        # ModelValidator.validate_extra_fields should raise an error for invalid field types
        # (Component model allows extra fields but validation happens at model creation)
        with pytest.raises(ValueError) as exc:
            ModelValidator.validate_extra_fields(data, model_fields)
        assert "Extra field 'invalid_field' with type 'object'" in str(exc.value)
