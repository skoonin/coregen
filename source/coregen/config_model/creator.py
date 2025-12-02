"""
Configuration creator for Coregen.

This module handles creating new configuration dictionaries for config generation.
It provides default values and structures for new configurations.
"""

from typing import Any, NotRequired, TypedDict

from coregen.config_model.models.settings import CoregenSettings


# Type definitions for better type checking and documentation
class ComponentConfigDict(TypedDict):
    """TypedDict for component configuration."""

    active: bool
    required: bool
    for_commit: bool
    dependencies: list[dict[str, str]]
    path: NotRequired[str]


class ComponentDict(TypedDict):
    """TypedDict for component dictionary."""

    name: str
    config: ComponentConfigDict


class ContextDict(TypedDict):
    """TypedDict for context dictionary."""

    name: str
    environment: str
    component_type: str
    active: bool
    commit_dir: str
    path: NotRequired[str]
    components: NotRequired[dict[str, Any]]
    # Dynamic component_type and components_dir keys are added at runtime


class WorkspaceDict(TypedDict):
    """TypedDict for workspace dictionary."""

    name: str
    archive_dir: str
    context_type: str
    context_config_files: list[str]
    output_dir: str
    workspace_dir: NotRequired[str]
    contexts: NotRequired[dict[str, Any]]
    # Dynamic context_type and contexts_dir keys are added at runtime


class ConfigDict(TypedDict):
    """TypedDict for configuration dictionary."""

    workspaces: list[WorkspaceDict]


