"""
Configuration generation service.

This module provides the service class for generating configuration files.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from coregen.cli.enums.enum_file_action import FileAction
from coregen.config_model.models.settings import get_settings
from coregen.services.config.cfg_base_service import ConfigServiceBase


@dataclass
class GenerateConfigResult:
    """Structured outcome of a config-generate operation for the CLI to render.

    Attributes:
        messages: Ordered status lines for the CLI to print.
    """

    messages: list[str] = field(default_factory=list)


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
    ) -> GenerateConfigResult:
        """Generate a configuration file.

        Returns the outcome as structured data; the CLI layer renders it.

        Args:
            config_file_path: Path to the configuration file
            config_file_only: If True, only generate config file without initializing workspace.
                             If None, use settings default.
            custom_values: Custom values to override defaults

        Returns:
            GenerateConfigResult: ordered status messages to render
        """
        self.logger.debug(f"Generating configuration at {config_file_path}")
        self.logger.debug(f"Custom values: {custom_values}")

        messages: list[str] = []

        # Get config_file_only setting if not explicitly provided
        use_config_file_only = (
            config_file_only
            if config_file_only is not None
            else self.settings.options.config.config_file_only
        )

        # Skip generation if file exists and SKIP action is configured
        if config_file_path.exists() and self.file_action == FileAction.SKIP:
            messages.append(
                f"Warning: Config file exists at {config_file_path}. Skipping."
            )
            return GenerateConfigResult(messages=messages)

        # Always generate a new config file with our defaults
        messages.append(self._create_new_config(config_file_path, custom_values or {}))

        # Initialize workspace directories unless config_file_only is set
        if not use_config_file_only:
            try:
                # Load processed configuration model for workspace initialization
                config_model = self.config_provider.load_config(config_file_path)
                self.workspace_initializer.initialize_workspace(
                    config=config_model, create_contexts=True
                )
                messages.append(
                    "Workspace directories initialized based on configuration."
                )
            except Exception as e:
                self.logger.error(f"Workspace initialization failed: {e}")
                raise
        else:
            # User requested config file only; skip workspace initialization
            messages.append(
                "Skipping workspace initialization (--config-file-only flag set)"
            )

        return GenerateConfigResult(messages=messages)

    def _create_new_config(self, config_file_path: Path, custom_values: dict) -> str:
        """Create a new configuration file.

        Args:
            config_file_path: Path to the configuration file
            custom_values: Custom values to override defaults

        Returns:
            Status message describing the created file.
        """
        self.logger.info(f"Creating configuration file at {config_file_path}")

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

        return f"Configuration file created at {config_file_path}"
