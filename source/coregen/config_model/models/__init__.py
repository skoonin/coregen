"""
Configuration models for Coregen.

This module defines the data models used by the configuration system.
Models use Pydantic for validation and serialization.

The model validation follows the three-level validation architecture:
1. Schema Validation: Fast checks for correct structure and types
2. Model Validation: Deeper checks for relationships and business rules
3. Path Validation: Environment-specific checks for filesystem state

Key models:
- CoregenConfig: Root configuration containing workspaces
- WorkspaceConfig: Workspace configuration with contexts
- Context: Context configuration
- Component: Component definition with configuration
- ComponentConfig: Component configuration settings
- ComponentDependency: Component dependency definition
- CoregenSettings: Global config settings with defaults (includes CLI settings)
"""

from coregen.config_model.models.config import (
    Component,
    ComponentConfig,
    ComponentDependency,
    Context,
    CoregenConfig,
    CoregenSettings,
    WorkspaceConfig,
)
from coregen.config_model.models.settings import get_settings
from coregen.config_model.models.validation import ModelValidator

__all__ = [
    "CoregenConfig",
    "CoregenSettings",
    "Component",
    "ComponentConfig",
    "ComponentDependency",
    "Context",
    "WorkspaceConfig",
    "ModelValidator",
    "get_settings",
]
