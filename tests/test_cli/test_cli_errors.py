"""Tests for CLI error handling."""

from unittest.mock import patch


def test_invalid_command_handling(cli_runner, cli_app):
    """Test handling of an invalid command."""
    result = cli_runner.invoke(cli_app, ["invalid-command"], catch_exceptions=True)
    assert result.exit_code != 0 or result.exception is not None


def test_invalid_option_handling(cli_runner, cli_app):
    """Test handling of an invalid command-line option."""
    result = cli_runner.invoke(cli_app, ["--invalid-option"], catch_exceptions=True)
    assert result.exit_code != 0 or result.exception is not None


def test_missing_required_argument(cli_runner, cli_app):
    """Test that generate command without arguments doesn't crash."""
    with patch("coregen.cli.commands.generate.gen_generate_cli.console.error"):
        result = cli_runner.invoke(cli_app, ["generate"], catch_exceptions=True)
        # Command shows help or handles gracefully -- no crash
        assert result.exception is None


def test_config_file_not_found(cli_runner, cli_app):
    """Test error handling when config file is not found."""
    with patch(
        "coregen.cli.commands.config.cfg_init.ConfigInitService"
    ) as mock_service:
        # Configure mock to simulate missing config file
        mock_instance = mock_service.return_value
        mock_instance.initialize_config.return_value = False

        # Use a non-existent config path
        result = cli_runner.invoke(
            cli_app, ["config", "init", "--config-file", "/nonexistent/config.yaml"]
        )

        # Command should fail
        assert result.exit_code != 0

        # Error messages may be sent to stderr in the CLI runner
        # We only need to check the exit code


def test_generate_workspace_errors(cli_runner, cli_app):
    """Test error handling for workspace generation errors."""
    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
    ) as mock_service:
        # Configure mock to simulate error during generation
        mock_instance = mock_service.return_value
        mock_instance.generate_files.return_value = {
            "generated_files": [],
            "skipped_files": [],
            "errors": ["Failed to create workspace: permission denied"],
            "warnings": [],
        }

        # Run generate command with catch_exceptions
        cli_runner.invoke(
            cli_app, ["generate", "workspace/test"], catch_exceptions=True
        )

        # Verify service was called correctly
        mock_service.assert_called_once()
        mock_instance.generate_files.assert_called_once()


def test_permission_error_handling(cli_runner, cli_app):
    """Test handling of permission errors."""
    with patch(
        "coregen.cli.commands.config.cfg_init.ConfigInitService"
    ) as mock_service:
        # Configure mock to raise a permission error
        mock_instance = mock_service.return_value
        mock_instance.initialize_config.side_effect = PermissionError(
            "Permission denied"
        )

        # Run command that will trigger permission error
        result = cli_runner.invoke(
            cli_app, ["config", "init", "--config-file", "/root/config.yaml"]
        )

        # Command should fail
        assert result.exit_code != 0

        # Error messages may be sent to stderr in the CLI runner
        # We only need to check the exit code


def test_file_not_writable_error(cli_runner, cli_app):
    """Test error handling when trying to write to a file that's not writable."""
    with patch(
        "coregen.cli.commands.config.cfg_init.ConfigInitService"
    ) as mock_service:
        # Configure mock to simulate writable file error
        mock_instance = mock_service.return_value
        mock_instance.initialize_config.side_effect = IOError("File not writable")

        # Run command that will trigger file not writable error
        result = cli_runner.invoke(
            cli_app, ["config", "init", "--config-file", "/etc/readonly.yaml"]
        )

        # Command should fail
        assert result.exit_code != 0

        # Error messages may be sent to stderr in the CLI runner
        # We only need to check the exit code


def test_check_pattern_invalid_pattern_error(cli_runner, cli_app):
    """Test error handling for invalid pattern format in check-pattern command."""
    with patch(
        "coregen.cli.commands.check_pattern.check_pattern_cli.CheckPatternService"
    ) as mock_service:
        # Configure mock to raise an error for invalid pattern
        mock_instance = mock_service.return_value
        mock_instance.check_pattern.side_effect = ValueError(
            "Invalid pattern format: missing prefix"
        )

        # Run command with invalid pattern and catch_exceptions
        cli_runner.invoke(
            cli_app, ["check-pattern", "invalid/pattern/format"], catch_exceptions=True
        )

        # Verify service was called correctly
        mock_service.assert_called_once()


def test_non_existent_directory_error(cli_runner, cli_app):
    """Test error handling when trying to access a non-existent directory."""
    with patch(
        "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
    ) as mock_service:
        # Configure mock to raise error for non-existent directory
        mock_instance = mock_service.return_value
        mock_instance.generate_files.side_effect = FileNotFoundError(
            "Directory not found: /nonexistent/dir"
        )

        # Run command that references non-existent directory with catch_exceptions
        cli_runner.invoke(
            cli_app, ["generate", "/nonexistent/dir/component"], catch_exceptions=True
        )

        # Verify service was called correctly
        mock_service.assert_called_once()


def test_syntax_error_in_config(cli_runner, cli_app):
    """Test error handling for syntax errors in config file."""
    with patch(
        "coregen.cli.commands.config.cfg_view.ConfigViewService"
    ) as mock_service:
        # Configure mock to raise error for syntax error
        mock_instance = mock_service.return_value
        mock_instance.view_config.side_effect = SyntaxError("Invalid YAML syntax")

        # Run command that would try to parse invalid config with catch_exceptions
        cli_runner.invoke(cli_app, ["config", "view"], catch_exceptions=True)

        # Verify service was called correctly
        mock_service.assert_called_once()


def test_detect_changes_no_git_repo_error(cli_runner, cli_app):
    """Test error handling when detect-changes is run outside a git repository."""
    with patch(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
    ) as mock_service:
        # Configure mock to raise an error indicating no git repo
        mock_instance = mock_service.return_value
        mock_instance.detect_changes.side_effect = RuntimeError("Not a git repository")

        # Run detect-changes command with catch_exceptions
        cli_runner.invoke(cli_app, ["detect-changes"], catch_exceptions=True)

        # Verify service was called correctly
        mock_service.assert_called_once()
