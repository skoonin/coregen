"""View configuration command."""

from pathlib import Path
from typing import Annotated, Any

import typer

from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.enums.enum_output_format import OutputFormat
from coregen.cli.enums.enum_view_mode import ViewMode
from coregen.cli.format_validation_mixin import FormatValidationMixin
from coregen.cli.global_options import GlobalOptions
from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.config_model.models.settings import get_settings
from coregen.services.config.cfg_view_service import ConfigViewService

# Get settings instance at module level for default values
settings = get_settings()

option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Global Options",
}

# List of valid view modes
VIEW_MODES = [mode.value for mode in ViewMode]

# app = typer.Typer(help="View configurationss files")


class ViewCommand(FormatValidationMixin):
    """View configuration command."""

    # Define supported formats for the config view command
    SUPPORTED_FORMATS = [
        OutputFormat.YAML,
        OutputFormat.JSON,
    ]
    DEFAULT_FORMAT = settings.options.config.view_output_format

    def __init__(self) -> None:
        """Initialize the view command."""
        self.logger = Logger(__name__)
        self.console = Console
        self.ctx: typer.Context | None = None
        self.options: dict[str, Any] | None = None
        self.view_service: Any | None = None
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
                **{**option_params, "is_eager": True},
            ),
        ] = False,
        config_file: Annotated[
            Path | None,
            typer.Option(
                "--config-file",
                "-c",
                help="Path to config file (.cgconfig.yaml)",
                **option_params,
            ),
        ] = settings.options.global_options.config_file,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                "-d",
                help="Show what would be done without making changes",
                hidden=True,
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
                help="Output format (YAML, JSON)",
                **option_params,
            ),
        ] = settings.options.config.view_output_format,
        file_action: Annotated[
            FileAction,
            typer.Option(
                "--file-action",
                "-fa",
                help="Action to take when file exists",
                hidden=True,
                **option_params,
            ),
        ] = settings.options.global_options.file_action,
        quiet: Annotated[
            bool,
            typer.Option(
                "--quiet",
                "-q",
                help="Suppress output",
                hidden=True,
                **option_params,
            ),
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
        # This is an ARGUMENT instead of an OPTION to allow for multiple view modes
        view_mode: Annotated[
            str | None,
            typer.Argument(help="View mode: (raw|discovered|resolved|enhanced)"),
        ] = ViewMode.RAW.value,
    ) -> None:
        """View configuration in different processing stages.

        Modes: raw (as-is), discovered (context merged), resolved (fully processed), enhanced (hierarchy + paths).
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

        # Store command-specific options in context
        ctx.obj["view_mode"] = view_mode

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
            output_format != settings.options.config.view_output_format
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
        cmd = ViewCommand()
        cmd.ctx = ctx
        cmd.run()

    def _get_options(self) -> dict[str, Any]:
        """Get command options from context with defaults from settings."""
        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Get global options using the standardized pattern
        self.logger.debug(f"ctx.obj before GlobalOptions.from_context: {self.ctx.obj}")
        global_options = GlobalOptions.from_context(self.ctx)
        self.logger.debug(
            f"global_options.config_file after from_context: {global_options.config_file}"
        )
        options = global_options.to_dict()

        # Add command-specific options
        options.update(
            {
                "view_mode": self.ctx.obj.get("view_mode", ViewMode.RAW.value),
                "config_file_path": global_options.config_file
                or Path(settings.system.config_file_name),
                "output_format": self.ctx.obj.get("output_format"),
            }
        )

        return options

    def run(self) -> None:
        """Run the view command."""
        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Get global options first
        self.logger.debug(f"View.run() - ctx.obj: {self.ctx.obj}")
        self.global_options = GlobalOptions.from_context(self.ctx)

        # Get options from context
        self.options = self._get_options()
        self.logger.debug(f"Running view command with options: {self.options}")

        try:
            # Validate output format is supported for this command
            output_format = self.options.get("output_format")
            self.validate_output_format(output_format)

            # Set output format for proper stderr/stdout routing (Output Pipeline pattern)
            self.console.set_output_format(output_format)

            # Initialize the view service with global options
            self.view_service = ConfigViewService(global_options=self.global_options)

            # Get configuration based on view mode
            config_file_path = self.options.get("config_file_path")
            view_mode = self.options.get("view_mode") or ViewMode.RAW.value

            # Fetch configuration via service
            config_data = self.view_service.view_config(
                config_file_path=config_file_path,
                view_mode=view_mode,  # type: ignore[arg-type]
                output_format=output_format,  # type: ignore[arg-type]
            )

            # No need to check for TABLE format since config view only supports YAML and JSON

            # Display the result using console.print which handles formatting
            self.console.print(config_data, output_format=output_format)

        except FileNotFoundError as e:
            self.console.error(f"{str(e)}")
            raise typer.Exit(1)
        except Exception as e:
            self.logger.error(f"Failed to view config: {str(e)}")
            self.logger.exception("Full traceback:")
            self.console.error(f"Failed to view config. {str(e)}")
            raise typer.Exit(1)
        finally:
            # Always reset output format (Output Pipeline pattern)
            self.console.set_output_format(None)


def register(app: typer.Typer) -> None:
    """
    Register the view command with the provided app.

    Args:
        app: The Typer app to register the command with
    """
    # Register the callback function as the main command
    app.callback()(ViewCommand.callback)
