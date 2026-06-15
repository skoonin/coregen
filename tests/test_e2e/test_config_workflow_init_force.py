"""
E2E test for config init with force flag.

This test validates that the config init command works with the --force flag
to overwrite existing config files.
"""

import os
import subprocess
import sys

import pytest
import yaml


@pytest.mark.e2e
def test_config_force_overwrite(temp_test_dir):
    """Test config generate with --file-action overwrite flag."""
    # Create test directory
    config_test_dir = temp_test_dir / "config_init_force_test"
    config_test_dir.mkdir(exist_ok=True)

    # Create initial config file
    config_file = config_test_dir / ".cgconfig.yaml"
    with open(config_file, "w") as f:
        f.write("""# Initial test config with a unique marker
workspaces:
  - name: initial-workspace
    context_type: custom-type-for-test
""")

    # Store the file content to compare later
    initial_content = config_file.read_text()

    # Run config with file-action overwrite
    original_dir = os.getcwd()
    try:
        os.chdir(config_test_dir)

        # First verify the initial config exists and has our expected content
        with open(config_file) as f:
            initial_config_data = yaml.safe_load(f)

        assert (
            "workspaces" in initial_config_data
        ), "Initial config missing workspaces section"
        assert (
            len(initial_config_data["workspaces"]) == 1
        ), "Expected exactly one workspace in initial config"
        assert (
            initial_config_data["workspaces"][0]["name"] == "initial-workspace"
        ), "Initial workspace name mismatch"
        assert (
            initial_config_data["workspaces"][0]["context_type"]
            == "custom-type-for-test"
        ), "Custom type mismatch"

        # Now run config generate with file-action overwrite
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "coregen",
                "config",
                "generate",
                "--file-action",
                "overwrite",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # Check success
        assert (
            result.returncode == 0
        ), f"Config generate with overwrite failed: {result.stderr}"

        # Check that config file still exists
        assert config_file.exists(), "Config file does not exist after overwrite"

        # Read updated config content
        updated_content = config_file.read_text()

        # Verify content changed
        assert updated_content != initial_content, "Config file content was not changed"

        # Read updated config as YAML
        with open(config_file) as f:
            config_data = yaml.safe_load(f)

        # Verify that basic structure is maintained
        assert (
            "workspaces" in config_data
        ), "Workspaces section not found in generated config"

    finally:
        os.chdir(original_dir)
