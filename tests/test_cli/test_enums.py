"""Tests for CLI enums."""

import pytest

# Import enums directly
from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.enums.enum_output_format import OutputFormat


@pytest.mark.parametrize(
    "enum_value,expected_string",
    [
        (FileAction.ASK, "ask"),
        (FileAction.SKIP, "skip"),
        (FileAction.OVERWRITE, "overwrite"),
        (FileAction.ARCHIVE, "archive"),
        (FileAction.DELETE, "delete"),
    ],
)
def test_file_action_enum_value(enum_value, expected_string):
    """Test FileAction enum has the expected values."""
    assert enum_value == expected_string


def test_file_action_enum_count():
    """Test FileAction enum count."""
    assert len(FileAction) == 5


@pytest.mark.parametrize(
    "enum_value,string_value",
    [
        (FileAction.ASK, "ask"),
        (FileAction.SKIP, "skip"),
        (FileAction.OVERWRITE, "overwrite"),
        (FileAction.ARCHIVE, "archive"),
        (FileAction.DELETE, "delete"),
    ],
)
def test_file_action_string_comparison(enum_value, string_value):
    """Test FileAction enum comparisons with strings."""
    # Compare enum with matching string
    assert enum_value == string_value
    # Case sensitivity check (should be case sensitive)
    assert enum_value != string_value.upper()


def test_file_action_enum_comparison():
    """Test FileAction enum self-comparison."""
    assert FileAction.ASK == FileAction.ASK
    assert FileAction.ASK != FileAction.SKIP


@pytest.mark.parametrize(
    "string_value,expected_enum",
    [
        ("ask", FileAction.ASK),
        ("skip", FileAction.SKIP),
        ("overwrite", FileAction.OVERWRITE),
        ("archive", FileAction.ARCHIVE),
        ("delete", FileAction.DELETE),
    ],
)
def test_file_action_from_string(string_value, expected_enum):
    """Test FileAction enum creation from strings."""
    assert FileAction(string_value) == expected_enum


def test_file_action_from_invalid_string():
    """Test FileAction enum rejects invalid strings."""
    with pytest.raises(ValueError):
        FileAction("invalid")


def test_output_format_enum_values():
    """Test OutputFormat enum has the expected values."""
    # Check all expected values are in the enum
    assert OutputFormat.TEXT == "text"
    assert OutputFormat.JSON == "json"
    assert OutputFormat.YAML == "yaml"
    assert (
        OutputFormat.MATRIX == "matrix"
    )  # Updated from GITHUB_ACTIONS_MATRIX to MATRIX
    assert hasattr(OutputFormat, "TABLE")  # Check if TABLE exists

    # Ensure the count matches expected (adjust if more formats exist)
    assert len(OutputFormat) >= 4


@pytest.mark.parametrize(
    "enum_value,string_value",
    [
        (OutputFormat.TEXT, "text"),
        (OutputFormat.JSON, "json"),
        (OutputFormat.YAML, "yaml"),
        (OutputFormat.MATRIX, "matrix"),
        (OutputFormat.TABLE, "table"),
    ],
)
def test_output_format_string_comparison(enum_value, string_value):
    """Test OutputFormat enum comparisons with strings."""
    # Compare enum with matching string
    assert enum_value == string_value
    # Case sensitivity check (should be case sensitive)
    assert enum_value != string_value.upper()


def test_output_format_enum_comparison():
    """Test OutputFormat enum self-comparison."""
    assert OutputFormat.TEXT == OutputFormat.TEXT
    assert OutputFormat.TEXT != OutputFormat.JSON


@pytest.mark.parametrize(
    "string_value,expected_enum",
    [
        ("text", OutputFormat.TEXT),
        ("json", OutputFormat.JSON),
        ("yaml", OutputFormat.YAML),
        ("matrix", OutputFormat.MATRIX),
        ("table", OutputFormat.TABLE),
    ],
)
def test_output_format_from_string(string_value, expected_enum):
    """Test OutputFormat enum creation from strings."""
    assert OutputFormat(string_value) == expected_enum


def test_output_format_from_invalid_string():
    """Test OutputFormat enum rejects invalid strings."""
    with pytest.raises(ValueError):
        OutputFormat("invalid")


def test_file_action_in_cli(cli_runner, cli_app):
    """Test FileAction enum integration with CLI."""
    # Test valid file action option
    result = cli_runner.invoke(cli_app, ["--file-action", "skip", "--help"])
    assert result.exit_code == 0

    # Test invalid file action option
    result = cli_runner.invoke(cli_app, ["--file-action", "invalid", "--help"])
    assert result.exit_code != 0
    # Typer exits immediately with invalid enum values, so just check the exit code


def test_output_format_in_cli(cli_runner, cli_app):
    """Test OutputFormat enum integration with CLI."""
    # Since output format is no longer a global option, test it at command level
    # Test valid output format option with config view command
    result = cli_runner.invoke(
        cli_app, ["config", "view", "--output", "json", "--help"]
    )
    assert result.exit_code == 0

    # Test invalid output format option
    result = cli_runner.invoke(cli_app, ["config", "view", "--output", "invalid"])
    assert result.exit_code != 0
    # Typer exits immediately with invalid enum values, so just check the exit code
