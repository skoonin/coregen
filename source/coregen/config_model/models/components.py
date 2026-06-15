"""Component configuration models."""

from __future__ import annotations

import functools
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from coregen.config_model.models.settings import get_settings
from coregen.config_model.models.validation import ModelValidator

# Get settings once at module level
settings = get_settings()


class ComponentDependency(BaseModel):
    """Component dependency definition."""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str, Field(..., description="Required: Name of the dependency component")
    ]
    path: Annotated[
        str | None,
        Field(None, description="Optional: Custom path to the dependency"),
    ]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not empty."""
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str | None) -> str | None:
        """Validate path syntax only.

        Existence is intentionally NOT checked here: dependency paths are
        relative to the context directory, which is resolved after model
        construction, so a filesystem check at validation time runs against
        the CWD and rejects valid configs.
        """
        if v is not None and not v.strip():
            raise ValueError("path cannot be empty")
        return v


class ComponentConfig(BaseModel):
    """Component configuration settings.

    A component configuration defines how a component should be processed,
    including whether it's active, required, for_commit, and its dependencies.

    Priority ordering: 0 (highest) -> 1 -> 2 -> ... -> None (lowest)
    Components with priority 0 or 1 are considered "early deployment"
    and cannot have dependencies.
    """

    model_config = ConfigDict(extra="forbid")

    # Processing flags - access settings directly
    active: Annotated[
        bool,
        Field(
            default_factory=lambda: settings.component.active,
            description="Whether this component should be processed",
        ),
    ]
    required: Annotated[
        bool,
        Field(
            default_factory=lambda: settings.component.required,
            description="If true, component will be included in all other components generation",
        ),
    ]
    for_commit: Annotated[
        bool,
        Field(
            default_factory=lambda: settings.component.for_commit,
            description="If true, component's files will be copied to the context's commit_dir during generation",
        ),
    ]

    # Path and processing configuration
    priority: Annotated[
        int | None,
        Field(
            default_factory=lambda: settings.component.priority,
            description="Processing priority (0 is highest, None for no priority)",
        ),
    ]
    path: Annotated[
        str | None, Field(default=None, description="Optional custom template path")
    ]
    dependencies: Annotated[
        list[ComponentDependency],
        Field(
            default_factory=list, description="Optional list of component dependencies"
        ),
    ]

    @model_validator(mode="after")
    def validate_component_config(self) -> ComponentConfig:
        """Validate component configuration rules.

        Rules:
        1. Priority must be a non-negative integer or None
        2. Components with high priority (0 or 1) should not have dependencies
        """

        if self.priority is not None and self.priority < 0:
            raise ValueError("Priority must be a non-negative integer or None")

        # Check for priority/dependency conflicts
        # Priority 0 or 1 means "deploy early" which conflicts with having dependencies
        EARLY_DEPLOYMENT_PRIORITY_THRESHOLD = 1

        if (
            self.priority is not None
            and self.priority <= EARLY_DEPLOYMENT_PRIORITY_THRESHOLD
            and self.dependencies
        ):
            raise ValueError(
                f"Priority {self.priority} component cannot have dependencies"
            )

        return self


@functools.total_ordering
class Component(BaseModel):
    """Component definition with config and extra fields.

    A component represents a unit of configuration or code that can be
    processed by the system. Components can have dependencies on other
    components and can be generated into output files.

    Components support additional custom key-value pairs beyond the standard fields,
    allowing users to add their own metadata that can be accessed in templates.

    Components are naturally sortable using comparison operators.
    """

    model_config = ConfigDict(extra="allow")

    # Required fields
    name: Annotated[
        str, Field(..., description="Required: Component name", min_length=1)
    ]
    config: Annotated[
        ComponentConfig,
        Field(default_factory=ComponentConfig, description="Component configuration"),
    ]

    # Runtime context fields (populated by ConfigAccess)
    environment: str | None = Field(
        default=None, description="Environment from parent context"
    )
    workspace: str | None = Field(default=None, description="Workspace name")
    context: str | None = Field(default=None, description="Parent context name")

    @field_validator("config", mode="before")
    @classmethod
    def validate_extra_fields(cls, data: Any) -> Any:
        """Validate that extra fields have allowed types.

        Args:
            data: The config data to validate

        Returns:
            Validated data
        """
        # Only validate extra fields if data is a dictionary
        # ComponentConfig objects don't have extra fields to validate
        if isinstance(data, dict):
            # Dynamically retrieve the field names from the ComponentConfig model
            # This ensures we stay in sync if ComponentConfig fields change
            config_model_fields = set(ComponentConfig.model_fields.keys())

            # Use the centralized validator
            ModelValidator.validate_extra_fields(data, config_model_fields)

        return data

    def get_dependencies(self) -> list[dict[str, str]]:
        """Get component dependencies as a list of dictionaries.

        Returns:
            List of dependency dictionaries with at minimum a 'name' key
        """
        # Access dependencies directly from the config object
        return [
            {
                k: v
                for k, v in dep.model_dump(exclude_defaults=False).items()
                if v is not None
            }
            for dep in self.config.dependencies
        ]

    def sort_key(self) -> tuple[str, bool, int, str]:
        """Return sort key for natural ordering.

        Components are sorted by:
        1. Context (the real field; empty string when unset)
        2. Priority (0 is highest; null priority sorts last via the is-None flag)
        3. Component name (for stable ordering)

        Returns:
            Tuple for sorting
        """
        priority = self.config.priority
        return (
            self.context or "",
            priority is None,
            priority if priority is not None else 0,
            self.name,
        )

    def __lt__(self, other: object) -> bool:
        """Compare components for natural ordering.

        Args:
            other: Another component to compare with

        Returns:
            True if this component should come before other
        """
        if not isinstance(other, Component):
            return NotImplemented
        return self.sort_key() < other.sort_key()

    def __eq__(self, other: object) -> bool:
        """Check equality on the same identity as ordering.

        Uses (context, name) so equality stays consistent with sort_key under
        @total_ordering: two same-named components in different contexts are
        distinct rather than equal.

        Args:
            other: Another object to compare with

        Returns:
            True if components share the same context and name
        """
        if not isinstance(other, Component):
            return NotImplemented
        return (self.context, self.name) == (other.context, other.name)
