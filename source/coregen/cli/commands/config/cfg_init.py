"""Initialize configuration command."""

from pathlib import Path
from typing import Annotated, Any

import typer

from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.enums.enum_output_format import OutputFormat
from coregen.cli.global_options import GlobalOptions
from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.config_model.models.settings import get_settings
from coregen.services.config.cfg_init_service import ConfigInitService

# Get settings instance at module level for default values
settings = get_settings()

option_params = {
    "case_sensitive": False,
    "show_choices": True,
    "show_default": True,
    "rich_help_panel": "Global Options",
}


class InitCommand:
    """Initialize workspace directories command.

    This command loads an existing configuration file, verifies its structure,
    and creates all required workspace directories as specified in the configuration.
    This command does NOT generate configuration files.
    """

    def __init__(self) -> None:
        """Initialize InitCommand."""
        self.logger = Logger(__name__)
        self.console = Console
        self.ctx: typer.Context | None = None
        self.options: dict[str, Any] | None = None
        self.service: Any | None = None
        self.global_options: GlobalOptions | None = None

    @staticmethod
    def callback(
        ctx: typer.Context,
        help: Annotated[
            bool,
            typer.Option(
                "--help",
                "-h",
                help="Show this message and exit.",
                show_envvar=False,
                **{**option_params, "is_eager": True},
            ),
        ] = False,
        config_file: Annotated[
            Path | None,
            typer.Option(
                "--config-file",
                "-c",
                help="Path to configuration file",
                exists=False,
                file_okay=True,
                dir_okay=False,
                writable=False,
                readable=True,
                resolve_path=False,  # Don't resolve non-existent paths
                **option_params,
            ),
        ] = settings.options.global_options.config_file,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                "-d",
                help="Show what would be done without making changes",
                **option_params,
            ),
        ] = settings.options.global_options.dry_run,
        no_color: Annotated[
            bool,
            typer.Option(
                "--no-color",
                "-nc",
                help="Disable colored output",
                **option_params,
            ),
        ] = settings.options.global_options.no_color,
        output_format: Annotated[
            OutputFormat,
            typer.Option(
                "--output",
                "-o",
                help="Output format",
                hidden=True,
                **option_params,
            ),
        ] = settings.options.config.init_output_format,
        file_action: Annotated[
            FileAction,
            typer.Option(
                "--file-action",
                "-fa",
                help="Action to take when file exists",
                **option_params,
            ),
        ] = settings.options.global_options.file_action,
        quiet: Annotated[
            bool, typer.Option("--quiet", "-q", help="Suppress output", **option_params)
        ] = settings.options.global_options.quiet,
        verbose: Annotated[
            bool,
            typer.Option(
                "--verbose",
                "-v",
                help="Enable verbose output",
                **option_params,
            ),
        ] = settings.options.global_options.verbose,
    ) -> None:
        """Create workspace directories from existing configuration file.

        Loads config file, verifies structure, and creates directories.
        Does NOT generate config files - use 'config generate' first.
        """
        Logger(__name__)

        # Check for help flag explicitly in parent context first
        parent_help = False
        if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj:
            parent_help = ctx.parent.obj.get("help", False)
        if help or parent_help:
            typer.echo(ctx.get_help())
            raise typer.Exit()

        # Ensure ctx.obj exists and inherit from parent
        if ctx.obj is None:
            ctx.obj = {}
            # If parent has ctx.obj, inherit it
            if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj:
                ctx.obj.update(ctx.parent.obj)

        # For global options in subcommands, we need to handle inheritance properly
        # Only override parent values if the local value was explicitly provided
        # For boolean flags, use OR logic with parent
        parent_obj = (
            ctx.parent.obj
            if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj
            else {}
        )

        ctx.obj["dry_run"] = dry_run or parent_obj.get("dry_run", False)
        ctx.obj["no_color"] = no_color or parent_obj.get("no_color", False)
        ctx.obj["quiet"] = quiet or parent_obj.get("quiet", False)
        ctx.obj["verbose"] = verbose or parent_obj.get("verbose", False)

        # For non-boolean options, check if they differ from defaults
        if (
            output_format != settings.options.config.init_output_format
            or "output_format" not in parent_obj
        ):
            ctx.obj["output_format"] = output_format

        if (
            file_action != settings.options.global_options.file_action
            or "file_action" not in parent_obj
        ):
            ctx.obj["file_action"] = file_action

        # For config_file, only override if explicitly provided (different from default)
        if (
            config_file != settings.options.global_options.config_file
            or "config_file" not in parent_obj
        ):
            ctx.obj["config_file"] = config_file

        # Create and run command
        cmd = InitCommand()
        cmd.ctx = ctx
        cmd.run()

    def _get_options(self) -> dict[str, Any]:
        """Get command options from context with defaults from settings.cli."""
        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Get global options using the standardized pattern
        global_options = GlobalOptions.from_context(self.ctx)
        options = global_options.to_dict()

        # No command-specific options for init command
        return options

    def run(self) -> None:
        """Run the init command."""
        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Get global options first
        self.global_options = GlobalOptions.from_context(self.ctx)

        # Get options from context
        self.options = self._get_options()
        self.logger.debug(f"Running init command with options: {self.options}")

        try:
            # Get config path from global options
            config_path = self.global_options.config_file
            self.logger.debug(f"Config path from global options: {config_path}")
            self.logger.debug(
                f"ctx.obj config_file: {self.ctx.obj.get('config_file') if self.ctx.obj else 'No ctx.obj'}"
            )

            # Ensure we use the actual config path specified
            if not config_path:
                raise ValueError("No config file path specified")

            # Initialize the service with global options
            self.service = ConfigInitService(global_options=self.global_options)

            # Delegate to the service to handle the business logic
            success = self.service.initialize_config(config_path)

            # Exit with appropriate code
            if not success:
                raise typer.Exit(1)

        except typer.Exit as e:
            # Re-raise typer.Exit exceptions
            raise e
        except FileNotFoundError as e:
            self.logger.error(f"Config file not found: {str(e)}")
            self.console.error(f"{str(e)}")
            raise typer.Exit(1)
        except Exception as e:
            self.logger.error(f"Failed to initialize config: {str(e)}")
            self.console.error(f"Failed to initialize config. {str(e)}")
            raise typer.Exit(1)
