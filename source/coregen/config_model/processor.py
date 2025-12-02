"""
Configuration Processor for Coregen.

Transforms raw configuration dictionaries into structured model instances.
Handles template resolution, validation, and path resolution cleanly and simply.
"""

import re
from pathlib import Path
from typing import Any

from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.common.path_resolver import PathResolver
from coregen.common.path_service import PathService
from coregen.config_model.models.components import (
    Component,
    ComponentConfig,
    ComponentDependency,
)
from coregen.config_model.models.context import Context
from coregen.config_model.models.settings import CoregenSettings
from coregen.config_model.models.workspace import WorkspaceConfig


class ConfigProcessor:
    """
    Processes raw configuration dictionaries into structured model instances.

    Responsibilities:
    - Converting raw dictionaries to structured model instances
    - Applying default values where necessary
    - Resolving paths for model instances
    - Validating configuration structures
    """

    def __init__(
        self,
        path_service: PathService | None = None,
        settings: CoregenSettings | None = None,
        provider: Any | None = None,
        skip_validation: bool = False,
    ):
        """
        Initialize the configuration processor.

        Args:
            path_service: Optional PathService instance, created if not provided.
            settings: Optional CoregenSettings instance, created if not provided.
            provider: Optional provider reference for error tracking.
            skip_validation: If True, skip validation during config processing (detect-changes only).
        """
        self.path_service = path_service or PathService()
        self.settings = settings or CoregenSettings()  # type: ignore[call-arg]  # Known Pydantic v2 mypy plugin bug
        self.path_resolver = PathResolver()
        self.provider = provider
        self.skip_validation = skip_validation
        self._logger = Logger(__name__)
        if provider and not hasattr(provider, "validation_errors"):
            provider.validation_errors = []

    def process(self, config_dict: dict[str, Any]) -> list[WorkspaceConfig]:
        """
        Process the configuration dictionary into WorkspaceConfig instances.

        Args:
            config_dict: Raw configuration dictionary.

        Returns:
            List of WorkspaceConfig instances.
        """
        resolved_config = self.path_resolver.resolve_config_templates(config_dict)
        workspaces = []

        for ws_dict in resolved_config.get("workspaces", []):
            workspace = self._safe_process_workspace(ws_dict)
            if workspace:
                workspaces.append(workspace)

        return workspaces

    def _safe_process_workspace(
        self, ws_dict: dict[str, Any]
    ) -> WorkspaceConfig | None:
        """
        Safely processes a workspace dictionary, handling exceptions.

        Args:
            ws_dict: Workspace configuration dictionary.

        Returns:
            WorkspaceConfig instance or None if an error occurs.
        """
        name = ws_dict.get("name", "unknown")
        try:
            return self._process_workspace(ws_dict)
        except Exception as e:
            self._log_error(f"Workspace '{name}' processing failed: {e}")
            return None

    def _process_workspace(self, ws_dict: dict[str, Any]) -> WorkspaceConfig:
        """
        Process workspace configuration into a WorkspaceConfig instance.

        Args:
            ws_dict: Workspace configuration dictionary.

        Returns:
            WorkspaceConfig instance.
        """
        ws_copy = ws_dict.copy()
        context_type = ws_copy.get("context_type", self.settings.workspace.context_type)
        context_dicts = ws_copy.pop(context_type, [])

        workspace = WorkspaceConfig(**ws_copy)
        workspace.context_type = (
            workspace.context_type or self.settings.workspace.context_type
        )
        workspace.contexts = {context_type: {}}

        self.path_service.resolve_workspace_paths(workspace)

        for ctx_dict in context_dicts:
            context = self._safe_process_context(ctx_dict, workspace)
            if context:
                workspace.contexts[context_type][context.name] = context

        return workspace

    def _safe_process_context(
        self, ctx_dict: dict[str, Any], workspace: WorkspaceConfig
    ) -> Context | None:
        """
        Safely processes a context dictionary, handling exceptions.

        Args:
            ctx_dict: Context configuration dictionary.
            workspace: Parent WorkspaceConfig instance.

        Returns:
            Context instance or None if an error occurs.
        """
        ctx_dict.get("name", "unknown")
        try:
            return self._process_context(ctx_dict, workspace)
        except Exception as e:
            self._log_error(str(e))
            return None

    @staticmethod
    def _is_component_collection(value: Any) -> bool:
        """
        Check if a value looks like a component collection.

        Args:
            value: Value to check.

        Returns:
            True if value appears to be a component collection.
        """
        if isinstance(value, list):
            # Lists might be component collections if they contain dicts with name/config
            return bool(
                value
                and isinstance(value[0], dict)
                and ("name" in value[0] or "config" in value[0])
            )
        elif isinstance(value, dict):
            # Dicts might be component collections if values are dicts with name/config
            if value:
                first_value = next(iter(value.values()))
                return isinstance(first_value, dict) and (
                    "config" in first_value or "name" in first_value
                )
        return False

    def _process_context(
        self, ctx_dict: dict[str, Any], workspace: WorkspaceConfig
    ) -> Context:
        """
        Process context configuration into a Context instance.

        Args:
            ctx_dict: Context configuration dictionary.
            workspace: Parent WorkspaceConfig instance.

        Returns:
            Context instance.
        """
        ctx_data = ctx_dict.copy()
        components = {}

        # Use the context's component_type to determine which key contains components
        component_type = ctx_data.get(
            "component_type", self.settings.context.component_type
        )

        # Check for component_type mismatch - find keys that look like component containers
        # Look for both list-based (new format) and dict-based (legacy format) component structures
        context_name = ctx_data.get("name", "unknown")
        config_file_path = ctx_data.get("config_file_path")
        potential_component_keys = []
        for k, v in ctx_data.items():
            # Skip known context fields
            if k in [
                "name",
                "environment",
                "active",
                "commit_dir",
                "component_type",
                "skip_validation",
                "internal_path",
                "config_file_path",
                "workspaces",  # This seems to be metadata
                "region",  # Context-specific field
                "workspace",
                "workspace_ref",
                "archive_dir",
                "output_dir",
                "path",
            ]:
                continue

            if self._is_component_collection(v):
                potential_component_keys.append(k)

        # Look for components under the specified component_type key
        if component_type in ctx_data:
            component_data = ctx_data[component_type]
            if isinstance(component_data, list):
                # New list-based format
                components[component_type] = [
                    self._process_component(c, context_name, config_file_path)
                    for c in ctx_data.pop(component_type)
                ]
            elif isinstance(component_data, dict):
                # Legacy dict-based format - convert to list format
                component_list = []
                for comp_name, comp_config in component_data.items():
                    if isinstance(comp_config, dict):
                        # Ensure name field is set
                        comp_config = comp_config.copy()
                        comp_config["name"] = comp_name
                        component_list.append(comp_config)

                components[component_type] = [
                    self._process_component(c, context_name, config_file_path)
                    for c in component_list
                ]
                ctx_data.pop(component_type)
        else:
            # component_type key not found or not a list
            if potential_component_keys:
                # Found component-like keys but none match the component_type
                error_msg = (
                    f"Component type mismatch in context '{context_name}': "
                    f"component_type is set to '{component_type}' but found component keys: {potential_component_keys}. "
                    f"Either change component_type to match your component key, or rename your component key to '{component_type}'."
                )
                self._logger.error(error_msg)
                if self.provider:
                    self.provider.validation_errors.append(error_msg)
            else:
                # No component keys found at all - this might be intentional for contexts with no components
                # Only log as debug since empty contexts are valid
                self._logger.debug(
                    f"No components found for context '{context_name}' with component_type '{component_type}'"
                )

        # Remove ALL component-like keys from context data before creating Context model
        # The Context model expects components to be in the correct nested structure
        for key in potential_component_keys:
            if key in ctx_data:
                ctx_data.pop(key)

        # Remove workspaces field if present (shouldn't be in context data)
        if "workspaces" in ctx_data:
            ctx_data.pop("workspaces")

        # Add workspace reference for field inheritance
        ctx_data["workspace_ref"] = workspace
        # Add workspace name for identification in outputs
        ctx_data["workspace"] = workspace.name
        # Pass skip_validation flag to Context (for detect-changes)
        ctx_data["skip_validation"] = self.skip_validation

        context = Context(**ctx_data)
        context.components = {
            ctype: {comp.name: comp for comp in clist}
            for ctype, clist in components.items()
        }

        for ctype, comps in context.components.items():
            setattr(context, ctype, comps)

        # Inherit fields from workspace if not set
        context.inherit_workspace_fields()

        # Re-run dependency validation now that components are properly set
        try:
            context._validate_component_dependencies()
        except Exception as e:
            # Don't wrap the error - just re-raise the original validation error
            if self.provider:
                self.provider.validation_errors.append(str(e))
            raise

        # First resolve context paths
        context_paths = self.path_service.resolve_context_paths(context, workspace)

        # Debug output for context paths
        self._logger.debug(
            f"Resolved paths for context '{context.name}' in workspace '{workspace.name}':"
        )
        for path_name, path_value in context_paths.items():
            self._logger.debug(f"  {path_name}: {path_value}")

        # Now resolve component paths
        for ctype, comps in context.components.items():
            for comp_name, component in comps.items():
                try:
                    # Set default path if not already set
                    if component.config.path is None and hasattr(
                        context, "internal_path"
                    ):
                        # Use the context's path relative to root
                        component.config.path = (
                            f"{context.internal_path}/{component.name}"
                        )

                    # Process dependencies to set default paths
                    for dep in component.config.dependencies:
                        if dep.path is None and hasattr(context, "internal_path"):
                            # Use the context's path relative to root for dependencies
                            dep.path = f"{context.internal_path}/{dep.name}"

                    # Resolve and store component paths directly on component
                    component_paths = self.path_service.resolve_component_paths(
                        component, context, workspace
                    )
                    setattr(
                        component, "resolved_paths", component_paths
                    )  # Dynamic attribute

                    # Debug output for component paths
                    self._logger.debug(
                        f"Resolved paths for component '{comp_name}' in context '{context.name}', workspace '{workspace.name}':"
                    )
                    for path_name, path_value in component_paths.items():
                        self._logger.debug(f"  {path_name}: {path_value}")

                except Exception as e:
                    self._log_error(
                        f"Failed to resolve paths for component {comp_name} in context {context.name}: {str(e)}"
                    )

        return context

    def _construct_dependencies(
        self, dependencies: list[Any]
    ) -> list[ComponentDependency]:
        """Convert dependency dictionaries to ComponentDependency objects without validation.

        Args:
            dependencies: List of dependency dictionaries or ComponentDependency objects.

        Returns:
            List of ComponentDependency objects constructed without validation.
        """
        return [
            ComponentDependency.model_construct(**dep) if isinstance(dep, dict) else dep
            for dep in dependencies
        ]

    def _coerce_config_types(
        self, config_dict: dict[str, Any], component_name: str
    ) -> None:
        """Apply type coercion to config fields when validation is skipped.

        When using model_construct() to bypass validation (for old schemas),
        YAML string values remain as strings. This method handles the necessary
        type coercions in-place.

        Args:
            config_dict: Config dictionary to modify in-place.
            component_name: Component name for logging.
        """
        # Priority: str → int (with non-negative validation)
        if "priority" in config_dict and config_dict["priority"] is not None:
            try:
                priority = int(config_dict["priority"])
                if priority < 0:
                    self._logger.debug(
                        f"Negative priority {priority} coerced to None "
                        f"in component '{component_name}' (skip_validation mode)"
                    )
                    config_dict["priority"] = None
                else:
                    config_dict["priority"] = priority
            except (ValueError, TypeError) as e:
                self._logger.debug(
                    f"Invalid priority '{config_dict['priority']}' "
                    f"in component '{component_name}': {e}. Using None."
                )
                config_dict["priority"] = None

        # Boolean fields: str → bool
        # YAML boolean strings that should coerce to True
        bool_true_values = frozenset(("true", "1", "yes"))

        for field in ("active", "required", "for_commit"):
            if field not in config_dict or config_dict[field] is None:
                continue

            value = config_dict[field]
            if isinstance(value, str):
                # Handle YAML string boolean values
                config_dict[field] = value.lower() in bool_true_values
            elif not isinstance(value, bool):
                # Coerce other types using Python's bool()
                config_dict[field] = bool(value)

    def _construct_component_without_validation(
        self, comp_dict: dict[str, Any], context_name: str
    ) -> Component:
        """Construct a Component instance bypassing all Pydantic validation.

        This is used for base branch comparison where old field names like
        config.generated need to exist without causing validation errors.

        Args:
            comp_dict: Component configuration dictionary.
            context_name: Name of the parent context for logging.

        Returns:
            Component instance constructed without validation.
        """
        component_name = comp_dict.get("name", "unknown")
        self._logger.debug(
            f"Skipping validation for component '{component_name}' "
            f"in context '{context_name}' (base branch)"
        )

        # Get or create config dict
        config_dict = comp_dict.get("config", {})

        # Copy to avoid mutating original
        config_dict = config_dict.copy()

        # Process dependencies if they exist
        if "dependencies" in config_dict and isinstance(
            config_dict["dependencies"], list
        ):
            config_dict["dependencies"] = self._construct_dependencies(
                config_dict["dependencies"]
            )

        # Apply type coercion (model_construct bypasses Pydantic's type coercion)
        self._coerce_config_types(config_dict, component_name)

        # Construct ComponentConfig without validation
        config = ComponentConfig.model_construct(**config_dict)

        # Construct Component without validation
        comp_dict_copy = comp_dict.copy()
        comp_dict_copy["config"] = config
        return Component.model_construct(**comp_dict_copy)

    def _format_component_error(
        self,
        error: Exception,
        component_name: str,
        context_name: str,
        config_file_path: str | None = None,
    ) -> str:
        """Format component processing errors for clear user feedback.

        Args:
            error: The exception that was raised.
            component_name: Name of the component being processed.
            context_name: Name of the parent context.
            config_file_path: Optional path to the config file.

        Returns:
            Formatted error message string.
        """
        error_msg = str(error)

        # Check if it's our specific priority/dependency validation error
        if "Priority" in error_msg and "cannot have dependencies" in error_msg:
            # Extract just the priority value from the error message
            priority_match = re.search(r"Priority (\d+)", error_msg)
            priority = priority_match.group(1) if priority_match else "0/1"

            # Include context and component names for better debugging
            location = f"{context_name}/{component_name}"

            # Add file path if available for additional context
            if config_file_path:
                try:
                    path = Path(config_file_path)
                    location = f"{location} ({path.name})"
                except (ValueError, TypeError):
                    filename = str(config_file_path).split("/")[-1]
                    location = f"{location} ({filename})"

            return f"{location}: Priority {priority} component cannot have dependencies"

        # Keep original error for other validation issues
        return f"Error processing component '{component_name}' in context '{context_name}': {error_msg}"

    def _process_component(
        self,
        comp_dict: dict[str, Any],
        context_name: str,
        config_file_path: str | None = None,
    ) -> Component:
        """Process component configuration into a Component instance.

        When skip_validation=True (detect-changes base branch), uses
        model_construct() to bypass all Pydantic validation including
        extra="forbid". This allows old field names like config.generated
        to exist without errors.

        Args:
            comp_dict: Component configuration dictionary.
            context_name: Name of the parent context.
            config_file_path: Optional path to the config file for error messages.

        Returns:
            Component instance.
        """
        # Check if component has a path, if not set the default
        if "config" not in comp_dict:
            comp_dict["config"] = {}

        # If path is not set or is None, use the default path template
        if comp_dict["config"].get("path") is None:
            # Default path will be set after context is created and has its path set
            pass  # Will be handled in _process_context after context.internal_path is set

        # Create component - bypass validation for base branch comparison
        try:
            if self.skip_validation:
                component = self._construct_component_without_validation(
                    comp_dict, context_name
                )
            else:
                # Normal validation for current branch
                component = Component(**comp_dict)
        except Exception as e:
            component_name = comp_dict.get("name", "unknown")
            error_message = self._format_component_error(
                e, component_name, context_name, config_file_path
            )
            raise ValueError(error_message) from e

        # Log the component we're creating - safely access type
        comp_type = getattr(component, "type", None) or comp_dict.get("type", "unknown")
        self._logger.debug(
            f"Processed component '{component.name}' for context '{context_name}' with type: {comp_type}"
        )

        return component

    def _log_error(self, message: str) -> None:
        """
        Log an error message and track it in the provider if available.

        Args:
            message: Error message to log.
        """
        Console.error(message)
        if self.provider:
            self.provider.validation_errors.append(message)
