"""Get command module."""

import typer

from coregen.cli.cli_functions import get_epilog
from coregen.cli.commands.get.get_cli import Get
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


def register_get_commands(app: typer.Typer) -> None:
    """Register the get command with the application.

    Args:
        app: The Typer application to register the command with
    """
    # Register the get command directly with the main app
    app.command(
        name="get",
        help="""Get configuration elements by pattern. Prefixes: w/ (workspace), c/ (context), cm/ (component)

Examples:
    coregen get "w/aws"                               # Get workspace
    coregen get "c/aws-cluster-dev"                   # Specific context
    coregen get "cm/metrics-server"                   # Component by name
    coregen get "c/*-dev"                             # Wildcard: ends with '-dev'
    coregen get "cm/*" --filter "component.config.priority>10"
    coregen get "c/*" --filter "context.name~=aws"    # Regex: contains 'aws'
    coregen get "cm/*" --output json --name-only
    coregen get "c/*" --include-inactive --filter "context.active=false" --verbose  # Debug

Filter Syntax:
    --filter "entity.field=value"      # Exact match (e.g., context.active=true)
    --filter "entity.field>10"         # Comparison (>, <, >=, <=)
    --filter "entity.field~=pattern"   # Regex match (e.g., context.name~=aws)

IMPORTANT: Pattern and filter entity types must match (cm/* with component.*, c/* with context.*).
Related: Use 'coregen check-pattern' to test patterns before running this command.
""",
        no_args_is_help=False,  # Disable to prevent empty error box
        context_settings=context_settings,
        epilog=get_epilog("get"),
    )(Get.callback)
