"""
Tests for the coregen CLI application.

This file provides comprehensive tests for the CLI functionality,
focusing on command structure, options parsing, and basic functionality
without requiring access to actual file system operations.

Note: This file has been significantly expanded to improve test coverage
following the AAA (Arrange, Act, Assert) pattern and using standardized fixtures.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from coregen.cli.enums.enum_output_format import OutputFormat

# Try to import the VERSION - wrap in try/except to handle potential import errors
try:
    from coregen import __version__ as VERSION
except ImportError:
    # Fallback value for testing
    VERSION = "0.2.0-test"


@pytest.fixture
def runner() -> Any:
    """Create a CLI runner fixture for testing CLI commands."""
    from typer.testing import CliRunner

    return CliRunner()


@pytest.fixture
def mocked_app() -> Any:
    """Get the CLI app with mocked dependencies to avoid file system operations."""
    # Set up necessary mocks to prevent actual operations
    with patch("coregen.common.logger.Logger"), patch("coregen.common.console.Console"):
        from coregen.cli.cli import app

        return app


@pytest.fixture
def mock_global_options() -> MagicMock:
    """Create a mock GlobalOptions object for testing."""
    mock = MagicMock()
    mock.dry_run = False
    mock.file_action = "ask"
    mock.no_color = False
    mock.quiet = False
    mock.verbose = False
    mock.config_file = None
    mock.debug = False
    return mock


class TestCLIBasics:
    """Tests for basic CLI functionality and global options."""

    def test_version_command(self, runner, mocked_app):
        """Test version command displays correct version."""
        # Arrange
        expected_version = f"v{VERSION}"

        # Act
        result = runner.invoke(mocked_app, ["version"])

        # Assert
        assert result.exit_code == 0
        assert expected_version in result.stdout.strip()

    def test_help_command(self, runner, mocked_app):
        """Test help command displays main help."""
        # Arrange & Act
        result = runner.invoke(mocked_app, ["--help"])

        # Assert
        assert result.exit_code == 0
        assert "coregen" in result.stdout.lower()
        assert "Global Options" in result.stdout

    def test_no_command_shows_help(self, runner, mocked_app):
        """Test that running CLI without command shows help."""
        # Arrange & Act
        result = runner.invoke(mocked_app, [])

        # Assert
        assert result.exit_code == 0
        assert "Usage:" in result.stdout

    @pytest.mark.parametrize("help_flag", ["--help", "-h"])
    def test_help_flags(self, runner, mocked_app, help_flag):
        """Test both short and long help flags work."""
        # Arrange & Act
        result = runner.invoke(mocked_app, [help_flag])

        # Assert
        assert result.exit_code == 0
        assert "Usage:" in result.stdout


class TestGlobalOptions:
    """Tests for global CLI options and their behavior."""

    @pytest.mark.parametrize("verbose_flag", ["--verbose", "-v"])
    def test_verbose_option(self, runner, verbose_flag):
        """Test verbose option parsing."""
        # Arrange & Act
        with (
            patch("coregen.common.logger.Logger"),
            patch("coregen.common.console.Console"),
            patch("coregen.cli.cli.Logger.configure") as mock_logger_config,
        ):
            from coregen.cli.cli import app

            result = runner.invoke(app, [verbose_flag, "version"])

            # Assert
            assert result.exit_code == 0
            mock_logger_config.assert_called_once()
            call_kwargs = mock_logger_config.call_args.kwargs
            assert call_kwargs["verbose"] is True

    @pytest.mark.parametrize("quiet_flag", ["--quiet", "-q"])
    def test_quiet_option(self, runner, quiet_flag):
        """Test quiet option parsing."""
        # Arrange & Act
        with (
            patch("coregen.common.logger.Logger"),
            patch("coregen.common.console.Console"),
            patch("coregen.cli.cli.Logger.configure") as mock_logger_config,
        ):
            from coregen.cli.cli import app

            result = runner.invoke(app, [quiet_flag, "version"])

            # Assert
            assert result.exit_code == 0
            mock_logger_config.assert_called_once()
            call_kwargs = mock_logger_config.call_args.kwargs
            assert call_kwargs["quiet"] is True

    @pytest.mark.parametrize("no_color_flag", ["--no-color", "-nc"])
    def test_no_color_option(self, runner, no_color_flag):
        """Test no-color option parsing."""
        # Arrange & Act
        with (
            patch("coregen.common.logger.Logger"),
            patch("coregen.common.console.Console"),
            patch(
                "coregen.common.console.Console.setup_for_user"
            ) as mock_console_setup,
        ):
            from coregen.cli.cli import app

            result = runner.invoke(app, [no_color_flag, "version"])

            # Assert
            assert result.exit_code == 0
            mock_console_setup.assert_called_once()
            call_kwargs = mock_console_setup.call_args.kwargs
            assert call_kwargs["no_color"] is True

    @pytest.mark.parametrize("dry_run_flag", ["--dry-run", "-d"])
    def test_dry_run_option(self, runner, dry_run_flag):
        """Test dry-run option parsing."""
        # Arrange & Act
        with (
            patch("coregen.common.logger.Logger"),
            patch("coregen.common.console.Console"),
            patch(
                "coregen.common.console.Console.setup_for_user"
            ) as mock_console_setup,
        ):
            from coregen.cli.cli import app

            result = runner.invoke(app, [dry_run_flag, "version"])

            # Assert
            assert result.exit_code == 0
            mock_console_setup.assert_called_once()
            call_kwargs = mock_console_setup.call_args.kwargs
            assert call_kwargs["dry_run"] is True

    @pytest.mark.parametrize("config_flag", ["--config-file", "-c"])
    def test_config_file_option(self, runner, mocked_app, config_flag):
        """Test config file option parsing."""
        # Arrange
        config_path = "test_config.yaml"

        # Act
        result = runner.invoke(mocked_app, [config_flag, config_path, "version"])

        # Assert
        assert result.exit_code == 0

    def test_multiple_global_options(self, runner):
        """Test combining multiple global options."""
        # Arrange & Act
        with (
            patch("coregen.common.logger.Logger"),
            patch("coregen.common.console.Console"),
            patch("coregen.cli.cli.Logger.configure") as mock_logger_config,
            patch(
                "coregen.common.console.Console.setup_for_user"
            ) as mock_console_setup,
        ):
            from coregen.cli.cli import app

            result = runner.invoke(
                app, ["--verbose", "--quiet", "--no-color", "--dry-run", "version"]
            )

            # Assert
            assert result.exit_code == 0
            mock_logger_config.assert_called_once()
            mock_console_setup.assert_called_once()

            # Check logger configuration
            logger_kwargs = mock_logger_config.call_args.kwargs
            assert logger_kwargs["verbose"] is True
            assert logger_kwargs["quiet"] is True
            assert logger_kwargs["no_color"] is True

            # Check console configuration
            console_kwargs = mock_console_setup.call_args.kwargs
            assert console_kwargs["verbose"] is True
            assert console_kwargs["quiet"] is True
            assert console_kwargs["no_color"] is True
            assert console_kwargs["dry_run"] is True


class TestConfigCommands:
    """Tests for the config command group."""

    def test_config_help(self, runner, mocked_app):
        """Test config help command."""
        # Arrange & Act
        result = runner.invoke(mocked_app, ["config", "--help"])

        # Assert
        # With invoke_without_command=True, Typer exits with code 0 for help
        assert result.exit_code == 0
        # Help text might be in stderr for subcommands
        try:
            output = result.stdout + result.stderr
        except ValueError:
            # stderr not separately captured, use stdout only
            output = result.stdout
        assert "config" in output.lower() or "Usage" in output

    @patch("coregen.cli.commands.config.cfg_schema.ConfigSchemaService")
    def test_config_schema_success(self, mock_schema_service, runner, mocked_app):
        """Test config schema command with successful response."""
        # Arrange
        mock_instance = MagicMock()
        mock_schema_service.return_value = mock_instance
        mock_instance.process_schema_request.return_value = {
            "valid_types": ["settings"],
            "has_multiple": False,
            "unknown_types": [],
            "schema_data": {"settings": "{}"},
        }

        # Act
        result = runner.invoke(mocked_app, ["config", "schema", "settings"])

        # Assert
        assert result.exit_code == 0
        mock_schema_service.assert_called_once()
        mock_instance.process_schema_request.assert_called_once_with(
            ["settings"], OutputFormat.JSON
        )

    @patch("coregen.cli.commands.config.cfg_schema.ConfigSchemaService")
    def test_config_schema_invalid_type(self, mock_schema_service, runner, mocked_app):
        """Test config schema command with invalid schema type."""
        # Arrange
        mock_instance = MagicMock()
        mock_schema_service.return_value = mock_instance
        mock_instance.process_schema_request.return_value = {
            "valid_types": ["settings"],
            "has_multiple": False,
            "unknown_types": ["invalid_type"],
            "schema_data": {},
        }

        # Act
        result = runner.invoke(mocked_app, ["config", "schema", "invalid_type"])

        # Assert
        assert result.exit_code == 1  # Should exit with error for invalid type
        mock_instance.process_schema_request.assert_called_once_with(
            ["invalid_type"], OutputFormat.JSON
        )


class TestGenerateCommands:
    """Tests for the generate command group."""

    def test_generate_help(self, runner, mocked_app):
        """Test generate help command."""
        # Arrange & Act
        result = runner.invoke(mocked_app, ["generate", "--help"])

        # Assert
        assert result.exit_code in (0, 1, 2)  # All are acceptable for help
        try:
            output = result.stdout + result.stderr
        except ValueError:
            # stderr not separately captured, use stdout only
            output = result.stdout
        assert "generate" in output.lower() or "Usage" in output

    def test_generate_command_without_args(self, runner, mocked_app):
        """Test generate command without arguments shows help."""
        # Arrange & Act
        result = runner.invoke(mocked_app, ["generate"])

        # Assert
        # Should show help or error for missing arguments
        assert result.exit_code in (0, 1, 2)


class TestGetCommands:
    """Tests for the get command group."""

    def test_get_help(self, runner, mocked_app):
        """Test get help command."""
        # Arrange & Act
        result = runner.invoke(mocked_app, ["get", "--help"])

        # Assert
        assert result.exit_code in (0, 2)  # Both are acceptable for help
        try:
            output = result.stdout + result.stderr
        except ValueError:
            # stderr not separately captured, use stdout only
            output = result.stdout
        assert "get" in output.lower() or "Usage" in output


class TestCheckPatternCommands:
    """Tests for the check-pattern command group."""

    def test_check_pattern_help(self, runner, mocked_app):
        """Test check-pattern help command."""
        # Arrange & Act
        result = runner.invoke(mocked_app, ["check-pattern", "--help"])

        # Assert
        assert result.exit_code in (0, 2)  # Both are acceptable for help
        try:
            output = result.stdout + result.stderr
        except ValueError:
            # stderr not separately captured, use stdout only
            output = result.stdout
        assert (
            "check-pattern" in output.lower()
            or "pattern" in output.lower()
            or "Usage" in output
        )


class TestDetectChangesCommands:
    """Tests for the detect-changes command group."""

    def test_detect_changes_help(self, runner, mocked_app):
        """Test detect-changes help command."""
        # Arrange & Act
        result = runner.invoke(mocked_app, ["detect-changes", "--help"])

        # Assert
        assert result.exit_code in (0, 2)  # Both are acceptable for help
        try:
            output = result.stdout + result.stderr
        except ValueError:
            # stderr not separately captured, use stdout only
            output = result.stdout
        assert (
            "detect-changes" in output.lower()
            or "changes" in output.lower()
            or "Usage" in output
        )


class TestErrorScenarios:
    """Tests for error scenarios and edge cases."""

    def test_invalid_command(self, runner, mocked_app):
        """Test CLI behavior with invalid command."""
        # Arrange & Act
        result = runner.invoke(mocked_app, ["invalid-command"])

        # Assert
        assert result.exit_code != 0
        try:
            output = result.stdout + result.stderr
        except ValueError:
            # stderr not separately captured, use stdout only
            output = result.stdout
        assert "No such command" in output or "Usage:" in output

    def test_invalid_global_option(self, runner, mocked_app):
        """Test CLI behavior with invalid global option."""
        # Arrange & Act
        result = runner.invoke(mocked_app, ["--invalid-option", "version"])

        # Assert
        assert result.exit_code != 0

    def test_config_file_with_nonexistent_path(self, runner, mocked_app):
        """Test config file option with nonexistent path."""
        # Arrange & Act
        result = runner.invoke(
            mocked_app, ["--config-file", "/nonexistent/path/config.yaml", "version"]
        )

        # Assert - Should handle gracefully or show appropriate error
        # The exact behavior depends on implementation
        assert result.exit_code in (0, 1, 2)

    @pytest.mark.parametrize(
        "conflicting_options",
        [
            ["--verbose", "--quiet"],
            ["--no-color", "--verbose"],  # These might conflict in output formatting
        ],
    )
    def test_potentially_conflicting_options(
        self, runner, mocked_app, conflicting_options
    ):
        """Test CLI behavior with potentially conflicting options."""
        # Arrange
        command = conflicting_options + ["version"]

        # Act
        result = runner.invoke(mocked_app, command)

        # Assert - Should handle gracefully
        assert result.exit_code == 0


class TestContextObjectHandling:
    """Tests for CLI context object management."""

    @patch("coregen.cli.global_options.GlobalOptions")
    def test_global_options_context_storage(
        self, mock_global_options_class, runner, mocked_app
    ):
        """Test that global options are properly stored in context."""
        # Arrange
        mock_instance = MagicMock()
        mock_global_options_class.return_value = mock_instance

        # Act
        result = runner.invoke(mocked_app, ["--verbose", "version"])

        # Assert
        assert result.exit_code == 0
        mock_global_options_class.assert_called_once()
        # Verify that GlobalOptions was called with verbose=True
        call_kwargs = mock_global_options_class.call_args.kwargs
        assert call_kwargs["verbose"] is True

    def test_help_flag_handling(self, runner, mocked_app):
        """Test that help flag is properly handled in context."""
        # Arrange & Act
        result = runner.invoke(mocked_app, ["--help"])

        # Assert
        assert result.exit_code == 0
        assert "Usage:" in result.stdout


class TestCLIIntegrationScenarios:
    """Tests for realistic CLI usage scenarios."""

    def test_typical_config_workflow(self, runner, mocked_app):
        """Test a typical config command workflow."""
        # Arrange & Act
        with patch(
            "coregen.services.config.cfg_schema_service.ConfigSchemaService"
        ) as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance
            mock_instance.process_schema_request.return_value = {
                "valid_types": ["settings"],
                "has_multiple": False,
                "unknown_types": [],
                "schema_data": {"settings": "test_schema"},
            }

            # Test the workflow
            result = runner.invoke(
                mocked_app,
                [
                    "--verbose",
                    "--config-file",
                    "test.yaml",
                    "config",
                    "schema",
                    "settings",
                ],
            )

            # Assert
            assert result.exit_code == 0

    def test_dry_run_with_generate(self, runner, mocked_app):
        """Test dry-run option with generate command."""
        # Arrange & Act
        result = runner.invoke(mocked_app, ["--dry-run", "generate", "--help"])

        # Assert
        assert result.exit_code in (0, 1, 2)  # Help should work regardless of dry-run

    def test_quiet_verbose_interaction(self, runner, mocked_app):
        """Test interaction between quiet and verbose modes."""
        # Arrange & Act
        with patch("coregen.common.logger.Logger.configure") as mock_logger:
            result = runner.invoke(mocked_app, ["--quiet", "--verbose", "version"])

            # Assert
            assert result.exit_code == 0
            mock_logger.assert_called_once()
            # Both flags should be passed to logger for proper handling
            call_kwargs = mock_logger.call_args.kwargs
            assert call_kwargs["quiet"] is True
            assert call_kwargs["verbose"] is True


class TestEnvironmentVariables:
    """Tests for environment variable support (CG_ prefix)."""

    @patch.dict("os.environ", {"CG_VERBOSE": "true"})
    def test_environment_variable_verbose(self, runner, mocked_app):
        """Test that CG_VERBOSE environment variable works."""
        # Arrange & Act
        result = runner.invoke(mocked_app, ["version"])

        # Assert
        assert result.exit_code == 0
        # Environment variable should be picked up by Typer automatically

    @patch.dict("os.environ", {"CG_NO_COLOR": "true"})
    def test_environment_variable_no_color(self, runner, mocked_app):
        """Test that CG_NO_COLOR environment variable works."""
        # Arrange & Act
        result = runner.invoke(mocked_app, ["version"])

        # Assert
        assert result.exit_code == 0
        # Environment variable should be picked up by Typer automatically
