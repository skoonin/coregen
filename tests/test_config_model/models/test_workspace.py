"""Tests for config.models.workspace module."""

import pytest
from pydantic import ValidationError

from coregen.config_model.models.workspace import WorkspaceConfig


class TestWorkspaceConfig:
    """Tests for WorkspaceConfig model."""

    def test_create_workspace(self):
        """Should create a workspace with default values."""
        workspace = WorkspaceConfig(name="test-workspace")
        assert workspace.name == "test-workspace"
        assert isinstance(workspace.contexts, dict)
        assert workspace.archive_dir.endswith("archive")
        assert workspace.output_dir.endswith("output")

    def test_create_workspace_with_custom_values(self):
        """Should create a workspace with custom values."""
        workspace = WorkspaceConfig(
            name="test-workspace",
            workspace_dir="custom/workspace",
            archive_dir="custom/archive",
            output_dir="custom/output",
            context_type="environment",
        )
        assert workspace.name == "test-workspace"
        assert workspace.workspace_dir == "custom/workspace"
        assert workspace.archive_dir == "custom/archive"
        assert workspace.output_dir == "custom/output"
        assert workspace.context_type == "environment"

    def test_create_workspace_with_custom_fields(self):
        """Should allow custom fields."""
        workspace = WorkspaceConfig(name="test-workspace", custom_field="custom-value")
        assert workspace.name == "test-workspace"
        assert workspace.custom_field == "custom-value"

    def test_workspace_name_validation(self):
        """Should validate workspace name."""
        # Empty name
        with pytest.raises(ValidationError):
            WorkspaceConfig(name="")

    def test_absolute_paths_with_dot_allowed(self):
        """Should allow paths starting with './'."""
        workspace = WorkspaceConfig(
            name="test-workspace",
            workspace_dir="./custom/workspace",
            archive_dir="./custom/archive",
            output_dir="./custom/output",
        )
        assert workspace.workspace_dir == "./custom/workspace"
        assert workspace.archive_dir == "./custom/archive"
        assert workspace.output_dir == "./custom/output"

    def test_absolute_paths_not_allowed(self):
        """Should not allow absolute paths starting with '/'."""
        with pytest.raises(ValidationError) as exc:
            WorkspaceConfig(name="test-workspace", workspace_dir="/absolute/path")
        assert "Path '/absolute/path' must be relative" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            WorkspaceConfig(name="test-workspace", archive_dir="/absolute/path")
        assert "Path '/absolute/path' must be relative" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            WorkspaceConfig(name="test-workspace", output_dir="/absolute/path")
        assert "Path '/absolute/path' must be relative" in str(exc.value)
