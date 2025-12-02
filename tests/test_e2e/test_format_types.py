"""End-to-end tests for format type functionality (flat/nested/grouped)."""

import json
import os

import pytest
import yaml


@pytest.mark.e2e
def test_format_type_with_type_filter(env_setup, run_cli_command):
    """Test format types combined with type filtering."""
    os.chdir(env_setup["root_dir"])

    # Get only components in flat format
    result = run_cli_command(
        "get 'w/*' --type component --format-type flat --output json"
    )
    assert result["success"]

    data = json.loads(result["stdout"])

    # Should only have components when filtered by type
    assert "components" in data
    assert "workspaces" not in data
    assert "contexts" not in data


@pytest.mark.e2e
def test_format_type_with_name_only(env_setup, run_cli_command):
    """Test format types with name-only option."""
    os.chdir(env_setup["root_dir"])

    # Flat format with name-only should return just an array of names
    result = run_cli_command("get 'w/*' --format-type flat --name-only --output json")
    assert result["success"]

    data = json.loads(result["stdout"])

    # With name-only, should just be an array of strings
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(isinstance(name, str) for name in data)

    # Nested format with name-only should also return array
    result_nested = run_cli_command(
        "get 'w/*' --format-type nested --name-only --output json"
    )
    assert result_nested["success"]

    data_nested = json.loads(result_nested["stdout"])
    assert isinstance(data_nested, list)

    # Both formats should produce same result with name-only
    assert data == data_nested


@pytest.mark.e2e
def test_format_type_yaml_output(env_setup, run_cli_command):
    """Test format types work with YAML output."""
    os.chdir(env_setup["root_dir"])

    result = run_cli_command("get 'w/*' --format-type flat --output yaml")
    assert result["success"]

    # Should be valid YAML
    data = yaml.safe_load(result["stdout"])

    # Verify structure is same as JSON
    assert "workspaces" in data
    assert isinstance(data["workspaces"], list)
    # May not have all entity types with w/* pattern
    if "contexts" in data:
        assert isinstance(data["contexts"], list)
    if "components" in data:
        assert isinstance(data["components"], list)


@pytest.mark.e2e
def test_invalid_format_type_error(env_setup, run_cli_command):
    """Test error handling for invalid format types."""
    os.chdir(env_setup["root_dir"])

    result = run_cli_command("get 'w/*' --format-type invalid", expected_code=2)
    assert result["success"]  # Success means we got expected exit code
    # The error should mention invalid format type (in stderr)
    assert (
        "invalid" in result["stderr"].lower()
        or "not one of" in result["stderr"].lower()
    )
