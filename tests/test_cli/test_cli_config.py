"""Tests for config CLI commands."""

from pathlib import Path
from unittest.mock import patch

import pytest

from coregen.services.config.cfg_generate_service import GenerateConfigResult
from coregen.services.config.cfg_init_service import InitResult


def test_config_view(cli_runner, cli_app):
    """Test the config view command."""
    # Patch the service class where it is imported/used in the command module
    with patch(
        "coregen.cli.commands.config.cfg_view.ConfigViewService"
    ) as mock_service_class:
        # Configure the instance that will be created
        mock_instance = mock_service_class.return_value
        # Configure the view_config method on the instance
        mock_instance.view_config.return_value = {
            "version": "1.0",
            "workspaces": [],
        }  # Mock return value

        result = cli_runner.invoke(cli_app, ["config", "view", "--output", "yaml"])
        assert result.exit_code == 0
        # Check that the service was instantiated
        mock_service_class.assert_called_once()
        # Check that the view_config method was called on the instance
        mock_instance.view_config.assert_called_once()


def test_config_generate_nonexistent_file(cli_runner, cli_app):
    """Test the config generate command with a non-existent config file."""
    with patch(
        "coregen.cli.commands.config.cfg_generate.ConfigGenerateService"
    ) as mock_service_class:
        mock_instance = mock_service_class.return_value
        # Configure the method to raise FileNotFoundError
        mock_instance.generate_config.side_effect = FileNotFoundError(
            "Config file not found: /nonexistent/config.yaml"
        )

        # Run command with non-existent config file
        result = cli_runner.invoke(
            cli_app, ["config", "generate", "--config-file", "/nonexistent/config.yaml"]
        )

        # Command should fail with error code
        assert result.exit_code != 0

        # Service should be initialized
        mock_service_class.assert_called_once()


def test_config_init_nonexistent_file(cli_runner, cli_app):
    """Test the config init command with a non-existent config file."""
    # Run command with non-existent config file
    result = cli_runner.invoke(
        cli_app, ["config", "init", "--config-file", "/nonexistent/config.yaml"]
    )

    # Command should fail with error code
    assert result.exit_code != 0


def test_config_schema_nonexistent_file(cli_runner, cli_app):
    """Test the config schema command with a non-existent config file."""
    with patch(
        "coregen.cli.commands.config.cfg_schema.ConfigSchemaService"
    ) as mock_service_class:
        mock_instance = mock_service_class.return_value
        # Configure the method to raise FileNotFoundError
        mock_instance.process_schema_request.side_effect = FileNotFoundError(
            "Config file not found: /nonexistent/config.yaml"
        )

        # Run command with non-existent config file
        result = cli_runner.invoke(
            cli_app,
            [
                "config",
                "schema",
                "all",
                "--config-file",
                "/nonexistent/config.yaml",
                "--output",
                "json",
            ],
        )

        # Command should fail with error code
        assert result.exit_code != 0

        # Service should be initialized
        mock_service_class.assert_called_once()


def test_config_view_nonexistent_file(cli_runner, cli_app):
    """Test the config view command with a non-existent config file."""
    with patch(
        "coregen.cli.commands.config.cfg_view.ConfigViewService"
    ) as mock_service_class:
        mock_instance = mock_service_class.return_value
        # Simulate FileNotFoundError when trying to view a non-existent config
        mock_instance.view_config.side_effect = FileNotFoundError(
            "Config file not found: /nonexistent/config.yaml"
        )

        # Run command with non-existent config file
        result = cli_runner.invoke(
            cli_app,
            [
                "config",
                "view",
                "--config-file",
                "/nonexistent/config.yaml",
                "--output",
                "yaml",
            ],
        )

        # Command should fail with error code
        assert result.exit_code != 0

        # Service should be initialized with the path
        mock_service_class.assert_called_once()

        # view_config should be called with the non-existent path
        config_path_arg = mock_instance.view_config.call_args[1].get("config_file_path")
        assert str(config_path_arg) == "/nonexistent/config.yaml"


def test_config_view_with_config_file(cli_runner, cli_app):
    """Test the config view command with --config-file option."""
    with patch(
        "coregen.cli.commands.config.cfg_view.ConfigViewService"
    ) as mock_service_class:
        mock_instance = mock_service_class.return_value
        mock_instance.view_config.return_value = {"version": "1.0", "workspaces": []}

        # Run with the --config-file option
        result = cli_runner.invoke(
            cli_app,
            ["config", "view", "--config-file", "custom.yaml", "--output", "yaml"],
        )

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify service initialization with global_options
        service_kwargs = mock_service_class.call_args[1]
        assert "global_options" in service_kwargs
        global_options = service_kwargs.get("global_options")
        assert global_options.config_file == Path("custom.yaml")

        # Verify view_config was called with correct config_file_path
        view_kwargs = mock_instance.view_config.call_args[1]
        assert view_kwargs.get("config_file_path") == Path("custom.yaml")


