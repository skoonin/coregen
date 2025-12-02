"""Config command group."""

from pathlib import Path
from typing import Annotated

import typer

from coregen.cli.cli_functions import get_epilog
from coregen.cli.commands.config.cfg_generate import GenerateCommand
from coregen.cli.commands.config.cfg_init import InitCommand
from coregen.cli.commands.config.cfg_schema import SchemaCommand
from coregen.cli.commands.config.cfg_view import ViewCommand
from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.global_options import GlobalOptions
from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.config_model.models.settings import get_settings

console = Console

# Get settings instance
settings = get_settings()

context_settings = {
    "allow_extra_args": True,
    # "allow_interspersed_args": True,  # This should allow options to be placed anywhere
    # This will make Click ignore unknown options and pass them to subcommands
    "ignore_unknown_options": True,
    "auto_envvar_prefix": "CG",
    "help_option_names": [],
    "show_default": True,
}

option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Global Options",
}


class ConfigCommand:
    """Config command group implementation.

    This class handles the CLI interaction for the config command group
    and manages global options inheritance.
    """

    def __init__(self) -> None:
        """Initialize command instance."""
        self.logger = Logger(self.__class__.__name__)
        self.ctx: typer.Context | None = None
        self.global_options: GlobalOptions | None = None

    @staticmethod
    def callback(
        ctx: typer.Context,
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
        no_color: Annotated[
            bool,
            typer.Option(
                "--no-color", "-nc", help="Disable colored output", **option_params
            ),
        ] = settings.options.global_options.no_color,
        quiet: Annotated[
            bool, typer.Option("--quiet", "-q", help="Suppress output", **option_params)
        ] = settings.options.global_options.quiet,
        verbose: Annotated[
            bool,
            typer.Option(
                "--verbose", "-v", help="Enable verbose output", **option_params
            ),
        ] = settings.options.global_options.verbose,
        config_file: Annotated[
            Path | None,
            typer.Option(
                "--config-file",
                "-c",
                help="Path to config file (.cgconfig.yaml)",
                **option_params,
            ),
        ] = settings.options.global_options.config_file,
    ) -> None:
        """Configuration commands.

        Pattern Prefixes (used in generate, get, check-pattern commands):
            w/  = workspace   (e.g., w/aws matches workspace named 'aws')
            c/  = context     (e.g., c/dev-* matches all contexts starting with 'dev-')
            cm/ = component   (e.g., cm/server matches component named 'server')

        Global Options:
            --dry-run, -d: Show what would be done without making changes
            --file-action, -fa: Action to take when a file exists [ask|skip|overwrite|archive]
            --no-color, -nc: Disable colored output
            --quiet, -q: Suppress output
            --verbose, -v: Show detailed output
        """
        # Check for help flag either from this level or inherited from parent
        parent_help = False
        if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj:
            parent_help = ctx.parent.obj.get("help", False)

        # If help flag is set either locally or from parent
        if help or parent_help:
            # If no subcommand is called, show the appropriate help
            if not ctx.invoked_subcommand:
                typer.echo(ctx.get_help())
                raise typer.Exit()

        # If no subcommand is provided, show help and error message like other commands
        if ctx.invoked_subcommand is None:
            typer.echo(ctx.get_help())
            console.error(
                "Error: Missing subcommand. Use 'config view' to view configuration."
            )
            raise typer.Exit()

        # Initialize context object if needed
        if ctx.obj is None:
            ctx.obj = {}

        # Get parent context values if they exist
        parent_obj = {}
        if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj:
            parent_obj = ctx.parent.obj

        # Merge parent values with local values, preferring explicitly set local values
        # For boolean flags, OR with parent values
        ctx.obj["dry_run"] = dry_run or parent_obj.get("dry_run", False)
        ctx.obj["quiet"] = quiet or parent_obj.get("quiet", False)
        ctx.obj["verbose"] = verbose or parent_obj.get("verbose", False)
        ctx.obj["no_color"] = no_color or parent_obj.get("no_color", False)

        # For help, use parent value if it exists, otherwise use local value
        ctx.obj["help"] = parent_obj.get("help", False) or help

        # For enum options, use local value if explicitly set, otherwise use parent value
        # We can determine if it was explicitly set by comparing with the default
        ctx.obj["file_action"] = (
            file_action
            if file_action != settings.options.global_options.file_action
            or "file_action" not in parent_obj
            else parent_obj["file_action"]
        )

        # Handle config_file - use local value if explicitly set, otherwise use parent value
        ctx.obj["config_file"] = (
            config_file
            if config_file != settings.options.global_options.config_file
            or "config_file" not in parent_obj
            else parent_obj["config_file"]
        )

        # Create and run command
        cmd = ConfigCommand()
        cmd.ctx = ctx
        cmd.run()

    def run(self) -> None:
        """Execute the command logic.

        For group commands, this primarily sets up context for subcommands.
        The actual work is done by the subcommands themselves.
        """
        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Get global options using the standard pattern
        self.global_options = GlobalOptions.from_context(self.ctx)

        # Group commands don't need to do much in run() since
        # the subcommands handle their own logic
        self.logger.debug(
            f"Config command group invoked with subcommand: {self.ctx.invoked_subcommand}"
        )


