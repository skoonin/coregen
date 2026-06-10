"""
Central configuration management system.

This class serves as a façade for the entire configuration system, coordinating
the loader, processor, and access components.
"""

from pathlib import Path
from typing import Any, TypedDict, cast

from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.logger import Logger
from coregen.common.path_resolver import PathResolver
from coregen.common.path_service import PathService
from coregen.config_model.access import ConfigAccess
from coregen.config_model.creator import ConfigCreator
from coregen.config_model.dictionary_validator import ConfigDictValidator
from coregen.config_model.loader import ConfigLoader
from coregen.config_model.models.components import Component
from coregen.config_model.models.config import CoregenConfig
from coregen.config_model.models.context import Context
from coregen.config_model.models.settings import get_settings
from coregen.config_model.models.workspace import WorkspaceConfig
from coregen.config_model.processor import ConfigProcessor
from coregen.config_model.validation_error_grouper import (
    VALIDATION_ERROR_HEADER,
    group_validation_errors,
)


class EffectiveOptions(TypedDict):
    """Type definition for effective options dictionary."""

    dry_run: bool
    file_action: FileAction
    quiet: bool
    verbose: bool
    no_color: bool


class ConfigurationProvider:
    """
    Central configuration management system.

    This class serves as a façade for the configuration system, coordinating:
    1. Loading configuration (via ConfigLoader)
    2. Validating configuration (via ConfigDictValidator)
    3. Processing configuration (via ConfigProcessor)
    4. Providing access to configuration (via ConfigAccess)
    5. Path resolution (via PathService)

    Example usage:
    ```python
    provider = ConfigurationProvider()
    provider.load_config(".cgconfig.yaml")

    # Access configuration using path-like identifiers
    context = provider.get_context("aws/dev/cluster1")
    component = provider.get_component("aws/dev/cluster1/nginx")
    contexts = provider.get_contexts_matching("aws/*/cluster*")
    ```
    """

    def __init__(
        self,
        config_mode: bool = False,
        root_path: Path | None = None,
        lenient_validation: bool = False,
        skip_validation: bool = False,
        # Global options
        dry_run: bool | None = None,
        file_action: FileAction | None = None,
        quiet: bool | None = None,
        verbose: bool | None = None,
        no_color: bool | None = None,
        # Support for explicit component injection (useful in testing)
        config_loader: ConfigLoader | None = None,
        config_processor: ConfigProcessor | None = None,
        config_creator: ConfigCreator | None = None,
        path_service: PathService | None = None,
        validator: ConfigDictValidator | None = None,
    ):
        """
        Initialize the configuration provider.

        Args:
            config_mode: If True, operates in config generation mode where
                       finding an existing config file is not required
            root_path: Optional root path to use (e.g., for tests)
            lenient_validation: If True, performs lenient path validation (checking syntax only)
            skip_validation: If True, skip validation during config processing (detect-changes only)
            dry_run: If True, show what would be done without making changes. None means use settings default.
            file_action: Action to take when a file exists. None means use settings default.
            quiet: If True, suppress non-essential output. None means use settings default.
            verbose: If True, show detailed output. None means use settings default.
            no_color: If True, disable colored output. None means use settings default.
            config_loader: Optional ConfigLoader instance
            config_processor: Optional ConfigProcessor instance
            config_creator: Optional ConfigCreator instance
            path_service: Optional PathService instance
            validator: Optional ConfigDictValidator instance
        """
        self._logger = Logger(__name__)
        self._config_mode = config_mode
        self._lenient_validation = lenient_validation
        self._settings = get_settings()
        self.validation_errors: list[str] = []  # Track validation errors

        cli_settings = self._settings.options.global_options

        # Store effective options locally without mutating global state
        # This prevents commands from affecting each other's state
        self._effective_options: EffectiveOptions = {
            "dry_run": dry_run if dry_run is not None else cli_settings.dry_run,
            "file_action": (
                file_action if file_action is not None else cli_settings.file_action
            ),
            "quiet": quiet if quiet is not None else cli_settings.quiet,
            "verbose": verbose if verbose is not None else cli_settings.verbose,
            "no_color": no_color if no_color is not None else cli_settings.no_color,
        }

        # Set root path
        if root_path:
            self.root_path = root_path
        elif config_mode:
            # In config generation mode, use current directory as root
            self.root_path = Path.cwd()
        else:
            # Try to discover the root path
            temp_loader = ConfigLoader()
            discovered_root = temp_loader.discover_root_path()
            self.root_path = discovered_root if discovered_root else Path.cwd()

        # Initialize components
        self._config: CoregenConfig | None = None

        # Use provided components or create new ones
        self._path_resolver = PathResolver(creating_config=config_mode)
        self._path_service = path_service or PathService(
            self._path_resolver, strict_validation=not self._lenient_validation
        )
        self._validator = validator or ConfigDictValidator(settings=self._settings)
        self._processor = config_processor or ConfigProcessor(
            path_service=self._path_service,
            settings=self._settings,
            provider=self,  # Pass self reference to processor for error tracking
            skip_validation=skip_validation,
        )
        self._loader = config_loader or ConfigLoader(
            path_resolver=self._path_resolver,
            settings=self._settings,
            dry_run=self._effective_options["dry_run"],
            file_action=self._effective_options["file_action"],
            quiet=self._effective_options["quiet"],
            verbose=self._effective_options["verbose"],
            no_color=self._effective_options["no_color"],
        )
        self._creator = config_creator or ConfigCreator()

        # Initialize access
        self._config_access: ConfigAccess | None = None

    @property
    def path_service(self) -> PathService:
        """Get the path service instance."""
        return self._path_service

    @property
    def config_creator(self) -> ConfigCreator:
        """Get the configuration creator instance."""
        return self._creator

    def load_config(self, config_path: str | Path) -> CoregenConfig:
        """
        Load configuration from a file.

        Args:
            config_path: Path to configuration file

        Returns:
            Processed configuration model

        Raises:
            ValueError: If configuration validation fails
            FileNotFoundError: If config file is not found
        """
        # Set the root path to the directory containing the config file
        config_path_obj = Path(config_path)

        # Always set the root path to the directory containing the config file
        # This ensures paths are always relative to the config file's location
        if config_path_obj.is_absolute():
            config_dir = config_path_obj.parent
        else:
            # If path is relative, make it absolute relative to CWD
            config_path_obj = Path.cwd() / config_path_obj
            config_dir = config_path_obj.parent

        # Set the root path to the config file's directory
        self.path_service.set_root_path(config_dir)
        self.root_path = config_dir
        self._logger.debug(
            f"Using root path: {config_dir} from config file: {config_path_obj}"
        )

        # Load the raw configuration
        try:
            config_dict = self._loader.load_config(config_path)
        except FileNotFoundError:
            self._logger.error(f"Configuration file not found: {config_path}")
            raise
        except Exception as e:
            error_msg = f"Error loading configuration: {str(e)}"
            self._logger.error(error_msg)
            raise ValueError(error_msg) from e

        # Validate the raw configuration structure
        errors = self._validator.validate_config(config_dict)
        if errors:
            self._logger.error("Configuration validation failed")
            for error in errors:
                self._logger.error(f"  • {error}")
            raise ValueError(f"Configuration validation failed: {errors}")

        # Discover additional context configurations
        try:
            config_dict = self._loader.discover_context_configs(
                config_dict, root_dir=self.root_path
            )
        except ValueError as e:
            # Re-raise critical validation errors like duplicate context names
            if "Duplicate context name" in str(e) or "Duplicate workspace name" in str(
                e
            ):
                self._logger.error(f"Critical validation error: {str(e)}")
                raise
            else:
                self._logger.error(
                    f"Error discovering context configurations: {str(e)}"
                )
                # Continue with what we have, just log the error and proceed
        except Exception as e:
            self._logger.error(f"Error discovering context configurations: {str(e)}")
            # Continue with what we have, just log the error and proceed

        # Clear validation errors before processing
        self.validation_errors = []

        # Process the configuration - this may log warnings for unresolved paths
        # but won't necessarily fail unless strict validation is enabled
        workspaces = self._processor.process(config_dict)

        # If no workspaces were processed successfully, that's a critical error
        if not workspaces and not self._config_mode:
            # In config generation mode, having no workspaces is fine
            error_msg = "No workspaces were loaded successfully from configuration"
            self._logger.error(error_msg)
            if not self._lenient_validation:
                raise ValueError(error_msg)

        # Create CoregenConfig instance
        self._config = CoregenConfig(workspaces=workspaces)

        # Initialize config access
        self._config_access = ConfigAccess(self._config, self._path_service)

        # Group and deduplicate validation errors, then log the result
        if self.validation_errors:
            self.validation_errors = group_validation_errors(self.validation_errors)
            for error in self.validation_errors:
                if VALIDATION_ERROR_HEADER not in error:
                    self._logger.error(f"Validation error: {error}")

        return self._config

    def create_config(
        self,
        workspace_name: str | None = None,
        custom_properties: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a new configuration with specified properties.

        This unified method creates a configuration with workspaces only (no contexts or components)
        and applies user overrides to customize it.

        Args:
            workspace_name: Optional name for the workspace (uses default if not provided)
            custom_properties: Optional dictionary of properties to override defaults
            **kwargs: Additional properties as key-value pairs to override defaults

        Returns:
            Dict containing a configuration with resolved template variables

        Example:
            provider.create_config(
                workspace_name="aws",
                custom_properties={"path": "custom/path"},
                output_dir="outputs"
            )
        """
        # Use default workspace name if not provided
        name = workspace_name
        if not name and custom_properties and "workspace_name" in custom_properties:
            name = custom_properties["workspace_name"]
        if not name:
            name = self._settings.workspace.workspace_name

        # Leverage ConfigCreator directly to create the base config
        config = self._creator.create_config(name)

        # Combine all override properties
        all_overrides = {}
        if custom_properties:
            all_overrides.update(custom_properties)
        if kwargs:
            all_overrides.update(kwargs)

        # If we have workspaces and overrides, apply them to first workspace
        if all_overrides and len(config["workspaces"]) > 0:
            workspace = cast(dict[str, Any], config["workspaces"][0])
            # Apply overrides
            for key, value in all_overrides.items():
                # Special handling for workspace name
                if key == "workspace_name" and "name" in workspace:
                    workspace["name"] = value
                # Handle known workspace properties
                elif key in workspace:
                    workspace[key] = value
                # Add any custom properties to the workspace
                else:
                    # Skip internal keys that shouldn't be in the config
                    if key not in ["workspace_name"]:
                        workspace[key] = value

        # Extract workspace properties from settings to ensure all default keys are included
        if len(config["workspaces"]) > 0:
            workspace = cast(dict[str, Any], config["workspaces"][0])
            # Get workspace defaults from CoregenSettings
            workspace_defaults = {
                "name": self._settings.workspace.workspace_name,
                "context_type": self._settings.workspace.context_type,
                "context_config_files": self._settings.workspace.context_config_files,
                "archive_dir": self._settings.workspace.archive_dir,
                "output_dir": self._settings.workspace.output_dir,
                "workspace_dir": "${name}",
            }

            # Apply any missing defaults
            for key, default_value in workspace_defaults.items():
                if key not in workspace:
                    workspace[key] = default_value

            # Remove internal "contexts" key - not for user configs
            if "contexts" in workspace:
                del workspace["contexts"]

        # Use PathResolver to resolve templates (delegation pattern)
        # This leverages the resolver's specialized template handling
        # Cast ConfigDict to Dict[str, Any] for compatibility
        resolved_config = self._path_resolver.resolve_config_templates(
            cast(dict[str, Any], config)
        )

        return resolved_config

    def process_config_dict(self, config_dict: dict[str, Any]) -> CoregenConfig:
        """
        Process a configuration dictionary into a CoregenConfig model.

        This method validates and processes a configuration dictionary,
        resolving all template variables and paths for use by the program.

        Args:
            config_dict: Raw configuration dictionary

        Returns:
            Fully processed CoregenConfig model

        Raises:
            ValueError: If configuration validation fails
        """
        # Validate the raw configuration structure
        errors = self._validator.validate_config(config_dict)
        if errors:
            self._logger.error("Configuration validation failed")
            for error in errors:
                self._logger.error(f"  • {error}")
            raise ValueError(f"Configuration validation failed: {errors}")

        # Process the configuration
        workspaces = self._processor.process(config_dict)

        # Create and return the config model
        return CoregenConfig(workspaces=workspaces)

    def _ensure_config_loaded(self) -> None:
        """Ensure configuration is loaded."""
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")

    def _delegate_to_config_access(
        self, method_name: str, *args: Any, **kwargs: Any
    ) -> Any:
        """
        Delegate a method call to the config access instance.

        This helper method centralizes the pattern of forwarding method calls to
        the ConfigAccess instance with error handling. It reduces code duplication
        when delegating multiple similar methods.

        Args:
            method_name: Name of the method to call on ConfigAccess
            *args: Positional arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method

        Returns:
            The result of the method call

        Raises:
            RuntimeError: If configuration is not loaded
        """
        self._ensure_config_loaded()
        method = getattr(self._config_access, method_name)
        return method(*args, **kwargs)

    # Access methods that delegate to ConfigAccess
    def find_contexts(self, pattern: str = "*/*", **filters: Any) -> list[Context]:
        """
        Find contexts matching a pattern and filters.

        Args:
            pattern: Pattern to match contexts
            **filters: Property filters

        Returns:
            List of matching contexts
        """
        return cast(
            list[Context],
            self._delegate_to_config_access("find_contexts", pattern, **filters),
        )

    def find_components(
        self, pattern: str = "*/*/*", **filters: Any
    ) -> list[Component]:
        """
        Find components matching a pattern and filters.

        Args:
            pattern: Pattern to match components
            **filters: Property filters

        Returns:
            List of matching components
        """
        return cast(
            list[Component],
            self._delegate_to_config_access("find_components", pattern, **filters),
        )

    def get_workspace(self, name: str) -> WorkspaceConfig | None:
        """
        Get workspace by name.

        Args:
            name: Name of workspace

        Returns:
            WorkspaceConfig or None if not found
        """
        try:
            return cast(
                WorkspaceConfig, self._delegate_to_config_access("get_workspace", name)
            )
        except ValueError:
            self._logger.warning(f"Workspace not found: {name}")
            return None
        except Exception as e:
            self._logger.warning(
                f"Unexpected error getting workspace '{name}': {str(e)}"
            )
            return None

    def get_context(self, path: str) -> Context | None:
        """
        Get context by path.

        Args:
            path: Path to context (typically "workspace_name/context_name")

        Returns:
            Context or None if not found
        """
        try:
            parts = path.split("/")
            if len(parts) < 2:
                self._logger.warning(
                    f"Invalid context path format: {path}. Expected format: workspace/context"
                )
                return None

            return cast(
                Context,
                self._delegate_to_config_access("get_context", parts[0], parts[1]),
            )
        except ValueError as e:
            self._logger.warning(f"Error getting context '{path}': {str(e)}")
            return None
        except Exception as e:
            self._logger.warning(f"Unexpected error getting context '{path}': {str(e)}")
            return None

    def get_component(self, path: str) -> Component | None:
        """
        Get component by path.

        Args:
            path: Path to component (e.g., "workspace/context/component")

        Returns:
            Component or None if not found
        """
        try:
            parts = path.split("/")
            if len(parts) < 3:
                self._logger.warning(
                    f"Invalid component path format: {path}. Expected format: workspace/context/component"
                )
                return None

            return cast(
                Component,
                self._delegate_to_config_access(
                    "get_component", parts[0], parts[1], parts[2]
                ),
            )
        except ValueError as e:
            self._logger.warning(f"Error getting component '{path}': {str(e)}")
            return None
        except Exception as e:
            self._logger.warning(
                f"Unexpected error getting component '{path}': {str(e)}"
            )
            return None

    def resolve_component_paths(
        self, workspace: WorkspaceConfig, context: Context, component: Component
    ) -> dict[str, Path]:
        """
        Resolve paths for a component.

        Args:
            workspace: Workspace containing the context
            context: Context containing the component
            component: Component to resolve paths for

        Returns:
            Dictionary of resolved paths
        """
        try:
            # Delegate path resolution to PathService
            return self.path_service.resolve_component_paths(
                component, context, workspace
            )
        except Exception as e:
            self._logger.warning(
                f"Error resolving paths for component {component.name}: {str(e)}"
            )
            return {}  # Return empty dict on error

    def validate_config(self) -> list[str]:
        """
        Validate the loaded configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        self._ensure_config_loaded()

        errors = []

        try:
            if self._config:
                for workspace in self._config.workspaces:
                    # Check that at least one context was found when not in config mode
                    if not self._config_mode and all(
                        len(contexts) == 0 for contexts in workspace.contexts.values()
                    ):
                        errors.append(
                            f"Workspace '{workspace.name}' has no contexts. Check context_config_files patterns."
                        )

                    # Check each context
                    for context_type, contexts in workspace.contexts.items():
                        for context_name, context in contexts.items():
                            # Check that at least one component was found when not in config mode
                            if not self._config_mode and all(
                                len(components) == 0
                                for components in context.components.values()
                            ):
                                errors.append(
                                    f"Context '{context_name}' has no components. Check component_config_file patterns."
                                )

                        # Path validation is now handled by WorkspaceInitializer
                        # when directories are created or accessed
        except Exception as e:
            self._logger.warning(f"Error validating configuration: {str(e)}")
            errors.append(f"Error validating configuration: {str(e)}")

        return errors

    def has_config(self) -> bool:
        """
        Check if configuration is loaded.

        Returns:
            True if configuration is loaded, False otherwise
        """
        return self._config is not None

    def get_root_path(self) -> Path | None:
        """
        Get the root path for configuration.

        Returns:
            Path to the root directory, or None if not set
        """
        return self.root_path

    def get_config_file_name(self) -> str:
        """
        Get the configuration file name.

        Returns:
            Name of the configuration file from settings
        """
        return self._settings.system.config_file_name

    def get_config(self) -> CoregenConfig | None:
        """
        Get the loaded configuration.

        Returns:
            CoregenConfig instance or None if not loaded
        """
        return self._config
