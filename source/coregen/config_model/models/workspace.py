"""
Workspace models for Coregen.

Defines the models for workspaces and their configurations, including:
- WorkspaceConfig: Main workspace configuration
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from coregen.config_model.models.context import Context
from coregen.config_model.models.settings import get_settings
from coregen.config_model.models.validation import ModelValidator

# Get settings once at module level
settings = get_settings()


class WorkspaceConfig(BaseModel):
    """Workspace configuration model.

    A workspace represents a logical grouping of contexts.
    For example, a workspace could represent a cloud provider (AWS, GCP)
    or a specific project.

    Workspaces are the top-level organizational unit in the configuration.
    """

    # we allow custom key/values
    model_config = ConfigDict(extra="allow")

    # Required fields, defaults pulled from settings
    name: Annotated[
        str,
        Field(
            default_factory=lambda: settings.workspace.workspace_name,
            description="Workspace name, defaults to workspace_name in settings",
        ),
    ]

    # Path configuration
    workspace_dir: Annotated[
        str,
        Field(
            default_factory=lambda: settings.workspace.workspace_dir,
            description="Directory name for this workspace (relative to root config file path)",
        ),
    ]
    archive_dir: Annotated[
        str,
        Field(
            default_factory=lambda: settings.workspace.archive_dir,
            description="Archive directory path (relative to root config file path)",
        ),
    ]
    output_dir: Annotated[
        str,
        Field(
            default_factory=lambda: settings.workspace.output_dir,
            description="Output directory path (relative to root config file path)",
        ),
    ]
    context_type: Annotated[
        str,
        Field(
            default_factory=lambda: settings.workspace.context_type,
            description="Type name for contexts in this workspace. Represents top key in context configs",
        ),
    ]
    context_config_files: Annotated[
        list[str],
        Field(
            default_factory=lambda: settings.workspace.context_config_files,
            description="File patterns for context discovery. Globs are supported.",
        ),
    ]

    # Content collections - supports nested dictionary structure
    # contexts: { context_type: { context_name: Context } }
    # "contexts" is a private field that is used internally by the PathService
    contexts: Annotated[
        dict[str, dict[str, Context]],
        Field(
            default_factory=dict,
            description="Dictionary of context types to dictionaries of contexts in this workspace",
        ),
    ]

    @model_validator(mode="before")
    @classmethod
    def validate_extra_fields(cls, data: Any) -> Any:
        """Validate that extra fields have allowed types.

        Args:
            data: The workspace data to validate

        Returns:
            Validated data
        """
        if not isinstance(data, dict):
            return data

        # Define fields that are part of the model
        model_fields = {
            "name",
            "workspace_dir",
            "archive_dir",
            "output_dir",
            "context_type",
            "context_config_files",
            "contexts",
        }

        # Use the centralized validator
        ModelValidator.validate_extra_fields(data, model_fields)

        return data

    @field_validator("context_type")
    @classmethod
    def validate_context_type(cls, v: str) -> str:
        """Validate that context_type does not use reserved keywords."""
        if v == "contexts":
            raise ValueError(
                "'contexts' is a reserved keyword and cannot be used as context_type. "
                "Please choose a different name for your context type."
            )
        return v

    @field_validator("workspace_dir", "archive_dir", "output_dir")
    @classmethod
    def validate_paths(cls, v: str | None) -> str | None:
        """Validate path formats for workspace paths."""
        if v is None:
            return None

        # Check for absolute paths (we allow './path' but not '/path')
        if v.startswith("/") and not v.startswith("./"):
            # Always raise an error for absolute paths beginning with /
            raise ValueError(f"Path '{v}' must be relative")

        return v

    @model_validator(mode="after")
    def validate_workspace(self) -> WorkspaceConfig:
        """Validate workspace configuration.

        This validator ensures that:
        1. The workspace has a valid name
        2. Default values are set for optional fields if not provided

        Note: Path resolution is handled by the PathService, not in the model.
        """
        # Validate name (simple validation only, path resolution handled elsewhere)
        if not self.name:
            raise ValueError("Workspace name cannot be empty")

        return self

    def resolve_context_type(self) -> str:
        """Resolve the context type, using default if not specified."""
        return self.context_type or settings.workspace.context_type