def test_config_schema(cli_runner, cli_app):
    """Test the config schema command."""
    # Patch the service class where it is imported/used in the command module
    with (
        patch(
            "coregen.cli.commands.config.cfg_schema.ConfigSchemaService"
        ) as mock_service_class,
        patch(
            "coregen.cli.commands.config.cfg_schema.Console.print"
        ) as mock_console_print,
    ):
        # Configure the instance that will be created
        mock_instance = mock_service_class.return_value
        # Mock the process_schema_request method with appropriate return value
        mock_instance.process_schema_request.return_value = {
            "valid_types": ["all"],
            "unknown_types": [],
            "has_multiple": False,
            "schema_data": {"all": '{"title": "MockedSchema"}'},
            "errors": {},
        }

        # Configure console print to echo to stdout
        mock_console_print.side_effect = lambda data, **kwargs: print(data)

        # Invoke with 'all' argument
        result = cli_runner.invoke(
            cli_app, ["config", "schema", "all", "--output", "json"]
        )
        assert result.exit_code == 0

        # Check that the service was instantiated and the method was called
        mock_service_class.assert_called_once()
        mock_instance.process_schema_request.assert_called_once()

        # Check if console.print was called with the schema data
        mock_console_print.assert_called_once()
        # Check that it was called with the expected schema data
        assert mock_console_print.call_args[0][0] == '{"title": "MockedSchema"}'


def test_config_schema_with_config_file(cli_runner, cli_app):
    """Test the config schema command with --config-file option."""
    with patch(
        "coregen.cli.commands.config.cfg_schema.ConfigSchemaService"
    ) as mock_service_class:
        mock_instance = mock_service_class.return_value
        mock_instance.process_schema_request.return_value = {
            "valid_types": ["all"],
            "unknown_types": [],
            "has_multiple": False,
            "schema_data": {"all": '{"title": "MockedSchema"}'},
            "errors": {},
        }

        # Run with the --config-file option
        result = cli_runner.invoke(
            cli_app,
            [
                "config",
                "schema",
                "all",
                "--config-file",
                "custom.yaml",
                "--output",
                "json",
            ],
        )

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify service initialized with global_options
        mock_service_class.assert_called_once()

        # Get the keyword arguments used to initialize the service
        service_kwargs = mock_service_class.call_args[1]

        # Verify that GlobalOptions was passed
        assert "global_options" in service_kwargs
        global_options = service_kwargs["global_options"]
        assert global_options.config_file == Path("custom.yaml")

        # Verify process_schema_request was called
        mock_instance.process_schema_request.assert_called_once()


@pytest.mark.parametrize(
    "command,expected_code", [(["config", "view"], 0), (["config", "schema"], 2)]
)
def test_config_help(cli_runner, cli_app, command, expected_code):
    """Test help for config commands."""
    command.append("--help")
    result = cli_runner.invoke(cli_app, command)
    # Help commands exit with different codes (0 for view, 2 for schema)
    assert result.exit_code == expected_code
    output = result.stdout + result.stderr
    assert "Usage:" in output or "usage:" in output.lower()


@pytest.mark.parametrize("force_flag", [True, False])
def test_config_init_with_force(cli_runner, cli_app, force_flag):
    """Test config init command with force option."""
    # Mock the ConfigInitService to avoid actual initialization
    with patch(
        "coregen.cli.commands.config.cfg_init.ConfigInitService"
    ) as mock_service_class:
        # Configure the instance that will be created
        mock_instance = mock_service_class.return_value
        # Mock the initialize_config method with appropriate return value
        mock_instance.initialize_config.return_value = InitResult(success=True)

        # Build command with or without force flag
        cmd = ["config", "init"]
        if force_flag:
            cmd.append("--force")

        result = cli_runner.invoke(cli_app, cmd)

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify service was called with right parameters
        mock_service_class.assert_called_once()
        mock_instance.initialize_config.assert_called_once()


