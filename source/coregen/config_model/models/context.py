"""
Context models for Coregen.

Defines the models for contexts and their configurations, including:
- Context: Context configuration with environment property and components
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from coregen.config_model.component_ordering import order_components
from coregen.config_model.models.components import Component
from coregen.config_model.models.settings import get_settings
from coregen.config_model.models.validation import ModelValidator

# Get settings once at module level
settings = get_settings()


class Context(BaseModel):
    """Context configuration model.

    A context represents a specific deployment target or configuration set.
    For example, a context could be a specific Kubernetes cluster or a
    specific AWS account.

    Contexts house our context's environment and contains components.
    """

    model_config = ConfigDict(extra="allow")

    # Required fields
    name: Annotated[str, Field(..., description="Required: Context name")]
    environment: Annotated[
        str | None,
        Field(
            default_factory=lambda: settings.context.environment,
            description="Context's environment. Defaults to the value in settings.",
        ),
    ]

    # Processing flags
    active: Annotated[
        bool,
        Field(
            default_factory=lambda: settings.context.active,
            description="Whether this context should be processed",
        ),
    ]

    # Workspace relationship
    workspace: Annotated[
        str | None,
        Field(
            default=None,
            description="Name of the parent workspace this context belongs to",
        ),
    ]

    # Inheritable fields from workspace (optional - will be inherited if not set)
    archive_dir: Annotated[
        str | None,
        Field(
            default=None,
            description="Archive directory path (inherited from workspace if not set)",
        ),
    ]
    output_dir: Annotated[
        str | None,
        Field(
            default=None,
            description="Output directory path (inherited from workspace if not set)",
        ),
    ]

    # Path is internally set by the PathService
    internal_path: Annotated[
        str,
        Field(
            default="",
            description="Path to context directory (INTERNAL USE ONLY - set dynamically)",
            exclude=True,  # Exclude from serialization
        ),
    ]

    # Optional fields with defaults
    commit_dir: Annotated[
        str,
        Field(
            default_factory=lambda: settings.context.commit_dir,
            description="Directory for commit files, defaults to 'for-commit'",
        ),
    ]
    component_type: Annotated[
        str,
        Field(
            default_factory=lambda: settings.context.component_type,
            description="Type name for components in this context",
        ),
    ]

    # Content collections - supports nested dictionary structure
    # components: { component_type: { component_name: component } }
    components: Annotated[
        dict[str, dict[str, Component]],
        Field(
            default_factory=dict,
            description="Dictionary of component types to dictionaries of components (component_type -> component_name -> Component)",
        ),
    ]

    # Flag to skip validation
    # (used by detect-changes for base branch)
    skip_validation: Annotated[
        bool,
        Field(
            default=False,
            description="Internal flag to skip validation rules",
            exclude=True,
        ),
    ]

    # Internal workspace reference for field inheritance
    workspace_ref: Annotated[
        Any | None,
        Field(
            default=None,
            description="Internal reference to parent workspace for field inheritance",
            exclude=True,
        ),
    ]

    # Cached deployment-ordered components; invalidated when components change.
    _sorted_components_cache: dict[str, Component] | None = PrivateAttr(default=None)

    def __setattr__(self, name: str, value: Any) -> None:
        """Invalidate the ordered-component cache when components is reassigned."""
        if name == "components":
            self._sorted_components_cache = None
        super().__setattr__(name, value)

    @field_validator("component_type")
    @classmethod
    def validate_component_type(cls, v: str) -> str:
        """Validate that component_type does not use reserved keywords."""
        if v == "components":
            raise ValueError(
                "'components' is a reserved keyword and cannot be used as component_type. "
                "Please choose a different name for your component type."
            )
        return v

    @model_validator(mode="before")
    @classmethod
    def validate_extra_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Validate that extra fields have allowed types."""
        model_fields = {
            "name",
            "environment",
            "active",
            "archive_dir",
            "output_dir",
            "commit_dir",
            "component_type",
            "components",
            "skip_validation",
            "internal_path",
            "workspace_ref",
        }
        ModelValidator.validate_extra_fields(data, model_fields)
        return data

    @model_validator(mode="after")
    def validate_context(self) -> Context:
        """Validate context configuration.

        This validator ensures that:
        1. The context has a valid name
        2. The context has a valid environment
        3. Default values are set for optional fields if not provided
        4. Active contexts have at least one active component (except during testing)

        Note: Path resolution is now handled by the PathService, not in the model.
        """
        # Validate name (simple validation only, path resolution handled elsewhere)
        if not self.name:
            raise ValueError("Context name cannot be empty")

        # Validate path - strictly prevent external path setting
        # Note: This check is conceptual - actual path validation is handled elsewhere
        # if "path" in getattr(self, 'model_fields_set', set()):
        #     raise ValueError(
        #         "Context path cannot be set directly. It is determined automatically by the system."
        #     )

        # Validate active context requirements - unless we're in test mode
        if self.active and not self.skip_validation:
            # Check if we have any components
            active_components = []

            # Check all component types
            components_dict = (
                self.components if isinstance(self.components, dict) else {}
            )

            # Validate component names are unique across all component types within this context
            all_component_names = set()
            for component_type, component_type_dict in components_dict.items():
                if isinstance(component_type_dict, dict):
                    for component_name, component in component_type_dict.items():
                        if component_name in all_component_names:
                            raise ValueError(
                                f"Duplicate component name '{component_name}' found in context '{self.name}'. "
                                "Component names must be unique across all component types within a context."
                            )
                        all_component_names.add(component_name)

            # Check active components
            for component_type, component_type_dict in components_dict.items():
                if isinstance(component_type_dict, dict):
                    for component_name, component in component_type_dict.items():
                        if (
                            hasattr(component, "config")
                            and hasattr(component.config, "active")
                            and component.config.active
                        ):
                            active_components.append(component)

            if not active_components:
                # During initialization we might not have components yet
                # But during normal operation (not testing), this would be an error
                if any(
                    component_type_dict
                    for component_type_dict in components_dict.values()
                ):  # Only check if we actually have components
                    raise ValueError(
                        "Active context must have at least one active component"
                    )

        # Dependency validation runs in the processor once components are
        # attached (processor attaches them after construction, so a run here
        # would only ever see a partial component set)
        return self

    def _validate_component_dependencies(self) -> None:
        """Validate that active components do not depend on inactive components.

        This validation ensures configuration consistency by checking that all
        dependencies of active components are also active. An active component
        should never depend on an inactive component as this would create an
        invalid state during generation.

        Raises:
            ValueError: If an active component depends on an inactive component
        """
        # Build a map of all components and their active status
        component_status = {}

        # Get all components using the helper method
        all_components = self.get_all_components()
        for comp_name, component in all_components.items():
            if hasattr(component, "config"):
                component_status[comp_name] = getattr(component.config, "active", True)

        # Check each active component's dependencies
        for comp_name, component in all_components.items():
            if not hasattr(component, "config"):
                continue

            # Only check dependencies for active components
            if not getattr(component.config, "active", True):
                continue

            # Check if component has dependencies
            if not hasattr(component.config, "dependencies"):
                continue

            dependencies = component.config.dependencies or []

            # Validate each dependency
            for dep in dependencies:
                dep_name = dep.name
                if not dep_name:
                    continue

                # Check if dependency exists and is inactive
                if dep_name in component_status and not component_status[dep_name]:
                    raise ValueError(
                        f"Configuration Error: Active component '{comp_name}' "
                        f"in context '{self.name}' depends on inactive "
                        f"component '{dep_name}'. An active component cannot "
                        f"have inactive dependencies. Either make '{dep_name}' "
                        f"active or remove it from the dependencies of '{comp_name}'."
                    )

                # Check if dependency is missing entirely
                if dep_name not in component_status:
                    raise ValueError(
                        f"Component '{comp_name}' depends on missing component '{dep_name}'"
                    )

    def inherit_workspace_fields(self) -> Context:
        """Inherit fields from workspace if not set.

        This validator runs after the context is created and handles:
        1. archive_dir and output_dir inheritance from workspace
        2. Custom field inheritance from workspace model_extra
        """
        if self.workspace_ref is not None:
            # Inherit archive_dir if not set
            if self.archive_dir is None and hasattr(self.workspace_ref, "archive_dir"):
                self.archive_dir = self.workspace_ref.archive_dir

            # Inherit output_dir if not set
            if self.output_dir is None and hasattr(self.workspace_ref, "output_dir"):
                self.output_dir = self.workspace_ref.output_dir

            # Inherit custom fields from workspace
            if (
                hasattr(self.workspace_ref, "model_extra")
                and self.workspace_ref.model_extra
            ):
                for key, value in self.workspace_ref.model_extra.items():
                    # Only inherit if not already set in context
                    if not hasattr(self, key) or getattr(self, key) is None:
                        # Set field directly since ConfigDict(extra="allow") handles this
                        setattr(self, key, value)

        return self

    def get_all_components(self) -> dict[str, Component]:
        """Get all components from all component types as a flattened dictionary.

        Components are returned in deployment order:
        1. By priority (0 highest, then 1, 2, 3... None lowest)
        2. Dependencies come before dependents
        3. Alphabetically by name for equal priority

        Components are immutable after config processing, so the ordered result
        is memoized on first access and reused thereafter. The cache is cleared
        whenever ``components`` is reassigned (see ``__setattr__``).
        """
        if self._sorted_components_cache is None:
            self._sorted_components_cache = order_components(
                self.components,
                context_name=self.name,
                workspace=self.workspace or "",
                skip_validation=self.skip_validation,
            )
        return self._sorted_components_cache

    @property
    def path(self) -> str:
        """Read-only property to get the context path."""
        return self.internal_path

    def set_internal_path(self, path: str) -> None:
        """Internal method to set the path. Should only be called by PathService."""
        self.internal_path = path
