"""Tests for check-pattern CLI commands."""

from unittest.mock import patch

import pytest


def test_check_pattern_help(cli_runner, cli_app):
    """Test the check-pattern help command."""
    result = cli_runner.invoke(cli_app, ["check-pattern", "--help"])

    # check-pattern exits with code 0 for help
    assert result.exit_code == 0
    assert "check-pattern" in result.stdout
    assert "Test and analyze pattern matching" in result.stdout


def test_check_pattern_basic(cli_runner, cli_app):
    """Test the basic check-pattern command with a simple pattern."""
    # Mock the entire command execution to avoid complex initialization
    with patch(
        "coregen.cli.commands.check_pattern.check_pattern_cli.CheckPattern.run"
    ) as mock_run:
        # Configure mock to do nothing (avoid actual execution)
        mock_run.return_value = None

        # Invoke command with a workspace pattern
        result = cli_runner.invoke(cli_app, ["check-pattern", "workspace/aws"])

        # Should succeed since we mocked the run method
        assert result.exit_code == 0

        # Verify run was called
        mock_run.assert_called_once()


@pytest.mark.parametrize(
    "pattern_type",
    [
        "workspace/aws",
        "context/dev-context",
        "component/metrics-server",
        "contexts/aws/",  # filesystem pattern
    ],
)
def test_check_pattern_different_types(cli_runner, cli_app, pattern_type):
    """Test check-pattern with different pattern types (workspace, context, component, filesystem)."""
    with patch(
        "coregen.cli.commands.check_pattern.check_pattern_cli.CheckPattern.run"
    ) as mock_run:
        # Configure mock to do nothing
        mock_run.return_value = None

        result = cli_runner.invoke(cli_app, ["check-pattern", pattern_type])

        assert result.exit_code == 0

        # Verify run was called
        mock_run.assert_called_once()


def test_check_pattern_with_filters(cli_runner, cli_app):
    """Test check-pattern with filters."""
    with patch(
        "coregen.cli.commands.check_pattern.check_pattern_cli.CheckPattern.run"
    ) as mock_run:
        # Configure mock to do nothing
        mock_run.return_value = None

        result = cli_runner.invoke(
            cli_app, ["check-pattern", "workspace/aws", "--filter", "environment=dev"]
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()


def test_check_pattern_show_rejected(cli_runner, cli_app):
    """Test check-pattern with show-rejected flag."""
    with patch(
        "coregen.cli.commands.check_pattern.check_pattern_cli.CheckPattern.run"
    ) as mock_run:
        # Configure mock to do nothing
        mock_run.return_value = None

        result = cli_runner.invoke(
            cli_app, ["check-pattern", "workspace/aws", "--show-rejected"]
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()


def test_check_pattern_analyze(cli_runner, cli_app):
    """Test check-pattern with analyze flag."""
    with patch(
        "coregen.cli.commands.check_pattern.check_pattern_cli.CheckPattern.run"
    ) as mock_run:
        # Configure mock to do nothing
        mock_run.return_value = None

        result = cli_runner.invoke(
            cli_app, ["check-pattern", "workspace/aws", "--analyze"]
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()


def test_check_pattern_include_inactive(cli_runner, cli_app):
    """Test check-pattern with include-inactive flag."""
    with patch(
        "coregen.cli.commands.check_pattern.check_pattern_cli.CheckPattern.run"
    ) as mock_run:
        # Configure mock to do nothing
        mock_run.return_value = None

        result = cli_runner.invoke(
            cli_app, ["check-pattern", "component/*", "--include-inactive"]
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()


def test_check_pattern_missing_arguments(cli_runner, cli_app):
    """Test check-pattern without required pattern arguments."""
    result = cli_runner.invoke(cli_app, ["check-pattern"])

    # Should succeed with exit code 0 when no patterns are provided
    assert result.exit_code == 0
    assert "Usage:" in result.stdout


def test_check_pattern_multiple_patterns(cli_runner, cli_app):
    """Test check-pattern with multiple patterns."""
    with patch(
        "coregen.cli.commands.check_pattern.check_pattern_cli.CheckPattern.run"
    ) as mock_run:
        # Configure mock to do nothing
        mock_run.return_value = None

        result = cli_runner.invoke(
            cli_app, ["check-pattern", "workspace/aws", "context/dev-*"]
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()


def test_check_pattern_with_type_filter(cli_runner, cli_app):
    """Test check-pattern with type filter."""
    with patch(
        "coregen.cli.commands.check_pattern.check_pattern_cli.CheckPattern.run"
    ) as mock_run:
        # Configure mock to do nothing
        mock_run.return_value = None

        result = cli_runner.invoke(
            cli_app, ["check-pattern", "workspace/*", "--type", "context"]
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()
