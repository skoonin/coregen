"""Generate command group."""

import typer

from coregen.cli.cli_functions import get_epilog
from coregen.cli.commands.generate.gen_generate_cli import GenerateCommand
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
    # Disable Rich's automatic error formatting to prevent empty error boxes
    "show_default": True,
}

option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Global Options",
}


def register_generate_commands(app: typer.Typer) -> None:
    """Register the generate command with the application."""

    # Register the generate command directly with the main app using the GenerateCommand class's callback
    app.command(
        name="generate",
        help="""Generate files based on configurations. Prefixes: w/ (workspace), c/ (context), cm/ (component)

Examples:
    coregen generate "w/aws"                          # All in workspace
    coregen generate "c/aws-cluster-dev"              # Specific context
    coregen generate "cm/metrics-server"              # Component by name
    coregen generate "c/*-dev"                        # Wildcard matching
    coregen generate "c/*" --filter "context.environment=dev"
    coregen generate "w/aws" "w/gcp" --dry-run        # Multiple + preview
    coregen generate "c/dev-*" --include-inactive --output-dir /tmp/output
    coregen generate "cm/*" --filter "component.config.priority>5" --verbose --dry-run  # Debug

Filter Syntax:
    --filter "entity.field=value"      # Exact match (e.g., context.active=true)
    --filter "entity.field>10"         # Comparison (>, <, >=, <=)
    --filter "entity.field~=pattern"   # Regex match (e.g., context.name~=aws)

IMPORTANT: All patterns MUST have prefixes. A pattern can be filtered by its own
or an ancestor entity's fields (e.g. cm/* with component.*, context.*, or
workspace.*); a filter on a more specific entity than the pattern is rejected.
Related: Use 'coregen check-pattern' to test patterns before running this command.
""",
        no_args_is_help=False,  # Disable automatic help to prevent conflict
        context_settings=context_settings,
        epilog=get_epilog("generate"),
    )(GenerateCommand.callback)
