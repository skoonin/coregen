"""
Unit tests for the GlobalOptions class.

This file provides comprehensive tests for global options management,
following the AAA (Arrange, Act, Assert) pattern and using standardized fixtures.
"""

from pathlib import Path

import pytest
import typer

from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.global_options import GlobalOptions


@pytest.fixture
def sample_context() -> typer.Context:
    """Create a sample Typer context for testing."""
    # Create a mock command with the required attributes
    from unittest.mock import MagicMock

    mock_command = MagicMock()
    mock_command.allow_extra_args = False
    mock_command.allow_interspersed_args = True
    mock_command.ignore_unknown_options = False

    ctx = typer.Context(mock_command)
    ctx.obj = {
        "dry_run": True,
        "file_action": FileAction.OVERWRITE,
        "quiet": True,
        "verbose": False,
        "no_color": True,
        "config_file": "test_config.yaml",
        "debug": True,
    }
    return ctx


@pytest.fixture
def empty_context() -> typer.Context:
    """Create an empty Typer context for testing."""
    # Create a mock command with the required attributes
    from unittest.mock import MagicMock

    mock_command = MagicMock()
    mock_command.allow_extra_args = False
    mock_command.allow_interspersed_args = True
    mock_command.ignore_unknown_options = False

    ctx = typer.Context(mock_command)
    ctx.obj = None
    return ctx


class TestGlobalOptionsInitialization:
    """Tests for GlobalOptions initialization."""

    def test_init_with_defaults(self, mock_settings):
        """Test GlobalOptions initialization with default values."""
        # Arrange & Act
        options = GlobalOptions()

        # Assert
        assert options.dry_run is False
        assert options.file_action == FileAction.OVERWRITE  # Default from defaults.py
        assert options.quiet is False
        assert options.verbose is False
        assert options.no_color is False
        assert options.config_file == Path(".cgconfig.yaml")  # Default from defaults.py
        assert options.debug is False

    def test_init_with_custom_values(self, mock_settings):
        """Test GlobalOptions initialization with custom values."""
        # Arrange
        config_path = Path("custom_config.yaml")

        # Act
        options = GlobalOptions(
            dry_run=True,
            file_action=FileAction.OVERWRITE,
            quiet=True,
            verbose=True,
            no_color=True,
            config_file=config_path,
            debug=True,
        )

        # Assert
        assert options.dry_run is True
        assert options.file_action == FileAction.OVERWRITE
        assert options.quiet is True
        assert options.verbose is True
        assert options.no_color is True
        assert options.config_file == config_path
        assert options.debug is True

    @pytest.mark.parametrize(
        "file_action",
        [
            FileAction.ASK,
            FileAction.SKIP,
            FileAction.OVERWRITE,
            FileAction.ARCHIVE,
            FileAction.DELETE,
        ],
    )
    def test_init_with_different_file_actions(self, mock_settings, file_action):
        """Test GlobalOptions initialization with different file actions."""
        # Arrange & Act
        options = GlobalOptions(file_action=file_action)

        # Assert
        assert options.file_action == file_action

    @pytest.mark.parametrize(
        "config_value,expected_type",
        [
            (None, type(None)),
            ("string_path.yaml", str),
            (Path("path_object.yaml"), Path),
        ],
    )
    def test_init_with_different_config_file_types(
        self, mock_settings, config_value, expected_type
    ):
        """Test GlobalOptions initialization with different config file types."""
        # Arrange & Act
        options = GlobalOptions(config_file=config_value)

        # Assert
        if expected_type is type(None):
            assert options.config_file is None
        else:
            assert isinstance(options.config_file, expected_type)


class TestConvertToPath:
    """Tests for the _convert_to_path class method."""

    def test_convert_string_to_path(self, mock_logger):
        """Test converting string to Path object."""
        # Arrange
        test_string = "test/path/config.yaml"

        # Act
        result = GlobalOptions._convert_to_path(test_string)

        # Assert
        assert isinstance(result, Path)
        assert str(result) == test_string
        mock_logger.debug.assert_called_once_with(
            f"Converting config_file from string to Path: {test_string}"
        )

    def test_convert_path_to_path(self, mock_logger):
        """Test that Path objects are returned unchanged."""
        # Arrange
        test_path = Path("test/path/config.yaml")

        # Act
        result = GlobalOptions._convert_to_path(test_path)

        # Assert
        assert result is test_path
        assert isinstance(result, Path)
        mock_logger.debug.assert_not_called()

    def test_convert_none_to_none(self, mock_logger):
        """Test that None values are returned as None."""
        # Arrange & Act
        result = GlobalOptions._convert_to_path(None)

        # Assert
        assert result is None
        mock_logger.debug.assert_not_called()

    def test_convert_empty_string_to_none(self, mock_logger):
        """Test that empty strings are converted to None."""
        # Arrange & Act
        result = GlobalOptions._convert_to_path("")

        # Assert
        assert result is None
        mock_logger.debug.assert_not_called()

    @pytest.mark.parametrize("invalid_value", [123, [], {}, object()])
    def test_convert_invalid_types_to_none(self, mock_logger, invalid_value):
        """Test that invalid types are converted to None."""
        # Arrange & Act
        result = GlobalOptions._convert_to_path(invalid_value)

        # Assert
        assert result is None
        mock_logger.debug.assert_not_called()


