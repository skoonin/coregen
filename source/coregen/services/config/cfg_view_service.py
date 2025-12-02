"""
Configuration view service.

This module provides the service class for viewing configuration data
in various formats and with different filtering options.
"""

from pathlib import Path
from typing import Any, Literal

from coregen.cli.enums.enum_output_format import OutputFormat
from coregen.common.console import Console
from coregen.config_model.models.config import CoregenConfig
from coregen.services.config.cfg_view_base_service import ConfigViewBaseService
from coregen.services.config.cfg_view_enhanced_service import (  # Moved import to top
    ConfigEnhancedViewService,
)


class ConfigViewService(ConfigViewBaseService):
    """Service for viewing configuration data.

    This service handles:
    1. Loading and displaying configuration data in different modes:
       - raw: Display the root config file without processing
       - discovered: Display the validated config with discovered contexts
       - resolved: Display the complete processed configuration dictionary
       - enhanced: Display configuration with hierarchical structure and resolved paths/defaults
    2. Formatting output in different formats (text, json, yaml)
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the ConfigViewService."""
        super().__init__(*args, **kwargs)

    def view_config(
        self,
        config_file_path: Path | None = None,
        view_mode: Literal["raw", "discovered", "resolved", "enhanced"] = "raw",
        output_format: OutputFormat = OutputFormat.TEXT,
    ) -> dict[str, Any]:
        """View configuration data in different modes.

        Args:
            config_file_path: Path to the configuration file. If not provided,
                             the default configuration file will be used.
            view_mode: Mode to view the configuration:
                      - "raw": Display the root config file without processing
                      - "discovered": Display configuration with discovered contexts before path resolution
                      - "resolved": Display the fully processed configuration with resolved paths
                      - "enhanced": Display both hierarchical structure and resolved paths/defaults
            output_format: Format for the output

        Returns:
            Dict[str, Any]: Configuration data in the requested mode
        """
        self.logger.debug(f"Viewing configuration in mode: {view_mode}")

        # Determine config file path
        if not config_file_path:
            config_file_path = Path(self.settings.system.config_file_name)
            if not config_file_path.is_absolute():
                config_file_path = Path.cwd() / config_file_path
            Console.debug(f"Using default config file path: {config_file_path}")
        else:
            Console.debug(f"Using provided config file path: {config_file_path}")

        # Ensure file exists
        if not config_file_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file_path}")

        # Handle different view modes by calling methods from base class or enhanced service
        if view_mode == "raw":
            # Inherited from ConfigViewBaseService
            result = self._view_raw_config(config_file_path)
        elif view_mode == "discovered":
            # Inherited from ConfigViewBaseService (fixed version)
            result = self._view_discovered_config(config_file_path)
        elif view_mode == "resolved":
            # Inherited from ConfigViewBaseService (fixed version with mode='json')
            result = self._view_resolved_config(config_file_path)
        elif view_mode == "enhanced":
            # Create enhanced view service instance using base class attributes
            enhanced_service = ConfigEnhancedViewService(
                console=self._console,
                file_manager=self._file_manager,
                workspace_initializer=self._workspace_initializer,
            )
            # Get enhanced view
            result = enhanced_service.view_enhanced_config(config_file_path)
        else:
            raise ValueError(f"Invalid view mode: {view_mode}")

        return result

    def filter_config_data(
        self,
        config: CoregenConfig | dict[str, Any],
        contexts: list[str] | None = None,
        context_type: str | None = None,
        environments: list[str] | None = None,
        components: list[str] | None = None,
        component_type: str | None = None,
        include_active_false: bool = False,
    ) -> dict[str, Any]:
        """Filter configuration data based on provided filters.

        Args:
            config: Configuration object or dictionary to filter
            contexts: List of context names to filter by
            context_type: Context type to filter by
            environments: List of environments to filter by
            components: List of component names to filter by
            component_type: Component type to filter by
            include_active_false: Whether to include inactive components

        Returns:
            Dict[str, Any]: Filtered configuration data
        """
        # Convert config to dictionary if it's not already
        if isinstance(config, CoregenConfig):
            config_dict = config.model_dump(exclude_defaults=False)
        else:
            config_dict = config

        # Create a filtered copy of the configuration
        filtered_config: dict[str, Any] = {"workspaces": []}

        # Copy global settings
        for key, value in config_dict.items():
            if key != "workspaces":
                filtered_config[key] = value

        # Filter workspaces
        for workspace in config_dict.get("workspaces", []):
            # Create a filtered copy of the workspace
            filtered_workspace = {k: v for k, v in workspace.items() if k != "contexts"}
            filtered_workspace["contexts"] = []

            # Filter contexts
            for context in workspace.get("contexts", []):
                # Skip if context name doesn't match filter
                if contexts and context.get("name") not in contexts:
                    continue

                # Skip if context type doesn't match filter
                if context_type and context.get("type") != context_type:
                    continue

                # Skip if environment doesn't match filter
                if environments and context.get("environment") not in environments:
                    continue

                # Create a filtered copy of the context
                filtered_context = {
                    k: v for k, v in context.items() if k != "components"
                }
                filtered_context["components"] = []

                # Filter components
                for component in context.get("components", []):
                    # Skip if component name doesn't match filter
                    if components and component.get("name") not in components:
                        continue

                    # Skip if component type doesn't match filter
                    if component_type and component.get("type") != component_type:
                        continue

                    # Skip inactive components if not including them
                    if not include_active_false and not component.get("active", True):
                        continue

                    # Add component to filtered context
                    filtered_context["components"].append(component)

                # Add context to filtered workspace if it has components or no component filter
                if filtered_context["components"] or not components:
                    filtered_workspace["contexts"].append(filtered_context)

            # Add workspace to filtered config if it has contexts or no context filter
            if filtered_workspace["contexts"] or not (
                contexts or context_type or environments
            ):
                filtered_config["workspaces"].append(filtered_workspace)

        return filtered_config
