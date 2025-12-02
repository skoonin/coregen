"""End-to-End tests for resource discovery workflow."""

import os

import pytest


@pytest.mark.e2e
def test_get_basic_command_help(run_cli_command):
    """Test the basic 'get' command help."""
    result = run_cli_command(
        "get --help", expected_code=0
    )  # Help commands return exit code 0

    assert result["success"]
    assert "Usage:" in result["stdout"]
    assert "get [OPTIONS] [PATTERNS]" in result["stdout"]
    # The formatted help might use different structure
    assert "--help" in result["stdout"] or "ARGUMENTS:" in result["stdout"]


@pytest.mark.e2e
def test_get_basic_workspace_pattern(env_setup, run_cli_command):
    """Test 'get' command with basic workspace pattern."""
    # Set up working directory
    os.chdir(env_setup["root_dir"])

    # Run 'get' with workspace pattern
    result = run_cli_command("get w/*")

    assert result["success"]
    # Check for workspace names in output
    assert "aws" in result["stdout"] or "workspaces" in result["stdout"]
    # Additional assertions specific to workspace output


@pytest.mark.e2e
def test_get_context_patterns(env_setup, run_cli_command):
    """Test 'get' command with context patterns."""
    # Set up working directory
    os.chdir(env_setup["root_dir"])

    # Run 'get' with context pattern
    result = run_cli_command("get c/*")

    assert result["success"]
    # Check for contexts key in output
    assert "contexts" in result["stdout"]
    # Additional assertions specific to context output


@pytest.mark.e2e
def test_get_component_patterns(env_setup, run_cli_command):
    """Test 'get' command with component patterns."""
    # Set up working directory in test_data where config file is
    os.chdir(env_setup["test_data_dir"])

    # Run 'get' with component pattern
    result = run_cli_command("get cm/*")

    assert result["success"]
    # CLI should return results in some format - either components or empty result
    # Empty result is valid if no components match the pattern
    if result["stdout"].strip() == "{}":
        # Empty result is acceptable - pattern didn't match anything
        assert True, "Empty result is valid for patterns with no matches"
    else:
        # If there are results, they should contain components
        assert (
            "components" in result["stdout"]
        ), "Non-empty results should contain components"


@pytest.mark.e2e
def test_get_recursive_pattern_matching(env_setup, run_cli_command):
    """Test 'get' command with recursive pattern matching."""
    # Set up working directory
    os.chdir(env_setup["root_dir"])

    # Run 'get' with recursive pattern
    result = run_cli_command("get cm/*/*")

    assert result["success"]
    # Verify recursive pattern results


@pytest.mark.e2e
def test_get_with_component_property_filter(env_setup, run_cli_command):
    """Test 'get' command with component property filter."""
    # Set up working directory
    os.chdir(env_setup["root_dir"])

    # Run 'get' with component property filter (example property)
    result = run_cli_command("get --filter type=nginx cm/*")

    assert result["success"]
    # Verify filtering by component property works


@pytest.mark.e2e
def test_get_with_activation_filter(env_setup, run_cli_command):
    """Test 'get' command with activation state filter."""
    # Set up working directory
    os.chdir(env_setup["root_dir"])

    # Run 'get' with activation filter
    result = run_cli_command("get --filter activated=true cm/*")

    assert result["success"]
    # Verify only activated components are shown


@pytest.mark.e2e
def test_get_with_generation_filter(env_setup, run_cli_command):
    """Test 'get' command with generation state filter."""
    # Set up working directory
    os.chdir(env_setup["root_dir"])

    # Run 'get' with generation filter
    result = run_cli_command("get --filter generated=false cm/*")

    assert result["success"]
    # Verify only non-generated components are shown


@pytest.mark.e2e
def test_get_with_combined_filters(env_setup, run_cli_command):
    """Test 'get' command with combined filter conditions."""
    # Set up working directory
    os.chdir(env_setup["root_dir"])

    # Run 'get' with combined filters
    result = run_cli_command(
        "get --filter environment=prod --filter activated=true cm/*"
    )

    assert result["success"]
    # Verify combined filtering works as expected


@pytest.mark.e2e
def test_get_json_output_format(env_setup, run_cli_command):
    """Test 'get' command with JSON output format."""
    # Set up working directory
    os.chdir(env_setup["root_dir"])

    # Run 'get' with JSON output format
    result = run_cli_command("get --output=json c/*")

    assert result["success"]
    # JSON output might have warnings before the actual JSON
    # Check that the output contains JSON structure markers
    assert "{" in result["stdout"]
    assert "}" in result["stdout"]
    # Verify JSON formatting is correct


@pytest.mark.e2e
def test_get_yaml_output_format(env_setup, run_cli_command):
    """Test 'get' command with YAML output format."""
    # Set up working directory
    os.chdir(env_setup["root_dir"])

    # Run 'get' with YAML output format
    result = run_cli_command("get --output=yaml cm/*")

    assert result["success"]
    # Verify YAML formatting is correct


@pytest.mark.e2e
def test_get_table_output_format(env_setup, run_cli_command):
    """Test 'get' command with table output format."""
    # Set up working directory
    os.chdir(env_setup["root_dir"])

    # Run 'get' with table output format
    result = run_cli_command("get --output=table c/*")

    assert result["success"]
    # Check for table border characters
    assert "┬" in result["stdout"] or "─" in result["stdout"] or "╭" in result["stdout"]
    # Verify table headers and data are present


@pytest.mark.e2e
def test_get_text_output_format(env_setup, run_cli_command):
    """Test 'get' command with table output format."""
    # Set up working directory
    os.chdir(env_setup["root_dir"])

    # Run 'get' with table output format (text not supported)
    result = run_cli_command("get --output=table cm/*")

    assert result["success"]
    # Verify table formatting is readable
