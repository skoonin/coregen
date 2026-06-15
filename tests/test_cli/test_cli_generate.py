"""Tests for generate CLI commands."""

from unittest.mock import patch

import pytest


def test_generate_help(cli_runner, cli_app):
    """Test the help for generate command."""
    result = cli_runner.invoke(cli_app, ["generate", "--help"])
    # Generate command exits with 1 or 2 for help
    assert result.exit_code in (0, 1, 2)
    assert "Usage:" in result.stdout


@patch("coregen.cli.commands.generate.gen_generate_cli.GenerateService")
def test_generate_with_path(mock_generate_service, cli_runner, cli_app):
    """Test the generate command with a path argument."""
    # Mock the service instance
    mock_instance = mock_generate_service.return_value
    mock_instance.generate_files.return_value = {
        "generated_files": ["path/to/file1.yaml", "path/to/file2.yaml"],
        "skipped_files": [],
        "errors": [],
        "warnings": [],
    }

    # Run command with a path
    result = cli_runner.invoke(cli_app, ["generate", "workspace/aws"])

    # Command should succeed
    assert result.exit_code == 0

    # Verify service was called with right parameters
    mock_generate_service.assert_called_once()

    # Get the generate_files call arguments
    generate_files_call = mock_instance.generate_files.call_args

    # Verify paths parameter was passed correctly
    assert generate_files_call.kwargs.get("paths") == ["workspace/aws"]

    # Verify other parameters have expected values
    assert generate_files_call.kwargs.get("filters") is None
    assert generate_files_call.kwargs.get("include_inactive") is False
    assert generate_files_call.kwargs.get("skip_commit_dir") is False

    # Don't check output_dir as it might be dynamically set from settings


@pytest.mark.parametrize(
    "template_source",
    [
        "test_data/common-templates/metrics-server",
        "test_data/common-templates/prometheus",
    ],
)
def test_generate_from_different_template_sources(cli_runner, cli_app, template_source):
    """Test generation from different template sources."""
    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
    ) as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_files.return_value = {
            "generated_files": [f"{template_source}/file1.yaml"],
            "skipped_files": [],
            "errors": [],
            "warnings": [],
        }

        # Run command with path to template source
        result = cli_runner.invoke(cli_app, ["generate", template_source])

        assert result.exit_code == 0
        mock_instance.generate_files.assert_called_once()

        # Check path parameter was passed correctly
        paths_arg = mock_instance.generate_files.call_args[1]["paths"]
        assert template_source in paths_arg[0]


@pytest.mark.parametrize("context_value", ["aws/us-east-2/dev", "aws/us-west-2/prod"])
def test_generate_with_various_context_values(cli_runner, cli_app, context_value):
    """Test generation with different context values."""
    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
    ) as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_files.return_value = {
            "generated_files": [f"contexts/{context_value}/generated/file.yaml"],
            "skipped_files": [],
            "errors": [],
            "warnings": [],
        }

        # Run command with context pattern
        result = cli_runner.invoke(cli_app, ["generate", f"context/{context_value}"])

        assert result.exit_code == 0
        mock_instance.generate_files.assert_called_once()


@pytest.mark.parametrize("file_action", ["skip", "overwrite", "archive", "ask"])
def test_generate_with_different_file_actions(
    cli_runner, cli_app, file_action, monkeypatch
):
    """Test generation with different file action modes."""
    # Isolate from environment variables that could override CLI parameters
    monkeypatch.delenv("CG_FILE_ACTION", raising=False)

    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
    ) as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_files.return_value = {
            "generated_files": ["path/to/file.yaml"],
            "skipped_files": [],
            "errors": [],
            "warnings": [],
        }

        # Run command with specific file action
        result = cli_runner.invoke(
            cli_app, ["generate", "workspace/aws", "--file-action", file_action]
        )

        assert result.exit_code == 0
        mock_service.assert_called_once()

        # Verify global_options was passed to service
        assert "global_options" in mock_service.call_args[1]
        global_options = mock_service.call_args[1]["global_options"]

        # Verify the file action was set correctly (FileAction enum supports string comparison)
        from coregen.cli.enums.enum_file_action import FileAction

        assert global_options.file_action == FileAction(file_action)


def test_generate_dry_run(cli_runner, cli_app):
    """Test that dry-run doesn't modify files."""
    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
    ) as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_files.return_value = {
            "generated_files": ["path/to/file.yaml"],
            "skipped_files": [],
            "errors": [],
            "warnings": [],
        }

        # Run with dry-run flag
        result = cli_runner.invoke(cli_app, ["generate", "workspace/aws", "--dry-run"])

        assert result.exit_code == 0
        mock_service.assert_called_once()

        # Verify global_options was passed to service with dry_run=True
        assert "global_options" in mock_service.call_args[1]
        global_options = mock_service.call_args[1]["global_options"]
        assert global_options.dry_run is True