class TestFromContext:
    """Tests for the from_context class method."""

    def test_from_context_with_values(self, mock_settings, mock_logger, sample_context):
        """Test creating GlobalOptions from context with values."""
        # Arrange & Act
        options = GlobalOptions.from_context(sample_context)

        # Assert
        assert options.dry_run is True
        assert options.file_action == FileAction.OVERWRITE
        assert options.quiet is True
        assert options.verbose is False
        assert options.no_color is True
        assert options.config_file == Path("test_config.yaml")
        assert options.debug is True

    def test_from_context_empty_context(
        self, mock_settings, mock_logger, empty_context
    ):
        """Test creating GlobalOptions from empty context."""
        # Arrange & Act
        options = GlobalOptions.from_context(empty_context)

        # Assert
        # Should use defaults from settings
        assert options.dry_run is False
        assert options.file_action == FileAction.OVERWRITE  # Default from defaults.py
        assert options.quiet is False
        assert options.verbose is False
        assert options.no_color is False
        assert options.config_file == Path(".cgconfig.yaml")  # Default from defaults.py
        assert options.debug is False
        mock_logger.debug.assert_called_with(
            "Context has no obj, using defaults from settings"
        )

    def test_from_context_partial_values(self, mock_settings, mock_logger):
        """Test creating GlobalOptions from context with partial values."""
        # Arrange
        from unittest.mock import MagicMock

        mock_command = MagicMock()
        mock_command.allow_extra_args = False
        mock_command.allow_interspersed_args = True
        mock_command.ignore_unknown_options = False

        ctx = typer.Context(mock_command)
        ctx.obj = {
            "dry_run": True,
            "verbose": True,
            # Missing other values - should use defaults
        }

        # Act
        options = GlobalOptions.from_context(ctx)

        # Assert
        assert options.dry_run is True  # From context
        assert options.verbose is True  # From context
        assert options.file_action == FileAction.OVERWRITE  # From settings default
        assert options.quiet is False  # From settings default
        assert options.no_color is False  # From settings default
        assert options.config_file == Path(".cgconfig.yaml")  # From settings default
        assert options.debug is False  # From settings default

    def test_from_context_with_string_config_file(self, mock_settings, mock_logger):
        """Test creating GlobalOptions from context with string config file."""
        # Arrange
        from unittest.mock import MagicMock

        mock_command = MagicMock()
        mock_command.allow_extra_args = False
        mock_command.allow_interspersed_args = True
        mock_command.ignore_unknown_options = False

        ctx = typer.Context(mock_command)
        ctx.obj = {
            "config_file": "string_config.yaml",
        }

        # Act
        options = GlobalOptions.from_context(ctx)

        # Assert
        assert isinstance(options.config_file, Path)
        assert str(options.config_file) == "string_config.yaml"

    def test_from_context_logging(self, mock_settings, mock_logger, sample_context):
        """Test that from_context logs debug information."""
        # Arrange & Act
        GlobalOptions.from_context(sample_context)

        # Assert
        mock_logger.debug.assert_any_call(
            f"Creating GlobalOptions from context obj: {sample_context.obj}"
        )
        mock_logger.debug.assert_any_call(
            f"config_file from ctx.obj: {sample_context.obj.get('config_file', 'NOT_FOUND')}"
        )


