"""
Base configuration view service.

This module provides the base class for viewing configuration data
in various formats and with different filtering options.
"""

from pathlib import Path
from typing import Any

from coregen.config_model.loader import ConfigLoader
from coregen.config_model.models.settings import get_settings
from coregen.services.services_base import ServicesBase


class ConfigViewBaseService(ServicesBase):
    """Base service for viewing configuration data.

    This class provides common functionality for all view-related services.
    It's designed to be inherited by specialized view services.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the configuration view service."""
        super().__init__(*args, **kwargs)
        self.settings = get_settings()
        # Create a separate loader for raw file access
        # Pass the global options from the base class to ConfigLoader
        self.config_loader = ConfigLoader(
            dry_run=self.dry_run,
            file_action=self.file_action,
            quiet=self.quiet,
            verbose=self.verbose,
            no_color=self.no_color,
        )

    def _view_raw_config(self, config_file_path: Path) -> dict[str, Any]:
        """View the raw configuration file exactly as it appears on disk, without any processing.

        Use this to view the original YAML content of your config files.

        Args:
            config_file_path: Path to the config file

        Returns:
            Dict containing the raw config data

        Raises:
            FileNotFoundError: If the config file is not found
        """
        self.logger.debug(f"Viewing raw configuration from: {config_file_path}")

        # Load the raw config file without any processing
        try:
            config_dict = self.config_loader.load_config(config_file_path)
            return config_dict
        except Exception as e:
            self.logger.error(f"Error loading raw configuration: {str(e)}")
            raise

    def _view_discovered_config(self, config_file_path: Path) -> dict[str, Any]:
        """View the configuration with discovered context files merged in, but before path resolution and validation.

        Use this to understand context discovery behavior. This shows the configuration after context discovery
        but before any paths are validated or resolved.

        Args:
            config_file_path: Path to the config file

        Returns:
            Dict containing the fully processed configuration

        Raises:
            FileNotFoundError: If the config file is not found
        """
        self.logger.debug(
            f"Viewing configuration with discovered contexts from: {config_file_path}"
        )

        try:
            # Load the raw config file
            config_dict = self.config_loader.load_config(config_file_path)

            # Discover context configurations
            config_dict = self.config_loader.discover_context_configs(
                config_dict, root_dir=config_file_path.parent
            )

            return config_dict
        except Exception as e:
            self.logger.error(f"Error loading discovered configuration: {str(e)}")
            raise

    def _view_resolved_config(self, config_file_path: Path) -> dict[str, Any]:
        """View the fully processed configuration with all paths resolved and validated.

        This is the final configuration that will be used by the application.
        Includes environment settings, paths, and component configurations.

        Args:
            config_file_path: Path to the config file

        Returns:
            Dict[str, Any]: Validated configuration data
        """
        from coregen.config_model.provider import ConfigurationProvider

        self.logger.debug(
            f"Viewing fully processed configuration from: {config_file_path}"
        )

        try:
            # Create a temporary provider with config_mode=False and lenient_validation=False
            # This will ensure full processing including path resolution
            temp_provider = ConfigurationProvider(
                config_mode=False,  # Process fully
                lenient_validation=False,  # Validate paths strictly
                root_path=config_file_path.parent,  # Set root path to config file directory
            )

            # Load and process the configuration
            config = temp_provider.load_config(config_file_path)

            # Convert to dictionary using JSON mode to ensure Path objects are strings
            config_dict = config.model_dump(mode="json")
            return config_dict
        except Exception as e:
            self.logger.error(f"Error loading resolved configuration: {str(e)}")
            raise
