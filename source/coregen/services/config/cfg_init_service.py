"""
Configuration initialization service.

This module provides the service class that validates an existing configuration
file and creates the directories it requires.
"""

from dataclasses import dataclass, field
from pathlib import Path

from coregen.services.services_base import ServicesBase


@dataclass
class InitResult:
    """Structured outcome of an init operation for the CLI to render.

    Attributes:
        success: Whether initialization completed without error.
        messages: Ordered status lines (Rich markup) for the CLI to print.
    """

    success: bool
    messages: list[str] = field(default_factory=list)


class ConfigInitService(ServicesBase):
    """Service that validates an existing config file and creates its required paths."""

    def initialize_config(self, config_path: Path) -> InitResult:
        """Initialize configuration and create required paths.

        This method loads an existing config file, verifies its structure,
        and creates all required paths specified in the configuration. It
        returns the outcome as structured data; the CLI layer renders it.

        Args:
            config_path: Path to the configuration file

        Returns:
            InitResult: success flag plus ordered status messages to render
        """
        messages: list[str] = []

        if not config_path.exists():
            self.logger.error(f"Config file not found: {config_path}")
            messages.append(f"[bold red]Config file not found:[/] {config_path}")
            messages.append(
                "Use 'coregen config generate' to create a new configuration file."
            )
            return InitResult(success=False, messages=messages)

        self.logger.debug(f"Loading configuration from {config_path}")
        messages.append(f"Loading configuration from {config_path}")

        # Step 1: Load and validate the configuration
        try:
            config = self.config_provider.load_config(config_path)

            # Check if there were any context validation errors
            if (
                hasattr(self.config_provider, "validation_errors")
                and self.config_provider.validation_errors
            ):
                messages.append(
                    "[bold red]Configuration validation failed due to context errors[/]"
                )
                return InitResult(success=False, messages=messages)

            messages.append("[green]✓[/] Configuration validated successfully")
        except ValueError as e:
            self.logger.error(f"Configuration validation failed: {str(e)}")
            messages.append(f"[bold red]Configuration validation failed:[/] {str(e)}")
            return InitResult(success=False, messages=messages)

        # Step 2: Process the configuration and discover contexts
        # This is handled automatically by the config_provider.load_config method
        messages.append(
            f"[green]✓[/] Discovered {sum(len(ws.contexts.get(ws.context_type, {})) for ws in config.workspaces)} contexts"
        )

        # Step 3: Create required directories
        messages.append("[bold]Creating required directories:[/]")

        # Use WorkspaceInitializer to create all required directories
        try:
            self.workspace_initializer.initialize_workspace(
                config=config, create_contexts=True
            )

            self.logger.info("All required directories created successfully")
            messages.append("[green]✓[/] All required directories created successfully")
            messages.append("[bold green]Configuration initialized successfully[/]")

            return InitResult(success=True, messages=messages)
        except Exception as e:
            self.logger.error(f"Failed to create directories: {str(e)}")
            messages.append(f"[bold red]Failed to create directories:[/] {str(e)}")
            return InitResult(success=False, messages=messages)
