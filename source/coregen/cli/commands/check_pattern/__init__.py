"""Test Pattern command module."""

import typer

from coregen.cli.cli_functions import get_epilog
from coregen.cli.commands.check_pattern.check_pattern_cli import CheckPattern
from coregen.config_model.models.settings import get_settings

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


def register_check_pattern_commands(app: typer.Typer) -> None:
    """Register the check-pattern command with the application."""

    # Register the check-pattern command directly with the main app
    app.command(
        name="check-pattern",
        help="""Test and analyze pattern matching. Prefixes: w/ (workspace), c/ (context), cm/ (component)

Examples:
    coregen check-pattern "w/aws" --analyze           # Test pattern
    coregen check-pattern "c/*-dev" --analyze         # Test wildcard
    coregen check-pattern "w/aws" --show-rejected     # Show non-matches
    coregen check-pattern "cm/*" --include-inactive --type component
    coregen check-pattern "c/*-dev" --analyze --show-rejected --verbose  # Deep analysis

Related: Use to test patterns before running 'coregen get' or 'coregen generate', debug matching issues, or learn syntax.
""",
        no_args_is_help=False,  # Disable to prevent empty error box
        context_settings=context_settings,
        epilog=get_epilog("check-pattern"),
    )(CheckPattern.callback)
