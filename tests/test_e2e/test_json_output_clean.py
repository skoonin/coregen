"""Test that config view JSON/YAML outputs are clean without debug messages."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml


@pytest.mark.integration
class TestJsonOutputClean:
    """Test that JSON/YAML output formats don't include console messages."""

    def create_test_config(self):
        """Create a minimal valid config file for testing."""
        config_content = """
workspaces:
  - name: test-workspace
    path: .
    context_type: environments
    context_config_files:
      - "**/context.yaml"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            return Path(f.name)

    def run_command(self, cmd_args):
        """Run coregen command and return result."""
        cmd = [sys.executable, "-m", "coregen"] + cmd_args

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result

    def test_json_output_discovered_clean(self):
        """Test that discovered mode JSON output is clean."""
        config_file = None
        try:
            config_file = self.create_test_config()

            result = self.run_command(
                ["config", "view", "discovered", "-o", "json", "-c", str(config_file)]
            )

            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify output is valid JSON
            data = json.loads(result.stdout)
            assert "workspaces" in data

            # Verify no discovery messages in output
            assert "Discovering contexts" not in result.stdout

        finally:
            if config_file and config_file.exists():
                config_file.unlink()

    def test_json_output_enhanced_clean(self):
        """Test that enhanced mode JSON output is clean."""
        config_file = None
        try:
            config_file = self.create_test_config()

            result = self.run_command(
                ["config", "view", "enhanced", "-o", "json", "-c", str(config_file)]
            )

            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify output is valid JSON
            data = json.loads(result.stdout)
            assert "workspaces" in data

            # Verify no discovery messages in output
            assert "Discovering contexts" not in result.stdout
            assert "Discovered" not in result.stdout

        finally:
            if config_file and config_file.exists():
                config_file.unlink()

    def test_yaml_output_enhanced_clean(self):
        """Test that enhanced mode YAML output is clean."""
        config_file = None
        try:
            config_file = self.create_test_config()

            result = self.run_command(
                ["config", "view", "enhanced", "-o", "yaml", "-c", str(config_file)]
            )

            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify output is valid YAML
            data = yaml.safe_load(result.stdout)
            assert "workspaces" in data

            # Verify no discovery messages in output
            assert "Discovering contexts" not in result.stdout
            assert "Discovered" not in result.stdout

        finally:
            if config_file and config_file.exists():
                config_file.unlink()

    def test_text_output_shows_discovery(self):
        """Test that config view handles invalid output format."""
        config_file = None
        try:
            config_file = self.create_test_config()

            # Text is not a valid output format for config view
            result = self.run_command(
                ["config", "view", "discovered", "-o", "text", "-c", str(config_file)]
            )

            # Should fail with invalid output format
            assert result.returncode != 0
            assert "Invalid value" in result.stderr or "text" in result.stderr

        finally:
            if config_file and config_file.exists():
                config_file.unlink()

    def test_jq_compatibility(self):
        """Test that JSON output can be parsed by jq."""
        config_file = None
        try:
            config_file = self.create_test_config()

            # Run coregen and pipe to jq
            coregen_cmd = [
                sys.executable,
                "-m",
                "coregen",
                "config",
                "view",
                "enhanced",
                "-o",
                "json",
                "-c",
                str(config_file),
            ]

            # First get the output
            result = subprocess.run(
                coregen_cmd, capture_output=True, text=True, check=False
            )

            assert result.returncode == 0, f"Coregen failed: {result.stderr}"

            # Then try to parse with Python's json (simulating jq)
            try:
                data = json.loads(result.stdout)
                # If we can parse it, jq would be able to as well
                assert len(data.get("workspaces", [])) == 1
            except json.JSONDecodeError as e:
                pytest.fail(f"JSON output is not valid: {e}")

        finally:
            if config_file and config_file.exists():
                config_file.unlink()
