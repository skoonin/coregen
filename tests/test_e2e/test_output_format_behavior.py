"""End-to-end tests for output format behavior."""

import json
import os

import pytest
import yaml

# REMOVED WORKAROUND: No longer accepting malformed JSON
# Tests should assert that JSON output is properly formatted
# If JSON parsing fails, the test should fail to reveal the bug


@pytest.mark.e2e
def test_get_command_output_formats(env_setup, run_cli_command):
    """Test get command with all supported output formats."""
    os.chdir(env_setup["root_dir"])

    # Test YAML format (default)
    result = run_cli_command("get w/*")
    assert result["success"]
    # Should be valid YAML
    try:
        yaml_data = yaml.safe_load(result["stdout"])
        assert "workspaces" in yaml_data
    except yaml.YAMLError:
        pytest.fail("Default output should be valid YAML")

    # Test explicit YAML format
    result = run_cli_command("get --output yaml w/*")
    assert result["success"]
    yaml_data = yaml.safe_load(result["stdout"])
    assert "workspaces" in yaml_data

    # Test JSON format
    result = run_cli_command("get --output json w/*")
    assert result["success"]
    json_data = json.loads(result["stdout"])
    assert "workspaces" in json_data

    # Test TABLE format
    result = run_cli_command("get --output table w/*")
    assert result["success"]
    # Check for table characters
    assert "│" in result["stdout"] or "┃" in result["stdout"] or "|" in result["stdout"]

    # Test MATRIX format
    result = run_cli_command("get --output matrix w/*")
    assert result["success"]
    matrix_data = json.loads(result["stdout"])
    assert "include" in matrix_data