class TestToDict:
    """Tests for the to_dict method."""

    def test_to_dict_complete(self, mock_settings):
        """Test converting GlobalOptions to dictionary."""
        # Arrange
        config_path = Path("test_config.yaml")
        options = GlobalOptions(
            dry_run=True,
            file_action=FileAction.ARCHIVE,
            quiet=True,
            verbose=False,
            no_color=True,
            config_file=config_path,
            debug=True,
        )

        # Act
        result = options.to_dict()

        # Assert
        expected = {
            "dry_run": True,
            "file_action": FileAction.ARCHIVE,
            "quiet": True,
            "verbose": False,
            "no_color": True,
            "config_file": config_path,
            "debug": True,
        }
        assert result == expected

    def test_to_dict_defaults(self, mock_settings):
        """Test converting GlobalOptions with defaults to dictionary."""
        # Arrange
        options = GlobalOptions()

        # Act
        result = options.to_dict()

        # Assert
        expected = {
            "dry_run": False,
            "file_action": FileAction.OVERWRITE,  # Default from settings
            "quiet": False,
            "verbose": False,
            "no_color": False,
            "config_file": Path(".cgconfig.yaml"),  # Default from settings
            "debug": False,
        }
        assert result == expected


class TestStringRepresentation:
    """Tests for the __str__ method."""

    def test_str_complete(self, mock_settings):
        """Test string representation with all values."""
        # Arrange
        options = GlobalOptions(
            dry_run=True,
            file_action=FileAction.ARCHIVE,
            quiet=True,
            verbose=False,
            no_color=True,
            config_file=Path("config.yaml"),
            debug=True,
        )

        # Act
        result = str(options)

        # Assert
        expected = (
            "GlobalOptions(dry_run=True, "
            "file_action=FileAction.ARCHIVE, "
            "quiet=True, "
            "verbose=False, "
            "no_color=True, "
            f"config_file={Path('config.yaml')}, "
            "debug=True)"
        )
        assert result == expected

    def test_str_defaults(self, mock_settings):
        """Test string representation with default values."""
        # Arrange
        options = GlobalOptions()

        # Act
        result = str(options)

        # Assert
        expected = (
            "GlobalOptions(dry_run=False, "
            "file_action=FileAction.OVERWRITE, "
            "quiet=False, "
            "verbose=False, "
            "no_color=False, "
            "config_file=.cgconfig.yaml, "
            "debug=False)"
        )
        assert result == expected


class TestGlobalOptionsIntegrationScenarios:
    """Integration tests for realistic GlobalOptions usage scenarios."""

    def test_cli_to_service_workflow(self, mock_settings):
        """Test typical workflow from CLI context to service usage."""
        # Arrange - Simulate CLI context
        from unittest.mock import MagicMock

        mock_command = MagicMock()
        mock_command.allow_extra_args = False
        mock_command.allow_interspersed_args = True
        mock_command.ignore_unknown_options = False

        ctx = typer.Context(mock_command)
        ctx.obj = {
            "dry_run": True,
            "file_action": FileAction.OVERWRITE,
            "verbose": True,
            "config_file": "production.yaml",
        }

        # Act - Create options from context
        options = GlobalOptions.from_context(ctx)

        # Simulate service initialization
        service_config = options.to_dict()

        # Assert
        assert options.dry_run is True
        assert options.file_action == FileAction.OVERWRITE
        assert options.verbose is True
        assert options.config_file == Path("production.yaml")

        assert service_config["dry_run"] is True
        assert service_config["file_action"] == FileAction.OVERWRITE

    def test_settings_override_workflow(self, mock_settings):
        """Test workflow with settings defaults and CLI overrides."""
        # Arrange - Update mock settings
        mock_settings.options.global_options.dry_run = True
        mock_settings.options.global_options.file_action = FileAction.SKIP
        mock_settings.options.global_options.verbose = True

        # Act - Create with defaults
        options_default = GlobalOptions()

        # Create with overrides
        options_override = GlobalOptions(
            dry_run=False,
            file_action=FileAction.ARCHIVE,
        )

        # Assert
        # Note: Default params are evaluated at import time, so mock changes don't affect them
        assert options_default.dry_run is False  # From original mock settings
        assert (
            options_default.file_action == FileAction.OVERWRITE
        )  # From original mock settings
        assert options_default.verbose is False  # From original mock settings

        assert options_override.dry_run is False  # Explicitly set
        assert options_override.file_action == FileAction.ARCHIVE  # Explicitly set
        assert options_override.verbose is False  # From original mock settings

    def test_type_conversion_workflow(self, mock_settings):
        """Test workflow with various config file type conversions."""
        # Test different input types via constructor
        options_none = GlobalOptions(config_file=None)
        options_path = GlobalOptions(config_file=Path("path_object.yaml"))

        # Assert - Verify type handling
        assert options_none.config_file is None
        assert isinstance(options_path.config_file, Path)
        assert options_path.config_file == Path("path_object.yaml")
