"""Detect Changes command module."""

import typer

from coregen.cli.cli_functions import get_epilog
from coregen.cli.commands.detect_changes.detect_changes_cli import DetectChanges
from coregen.config_model.models.settings import get_settings

# Get settings instance
settings = get_settings()

context_settings = {
    "allow_extra_args": False,
    # "allow_interspersed_args": True,
    "ignore_unknown_options": True,
    "auto_envvar_prefix": "CG",
    "help_option_names": ["--help", "-h"],
    "show_default": True,
}

option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Global Options",
}


def register_detect_changes_commands(app: typer.Typer) -> None:
    """Register the detect-changes command with the application.

    Args:
        app: The Typer application to register the command with
    """
    # Register the detect-changes command directly with the main app
    app.command(
        name="detect-changes",
        help="""Detect components changed between branches by comparing generated output.

Status: changed | deleted
Reason: direct | deleted | required_cascade (required component changed triggers all in context)

Examples:
    coregen detect-changes                                # Current vs main
    coregen detect-changes --base-branch develop --output matrix
    coregen detect-changes --name-only --changed-only
    coregen detect-changes --filter "context.name~=aws"
    coregen detect-changes --deleted-only --output json
    coregen detect-changes --include-required-changes    # Include cascade info
    coregen detect-changes --keep-generated --output-dir /tmp/debug  # Debug mode
    coregen detect-changes --base-branch develop --changed-only --output matrix --verbose  # CI/CD analysis

Filter Syntax:
    --filter "entity.field=value"      # Exact match (e.g., context.active=true)
    --filter "entity.field>10"         # Comparison (>, <, >=, <=)
    --filter "entity.field~=pattern"   # Regex match (e.g., context.name~=aws)

Related: Use 'coregen generate' to create files, then compare branches with this command.
""",
        no_args_is_help=False,
        context_settings=context_settings,
        epilog=get_epilog("detect-changes"),
    )(DetectChanges.callback)
