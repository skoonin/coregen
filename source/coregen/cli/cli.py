"""Main CLI application module."""

import shutil
from pathlib import Path
from typing import Annotated

import typer

from coregen import PROGRAM_NAME, __version__
from coregen.cli.cli_functions import get_epilog
from coregen.cli.commands.check_pattern import register_check_pattern_commands
from coregen.cli.commands.config import register_config_commands
from coregen.cli.commands.detect_changes import register_detect_changes_commands
from coregen.cli.commands.generate import register_generate_commands
from coregen.cli.commands.get import register_get_commands
from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.logger import Logger
from coregen.config_model.models.settings import get_settings

# Get default values from our model settings
settings = get_settings()
logger = Logger(__name__)

context_settings = {
    "allow_extra_args": True,
    # Allows options to be placed anywhere on the command line
    "allow_interspersed_args": True,
    # This will make Click ignore unknown options and pass them to subcommands
    "ignore_unknown_options": True,
    "auto_envvar_prefix": "CG",  # Enable environment variable support
    "help_option_names": [],  # we manually pass help option names
    "show_default": True,  # Always show default values in help
    # Use full terminal width for help text
    "max_content_width": shutil.get_terminal_size().columns,
}

# Our default option params
# Amend or override with **{**option_params, "is_eager": False}
option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "is_eager": True,
    "rich_help_panel": "Global Options",
}

# ------------------- Main Application ------------------- #

app = typer.Typer(
    rich_markup_mode="rich",
    no_args_is_help=False,
    help=f"{PROGRAM_NAME}: A flexible code generation and management tool.\n\n  v{__version__}",
    context_settings=context_settings,
    epilog=get_epilog(PROGRAM_NAME),
    add_completion=False,
)

# --------------- Main Application Callback -------------- #


@app.callback(rich_help_panel="Global Options", invoke_without_command=True)  # type: ignore[misc]
def main(
    ctx: typer.Context,
    help: Annotated[
        bool,
        typer.Option(
            "--help", "-h", help="Show this message and exit.", **option_params
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Show what would be done without making changes",
            hidden=True,  # Hide this from the main help output
            **option_params,
        ),
    ] = settings.options.global_options.dry_run,
    no_color: Annotated[
        bool,
        typer.Option(
            "--no-color", "-nc", help="Disable colored output", **option_params
        ),
    ] = settings.options.global_options.no_color,
    file_action: Annotated[
        FileAction,
        typer.Option(
            "--file-action",
            "-fa",
            help="Action to take when file exists",
            hidden=True,  # Hide this from the main help output
            **option_params,
        ),
    ] = settings.options.global_options.file_action,
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config-file",
            "-c",
            help="Path to config file (.cgconfig.yaml)",
            hidden=True,  # Hide this from the main help output
            **option_params,
        ),
    ] = settings.options.global_options.config_file,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress output", **option_params),
    ] = settings.options.global_options.quiet,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output", **option_params),
    ] = settings.options.global_options.verbose,
) -> None:
    """Initialize CLI and set global options.

    This callback processes global options and initializes the logger and console settings.
    All global options are defined here so they show up in the help output.

    Global Options:
        --dry-run, -d: Show what would be done without making changes
        --file-action, -fa: Action to take when file exists [ask|skip|overwrite|archive]
        --no-color, -nc: Disable colored output
        --output, -o: Output format [text|json|yaml|matrix|table]
        --config-file, -c: Path to config file (.cgconfig.yaml)
        --quiet, -q: Suppress output
        --verbose, -v: Show detailed output
    """
    # Check for help flag explicitly
    if help:
        # If help is true and there's a subcommand, we want to pass through to let the subcommand show its help
        if not ctx.invoked_subcommand:
            # No subcommand, show the main help
            typer.echo(ctx.get_help())
            raise typer.Exit()
        # Otherwise, we'll let the subcommand handle its own help

    # Create or update global options dictionary
    if ctx.obj is None:
        ctx.obj = {}

    # Import GlobalOptions class
    from coregen.cli.global_options import GlobalOptions

    # Create a GlobalOptions instance with the values from command line
    global_options = GlobalOptions(
        dry_run=dry_run,
        file_action=file_action,
        no_color=no_color,
        quiet=quiet,
        verbose=verbose,
        config_file=config_file,
        debug=False,  # Default to debug=False
    )

    # Store all options directly in context object (backward compatibility)
    ctx.obj["dry_run"] = dry_run
    ctx.obj["file_action"] = file_action
    ctx.obj["no_color"] = no_color
    ctx.obj["quiet"] = quiet
    ctx.obj["verbose"] = verbose
    ctx.obj["help"] = help  # Store help flag in context for subcommands

    # Store config_file with debug logging
    logger.debug(f"Setting config_file in context to: {config_file}")
    ctx.obj["config_file"] = config_file

    # Store GlobalOptions instance in context for easy access by subcommands
    ctx.obj["global_options"] = global_options
    logger.debug(f"Stored GlobalOptions in context: {global_options}")

    # Configure logger output settings
    Logger.configure(
        no_color=no_color,
        quiet=quiet,
        verbose=verbose,
    )

    # Configure console for user-facing output
    # This is separate from logger configuration to maintain clear separation of concerns
    from coregen.common.console import Console

    Console.setup_for_user(
        no_color=no_color,
        quiet=quiet,
        verbose=verbose,
        dry_run=dry_run,
    )

    # Log the final state
    logger.debug(
        f"Main callback with file_action={file_action}, dry_run={dry_run}, quiet={quiet}, verbose={verbose}, no_color={no_color}, config_file={config_file}"
    )

    logger.debug(f"Invoking subcommand: {ctx.invoked_subcommand}")

    # If no subcommand is provided, show help and helpful error message
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        # Import Console here to avoid circular imports
        from coregen.common.console import Console

        Console.error(
            "Missing command. Try 'coregen generate', 'coregen get', or 'coregen config view'."
        )
        raise typer.Exit()


# Register command groups first
register_config_commands(app)
register_check_pattern_commands(app)
register_detect_changes_commands(app)
register_generate_commands(app)
register_get_commands(app)


# Then define and register the version command (move this code from above)
@app.command(  # type: ignore[misc]
    name="version",
    help="Show the version of coregen",
    no_args_is_help=False,
    rich_help_panel="Utilities",
)
def version(_: typer.Context) -> None:
    """Show the version of coregen."""
    typer.echo(f"v{__version__}")


# Entry point for the application
if __name__ == "__main__":
    app()
