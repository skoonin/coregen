# common/path_service.py

from pathlib import Path
from typing import Any

from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.common.path_resolver import PathResolver


class PathService:
    """
    High-level path service bridging configuration models and path resolution logic.

    Delegates path operations to PathResolver and keeps model classes free of path resolution logic.
    Provides convenient methods for resolving workspace, context, and component paths
    based on configuration models.

    Available methods:
        - set_root_path: Set the root path for the path resolver.
        - resolve_workspace_paths: Resolve paths relevant to a workspace configuration.
        - resolve_context_paths: Resolve paths relevant to a context configuration.
        - resolve_component_paths: Resolve paths relevant to a component configuration.
        - resolve_template_path: Resolve a template path with given variables.
        - get_workspace_path: Get the path for a workspace model.
        - get_context_path: Get the path for a context model within its workspace.
        - get_component_path: Get the path for a component model within its context and workspace.
        - make_path_relative: Return the relative path to CWD if possible, otherwise the original.

    """

    def __init__(
        self, resolver: PathResolver | None = None, strict_validation: bool = True
    ):
        """
        Initialize a new PathService instance.

        Args:
            resolver (Optional[PathResolver], optional): Path resolver instance to use.
                                                         If None, creates a new PathResolver. Defaults to None.
            strict_validation (bool, optional): Whether to use strict path validation. Defaults to True.
        """
        self.resolver = resolver or PathResolver()
        self.strict_validation = strict_validation
        self.logger = Logger(__name__)

    def set_root_path(self, root_path: Path) -> None:
        """
        Set the root path for the path resolver.

        Args:
            root_path (Path): The root path to use for path resolution
        """
        self.resolver.root_path = root_path

    def resolve_workspace_paths(self, workspace: Any) -> dict[str, Path]:
        """
        Resolve all paths relevant to a workspace configuration.

        Args:
            workspace (Any): Workspace configuration object with name and optional workspace_dir attributes

        Returns:
            Dict[str, Path]: Dictionary of resolved paths including workspace_path,
                             and optional archive_path and output_path if configured
        """
        # Use custom path only if it's explicitly defined and not the default
        custom_path = getattr(workspace, "workspace_dir", None)

        paths = {
            "workspace_path": self.resolver.set_workspace_path(
                workspace_name=workspace.name,
                custom_path=custom_path,
            )
        }

        if getattr(workspace, "archive_dir", None):
            paths["archive_path"] = self.resolver.root_path / workspace.archive_dir

        if getattr(workspace, "output_dir", None):
            paths["output_path"] = self.resolver.root_path / workspace.output_dir

        return paths

    def resolve_context_paths(self, context: Any, workspace: Any) -> dict[str, Path]:
        """
        Resolve all paths relevant to a context configuration.

        Args:
            context (Any): Context configuration object with name, environment attributes
                          and optional config_file_path attribute
            workspace (Any): Workspace configuration object with name and context_type attributes

        Returns:
            Dict[str, Path]: Dictionary of resolved paths including context_path and commit_dir
        """
        context_path = self.resolver.set_context_path(
            workspace_name=workspace.name,
            context_name=context.name,
            environment=context.environment,
            workspace_config={"context_type": workspace.context_type},
            config_file_path=getattr(context, "config_file_path", None),
        )

        if hasattr(context, "set_internal_path"):
            # Set the internal path as relative to root
            root_path = getattr(self.resolver, "root_path", Path("."))
            try:
                relative_path = context_path.relative_to(root_path)
                context.set_internal_path(str(relative_path))
            except ValueError:
                # If not relative to root, use the full path
                context.set_internal_path(str(context_path))

        # Determine the commit directory path
        context_commit_dir = getattr(context, "commit_dir", None)
        commit_dir: Path = (
            context_path / context_commit_dir
            if context_commit_dir
            else self.resolver.get_commit_dir(str(context_path))
        )

        return {"context_path": context_path, "commit_dir": commit_dir}  # type: ignore[dict-item]

    def resolve_component_paths(
        self, component: Any, context: Any, workspace: Any
    ) -> dict[str, Path]:
        """
        Resolve all paths relevant to a component configuration.

        Args:
            component (Any): Component configuration object with name and config attributes
            context (Any): Context configuration object with name and environment attributes
            workspace (Any): Workspace configuration object with name and context_type attributes

        Returns:
            Dict[str, Path]: Dictionary of resolved paths including component_path
                            and optional commit_path if component is for_commit

        Raises:
            ValueError: If path resolution fails for the component
        """
        self.resolver.set_context_path(
            workspace_name=workspace.name,
            context_name=context.name,
            environment=context.environment,
            workspace_config={"context_type": workspace.context_type},
            config_file_path=getattr(context, "config_file_path", None),
        )

        try:
            # Attempt to get custom path from component config
            custom_path_str = getattr(getattr(component, "config", {}), "path", None)

            # First, get the default component path using the resolver
            default_component_path = self.resolver.get_component_path(
                workspace_name=workspace.name,
                context_name=context.name,
                component_name=component.name,
                custom_path=None,  # Explicitly pass None to get default path
            )

            # Now, determine the final component path
            if custom_path_str:
                # Resolve through the resolver so component custom paths get
                # the same root-containment enforcement as workspace/context
                # custom paths.
                final_component_path = self.resolver.get_component_path(
                    workspace_name=workspace.name,
                    context_name=context.name,
                    component_name=component.name,
                    custom_path=custom_path_str,
                )
                self.logger.debug(
                    f"Using custom path override for component '{component.name}': {final_component_path}"
                )
            else:
                # Otherwise, use the default path
                final_component_path = default_component_path
                self.logger.debug(
                    f"Using default path for component '{component.name}': {final_component_path}"
                )

            paths = {"component_path": final_component_path}

            if getattr(component.config, "for_commit", False):
                # Ensure resolver context is set before calling get_commit_path
                self.resolver.set_context_path(
                    workspace_name=workspace.name,
                    context_name=context.name,
                    environment=context.environment,
                    workspace_config={"context_type": workspace.context_type},
                    config_file_path=getattr(context, "config_file_path", None),
                )
                paths["commit_path"] = self.resolver.get_commit_path(
                    workspace_name=workspace.name,
                    context_name=context.name,
                    component_name=component.name,
                )

            return paths

        except Exception as e:
            error_msg = f"Error resolving path for component '{component.name}' in context '{context.name}': {str(e)}"
            Console.error(error_msg)
            raise ValueError(error_msg) from e

    def resolve_template_path(
        self,
        template: str,
        variables: dict[str, str],
        context_config: dict[str, Any] | None = None,
    ) -> str:
        """
        Resolve a template path with the given variables.

        Args:
            template (str): Template string with placeholders to be resolved
            variables (Dict[str, str]): Dictionary of variables to use for template resolution
            context_config (Optional[Dict[str, Any]], optional): Context configuration. Defaults to None.

        Returns:
            str: Resolved template path as a string
        """
        return self.resolver.resolve_template(template, variables, context_config)

    def get_workspace_path(self, workspace: Any) -> Path:
        """
        Get the path for a workspace model.

        Args:
            workspace (Any): Workspace configuration object with name and optional workspace_dir attribute

        Returns:
            Path: Resolved workspace path
        """
        return self.resolver.set_workspace_path(
            workspace_name=workspace.name,
            custom_path=getattr(workspace, "workspace_dir", None),
        )

    def get_context_path(self, context: Any, workspace: Any) -> Path:
        """
        Get the path for a context model within its workspace.

        Args:
            context (Any): Context configuration object with name and optional environment attributes
            workspace (Any): Workspace configuration object with name and context_type attributes

        Returns:
            Path: Resolved context path
        """

        # Get environment with proper type handling
        environment = getattr(context, "environment", None)
        if environment is None:
            environment = ""  # Default to empty string if not provided

        # Get config file path as string
        config_file_path = getattr(context, "config_file_path", None)
        config_file_path_str = str(config_file_path) if config_file_path else None

        result = self.resolver.set_context_path(
            workspace_name=workspace.name,
            context_name=context.name,
            environment=environment,
            workspace_config={"context_type": workspace.context_type},
            config_file_path=config_file_path_str,
        )
        if result is None:
            raise ValueError(f"Failed to resolve context path for {context.name}")
        return result

    def get_component_path(self, component: Any, context: Any, workspace: Any) -> Path:
        """
        Get the path for a component model within its context and workspace.

        Args:
            component: Component configuration object
            context: Context configuration object
            workspace: Workspace configuration object

        Returns:
            Path: Resolved component path
        """
        # Get the context path first
        self.get_context_path(context, workspace)

        # Check if component has a custom path defined
        custom_path = None
        if hasattr(component, "config") and hasattr(component.config, "path"):
            custom_path = component.config.path

        # Use resolver to get the component path
        return self.resolver.get_component_path(
            workspace_name=workspace.name,
            context_name=context.name,
            component_name=component.name,
            custom_path=custom_path,
        )

    def make_path_relative(self, path: str | Path) -> str:
        """
        Return the relative path to CWD if possible, otherwise the original.

        Args:
            path (Union[str, Path]): A string or Path instance to convert

        Returns:
            str: Relative path string if within current working directory, otherwise absolute path string
        """
        if not path:
            return ""

        path = Path(path)
        abs_path = path.absolute()
        cwd = Path.cwd().absolute()

        try:
            return str(abs_path.relative_to(cwd))
        except ValueError:
            return str(path)
