"""Unit tests for output formatting functionality."""

import json
from io import StringIO
from typing import Any

import pytest
import yaml
from rich.console import Console
from rich.table import Table
from rich.text import Text

from coregen.cli.enums.enum_output_format import OutputFormat
from coregen.common.formatter import Formatter


@pytest.fixture
def sample_data() -> Any:
    """Sample data for testing different formats."""
    return {
        "string": "test string",
        "integer": 42,
        "boolean": True,
        "list": ["item1", "item2"],
        "nested": {"key": "value", "nums": [1, 2, 3]},
    }


@pytest.fixture
def rich_console() -> Any:
    """Fixture to create a Rich console for testing rendered output."""
    console = Console(file=StringIO(), width=100)
    return console


def test_json_formatting(sample_data):
    """Test JSON formatting with different data structures."""
    # Format dictionary
    result = Formatter.format_output(sample_data, "json")
    assert isinstance(result, str)
    assert '"string": "test string"' in result
    assert '"integer": 42' in result

    # Verify JSON is valid by parsing it
    parsed = json.loads(result)
    assert parsed["string"] == "test string"
    assert parsed["integer"] == 42
    assert parsed["boolean"] is True
    assert parsed["list"] == ["item1", "item2"]
    assert parsed["nested"]["key"] == "value"

    # Format string that's already JSON
    json_str = '{"key": "value"}'
    result = Formatter.format_output(json_str, "json")
    assert isinstance(result, str)
    assert '"key": "value"' in result

    # Invalid JSON string should be returned with newline
    invalid_json = "not json"
    result = Formatter.format_output(invalid_json, "json")
    assert result == "not json\n"  # Formatter adds newline for consistency

    # Test with complex nested structures
    complex_data = {"level1": {"level2": {"level3": [1, 2, {"level4": "deep"}]}}}
    result = Formatter.format_output(complex_data, "json")
    assert isinstance(result, str)
    # Verify JSON is valid
    parsed = json.loads(result)
    assert parsed["level1"]["level2"]["level3"][2]["level4"] == "deep"


def test_yaml_formatting(sample_data):
    """Test YAML formatting with different data structures."""
    # Format dictionary
    result = Formatter.format_output(sample_data, "yaml")
    assert isinstance(result, str)
    assert "string: test string" in result
    assert "integer: 42" in result

    # Verify YAML is valid by parsing it
    parsed = yaml.safe_load(result)
    assert parsed["string"] == "test string"
    assert parsed["integer"] == 42
    assert parsed["boolean"] is True
    assert parsed["list"] == ["item1", "item2"]
    assert parsed["nested"]["key"] == "value"

    # Multi-line string should be properly formatted
    data = {"key": "line1\nline2"}
    result = Formatter.format_output(data, "yaml")
    assert isinstance(result, str)

    # Check the key value is formatted as a multi-line block
    # Here we're just checking that the string is formatted properly,
    # either with literal style (|) or folded style (>)
    assert "key:" in result
    assert "line1" in result
    assert "line2" in result

    # Test with complex nested structures
    complex_data = {"level1": {"level2": {"level3": [1, 2, {"level4": "deep"}]}}}
    result = Formatter.format_output(complex_data, "yaml")
    assert isinstance(result, str)
    # Verify YAML is valid
    parsed = yaml.safe_load(result)
    assert parsed["level1"]["level2"]["level3"][2]["level4"] == "deep"


