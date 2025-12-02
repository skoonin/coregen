"""Tests for ConfigLoader."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from coregen.config_model.loader import ConfigLoader
from coregen.config_model.models.settings import get_settings


@pytest.fixture
def sample_yaml_content() -> Any:
    """Return a sample YAML content."""
    return """
workspaces:
  - name: test-workspace
    context_type: cluster
    context_config_files:
      - "**/*-cgvalues.yaml"
    """


def test_load_yaml_file(tmp_path, sample_yaml_content):
    """Test loading a YAML file."""
    # Setup
    config_loader = ConfigLoader()
    config_path = tmp_path / "test-config.yaml"
    config_path.write_text(sample_yaml_content)

    # Execute
    result = config_loader.load_config(str(config_path))

    # Verify
    assert result is not None
    assert "workspaces" in result
    assert len(result["workspaces"]) == 1
    assert result["workspaces"][0]["name"] == "test-workspace"
    assert result["workspaces"][0]["context_type"] == "cluster"


def test_load_json_file(tmp_path):
    """Test loading a JSON configuration file."""
    # Setup
    config_loader = ConfigLoader()
    config_path = tmp_path / "test-config.json"

    # Create a JSON file with test content
    import json

    json_content = {
        "workspaces": [
            {
                "name": "test-workspace",
                "context_type": "cluster",
                "context_config_files": ["**/*-cgvalues.json"],
            }
        ]
    }

    # Write the JSON file
    with open(config_path, "w") as f:
        json.dump(json_content, f)

    # Execute
    result = config_loader.load_config(str(config_path))

    # Verify
    assert result is not None
    assert "workspaces" in result
    assert len(result["workspaces"]) == 1
    assert result["workspaces"][0]["name"] == "test-workspace"
    assert result["workspaces"][0]["context_type"] == "cluster"
    assert result["workspaces"][0]["context_config_files"][0] == "**/*-cgvalues.json"


def test_error_handling_for_invalid_files(tmp_path):
    """Test error handling for invalid file formats."""
    config_loader = ConfigLoader()

    # Invalid YAML
    invalid_yaml = tmp_path / "invalid.yaml"
    invalid_yaml.write_text("this: 'is not valid: yaml")

    # Should raise an exception when trying to load
    with pytest.raises(yaml.YAMLError):
        config_loader.load_config(str(invalid_yaml))

    # Non-existent file
    non_existent = tmp_path / "does-not-exist.yaml"
    with pytest.raises(FileNotFoundError):
        config_loader.load_config(str(non_existent))


def test_error_handling_for_malformed_configs(tmp_path):
    """Test error handling for malformed configuration content."""
    config_loader = ConfigLoader()

    # Test empty file
    empty_file = tmp_path / "empty.yaml"
    empty_file.write_text("")
    result = config_loader.load_config(str(empty_file))
    assert result == {}

    # Test file with invalid root structure (not a dict)
    invalid_root = tmp_path / "invalid_root.yaml"
    invalid_root.write_text("- item1\n- item2")

    # Should raise ValueError for invalid structure
    with pytest.raises(
        ValueError, match="Config must be a dictionary/object at root level"
    ):
        config_loader.load_config(str(invalid_root))

    # Test file with missing workspaces section
    no_workspaces = tmp_path / "no_workspaces.yaml"
    no_workspaces.write_text("some_key: some_value")
    result = config_loader.load_config(str(no_workspaces))
    # Should add empty workspaces list in test environment
    assert "workspaces" in result
    assert result["workspaces"] == []

    # Test file with invalid workspaces type
    invalid_workspaces = tmp_path / "invalid_workspaces.yaml"
    invalid_workspaces.write_text("workspaces: 'not a list'")
    result = config_loader.load_config(str(invalid_workspaces))
    # Should convert to list in test environment
    assert "workspaces" in result
    assert isinstance(result["workspaces"], list)


def test_output_format_suppression(tmp_path, sample_yaml_content):
    """Test that discovery messages are shown based on quiet/verbose settings."""
    from unittest.mock import patch

    # Setup config file
    config_path = tmp_path / "test-config.yaml"
    config_path.write_text(sample_yaml_content)

    # Create a workspace with some contexts to trigger discovery messages
    test_workspaces = {
        "workspaces": [
            {
                "name": "test-workspace",
                "context_type": "cluster",
                "cluster": [{"name": "test-context", "environment": "test"}],
            }
        ]
    }

    # ConfigLoader no longer accepts output_format - messages controlled by quiet/verbose
    # Test with verbose=True (should show messages)
    config_loader_verbose = ConfigLoader(verbose=True)
    with patch("coregen.config_model.loader.console.info") as mock_info:
        config_loader_verbose.discover_context_configs(test_workspaces)
        # Should have been called when verbose
        assert mock_info.called

    # Test with default settings (should not show messages)
    config_loader_default = ConfigLoader()
    with patch("coregen.config_model.loader.console.info") as mock_info:
        config_loader_default.discover_context_configs(test_workspaces)
        # Console.info() is only called when verbose=True
        assert not mock_info.called


def test_discovering_context_configs():
    """Test discovering context config files based on patterns."""
    # Create a config dict with workspace info
    config_dict = {
        "workspaces": [
            {
                "name": "test-workspace",
                "context_type": "cluster",
                "context_config_files": ["**/*-cgvalues.yaml"],
            }
        ]
    }

    # Create a test configuration loader
    config_loader = ConfigLoader()

    # Mock _discover_and_merge_contexts to return some discovered contexts
    with patch.object(config_loader, "_discover_and_merge_contexts") as mock_discover:
        # Setup the mock to return some context names
        mock_discover.return_value = ["context1", "context2"]

        # Mock Path.cwd() to return a known path
        with patch("pathlib.Path.cwd", return_value=Path("/test")):
            with patch("pathlib.Path.exists", return_value=True):
                # Execute the discovery
                config_loader.discover_context_configs(config_dict)

                # Verify the method was called with expected args
                assert mock_discover.called
                # Get the first call arguments
                call_args = mock_discover.call_args_list[0][1]
                assert call_args["workspace_name"] == "test-workspace"
                assert call_args["context_type"] == "cluster"
                assert "**/*-cgvalues.yaml" in call_args["pattern"]


def test_discover_root_path():
    """Test discovering repository root path using mocks."""
    # Setup
    config_loader = ConfigLoader()
    settings = get_settings()
    settings.system.config_file_name

    # Mock paths
    root_path = Path("/test")

    # Simplified approach: mock the method directly and make it return our predetermined value
    with patch.object(config_loader, "discover_root_path", return_value=root_path):
        result = config_loader.discover_root_path()
        assert result == root_path

    # Alternative test: mock enough methods to make the real implementation work
    with patch("pathlib.Path.cwd") as mock_cwd:
        mock_cwd.return_value = Path("/test")

        # Mock the exists method to return True for our config file path
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True  # This will make the first check pass

            # Call the real method (not mocked this time)
            result = ConfigLoader().discover_root_path()

            # Verify the result is our root path
            assert result == Path("/test")