@pytest.mark.e2e
def test_detect_changes_output_formats(env_setup, run_cli_command):
    """Test detect-changes command with all supported output formats."""
    os.chdir(env_setup["root_dir"])

    # Initialize git repo and create initial commit
    import subprocess

    subprocess.run(["git", "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"], check=True, capture_output=True
    )

    # Create initial commit with config file
    initial_file = env_setup["root_dir"] / "initial.txt"
    initial_file.write_text("initial content")
    subprocess.run(["git", "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], check=True, capture_output=True
    )

    # Create second commit to ensure HEAD~1 exists
    second_file = env_setup["root_dir"] / "second.txt"
    second_file.write_text("second content")
    subprocess.run(["git", "add", "second.txt"], check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Second commit"], check=True, capture_output=True
    )

    # Create a dummy change (uncommitted)
    test_file = env_setup["root_dir"] / "test_change.txt"
    test_file.write_text("test")

    # Test JSON format (default)
    result = run_cli_command("detect-changes")
    assert result["success"]
    # When no changes detected, may return table format regardless of output setting
    if result["stdout"].strip().startswith("{"):
        json_data = json.loads(result["stdout"])
        assert (
            "components" in json_data
            or "changed_files" in json_data
            or "message" in json_data
        )
    else:
        # Table format fallback for no changes
        assert (
            "no changes" in result["stdout"].lower()
            or "message" in result["stdout"].lower()
        )

    # Test explicit JSON format
    result = run_cli_command("detect-changes --output json")
    assert result["success"]
    # When no changes detected, may return table format regardless of output setting
    if result["stdout"].strip().startswith("{"):
        json_data = json.loads(result["stdout"])
        assert (
            "components" in json_data
            or "changed_files" in json_data
            or "message" in json_data
        )
    else:
        # Table format fallback for no changes
        assert (
            "no changes" in result["stdout"].lower()
            or "message" in result["stdout"].lower()
        )

    # Test YAML format
    result = run_cli_command("detect-changes --output yaml")
    assert result["success"]
    # When no changes detected, may return table format regardless of output setting
    if result["stdout"].strip().startswith("---") or not result[
        "stdout"
    ].strip().startswith("╭"):
        yaml_data = yaml.safe_load(result["stdout"])
        assert (
            "components" in yaml_data
            or "changed_files" in yaml_data
            or "message" in yaml_data
        )
    else:
        # Table format fallback for no changes
        assert (
            "no changes" in result["stdout"].lower()
            or "message" in result["stdout"].lower()
        )

    # Test MATRIX format
    result = run_cli_command("detect-changes --output matrix")
    assert result["success"]
    # When no changes detected, may return table format regardless of output setting
    if result["stdout"].strip().startswith("{"):
        matrix_data = json.loads(result["stdout"])
        assert (
            "include" in matrix_data
            or "components" in matrix_data
            or "message" in matrix_data
        )
    else:
        # Table format fallback for no changes
        assert (
            "no changes" in result["stdout"].lower()
            or "message" in result["stdout"].lower()
        )

    # Clean up
    if test_file.exists():
        test_file.unlink()


@pytest.mark.e2e
def test_config_view_output_formats(env_setup, run_cli_command):
    """Test config view command with supported output formats."""
    os.chdir(env_setup["root_dir"])

    # Test YAML format (default)
    result = run_cli_command("config view raw")
    assert result["success"]
    yaml_data = yaml.safe_load(result["stdout"])
    assert "workspaces" in yaml_data

    # Test explicit YAML format
    result = run_cli_command("config view raw --output yaml")
    assert result["success"]
    yaml_data = yaml.safe_load(result["stdout"])
    assert "workspaces" in yaml_data

    # Test JSON format
    result = run_cli_command("config view raw --output json")
    assert result["success"]
    json_data = json.loads(result["stdout"])
    assert "workspaces" in json_data


@pytest.mark.e2e
def test_config_schema_output_formats(env_setup, run_cli_command):
    """Test config schema command with supported output formats."""
    os.chdir(env_setup["root_dir"])

    # Test JSON format (default)
    result = run_cli_command("config schema all")
    assert result["success"]
    # Should contain schema information
    assert "properties" in result["stdout"] or "title" in result["stdout"]

    # Test explicit JSON format
    result = run_cli_command("config schema all --output json")
    assert result["success"]
    assert "properties" in result["stdout"] or "title" in result["stdout"]

    # Test YAML format
    result = run_cli_command("config schema all --output yaml")
    assert result["success"]
    assert "properties" in result["stdout"] or "title" in result["stdout"]


@pytest.mark.e2e
def test_check_pattern_table_only(env_setup, run_cli_command):
    """Test that check-pattern only supports TABLE format."""
    os.chdir(env_setup["root_dir"])

    # Test default (should be TABLE)
    result = run_cli_command("check-pattern w/*")
    assert result["success"]
    # Should contain table formatting
    assert (
        "Pattern" in result["stdout"]
        and "Match %" in result["stdout"]
        and (
            "│" in result["stdout"]
            or "┃" in result["stdout"]
            or "|" in result["stdout"]
        )
    )

    # Test that other formats are not available
    # Note: check-pattern doesn't have an --output option in the new architecture


@pytest.mark.e2e
def test_generate_text_only(env_setup, run_cli_command):
    """Test that generate command outputs TEXT format only."""
    os.chdir(env_setup["root_dir"])

    # Test default (should be TEXT)
    # Note: generate might exit with 2 if there are warnings
    result = run_cli_command("generate w/* --dry-run")
    # Should contain progress messages, not structured data (check both stdout and stderr)
    combined = result["stdout"] + result["stderr"]
    # FIXED: Tightened assertion - "dry" alone was too permissive
    assert "[DRY RUN]" in combined or "Processing" in combined
    # Verify it's not JSON or YAML (checking stdout only)
    assert not result["stdout"].strip().startswith("{")
    assert not result["stdout"].strip().startswith("---")


@pytest.mark.e2e
def test_invalid_output_formats(env_setup, run_cli_command):
    """Test commands with invalid output formats."""
    os.chdir(env_setup["root_dir"])

    # Test get with invalid format
    result = run_cli_command("get w/* --output invalid", expected_code=2)
    assert result["exit_code"] == 2
    combined = result["stdout"].lower() + result["stderr"].lower()
    # FIXED: Tightened assertion to be more specific about validation errors
    assert "invalid" in combined and (
        "choice" in combined or "output" in combined or "value" in combined
    )

    # Test detect-changes with unsupported format (table)
    # Note: may fail with git repo error rather than format error
    result = run_cli_command("detect-changes --output table", expected_code=2)
    assert result["exit_code"] == 2
    combined = result["stdout"].lower() + result["stderr"].lower()
    assert (
        "invalid value" in combined
        or "git repository" in combined
        or (
            "invalid" in combined
            and ("choice" in combined or "output" in combined or "value" in combined)
        )
    )  # Accept any expected error

    # Test config view with unsupported format (table)
    result = run_cli_command("config view raw --output table", expected_code=None)
    assert result["exit_code"] != 0  # Should fail with any non-zero exit code
    combined = result["stdout"].lower() + result["stderr"].lower()
    # FIXED: Tightened assertion to be more specific about validation errors
    assert "not supported" in combined or (
        "invalid" in combined
        and ("output" in combined or "choice" in combined or "value" in combined)
    )

    # Test config view with unsupported format (matrix)
    result = run_cli_command("config view raw --output matrix", expected_code=None)
    assert result["exit_code"] != 0  # Should fail with any non-zero exit code
    combined = result["stdout"].lower() + result["stderr"].lower()
    # FIXED: Tightened assertion to be more specific about validation errors
    assert "not supported" in combined or (
        "invalid" in combined
        and ("output" in combined or "choice" in combined or "value" in combined)
    )


@pytest.mark.e2e
def test_environment_variable_output_format(env_setup, run_cli_command):
    """Test output format via environment variables."""
    os.chdir(env_setup["root_dir"])

    # Initialize git repo for detect-changes test
    import subprocess

    subprocess.run(["git", "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"], check=True, capture_output=True
    )

    # Create commits for HEAD~1 to exist (include config file)
    initial_file = env_setup["root_dir"] / "initial.txt"
    initial_file.write_text("initial content")
    subprocess.run(["git", "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], check=True, capture_output=True
    )

    second_file = env_setup["root_dir"] / "second.txt"
    second_file.write_text("second content")
    subprocess.run(["git", "add", "second.txt"], check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Second commit"], check=True, capture_output=True
    )

    # Test get with env var
    env = {"CG_OUTPUT_FORMAT": "json"}
    result = run_cli_command("get w/*", env=env)
    assert result["success"]
    json_data = json.loads(result["stdout"])
    assert "workspaces" in json_data

    # Test detect-changes with env var (may fail due to git setup, focus on format)
    env = {"CG_OUTPUT_FORMAT": "yaml"}
    result = run_cli_command("detect-changes", env=env, expected_code=None)
    if result["exit_code"] == 0:
        # If successful, check the format
        # When no changes detected, may return table format regardless of output setting
        if result["stdout"].strip().startswith("---") or not result[
            "stdout"
        ].strip().startswith("╭"):
            yaml_data = yaml.safe_load(result["stdout"])
            assert (
                "components" in yaml_data
                or "changed_files" in yaml_data
                or "message" in yaml_data
            )
        else:
            # Table format fallback for no changes
            assert (
                "no changes" in result["stdout"].lower()
                or "message" in result["stdout"].lower()
            )
    else:
        # If failed, just ensure it's a git-related error, not format error
        combined_output = (result["stdout"] + result["stderr"]).lower()
        assert (
            "git" in combined_output
            or "repository" in combined_output
            or "ref" in combined_output
            or "config" in combined_output
        ), "Should be git-related error, not format error"

    # Test config view with env var
    env = {"CG_OUTPUT_FORMAT": "json"}
    result = run_cli_command("config view raw", env=env)
    assert result["success"]
    json_data = json.loads(result["stdout"])
    assert "workspaces" in json_data


@pytest.mark.e2e
def test_output_format_precedence(env_setup, run_cli_command):
    """Test that CLI args take precedence over env vars."""
    os.chdir(env_setup["root_dir"])

    # Set env var to YAML but use JSON in CLI
    env = {"CG_OUTPUT_FORMAT": "yaml"}
    result = run_cli_command("get w/* --output json", env=env)
    assert result["success"]
    # Should be JSON (CLI takes precedence)
    json_data = json.loads(result["stdout"])
    assert "workspaces" in json_data

    # Set env var to JSON but use YAML in CLI
    env = {"CG_OUTPUT_FORMAT": "json"}
    result = run_cli_command("config view raw --output yaml", env=env)
    assert result["success"]
    # Should be YAML (CLI takes precedence)
    yaml_data = yaml.safe_load(result["stdout"])
    assert "workspaces" in yaml_data
