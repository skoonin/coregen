"""Generate configuration command."""

from pathlib import Path
from typing import Annotated, Any

import typer

from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.enums.enum_output_format import OutputFormat
from coregen.cli.global_options import GlobalOptions
from coregen.common.logger import Logger
from coregen.common.path_service import PathService
from coregen.config_model.models.settings import get_settings
from coregen.services.config.cfg_generate_service import ConfigGenerateService

# Get settings instance at module level for default values
settings = get_settings()

option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Global Options",
}

path_params = {
    "exists": False,
    "file_okay": True,
    "dir_okay": True,  # Allow both files and directories
    "writable": True,
    "readable": True,
    "resolve_path": True,
    "rich_help_panel": "Generate Options",
}

# Define separate params for config file which should be a file, not a directory
config_file_params = {
    "exists": False,
    "file_okay": True,
    "dir_okay": False,  # Config file should not be a directory
    "writable": True,
    "readable": True,
    "resolve_path": True,
    "rich_help_panel": "Generate Options",
}

generate_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Generate Options",
}


class GenerateCommand:
    """Generate configuration command.

    This command generates a configuration file and optionally initializes workspace directories.
    It supports both creating new configurations and updating existing ones.
    """

    def __init__(self) -> None:
        """Initialize the command."""
        self.logger = Logger(__name__)
        self.ctx: typer.Context | None = None
        self.options: dict[str, Any] | None = None
        self.service: Any | None = None
        self.path_service = PathService()
        self.global_options: GlobalOptions | None = None
        self.console: Any | None = None

    @staticmethod
    def callback(
        ctx: typer.Context,  # Used to access global options from context
        # Config generate options
        output_config_path: Annotated[
            Path,
            typer.Option(
                "--output-config",
                "-oc",
                help="Path to output configuration file",
                **config_file_params,
            ),
        ] = Path(settings.system.config_file_name),
        config_file_only: Annotated[
            bool,
            typer.Option(
                "--config-file-only",
                "-cf",
                help="Generate only the config file without creating directories",
                **generate_params,
            ),
        ] = settings.options.config.config_file_only,
        # Generate Options - core workspace schema fields
        workspace_name: Annotated[
            str | None,
            typer.Option(
                "--workspace-name",
                "-wn",
                help="Name of the workspace to generate",
                **generate_params,
            ),
        ] = settings.workspace.workspace_name,
        # Generate Options - relevant for workspace level
        archive_dir: Annotated[
            Path | None,
            typer.Option(
                "--archive-dir",
                "-ad",
                help=f"Path to archive directory",
                **path_params,
            ),
        ] = Path(settings.workspace.archive_dir),
        output_dir: Annotated[
            Path | None,
            typer.Option(
                "--output-dir",
                "-od",
                help=f"Path to output directory",
                **path_params,
            ),
        ] = Path(settings.workspace.output_dir),
        workspace_dir: Annotated[
            Path | None,
            typer.Option(
                "--workspace-dir",
                "-wd",
                help=f"Path to workspace directory",
                **path_params,
            ),
        ] = Path(settings.workspace.workspace_dir),
        # Context type option
        context_type: Annotated[
            str | None,
            typer.Option(
                "--context-type",
                "-ct",
                help="Type name for contexts in this workspace",
                **generate_params,
            ),
        ] = settings.workspace.context_type,
        # Context config pattern option
        context_config_files: Annotated[
            list[str] | None,
            typer.Option(
                "--context-config-pattern",
                "-ccp",
                help="File patterns for context discovery",
                **generate_params,
            ),
        ] = settings.workspace.context_config_files,
        # Custom key-value pairs option
        set_values: Annotated[
            list[str] | None,
            typer.Option(
                "--set",
                "-s",
                help="Set custom key-value pairs (format: key=value)",
                **generate_params,
            ),
        ] = None,
        # Global options
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
                help="Path to config file (.cgconfig.yaml)",
                exists=False,
                file_okay=True,
                dir_okay=False,
                readable=True,
                resolve_path=False,  # Don't resolve non-existent paths
                hidden=True,  # Hide this option from config generate
                rich_help_panel="Global Options",
            ),
        ] = settings.options.global_options.config_file,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                "-d",
                help="Show what would be done without making changes",
                rich_help_panel="Global Options",
            ),
        ] = settings.options.global_options.dry_run,
        no_color: Annotated[
            bool,
            typer.Option(
                "--no-color",
                "-nc",
                help="Disable colored output",
                rich_help_panel="Global Options",
            ),
        ] = settings.options.global_options.no_color,
        output_format: Annotated[
            OutputFormat,
            typer.Option(
                "--output",
                "-o",
                help="Output format",
                hidden=True,  # Hide this from the help output
                rich_help_panel="Global Options",
            ),
        ] = settings.options.config.generate_output_format,
        file_action: Annotated[
            FileAction,
            typer.Option(
                "--file-action",
                "-fa",
                help="Action to take when file exists",
                rich_help_panel="Global Options",
            ),
        ] = settings.options.global_options.file_action,
        quiet: Annotated[
            bool,
            typer.Option(
                "--quiet",
                "-q",
                help="Suppress output",
                rich_help_panel="Global Options",
            ),
        ] = settings.options.global_options.quiet,
        verbose: Annotated[
            bool,
            typer.Option(
                "--verbose",
                "-v",
                help="Enable verbose output",
                rich_help_panel="Global Options",
            ),
        ] = settings.options.global_options.verbose,
    ) -> None:
        """Generate configuration file and optionally initialize workspace directories.

        Creates workspace config from settings defaults and custom values.
        If --config-file-only not set, also initializes workspace directories.
        """

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
        ctx.obj["output_config_path"] = output_config_path
        ctx.obj["config_file_only"] = config_file_only
        ctx.obj["workspace_name"] = workspace_name
        ctx.obj["archive_dir"] = archive_dir
        ctx.obj["output_dir"] = output_dir
        ctx.obj["workspace_dir"] = workspace_dir
        ctx.obj["context_type"] = context_type
        ctx.obj["context_config_files"] = context_config_files
        ctx.obj["set_values"] = set_values

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
            output_format != settings.options.config.generate_output_format
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
        cmd = GenerateCommand()
        cmd.ctx = ctx
        cmd.run()

    def _get_options(self) -> dict[str, Any]:
        """Get command options from context with defaults from settings."""

        if not self.ctx:
            raise RuntimeError("Context not initialized")
        # Get global options using the standardized pattern
        global_options = GlobalOptions.from_context(self.ctx)
        options = global_options.to_dict()

        # Add command-specific options
        options.update(
            {
                "output_config_path": self.ctx.obj.get(
                    "output_config_path", Path(settings.system.config_file_name)
                ),
                "config_file_only": self.ctx.obj.get(
                    "config_file_only", settings.options.config.config_file_only
                ),
                "workspace_name": self.ctx.obj.get(
                    "workspace_name", settings.workspace.workspace_name
                ),
                "archive_dir": self.ctx.obj.get(
                    "archive_dir", Path(settings.workspace.archive_dir)
                ),
                "output_dir": self.ctx.obj.get(
                    "output_dir", Path(settings.workspace.output_dir)
                ),
                "workspace_dir": self.ctx.obj.get(
                    "workspace_dir", Path(settings.workspace.workspace_dir)
                ),
                "context_type": self.ctx.obj.get(
                    "context_type", settings.workspace.context_type
                ),
                "context_config_files": self.ctx.obj.get(
                    "context_config_files", settings.workspace.context_config_files
                ),
                "set_values": self.ctx.obj.get("set_values", None),
            }
        )

        return options

    def run(self) -> None:
        """Run the generate command."""
        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Get global options first
        self.global_options = GlobalOptions.from_context(self.ctx)

        # Get options from context
        self.options = self._get_options()
        self.logger.debug(f"Running generate command with options: {self.options}")
        self.logger.debug(f"File action: {self.global_options.file_action}")

        try:

            # Create service instance with global options
            self.service = ConfigGenerateService(global_options=self.global_options)
            self.console = self.service.console

            # Collect custom values from options - focused on workspace level only
            custom_values = {}

            # Add workspace name
            custom_values["name"] = self.options["workspace_name"]

            # Add workspace options to custom values as relative paths
            custom_values["archive_dir"] = self.path_service.make_path_relative(
                self.options["archive_dir"]
            )
            custom_values["output_dir"] = self.path_service.make_path_relative(
                self.options["output_dir"]
            )
            # Removed redundant workspace_dir field

            # Add context type option
            custom_values["context_type"] = self.options["context_type"]

            # Add context config pattern if provided
            if self.options["context_config_files"]:
                custom_values["context_config_files"] = self.options[
                    "context_config_files"
                ]

            # Process custom key-value pairs from --set option
            if self.options["set_values"]:

                for kv_pair in self.options["set_values"]:
                    try:
                        # Split by the first equals sign
                        key, value = kv_pair.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Handle special value conversions
                        if value.lower() == "true":
                            value = True
                        elif value.lower() == "false":
                            value = False
                        elif value.isdigit():
                            value = int(value)
                        elif (
                            value.replace(".", "", 1).isdigit()
                            and value.count(".") == 1
                        ):
                            value = float(value)

                        # Add to custom values
                        custom_values[key] = value

                    except ValueError:
                        self.logger.warning(
                            f"Invalid key-value pair format: {kv_pair}. Expected format: key=value"
                        )

            self.logger.debug(f"Custom values: {custom_values}")

            # Generate configuration with config_file_only option
            self.service.generate_config(
                config_file_path=self.options["output_config_path"],
                config_file_only=self.options["config_file_only"],
                custom_values=custom_values,
            )

        except FileNotFoundError as e:
            self.logger.error(f"Config file not found: {str(e)}")
            if self.console:
                self.console.error(f"{str(e)}")
            raise typer.Exit(1)
        except Exception as e:
            self.logger.error(f"Failed to generate config: {str(e)}")
            if self.console:
                self.console.error(f"Failed to generate config. {str(e)}")
            raise typer.Exit(1)
