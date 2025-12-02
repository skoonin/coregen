"""
E2E tests for environment setup and prerequisites.

These tests validate that the test environment is properly set up for running E2E tests.
"""

import os
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_temp_dir_creation(temp_test_dir):
    """Test that temporary test directory is created correctly."""
    assert temp_test_dir.exists()
    assert temp_test_dir.is_dir()


@pytest.mark.e2e
def test_test_data_setup(test_data_dir):
    """Test that test data is copied correctly."""
    # Test that the directory exists
    assert test_data_dir.exists()
    assert test_data_dir.is_dir()

    # Test that key subdirectories are copied
    assert (test_data_dir / "common-templates").exists()
    assert (test_data_dir / "contexts").exists()

    # Test that config file is copied
    assert (test_data_dir / ".cgconfig.yaml").exists()


@pytest.mark.e2e
def test_git_repo_setup(test_git_repo):
    """Test that git repository is set up correctly."""
    # Test that the directory exists
    assert test_git_repo.exists()
    assert test_git_repo.is_dir()

    # Test that git directory exists
    assert (test_git_repo / ".git").exists()

    # Test that initial commit exists
    os.chdir(test_git_repo)
    git_log = os.popen("git log --oneline").read()
    assert "Initial commit" in git_log

    # Test that test file exists and has content
    test_file = test_git_repo / "test_file.txt"
    assert test_file.exists()
    assert "Initial content" in test_file.read_text()


@pytest.mark.e2e
def test_full_env_setup(env_setup):
    """Test that full environment setup works correctly."""
    # Test all paths in env_setup
    for key, path in env_setup.items():
        if isinstance(path, Path):
            assert path.exists(), f"Path for {key} does not exist: {path}"

    # Test config file
    assert env_setup["config_path"].exists()

    # Test contexts directory
    assert env_setup["contexts_dir"].exists()
    assert (env_setup["contexts_dir"] / "context-dev").exists()
    assert (env_setup["contexts_dir"] / "prod").exists()

    # Test templates directory
    assert env_setup["templates_dir"].exists()
    assert (env_setup["templates_dir"] / "metrics-server").exists()
    assert (env_setup["templates_dir"] / "prometheus").exists()


@pytest.mark.e2e
def test_cli_command_runner(temp_test_dir, run_cli_command):
    """Test that CLI command runner works correctly."""
    # Create a test directory structure
    test_dir = temp_test_dir / "cli_test"
    test_dir.mkdir()

    # Test help command
    result = run_cli_command("--help", test_dir)
    assert result["success"]
    assert "Usage:" in result["stdout"]

    # Test version command
    result = run_cli_command("version", test_dir)
    assert result["success"]
    assert result["exit_code"] == 0

    # Test invalid command
    result = run_cli_command("invalid-command", test_dir, expected_code=2)
    assert result["exit_code"] == 2
