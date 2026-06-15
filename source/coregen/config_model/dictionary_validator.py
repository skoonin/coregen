"""
Configuration dictionary validator.

This module provides validation for raw configuration dictionaries
before they are processed into model instances.
"""

from typing import Any

from coregen.config_model.models.settings import CoregenSettings


class ConfigDictValidator:
    """
    Validator for raw configuration dictionaries.

    This class performs basic structure validation on raw configuration
    dictionaries before they are processed into model instances.
    """

    def __init__(self, settings: CoregenSettings | None = None):
        """Initialize the validator with optional settings."""
        self.settings = settings or CoregenSettings()  # type: ignore[call-arg]  # Known Pydantic v2 mypy plugin bug

    def validate_config(self, config_dict: Any) -> list[str]:
        """
        Validate a configuration dictionary and return a list of validation errors.

        Args:
            config_dict: The configuration dictionary to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not isinstance(config_dict, dict):
            errors.append("Configuration must be a dictionary")
            return errors

        # Validate version if present
        if "version" in config_dict:
            try:
                self._validate_version(config_dict["version"])
            except ValueError as e:
                errors.append(str(e))

        # Validate workspaces
        try:
            self._validate_workspaces(config_dict)
        except ValueError as e:
            errors.append(str(e))

        return errors

    def _validate_version(self, version: str) -> None:
        """Validate the configuration version."""
        # In a real implementation, we would check against supported versions
        # For now, we'll just accept any string version
        if not isinstance(version, str):
            raise ValueError(f"Version must be a string, got {type(version).__name__}")

    def _validate_workspaces(self, config_dict: dict[str, Any]) -> None:
        """Validate the workspaces section of the configuration."""
        if "workspaces" not in config_dict:
            raise ValueError(
                "Invalid configuration structure: missing 'workspaces' key"
            )

        workspaces = config_dict["workspaces"]
        if not isinstance(workspaces, list):
            raise ValueError(
                "Invalid configuration structure: 'workspaces' must be a list"
            )

        # Validate workspace names are unique
        workspace_names = set()
        for workspace in workspaces:
            if not isinstance(workspace, dict):
                raise ValueError(
                    "Invalid configuration structure: workspace must be a dictionary"
                )

            if "name" not in workspace:
                raise ValueError(
                    "Invalid configuration structure: workspace missing 'name' key"
                )

            workspace_name = workspace["name"]
            if workspace_name in workspace_names:
                raise ValueError(
                    f"Duplicate workspace name '{workspace_name}' found. "
                    "All workspace names must be unique across the configuration."
                )
            workspace_names.add(workspace_name)

            # Validate contexts if present
            context_type = workspace.get(
                "context_type", self.settings.workspace.context_type
            )
            if context_type in workspace:
                self._validate_contexts(workspace[context_type], context_type)

    def _validate_contexts(
        self, contexts: list[dict[str, Any]], context_type: str
    ) -> None:
        """Validate the contexts section of a workspace."""
        if not isinstance(contexts, list):
            raise ValueError(
                f"Invalid configuration structure: '{context_type}' must be a list"
            )

        for context in contexts:
            if not isinstance(context, dict):
                raise ValueError(
                    f"Invalid configuration structure: {context_type} entry must be a dictionary"
                )

            if "name" not in context:
                raise ValueError(
                    f"Invalid configuration structure: {context_type} missing 'name' key"
                )

            # Validate components if present
            component_type = context.get(
                "component_type", self.settings.context.component_type
            )
            if component_type in context:
                self._validate_components(context[component_type], component_type)

    def _validate_components(
        self, components: list[dict[str, Any]], component_type: str
    ) -> None:
        """Validate the components section of a context."""
        if not isinstance(components, list):
            raise ValueError(
                f"Invalid configuration structure: '{component_type}' must be a list"
            )

        for component in components:
            if not isinstance(component, dict):
                raise ValueError(
                    f"Invalid configuration structure: {component_type} entry must be a dictionary"
                )

            if "name" not in component:
                raise ValueError(
                    f"Invalid configuration structure: {component_type} missing 'name' key"
                )

            # Validate config if present
            if "config" in component and not isinstance(component["config"], dict):
                raise ValueError(
                    f"Invalid configuration structure: component '{component.get('name', 'unknown')}' has invalid 'config' (must be a dictionary)"
                )
