"""
Configuration validation utilities.

Contains validation logic that's shared across multiple models to avoid circular imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Import get_settings directly to avoid circular imports
from coregen.config_model.models.settings import get_settings

# Forward references to avoid circular imports
if TYPE_CHECKING:
    from coregen.config_model.models.components import ComponentConfig


class ModelValidator:
    @classmethod
    def validate_priority(cls, priority: Any) -> None:
        """Validate component priority.

        Priority can be:
        - None (default, no priority)
        - A non-negative integer (0 or greater)

        Args:
            priority: The priority value to validate

        Raises:
            ValueError: If priority is invalid
        """
        if priority is None:
            return  # Allow None values as documented

        try:
            priority_int = int(priority)  # Convert to int if string
            if priority_int < 0:
                raise ValueError("Priority must be a non-negative integer")
        except (ValueError, TypeError) as exc:
            raise ValueError("Priority must be None or a non-negative integer") from exc

    @classmethod
    def validate_component_config(cls, config: ComponentConfig) -> None:
        """Validate component configuration settings.

        Args:
            config: The component configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        if config.for_commit and not config.active:
            raise ValueError("Components for commit must be active")

        cls.validate_priority(config.priority)

    @classmethod
    def validate_extra_fields(
        cls, model_data: dict[str, Any], model_fields: set[str]
    ) -> None:
        """Validate extra fields in a model against allowed types."""
        # Get allowed types from settings directly
        settings = get_settings()
        # Use settings directly instead of creating an unused variable
        allowed_types = settings.system.allowed_extra_field_types

        # Validate each extra field's type
        extra_fields = {k: v for k, v in model_data.items() if k not in model_fields}
        for key, value in extra_fields.items():
            value_type = type(value).__name__
            if value_type not in allowed_types:
                raise ValueError(
                    f"Extra field '{key}' with type '{value_type}' must be one of: "
                    f"{', '.join(allowed_types)}"
                )