def register_config_commands(app: typer.Typer) -> None:
    """Register all config commands with the application."""

    config_app = typer.Typer(
        help="Manage configuration settings.",
        no_args_is_help=False,  # Disable to prevent empty error box
        context_settings=context_settings,
    )

    # Register the group callback using the ConfigCommand class
    config_app.callback(invoke_without_command=True)(ConfigCommand.callback)

    # Register individual commands
    config_app.command(
        name="generate",
        help="""Generate configuration files and optionally initialize workspace directories.

Examples:
    coregen config generate -wn my-workspace              # Basic initialization
    coregen config generate -wn my-workspace --config-file-only
    coregen config generate -wn my-workspace --set "key=value"
    coregen config generate -wn my-workspace -ad ./archives -od ./output
    coregen config generate -wn my-workspace --dry-run --verbose  # Preview changes

Related: Use 'coregen config init' to create/update directories from the generated config if not created initially here.
""",
        context_settings=context_settings,
        epilog=get_epilog("config", "generate"),
    )(GenerateCommand.callback)
    config_app.command(
        name="init",
        help="""Creates required workspace directories from existing configuration.

Examples:
    coregen config init                                       # Basic usage
    coregen config init --config-file ./custom/.cgconfig.yaml
    coregen config init --dry-run --verbose

Related: If needed, use 'coregen config generate' first to create config.
""",
        context_settings=context_settings,
        epilog=get_epilog("config", "init"),
    )(InitCommand.callback)
    config_app.command(
        name="schema",
        help="""Display JSON schema for configuration models.

Schema Types:
    settings    - Application settings and defaults
    workspace   - Workspace structure with contexts/components
    context     - Context configuration with components
    component   - Individual component configuration
    all         - All schema types combined

Examples:
    coregen config schema settings                    # Settings schema only
    coregen config schema workspace context           # Multiple schemas
    coregen config schema all --output yaml           # All schemas as YAML
""",
        no_args_is_help=True,
        context_settings=context_settings,
        epilog=get_epilog("config", "schema"),
    )(SchemaCommand.callback)
    # view command with help text
    config_app.command(
        name="view",
        help="""View configuration files in different stages of processing.

Modes: raw | discovered | resolved | enhanced

Examples:
    coregen config view raw                       # As-is from disk
    coregen config view discovered                # With context files merged
    coregen config view resolved                  # Fully processed
    coregen config view enhanced --output json    # With hierarchy + paths
""",
        no_args_is_help=False,
        context_settings=context_settings,
        epilog=get_epilog("config", "view"),
    )(ViewCommand.callback)

    # Add config command group to main app
    app.add_typer(config_app, name="config", epilog=get_epilog("config"))