class ConfigCreator:
    """
    Creates new configuration dictionaries for config generation.

    This class is responsible for:
    - Creating new configuration dictionaries with default values
    - Applying user-provided overrides
    - Ensuring created configurations are valid

    The creator follows these principles:
    - Uses CoregenSettings as the single source of truth for default values
    - Creates immutable dictionaries (returns new instances rather than modifying existing ones)
    - Validates input parameters before creating configurations
    - Provides clear error messages for validation failures
    """

    def __init__(self) -> None:
        """Initialize the creator with default settings."""
        self.settings = CoregenSettings()  # type: ignore[call-arg]  # Known Pydantic v2 mypy plugin bug

    def create_config(self, workspace_name: str | None = None) -> ConfigDict:
        """
        Create a new configuration dictionary with default values.

        Args:
          workspace_name: Optional name for the workspace,
                    defaults to settings.workspace.workspace_name
                          workspace with this name will be included in the config.

        Returns:
            Dict containing the default configuration
        """
        config: ConfigDict = {"workspaces": []}

        # Use provided name or fall back to settings default
        name = (
            workspace_name if workspace_name else self.settings.workspace.workspace_name
        )
        workspace = self.create_workspace(name)
        config["workspaces"].append(workspace)

        return config

    def create_workspace(
        self, name: str, workspace_dir: str | None = None
    ) -> WorkspaceDict:
        """
        Create a new workspace dictionary with default values.

        Args:
            name: Name for the workspace
            workspace_dir: Optional custom directory for this workspace (relative to root config file path)
                  If not provided, workspace directory defaults to the workspace name

        Returns:
            Dict containing the workspace configuration

        Raises:
            ValueError: If name is empty or invalid
        """
        name if name else self.settings.workspace.workspace_name

        if not name or not name.strip():
            raise ValueError("Workspace name is required and cannot be empty")

        # Get context config files from workspace settings (fix)
        context_config_files = self.settings.workspace.context_config_files

        # Start with required fields
        workspace: dict[str, Any] = {
            "name": name,
            "context_type": self.settings.workspace.context_type,
            "context_config_files": context_config_files,
            "archive_dir": self.settings.workspace.archive_dir,
            "output_dir": self.settings.workspace.output_dir,
        }

        # Add optional workspace_dir if provided
        if workspace_dir and workspace_dir.strip():
            workspace["workspace_dir"] = workspace_dir

        # Initialize contexts as a nested dictionary structure using context_type:
        # contexts: { context_type: {} }
        # (avoid adding an empty "contexts" dictionary with another empty "contexts" dictionary inside)
        context_type = self.settings.workspace.context_type
        workspace["contexts"] = {context_type: {}}

        return workspace  # type: ignore

    def create_context(
        self,
        name: str,
        environment: str,
        component_type: str | None = None,
        path: str | None = None,
    ) -> ContextDict:
        """
        Create a new context dictionary with default values.

        Args:
            name: Name for the context
            environment: Environment the context belongs to (required)
            component_type: Optional type name for components in this context
            path: Optional custom path for this context (relative to workspace/environment)
                  If not provided, context path defaults to the context name

        Returns:
            Dict containing the context configuration

        Raises:
            ValueError: If name or environment is not provided or invalid
        """
        # Validate inputs
        if not name or not name.strip():
            raise ValueError("Context name is required and cannot be empty")

        # Validate environment is provided
        if not environment or not environment.strip():
            raise ValueError(
                "Environment is required for context creation and cannot be empty"
            )

        # Use default component type if none provided or empty
        if not component_type or not component_type.strip():
            component_type = self.settings.context.component_type

        # Create the context dictionary
        context: dict[str, Any] = {
            "name": name,
            "environment": environment,
            "component_type": component_type,
            "active": self.settings.context.active,
            "commit_dir": self.settings.context.commit_dir,
        }

        # Add optional path if provided and not empty
        if path and path.strip():
            context["path"] = path

        # Initialize components as a nested dictionary structure:
        # components: { component_type: {} }
        context["components"] = {component_type: {}}

        return context  # type: ignore

    def create_component(self, name: str, path: str | None = None) -> ComponentDict:
        """
        Create a new component dictionary with default values.

        Args:
            name: Name for the component
            path: Optional custom path for this component (relative to context/components_dir)
                  If not provided, component path defaults to the component name

        Returns:
            Dict containing the component configuration

        Raises:
            ValueError: If name is empty or invalid
        """
        if not name or not name.strip():
            raise ValueError("Component name is required and cannot be empty")

        # Create the component configuration
        config: ComponentConfigDict = {
            "active": self.settings.component.active,
            "required": self.settings.component.required,
            "for_commit": self.settings.component.for_commit,
            "dependencies": [],
        }

        # Add optional path if provided
        if path:
            if not path.strip():
                raise ValueError("Component path cannot be empty if provided")
            config["path"] = path

        # Create the component dictionary
        component: ComponentDict = {"name": name, "config": config}

        return component

    def add_context_to_workspace(
        self, workspace: WorkspaceDict, context: ContextDict
    ) -> WorkspaceDict:
        """
        Add a context to a workspace configuration.

        Args:
            workspace: Workspace dictionary to update
            context: Context dictionary to add

        Returns:
            Updated workspace dictionary

        Raises:
            ValueError: If workspace or context is invalid
        """
        if "name" not in workspace:
            raise ValueError("Invalid workspace: missing 'name' field")

        if "name" not in context:
            raise ValueError("Invalid context: missing 'name' field")

        if "environment" not in context:
            raise ValueError("Invalid context: missing 'environment' field")

        context_type = workspace.get(
            "context_type", self.settings.workspace.context_type
        )

        # Create a copy to avoid modifying the original
        workspace_dict: dict[str, Any] = dict(workspace)

        # Ensure contexts dictionary exists with proper nesting structure
        if "contexts" not in workspace_dict:
            workspace_dict["contexts"] = {}

        contexts_dict = workspace_dict["contexts"]
        if not isinstance(contexts_dict, dict):
            contexts_dict = {}
            workspace_dict["contexts"] = contexts_dict

        if context_type not in contexts_dict:
            contexts_dict[context_type] = {}

        # Add to the nested structure: contexts[context_type][context_name] = context
        context_type_dict = contexts_dict[context_type]
        if isinstance(context_type_dict, dict):
            context_type_dict[context["name"]] = context

        return workspace_dict  # type: ignore

    def add_component_to_context(
        self, context: ContextDict, component: ComponentDict
    ) -> ContextDict:
        """
        Add a component to a context configuration.

        Args:
            context: Context dictionary to update
            component: Component dictionary to add

        Returns:
            Updated context dictionary

        Raises:
            ValueError: If context or component is invalid
        """
        if "name" not in context:
            raise ValueError("Invalid context: missing 'name' field")

        if "name" not in component:
            raise ValueError("Invalid component: missing 'name' field")

        if "config" not in component:
            raise ValueError("Invalid component: missing 'config' field")

        component_type = context.get(
            "component_type", self.settings.context.component_type
        )

        # Create a copy to avoid modifying the original
        context_dict: dict[str, Any] = dict(context)

        # Ensure components dictionary exists with the component_type key
        if "components" not in context_dict:
            context_dict["components"] = {}

        components_dict = context_dict["components"]
        if not isinstance(components_dict, dict):
            components_dict = {}
            context_dict["components"] = components_dict

        if component_type not in components_dict:
            components_dict[component_type] = {}

        # Add to the nested structure: components[component_type][component_name] = component
        component_type_dict = components_dict[component_type]
        if isinstance(component_type_dict, dict):
            component_type_dict[component["name"]] = component

        return context_dict  # type: ignore
