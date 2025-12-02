"""
Root configuration model for Coregen.

This is the main entry point for all configuration models. It imports and exports
all models to provide a clean interface for other modules.

To import these models, use:
  from coregen.config_model.models.config import (
    CoregenConfig, WorkspaceConfig, Context,
    Component, ComponentConfig, CoregenSettings
  )

To use __all__ for convenience:
  from coregen.config_model.models import *

"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from coregen.config_model.models.components import (
    Component,
    ComponentConfig,
    ComponentDependency,
)
from coregen.config_model.models.context import Context
from coregen.config_model.models.settings import CoregenSettings
from coregen.config_model.models.workspace import WorkspaceConfig


class CoregenConfig(BaseModel):
    """Root configuration containing workspaces."""

    model_config = ConfigDict(extra="forbid")

    workspaces: list[WorkspaceConfig] = Field(
        ...,
        min_length=1,
        description="Program-required: List of at least one workspace configuration",
    )

    @model_validator(mode="after")
    def validate_non_empty_workspaces(self) -> "CoregenConfig":
        """Ensure at least one workspace is provided."""
        if not self.workspaces or len(self.workspaces) == 0:
            raise ValueError("At least one workspace configuration is required")
        return self

    @property
    def settings(self) -> CoregenSettings:
        """Get global settings with defaults."""
        return CoregenSettings()  # type: ignore[call-arg]  # Known Pydantic v2 mypy plugin bug


# Export all models for convenience
__all__ = [
    "CoregenConfig",
    "CoregenSettings",
    "Component",
    "ComponentConfig",
    "ComponentDependency",
    "Context",
    "WorkspaceConfig",
]