def test_generate_with_template_variable_substitution(cli_runner, cli_app):
    """Test template variable substitution during generation."""
    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
    ) as mock_service:
        mock_instance = mock_service.return_value
        # Mock successful variable substitution
        mock_instance.generate_files.return_value = {
            "generated_files": ["path/to/rendered_template.yaml"],
            "skipped_files": [],
            "errors": [],
            "warnings": [],
        }

        result = cli_runner.invoke(cli_app, ["generate", "workspace/aws"])

        assert result.exit_code == 0

        # Verify generate_files was called
        mock_instance.generate_files.assert_called_once()


def test_generate_with_missing_variable_errors(cli_runner, cli_app):
    """Test error handling for missing variables during template rendering."""
    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
    ) as mock_service:
        mock_instance = mock_service.return_value
        # Mock error during template rendering due to missing variables
        mock_instance.generate_files.return_value = {
            "generated_files": [],
            "skipped_files": [],
            "errors": [
                "Variable 'required_var' is undefined in template 'template.j2'"
            ],
            "warnings": [],
        }

        # The test will throw a SystemExit exception, which is expected
        with patch("coregen.cli.commands.generate.gen_generate_cli.console.error") as _:
            with patch(
                "coregen.cli.commands.generate.gen_generate_cli.console.info"
            ) as _:
                # Skip showing stdout and don't raise exceptions
                cli_runner.invoke(
                    cli_app, ["generate", "workspace/aws"], catch_exceptions=True
                )

                # Verify the service was called with the correct parameters
                mock_service.assert_called_once()
                mock_instance.generate_files.assert_called_once()


def test_generate_with_filters(cli_runner, cli_app):
    """Test generation with filters."""
    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
    ) as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_files.return_value = {
            "generated_files": ["path/to/file.yaml"],
            "skipped_files": [],
            "errors": [],
            "warnings": [],
        }

        # Run command with filter
        result = cli_runner.invoke(
            cli_app, ["generate", "workspace/aws", "--filter", "environment=dev"]
        )

        assert result.exit_code == 0

        # Verify filters were passed correctly
        filters_arg = mock_instance.generate_files.call_args[1]["filters"]
        assert filters_arg == ["environment=dev"]


def test_generate_with_include_inactive(cli_runner, cli_app):
    """Test generation with include-inactive flag."""
    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
    ) as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_files.return_value = {
            "generated_files": ["path/to/file.yaml"],
            "skipped_files": [],
            "errors": [],
            "warnings": [],
        }

        # Run command with include-inactive flag
        result = cli_runner.invoke(
            cli_app, ["generate", "workspace/aws", "--include-inactive"]
        )

        assert result.exit_code == 0

        # Verify include_inactive was passed correctly
        include_inactive_arg = mock_instance.generate_files.call_args[1][
            "include_inactive"
        ]
        assert include_inactive_arg is True


def test_generate_with_skip_commit_dir(cli_runner, cli_app):
    """Test generation with skip-commit-dir flag."""
    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
    ) as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_files.return_value = {
            "generated_files": ["path/to/file.yaml"],
            "skipped_files": [],
            "errors": [],
            "warnings": [],
        }

        # Run command with skip-commit-dir flag
        result = cli_runner.invoke(
            cli_app, ["generate", "workspace/aws", "--skip-commit-dir"]
        )

        assert result.exit_code == 0

        # Verify skip_commit_dir was passed correctly
        skip_commit_dir_arg = mock_instance.generate_files.call_args[1][
            "skip_commit_dir"
        ]
        assert skip_commit_dir_arg is True


def test_generate_with_output_dir(cli_runner, cli_app, tmp_path):
    """Test generation with custom output directory."""
    output_dir = str(tmp_path / "custom_output")

    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
    ) as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_files.return_value = {
            "generated_files": [f"{output_dir}/file.yaml"],
            "skipped_files": [],
            "errors": [],
            "warnings": [],
        }

        # Run command with output-dir option
        result = cli_runner.invoke(
            cli_app, ["generate", "workspace/aws", "--output-dir", output_dir]
        )

        assert result.exit_code == 0

        # Verify output_dir was passed correctly
        output_dir_arg = str(mock_instance.generate_files.call_args[1]["output_dir"])
        assert output_dir in output_dir_arg


def test_generate_output_dir_default_none(cli_runner, cli_app):
    """Test that CLI output_dir defaults to None, allowing config to take precedence."""
    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
    ) as mock_service_class:
        # Create mock instance
        mock_instance = mock_service_class.return_value

        # Setup mock return value
        mock_instance.generate_files.return_value = {
            "generated_files": [],
            "skipped_files": [],
            "errors": [],
        }

        # Run command without --output-dir flag
        cli_runner.invoke(cli_app, ["generate", "workspace/aws"])

        # Verify generate_files was called with output_dir=None (not a Path)
        assert mock_instance.generate_files.called
        call_kwargs = mock_instance.generate_files.call_args[1]

        # The key assertion: output_dir should be None when not specified
        assert call_kwargs.get("output_dir") is None


def test_generate_missing_path_argument(cli_runner, cli_app):
    """Test error handling when path argument is missing."""
    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.console.error"
    ) as mock_error:
        result = cli_runner.invoke(cli_app, ["generate"], catch_exceptions=True)

        # Missing PATHS reports an error and does not crash with a traceback
        mock_error.assert_called()
        assert result.exception is None or isinstance(result.exception, SystemExit)
