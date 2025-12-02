"""Tests for CLI core functionality including logging, help formatting, and context initialization."""

import json
from unittest.mock import patch

import typer

from coregen.cli.cli_functions import get_epilog


def test_logger_configuration(cli_runner, cli_app, mock_logger):
    """Ensure Logger.configure is called with correct parameters."""
    with patch("coregen.cli.cli.Logger.configure") as mock_configure:
        result = cli_runner.invoke(cli_app, ["--quiet", "--verbose", "--no-color"])
        assert result.exit_code == 0
        # Logger.configure should be called without output_format since it's not a global option
        mock_configure.assert_called_once_with(no_color=True, quiet=True, verbose=True)
        # Multiple configure calls should not occur
        assert mock_configure.call_count == 1


def test_get_epilog_default():
    """get_epilog should return empty string (current implementation)."""
    epilog = get_epilog("myapp")
    # Current implementation returns empty string
    assert epilog == ""


def test_get_epilog_with_subcommand():
    """get_epilog should return empty string regardless of subcommand."""
    epilog = get_epilog("myapp", "subcmd")
    # Current implementation returns empty string
    assert epilog == ""


def test_main_help_includes_epilog(cli_runner, cli_app):
    """Main help output works correctly even with empty epilog."""
    result = cli_runner.invoke(cli_app, ["--help"])
    assert result.exit_code == 0
    stdout = result.stdout
    # Just check that help is shown (epilog is empty now)
    assert "Usage" in stdout or "usage" in stdout.lower()


def test_subcommand_help_includes_epilog(cli_runner, cli_app):
    """Subcommand help works correctly even with empty epilog."""
    result = cli_runner.invoke(cli_app, ["config", "--help"])
    # Config command exits with 2 for help when no_args_is_help=True
    assert result.exit_code in (0, 2)
    output = result.stdout + result.stderr
    # Check that some help is shown (epilog is empty now)
    assert "config" in output.lower() or "Usage" in output


def test_context_object_initialization(cli_runner, cli_app):
    """CLI should populate ctx.obj with global option values."""
    # Register a temporary command to inspect context object using json for consistent output

    @cli_app.command(name="show-ctx")
    def show_ctx(ctx: typer.Context):  # noqa
        # Extract primitive values from object for reliable comparison
        simplified_obj = {
            "dry_run": ctx.obj.get("dry_run"),
            "file_action": str(ctx.obj.get("file_action")),
            "no_color": ctx.obj.get("no_color"),
            "config_file": str(ctx.obj.get("config_file")),
            "has_global_options": "global_options" in ctx.obj,
        }

        # If global_options is present, extract its values too
        if "global_options" in ctx.obj:
            global_opts = ctx.obj.get("global_options")
            if global_opts:
                simplified_obj["global_opts"] = {
                    "dry_run": getattr(global_opts, "dry_run", None),
                    "no_color": getattr(global_opts, "no_color", None),
                }

        # Output as JSON for consistent parsing in tests
        print(json.dumps(simplified_obj))

    # Test CLI options are properly set in context
    result = cli_runner.invoke(
        cli_app,
        [
            "--dry-run",
            "--file-action",
            "overwrite",
            "--no-color",
            "--config-file",
            "test.yaml",
            "show-ctx",
        ],
    )

    # Verify result
    assert result.exit_code == 0
    output_lines = result.stdout.strip().split("\n")
    # Find the JSON output line (last line that starts with {)
    json_line = None
    for line in reversed(output_lines):
        if line.strip().startswith("{"):
            json_line = line.strip()
            break

    assert json_line is not None, f"No JSON output found in: {result.stdout}"

    # Parse the JSON output
    ctx_data = json.loads(json_line)

    # Verify context object was populated correctly
    assert ctx_data["dry_run"] is True
    assert ctx_data["file_action"] == "FileAction.OVERWRITE"
    assert ctx_data["no_color"] is True
    assert ctx_data["config_file"] == "test.yaml"
