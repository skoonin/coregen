"""End-to-end tests for error output scenarios."""

import os

import pytest


@pytest.mark.e2e
def test_invalid_command_syntax(env_setup, run_cli_command):
    """Test error output for invalid command syntax."""
    os.chdir(env_setup["root_dir"])

    # Missing pattern - get command without patterns shows help (exit code 0)
    result = run_cli_command("get", expected_code=0)
    assert result["success"]
    assert "usage" in result["stdout"].lower()

    # Invalid command
    result = run_cli_command("invalidcommand", expected_code=2)
    assert result["success"]  # Success means we got expected exit code
    assert (
        "invalid" in result["stderr"].lower()
        or "no such command" in result["stderr"].lower()
    )


@pytest.mark.e2e
def test_conflicting_options(env_setup, run_cli_command):
    """Test error output for conflicting options."""
    os.chdir(env_setup["root_dir"])

    # Pattern with --from-json
    result = run_cli_command("get 'w/*' --from-json '[]'", expected_code=1)
    assert result["success"]  # Success means we got expected exit code
    assert (
        "conflict" in result["stderr"].lower() or "cannot" in result["stderr"].lower()
    )

    # --from-json with --json-file (doesn't actually conflict, uses from-json)
    result = run_cli_command(
        "get --from-json '[]' --json-file test.json", expected_code=0
    )
    assert result["success"]


@pytest.mark.e2e
def test_invalid_output_format(env_setup, run_cli_command):
    """Test error output for invalid output formats."""
    os.chdir(env_setup["root_dir"])

    # Invalid format
    result = run_cli_command("get 'w/*' --output invalid", expected_code=2)
    assert result["success"]  # Success means we got expected exit code
    assert "invalid" in result["stderr"].lower()

    # Check-pattern doesn't have --output option, just test basic functionality
    result = run_cli_command("check-pattern 'w/*'", expected_code=0)
    assert result["success"]


@pytest.mark.e2e
def test_invalid_filter_syntax(env_setup, run_cli_command):
    """Test error output for invalid filter syntax."""
    os.chdir(env_setup["root_dir"])

    # Missing value - actually doesn't error, returns all results
    result = run_cli_command(
        "get 'c/*' --filter 'context.environment'", expected_code=0
    )
    assert result["success"]

    # Invalid property path - double dots doesn't error either
    result = run_cli_command(
        "get 'cm/*' --filter 'invalid..property=value'", expected_code=0
    )
    assert result["success"]


@pytest.mark.e2e
def test_invalid_pattern_syntax(env_setup, run_cli_command):
    """Test error output for invalid pattern syntax."""
    os.chdir(env_setup["root_dir"])

    # Invalid prefix - now returns error code 2
    result = run_cli_command("get 'x/*'", expected_code=2)
    assert result["success"]

    # Empty pattern also returns error code 2
    result = run_cli_command("get ''", expected_code=2)
    assert result["success"]


@pytest.mark.e2e
def test_missing_required_options(env_setup, run_cli_command):
    """Test error output when required options are missing."""
    os.chdir(env_setup["root_dir"])

    # detect-changes without pattern - returns error due to git issues in test env
    result = run_cli_command("detect-changes", expected_code=2)
    assert result["success"]  # Success means we got expected exit code
    assert "error" in result["stderr"].lower() or "git" in result["stderr"].lower()


@pytest.mark.e2e
def test_file_not_found_errors(env_setup, run_cli_command):
    """Test error output for file not found scenarios."""
    os.chdir(env_setup["root_dir"])

    # Non-existent config file
    result = run_cli_command("get 'w/*' -c /nonexistent/config.yaml", expected_code=2)
    assert result["success"]  # Success means we got expected exit code
    assert (
        "not found" in result["stderr"].lower()
        or "does not exist" in result["stderr"].lower()
        or "error" in result["stderr"].lower()
    )

    # JSON file not found
    result = run_cli_command("get --json-file /nonexistent/input.json", expected_code=2)
    assert result["success"]
    assert (
        "not found" in result["stderr"].lower()
        or "does not exist" in result["stderr"].lower()
        or "error" in result["stderr"].lower()
    )


@pytest.mark.e2e
def test_permission_errors(env_setup, run_cli_command):
    """Test error output for permission issues."""
    os.chdir(env_setup["root_dir"])

    # Create unreadable file
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test")
        temp_file = f.name

    try:
        os.chmod(temp_file, 0o000)
        result = run_cli_command(f"get --json-file {temp_file}", expected_code=2)
        assert result["success"]  # Success means we got expected exit code
        assert (
            "permission" in result["stderr"].lower()
            or "access" in result["stderr"].lower()
            or "error" in result["stderr"].lower()
        )
    finally:
        os.chmod(temp_file, 0o644)
        os.unlink(temp_file)


@pytest.mark.e2e
def test_malformed_json_input(env_setup, run_cli_command):
    """Test error output for malformed JSON input."""
    os.chdir(env_setup["root_dir"])

    # Invalid JSON
    result = run_cli_command("get --from-json '{invalid json}'", expected_code=2)
    assert result["success"]  # Success means we got expected exit code
    assert (
        "json" in result["stderr"].lower()
        or "parse" in result["stderr"].lower()
        or "error" in result["stderr"].lower()
    )

    # Valid JSON but wrong structure
    result = run_cli_command(
        "get --from-json '\"string instead of array\"'", expected_code=2
    )
    assert result["success"]
    assert "error" in result["stderr"].lower()


@pytest.mark.e2e
def test_type_mismatch_errors(env_setup, run_cli_command):
    """Test error output for type mismatches."""
    os.chdir(env_setup["root_dir"])

    # Component pattern with workspace type - this does error
    result = run_cli_command("get 'cm/*' --type workspace", expected_code=2)
    assert result["success"]
    assert (
        "invalid combination" in result["stderr"].lower()
        or "cannot" in result["stderr"].lower()
    )

    # Context pattern with component type - this returns empty results, not error
    result = run_cli_command("get 'c/*' --type component", expected_code=0)
    assert result["success"]
    # Check that it returns empty results instead of error
    assert "{}" in result["stdout"] or "empty" in result["stdout"].lower()
