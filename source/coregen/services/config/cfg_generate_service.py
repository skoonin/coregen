"""
Configuration generation service.

This module provides the service class for generating configuration files.
"""

from pathlib import Path
from typing import Any

from coregen.cli.enums.enum_file_action import FileAction
from coregen.config_model.models.settings import get_settings
from coregen.services.config.cfg_base_service import ConfigServiceBase


class ConfigGenerateService(ConfigServiceBase):
    """Service for generating configuration files.

    This service handles:
    1. Creating new configuration files using settings as the single source of truth
    2. Workspace initialization is temporarily disabled
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the service with required dependencies."""
        super().__init__(*args, **kwargs)
        self.settings = get_settings()

    def generate_config(
        self,
        config_file_path: Path,
        config_file_only: bool | None = None,
        custom_values: dict | None = None,
    ) -> None:
        """Generate a configuration file.

        Args:
            config_file_path: Path to the configuration file
            config_file_only: If True, only generate config file without initializing workspace.
                             If None, use settings default.
            custom_values: Custom values to override defaults
        """
        self.logger.debug(f"Generating configuration at {config_file_path}")
        self.logger.debug(f"Custom values: {custom_values}")

        # Get config_file_only setting if not explicitly provided
        use_config_file_only = (
            config_file_only
            if config_file_only is not None
            else self.settings.options.config.config_file_only
        )

        # Skip generation if file exists and SKIP action is configured
        if config_file_path.exists() and self.file_action == FileAction.SKIP:
            self.console.warning(f"Config file exists at {config_file_path}. Skipping.")
            return

        # Always generate a new config file with our defaults
        self._create_new_config(config_file_path, custom_values or {})

        # Initialize workspace directories unless config_file_only is set
        if not use_config_file_only:
            try:
                # Load processed configuration model for workspace initialization
                config_model = self.config_provider.load_config(config_file_path)
                self.workspace_initializer.initialize_workspace(
                    config=config_model, create_contexts=True
                )
                self.console.info(
                    "Workspace directories initialized based on configuration."
                )
            except Exception as e:
                self.logger.error(f"Workspace initialization failed: {e}")
                raise
        # elif self.dry_run:
        #     self.console.info("Skipping workspace initialization (--dry-run flag set)")
        else:
            # User requested config file only; skip workspace initialization
            self.console.info(
                "Skipping workspace initialization (--config-file-only flag set)"
            )

    def _create_new_config(self, config_file_path: Path, custom_values: dict) -> None:
        """Create a new configuration file.

        Args:
            config_file_path: Path to the configuration file
            custom_values: Custom values to override defaults
        """
        self.logger.info(f"Creating configuration file at {config_file_path}")

        # Track whether file existed before generation
        config_file_path.exists()

        # Create base configuration using provider
        # The provider is already in config_mode with lenient_validation
        config_dict = self.config_provider.create_config(
            custom_properties=custom_values
        )

        # Convert dictionary to YAML
        import yaml

        yaml_content = yaml.safe_dump(
            config_dict, default_flow_style=False, sort_keys=False
        )

        # Ensure parent directory exists
        config_file_path.parent.mkdir(parents=True, exist_ok=True)

        # The file_manager was initialized with the file_action in ConfigServiceBase
        self.file_manager.create_file(config_file_path, yaml_content)

        self.console.info(f"Configuration file created at {config_file_path}")
