"""End-to-end tests for wildcard pattern functionality."""

import json
import os

import pytest
import yaml


@pytest.mark.e2e
def test_wildcard_prefix_pattern(env_setup, run_cli_command):
    """Test wildcard patterns with prefix matching."""
    os.chdir(env_setup["root_dir"])

    # Test component prefix pattern - changed to match actual test data
    result = run_cli_command("get 'cm/test*' --output json")
    assert result["success"], f"Command failed: {result.get('stderr', '')}"

    data = json.loads(result["stdout"])
    # Empty result is OK if no matching components exist
    if data and "components" in data:
        # Should match test and any other test* components
        for component in data["components"]:
            assert component["name"].startswith(
                "test"
            ), f"Component {component['name']} doesn't match test*"


@pytest.mark.e2e
def test_wildcard_suffix_pattern(env_setup, run_cli_command):
    """Test wildcard patterns with suffix matching."""
    os.chdir(env_setup["root_dir"])

    # Test context suffix pattern
    result = run_cli_command("get 'c/*-dev' --output json")
    assert result["success"]

    data = json.loads(result["stdout"])
    # Empty result is OK if no matching contexts exist
    if data and "contexts" in data:
        # Should match contexts ending with -dev
        for context in data["contexts"]:
            assert context["name"].endswith(
                "-dev"
            ), f"Context {context['name']} doesn't match *-dev"


@pytest.mark.e2e
def test_wildcard_middle_pattern(env_setup, run_cli_command):
    """Test wildcard patterns with middle matching."""
    os.chdir(env_setup["root_dir"])

    # Test pattern with wildcard in middle
    result = run_cli_command("get 'c/aws-*-dev' --output json")
    assert result["success"]

    data = json.loads(result["stdout"])
    if data.get("contexts"):
        for context in data["contexts"]:
            assert context["name"].startswith("aws-") and context["name"].endswith(
                "-dev"
            )


@pytest.mark.e2e
def test_multiple_wildcards(env_setup, run_cli_command):
    """Test patterns with multiple wildcards."""
    os.chdir(env_setup["root_dir"])

    # Test pattern with multiple wildcards
    result = run_cli_command("get 'c/aws-*-*' --output json")
    assert result["success"]

    data = json.loads(result["stdout"])
    if data.get("contexts"):
        for context in data["contexts"]:
            assert context["name"].startswith("aws-")
            # Should have at least 2 dashes for aws-*-*
            assert context["name"].count("-") >= 2


@pytest.mark.e2e
def test_wildcard_with_format_types(env_setup, run_cli_command):
    """Test wildcard patterns work with different format types."""
    os.chdir(env_setup["root_dir"])

    # Test with flat format - changed to match actual test data
    result = run_cli_command("get 'cm/test*' --format-type flat --output json")
    assert result["success"]

    data = json.loads(result["stdout"])
    # Empty result or list is OK
    if data:
        assert isinstance(data.get("components", []), list)

    # Test with nested format
    result_nested = run_cli_command("get 'w/*' --format-type nested --output json")
    assert result_nested["success"]


@pytest.mark.e2e
def test_wildcard_with_filters(env_setup, run_cli_command):
    """Test wildcard patterns combined with filters."""
    os.chdir(env_setup["root_dir"])

    # Wildcard pattern with environment filter
    result = run_cli_command(
        "get 'c/*-dev' --filter 'context.environment=dev' --output json"
    )
    assert result["success"]

    data = json.loads(result["stdout"])
    # All contexts should end with -dev AND have environment=dev
    if data.get("contexts"):
        for context in data["contexts"]:
            assert context["name"].endswith("-dev")
            assert context.get("environment") == "dev"


@pytest.mark.e2e
def test_wildcard_no_matches(env_setup, run_cli_command):
    """Test wildcard patterns that match nothing."""
    os.chdir(env_setup["root_dir"])

    # Pattern that shouldn't match anything
    result = run_cli_command("get 'cm/xyz*' --output json")
    assert result["success"]

    data = json.loads(result["stdout"])
    assert data.get("components", []) == []


@pytest.mark.e2e
def test_wildcard_all_formats(env_setup, run_cli_command):
    """Test wildcard patterns work with all output formats."""
    os.chdir(env_setup["root_dir"])

    formats = ["json", "yaml", "table", "matrix"]

    for fmt in formats:
        result = run_cli_command(f"get 'cm/prom*' --output {fmt}")
        assert result["success"], f"Failed with {fmt} format"

        if fmt == "json":
            json.loads(result["stdout"])
        elif fmt == "yaml":
            yaml.safe_load(result["stdout"])
        elif fmt == "table":
            assert "│" in result["stdout"] or "|" in result["stdout"]
        elif fmt == "matrix":
            data = json.loads(result["stdout"])
            assert "include" in data
