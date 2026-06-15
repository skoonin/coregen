"""
Simplified Path resolver for configuration paths.

This module resolves paths for workspaces, contexts, and components
with template support and path safety checks.
"""

import glob
import importlib
import os
import re
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from coregen.common.console import Console
from coregen.common.logger import Logger

if TYPE_CHECKING:
    from coregen.config_model.models.settings import CoregenSettings

logger = Logger(__name__)


class PathResolver:
    """
    Path resolver for configuration paths.

    Manages workspace, context, and component paths with template support
    and path safety validation.
    """

    def __init__(
        self,
        root_path: str | Path | None = None,
        creating_config: bool = False,
    ):
        """Initialize PathResolver with root path and configuration mode."""
        self._root_path = Path(root_path or os.getcwd()).resolve()
        self._workspace_paths: dict[str, Path] = {}
        self._context_paths: dict[str, Path] = {}
        self.creating_config = creating_config

    @property
    def root_path(self) -> Path:
        """Root path where all relative paths are resolved from."""
        return self._root_path

    @root_path.setter
    def root_path(self, path: str | Path) -> None:
        """Set the root path for the resolver."""
        self._root_path = Path(path).resolve()

    @cached_property
    def settings(self) -> "CoregenSettings":
        """
        Get application settings from coregen.config_model.models.settings module.

        Raises an exception if settings cannot be loaded - we require settings
        to be available for all path resolution operations.

        cached_property (not property+lru_cache): lru_cache on an instance
        method keys on self and pins every instance for the process lifetime.
        """
        # Dynamic import avoids a circular import at module load time.
        module = importlib.import_module("coregen.config_model.models.settings")
        return cast("CoregenSettings", module.get_settings())

    def set_workspace_path(
        self, workspace_name: str, custom_path: str | None = None
    ) -> Path:
        """Set the path for a workspace."""
        # Use custom path if provided, otherwise use workspace_dir from settings
        if custom_path:
            path = self._resolve_custom_path(custom_path)
        else:
            # Get workspace_dir from settings
            settings = self.settings
            # Use the actual default from WorkspaceSettings.workspace_dir
            workspace_dir = settings.workspace.workspace_dir
            path = self.root_path / workspace_dir

        self._workspace_paths[workspace_name] = path
        return path

    def set_context_path(
        self,
        workspace_name: str,
        context_name: str,
        environment: str,
        workspace_config: dict[str, Any] | None = None,
        custom_path: str | list[str] | None = None,
        config_file_path: str | None = None,
    ) -> Path | None:
        """Set the path for a context within a workspace."""
        path_key = f"{workspace_name}/{context_name}"

        # Try using config file path if provided
        if config_file_path:
            try:
                context_path = Path(config_file_path).parent
                self._context_paths[path_key] = context_path
                return context_path
            except Exception as e:
                logger.warning(
                    f"Invalid config path '{config_file_path}' for context '{context_name}': {str(e)}"
                )

        # Try resolving from custom path list
        if custom_path:
            resolved_path = self._try_resolve_custom_paths(custom_path, context_name)
            if resolved_path:
                self._context_paths[path_key] = resolved_path
                return resolved_path

        # Fall back to default path resolution
        try:
            return self._resolve_default_context_path(
                workspace_name, context_name, environment
            )
        except Exception as e:
            Console.warning(
                f"Default path resolution failed for context '{context_name}': {str(e)}"
            )
            return None

    def _try_resolve_custom_paths(
        self, custom_path: str | list[str], context_name: str
    ) -> Path | None:
        """Try to resolve a context path from custom path patterns."""
        paths = (
            custom_path
            if isinstance(custom_path, list)
            else [custom_path] if custom_path else []
        )

        for path_pattern in paths:
            try:
                # Handle glob patterns
                if any(c in path_pattern for c in "*?["):
                    matches = glob.glob(
                        str(self.root_path / path_pattern), recursive=True
                    )
                    if matches:
                        return Path(matches[0])

                # Handle direct path
                resolved = self._resolve_custom_path(path_pattern)
                if resolved.exists():
                    return resolved
            except Exception as e:
                Console.warning(
                    f"Failed to resolve path '{path_pattern}' for context '{context_name}': {str(e)}"
                )

        return None

    def _resolve_default_context_path(
        self, workspace_name: str, context_name: str, environment: str
    ) -> Path:
        """Resolve default context path using workspace path and templates."""
        workspace_path = self._workspace_paths[workspace_name]

        # Get the context_path template directly from settings
        template = self.settings.paths.context_path

        path = Path(
            self.resolve_template(
                template,
                {
                    "workspace_path": str(workspace_path),
                    "environment": environment,
                    "name": context_name,
                },
            )
        )

        self._context_paths[f"{workspace_name}/{context_name}"] = path
        return path

    def get_component_path(
        self,
        workspace_name: str,
        context_name: str,
        component_name: str,
        custom_path: str | None = None,
        **kwargs: Any,
    ) -> Path:
        """Get the path for a component within a context."""
        # Custom paths get the same root-containment enforcement as
        # workspace/context custom paths; unchecked absolute values let a
        # config point a component outside the repository.
        if custom_path:
            return self._resolve_custom_path(custom_path)

        # Get the context path from stored paths
        path_key = f"{workspace_name}/{context_name}"
        context_path = self._context_paths.get(path_key)

        if not context_path:
            raise ValueError(f"Context {workspace_name}/{context_name} not found")

        # Return the component path within the context directory
        return context_path / component_name

    def get_commit_path(
        self, workspace_name: str, context_name: str, component_name: str
    ) -> Path:
        """Get the path for commit files of a component."""
        path = self._context_paths.get(f"{workspace_name}/{context_name}")
        if not path:
            raise ValueError(f"Context {workspace_name}/{context_name} not found")

        # Get commit_dir directly from settings
        dir_name = self.settings.context.commit_dir
        return path / dir_name / component_name

    def get_commit_dir(
        self,
        context_path: str | Path,
        context_config: dict[str, Any] | None = None,
    ) -> Path:
        """Get the commit directory path for a context."""
        context_path = Path(context_path)

        # Get commit directory name from context config or settings
        if context_config and "commit_dir" in context_config:
            # Use from context config if specified
            commit_dir = str(context_config.get("commit_dir"))
        else:
            # Use from settings
            commit_dir = self.settings.context.commit_dir

        return context_path / commit_dir

    def resolve_template(
        self,
        template: str,
        variables: dict[str, Any],
        context_config: dict[str, Any] | None = None,
    ) -> str:
        """Resolve a template string by substituting variables."""
        # Extract required variables from template
        required = self._extract_template_variables(template)
        self.validate_path_variables(required, variables)

        # Replace all variables in template
        for var in required:
            val = self._get_nested_value(variables, var)
            if val is None:
                raise ValueError(f"Missing variable: {var}")

            # Replace both ${var} and {var} syntax
            template = template.replace(f"${{{var}}}", str(val)).replace(
                f"{{{var}}}", str(val)
            )

        return template

    def _extract_template_variables(self, template: str) -> set[str]:
        """Extract variable names from a template string."""
        matches = re.findall(r"\${([^}]+)}|{([^}]+)}", template)
        return {item for pair in matches for item in pair if item}

    def resolve_config_templates(self, config_dict: dict[str, Any]) -> dict[str, Any]:
        """Recursively resolve templates in a configuration dictionary."""
        result: dict[str, Any] = {}
        for k, v in config_dict.items():
            if isinstance(v, dict):
                result[k] = self.resolve_config_templates(v)
            elif isinstance(v, list):
                result[k] = self._resolve_list_templates(v, config_dict)
            elif isinstance(v, str):
                result[k] = self._resolve_string_template(v, config_dict)
            else:
                result[k] = v
        return result

    def _resolve_list_templates(
        self, items: list[Any], variables: dict[str, Any]
    ) -> list[Any]:
        """Resolve templates in a list of items."""
        return [
            (
                self.resolve_config_templates(item)
                if isinstance(item, dict)
                else (
                    self._resolve_string_template(item, variables)
                    if isinstance(item, str)
                    else item
                )
            )
            for item in items
        ]

    def _resolve_string_template(self, template: str, variables: dict[str, Any]) -> str:
        """Resolve a string template by substituting variables."""
        for var in re.findall(r"\${([^}]+)}", template):
            value = variables.get(
                var,
                variables.get("name") if var in ["name", "workspace_name"] else None,
            )
            if value:
                template = template.replace(f"${{{var}}}", str(value))
        return template

    def validate_path_variables(
        self, required: set[str], provided: dict[str, Any]
    ) -> bool:
        """Validate that all required variables are provided in the dictionary."""
        missing = self._find_missing_variables(required, provided)
        if missing:
            raise ValueError(f"Missing variables: {', '.join(missing)}")
        return True

    def _find_missing_variables(
        self, required: set[str], provided: dict[str, Any]
    ) -> list[str]:
        """Find variables that are missing from the provided dictionary."""
        missing = []
        for var in required:
            if "." in var:
                # Handle nested variables
                if not self._check_nested_variable(var, provided):
                    missing.append(var)
            elif var not in provided:
                missing.append(var)
        return missing

    def _check_nested_variable(self, var: str, provided: dict[str, Any]) -> bool:
        """Check if a nested variable exists in the provided dictionary."""
        current = provided
        for part in var.split("."):
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        return True

    def _resolve_custom_path(self, path: str) -> Path:
        """Resolve a custom path string to an absolute Path object."""
        # Remove leading ./ if present
        path = path[2:] if path.startswith("./") else path

        # Resolve the path relative to the root path if not absolute
        resolved = (
            Path(path).resolve()
            if os.path.isabs(path)
            else (self.root_path / path).resolve()
        )

        # ALWAYS validate path is within root directory to prevent stray paths
        # At some point we may want to allow this, but for now it's a strict requirement
        try:
            # This properly handles symlinks and relative paths
            resolved.relative_to(self.root_path)
        except ValueError:
            raise ValueError(
                f"Path '{path}' resolves to '{resolved}' which is outside the root directory '{self.root_path}'"
            )

        return resolved

    def _get_nested_value(self, data: dict[str, Any], key: str) -> Any | None:
        """Get a value from a nested dictionary using dot notation."""
        for part in key.split("."):
            if not isinstance(data, dict) or part not in data:
                return None
            data = data[part]
        return data
