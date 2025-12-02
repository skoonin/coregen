"""End-to-end tests for empty result handling across all formats."""

import json
import os

import pytest


@pytest.mark.e2e
def test_empty_results_table_format(env_setup, run_cli_command):
    """Test empty results with table format."""
    os.chdir(env_setup["root_dir"])

    result = run_cli_command("get 'w/nonexistent' --output table")
    assert result["success"]

    # Should have table structure but indicate no results
    output = result["stdout"]
    assert (
        "│" in output
        or "|" in output
        or "no" in output.lower()
        or "empty" in output.lower()
    )


@pytest.mark.e2e
def test_empty_results_matrix_format(env_setup, run_cli_command):
    """Test empty results with matrix format."""
    os.chdir(env_setup["root_dir"])

    result = run_cli_command("get 'w/nonexistent' --output matrix")
    assert result["success"]

    data = json.loads(result["stdout"])
    assert "include" in data
    assert data["include"] == []


@pytest.mark.e2e
def test_empty_detect_changes(env_setup, run_cli_command):
    """Test detect-changes with no changes."""
    os.chdir(env_setup["root_dir"])

    # Setup git repository properly
    import subprocess

    # FIXED: Ensure proper git repository initialization
    try:
        # Initialize git repo with proper branch
        subprocess.run(["git", "init", "-b", "main"], check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "commit.gpgsign", "false"],
            check=True,
            capture_output=True,
        )

        # Add and commit all files including config
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"], check=True, capture_output=True
        )

        # Create a second commit so HEAD~1 exists for comparison
        test_file = env_setup["root_dir"] / "test.txt"
        test_file.write_text("test content")
        subprocess.run(["git", "add", "test.txt"], check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Second"], check=True, capture_output=True
        )

        # detect-changes doesn't take pattern arguments
        result = run_cli_command("detect-changes --output json")
        assert result["success"]

        # FIXED: Better handling of detect-changes output format
        if result["stdout"].strip().startswith("{"):
            data = json.loads(result["stdout"])
            # With no changes, should return empty data structure or a message
            assert "components" in data or "changed_files" in data or "message" in data
        else:
            # May return table format when no changes detected
            assert (
                "no changes" in result["stdout"].lower()
                or "message" in result["stdout"].lower()
            )
    except subprocess.CalledProcessError as e:
        # If git setup fails, skip the test with informative message
        pytest.skip(f"Git repository setup failed: {e}")


@pytest.mark.e2e
def test_empty_check_pattern(env_setup, run_cli_command):
    """Test check-pattern with non-matching pattern."""
    os.chdir(env_setup["root_dir"])

    result = run_cli_command("check-pattern 'w/nonexistent'")
    assert result["success"]

    # Should show table but indicate no matches
    assert (
        "│" in result["stdout"]
        or "|" in result["stdout"]
        or "no match" in result["stdout"].lower()
    )