def test_table_formatting(rich_console):
    """Test table formatting with different input types."""
    # Dictionary to two-column table
    data = {"name": "test", "value": 123}
    result = Formatter.format_output(data, "table")
    assert isinstance(result, Table)
    assert len(result.columns) == 2  # Key and Value columns

    # Render table to check output
    rich_console.print(result)
    output = rich_console.file.getvalue()
    assert "name" in output
    assert "test" in output
    assert "value" in output
    assert "123" in output
    rich_console.file = StringIO()  # Reset output buffer

    # List of dictionaries to multi-column table
    data = [
        {"name": "item1", "value": 100, "active": True},
        {"name": "item2", "value": 200, "active": False},
    ]
    result = Formatter.format_output(data, "table")
    assert isinstance(result, Table)
    assert len(result.columns) == 3  # name, value, active columns

    # Render table to check output
    rich_console.print(result)
    output = rich_console.file.getvalue()
    # Table formatter capitalizes headers
    assert "Name" in output or "name" in output.lower()
    assert "Value" in output or "value" in output.lower()
    assert "Active" in output or "active" in output.lower()
    assert "item1" in output
    assert "item2" in output
    assert "100" in output
    assert "200" in output
    # Table formatter uses checkmarks for booleans
    assert "✓" in output or "True" in output or "true" in output.lower()
    assert "✗" in output or "False" in output or "false" in output.lower()
    rich_console.file = StringIO()  # Reset output buffer

    # List of lists with headers
    data = [
        ["Name", "Value", "Status"],
        ["item1", 100, "active"],
        ["item2", 200, "inactive"],
    ]
    result = Formatter.format_output(data, "table")
    assert isinstance(result, Table)
    assert len(result.columns) == 3

    # Render table to check output
    rich_console.print(result)
    output = rich_console.file.getvalue()
    assert "Name" in output
    assert "Value" in output
    assert "Status" in output
    assert "item1" in output
    assert "item2" in output
    assert "100" in output
    assert "200" in output
    assert "active" in output
    assert "inactive" in output


def test_table_column_config(rich_console):
    """Test table formatting with column configurations."""
    # Test with width constraints and column alignment
    data = [
        {
            "name": "Very Long Name That Should Be Truncated",
            "value": 100,
            "active": True,
        },
        {"name": "Short", "value": 999999999, "active": False},
    ]

    # Using OutputFormat enum to test real-world usage
    result = Formatter.format_output(data, OutputFormat.TABLE)
    assert isinstance(result, Table)

    # Render table to check output
    rich_console.print(result)
    output = rich_console.file.getvalue()
    # Table formatter capitalizes headers
    assert "Name" in output or "name" in output.lower()
    assert "Very Long Name" in output  # Should contain at least part of the name
    assert "Short" in output
    assert "100" in output
    assert "999999999" in output


def test_error_handling():
    """Test error handling in formatting."""
    # Invalid format type - should return Text with the content
    result = Formatter.format_output("test", "invalid_format")
    assert isinstance(result, Text)
    assert result.plain == "test"  # Use .plain to get text content without style

    # JSON formatting with custom object - should serialize to {}
    class UnserializableObject:
        pass

    result = Formatter.format_output(UnserializableObject(), "json")
    # JSON formatter now handles all objects by converting to serializable format
    assert isinstance(result, str)
    assert result == "{}\n"  # Empty object serialization with newline

    # YAML formatting error
    import datetime

    # YAML can handle datetime but might format it differently than expected
    data = {"date": datetime.datetime.now()}
    result = Formatter.format_output(data, "yaml")
    assert isinstance(result, str)
    assert "date:" in result

    # Test JSON decode error handling
    invalid_json = '{"key": invalid}'
    result = Formatter.JSON().format(invalid_json)
    # JSON formatter returns a string when given invalid JSON
    assert invalid_json in result

    # Test YAML error handling
    invalid_yaml = "key: [unclosed"
    result = Formatter.YAML().format(invalid_yaml)
    # YAML formatter returns a string when given invalid YAML
    assert invalid_yaml in result


def test_format_output_with_none():
    """Test handling of None values in different formats."""
    # Text format
    assert str(Formatter.format_output(None, "text")) == "None"

    # JSON format
    result = Formatter.format_output(None, "json")
    assert "null" in result

    # YAML format
    result = Formatter.format_output(None, "yaml")
    assert "null" in result.lower()

    # Table format
    result = Formatter.format_output(None, "table")
    assert isinstance(result, Table)

    # Dict format
    result = Formatter.format_output(None, "dict")
    assert isinstance(result, Text)
    assert str(result) == "None"