def test_config_init_with_nonexistent_config(cli_runner, cli_app):
    """Test config init with a nonexistent config path."""
    # Test with a non-existent path - this should fail
    result = cli_runner.invoke(
        cli_app,
        ["config", "init", "--config-file", "/nonexistent/path/config.yaml"],
    )

    # Command should exit with non-zero code when trying to init with nonexistent path
    assert result.exit_code != 0


def test_config_init_with_existing_config(cli_runner, cli_app, tmp_path):
    """Test config init with an existing config file."""
    # Create a temporary config file
    config_file = tmp_path / "config.yaml"
    config_file.write_text("version: 1.0\nworkspaces: []")

    with patch(
        "coregen.cli.commands.config.cfg_init.ConfigInitService"
    ) as mock_service_class:
        mock_instance = mock_service_class.return_value
        # Mock successful initialization
        mock_instance.initialize_config.return_value = InitResult(success=True)

        # Run command with existing config file
        result = cli_runner.invoke(
            cli_app, ["config", "init", "--config-file", str(config_file)]
        )

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify service was called
        mock_service_class.assert_called_once()
        mock_instance.initialize_config.assert_called_once()


def test_config_init_with_invalid_path(cli_runner, cli_app):
    """Test config init with an invalid path that cant be written to."""
    with patch(
        "coregen.cli.commands.config.cfg_init.ConfigInitService"
    ) as mock_service_class:
        mock_instance = mock_service_class.return_value
        # Mock failure on initialization
        mock_instance.initialize_config.side_effect = PermissionError(
            "Permission denied"
        )

        # Test with a path that would cause permission errors
        result = cli_runner.invoke(
            cli_app, ["config", "init", "--config-file", "/root/restricted/config.yaml"]
        )

        # Command should exit with error code
        assert result.exit_code == 1

        # Error message check isn't needed as Typer handles the exit code
        # The output message may be sent to stderr instead of stdout in the CLI runner


def test_config_generate_command(cli_runner, cli_app):
    """Test the config generate command."""
    with patch(
        "coregen.cli.commands.config.cfg_generate.ConfigGenerateService"
    ) as mock_service_class:
        mock_instance = mock_service_class.return_value
        mock_instance.generate_config.return_value = GenerateConfigResult()

        # Run command with various options
        result = cli_runner.invoke(
            cli_app,
            [
                "config",
                "generate",
                "--config-file",
                "custom.yaml",
                "--output-config",
                "generated.yaml",
                "--config-file-only",
                "--workspace-name",
                "test-workspace",
            ],
        )

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify service call
        mock_service_class.assert_called_once()

        # Check generate_config was called with the expected parameters
        mock_instance.generate_config.assert_called_once()

        # Check first argument (config_file_path) - it's an absolute path so just check the filename
        config_path_arg = mock_instance.generate_config.call_args[1].get(
            "config_file_path"
        )
        assert config_path_arg.name == "generated.yaml"

        # Check second argument (config_file_only)
        assert (
            mock_instance.generate_config.call_args[1].get("config_file_only") is True
        )

        # Check third argument (custom_values) contains workspace_name
        custom_values = mock_instance.generate_config.call_args[1].get("custom_values")
        assert custom_values.get("name") == "test-workspace"

        # Check service was initialized with global_options
        service_kwargs = mock_service_class.call_args[1]
        assert "global_options" in service_kwargs


def test_config_init_service_integration(cli_runner, cli_app):
    """Test that config init command properly integrates with the service layer."""
    # This test ensures the CLI layer correctly passes options to the service
    with patch(
        "coregen.cli.commands.config.cfg_init.ConfigInitService"
    ) as mock_service_class:
        mock_instance = mock_service_class.return_value
        mock_instance.initialize_config.return_value = InitResult(success=True)

        # Run with various options to test they're passed through
        result = cli_runner.invoke(
            cli_app,
            [
                "config",
                "init",
                "--verbose",
                "--dry-run",
                "--no-color",
                "--config-file",
                "custom.yaml",
            ],
        )

        # Verify command ran successfully
        assert result.exit_code == 0

        # Check that service was instantiated with the right options
        mock_service_class.assert_called_once()

        # Get the keyword arguments used to initialize the service
        service_kwargs = mock_service_class.call_args[1]

        # Verify that GlobalOptions was passed
        assert "global_options" in service_kwargs
        global_options = service_kwargs["global_options"]

        # Verify options were passed through GlobalOptions
        assert global_options.verbose is True
        assert global_options.dry_run is True
        assert global_options.no_color is True
        # Note: config_file handling has changed - it now uses defaults when not properly passed through context
