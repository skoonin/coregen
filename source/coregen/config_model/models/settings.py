"""
Core configuration settings for Coregen.

Provides global defaults and configuration rules that apply across all workspaces.
All program default values should be defined here to ensure consistency.
"""

import functools
import json
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from coregen.config_model.models.defaults import (
    CliSettings,
    ComponentSettings,
    ContextSettings,
    GitSettings,
    PathSettings,
    SystemSettings,
    WorkspaceSettings,
)


class CoregenSettings(BaseModel):
    """

    Global settings for Coregen with defaults and configuration rules.

    This is the facade for single source of truth for default values used throughout the application.

    All actual default values are defined in the defaults.py file.

    Path rules:
    - All paths in user config files are relative to workspace root unless absolute
    - The path templates in 'paths' section are only used internally by the path resolver

    """

    model_config = ConfigDict(extra="forbid")

    system: Annotated[
        SystemSettings,
        Field(default_factory=SystemSettings, description="Global system settings"),
    ]
    workspace: Annotated[
        WorkspaceSettings,
        Field(
            default_factory=WorkspaceSettings, description="Workspace-level settings"
        ),
    ]
    context: Annotated[
        ContextSettings,
        Field(default_factory=ContextSettings, description="Context-level settings"),
    ]
    component: Annotated[
        ComponentSettings,
        Field(
            default_factory=ComponentSettings, description="Component-level settings"
        ),
    ]
    paths: Annotated[
        PathSettings,
        Field(
            default_factory=PathSettings,
            description="Path templates for internal resolution (not user config)",
        ),
    ]
    options: Annotated[
        CliSettings,
        Field(default_factory=CliSettings, description="CLI-specific settings"),
    ]
    git: Annotated[
        GitSettings,
        Field(default_factory=GitSettings, description="Git-related settings"),
    ]

    def get_defaults(self) -> dict[str, Any]:
        """
        Get all default values as a flattened dictionary.

        Returns:
            Dict[str, Any]: Dictionary of all default values
        """
        result = {}
        for _, category in self:
            if isinstance(category, BaseModel):
                for key, value in category.model_dump(exclude_defaults=False).items():
                    result[key] = value
        return result

    def get_model_schema(
        self, model_class: type[BaseModel] | None = None
    ) -> dict[str, Any]:
        """
        Generate JSON schema for a model class or this settings class if none provided.

        Args:
            model_class: Optional Pydantic model class to generate schema for
                        If None, generates schema for this settings class

        Returns:
            Dict[str, Any]: JSON schema for the model
        """
        if model_class is None:
            return self.model_json_schema()
        return model_class.model_json_schema()

    def get_yaml_schema(self, model_class: type[BaseModel] | None = None) -> str:
        """
        Generate YAML schema for a model class or this settings class if none provided.

        Args:
            model_class: Optional Pydantic model class to generate schema for
                        If None, generates schema for this settings class

        Returns:
            str: YAML schema for the model
        """
        schema = self.get_model_schema(model_class)
        try:
            import yaml

            return yaml.dump(schema, sort_keys=False, default_flow_style=False)
        except ImportError:
            return json.dumps(schema, indent=2)


# Allows for lazy loading of settings
@functools.lru_cache(maxsize=1)
def get_settings() -> CoregenSettings:
    """
    Get the application settings singleton.

    Returns a cached instance of CoregenSettings to avoid recreating
    settings objects throughout the application.

    Returns:
        CoregenSettings: The application settings
    """
    return CoregenSettings()  # type: ignore[call-arg]  # Known Pydantic v2 mypy plugin bug with Annotated + default_factory
