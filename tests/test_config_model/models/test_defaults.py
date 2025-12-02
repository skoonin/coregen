"""Tests for config.models.defaults module."""

import pytest

from coregen.cli.enums.enum_file_action import FileAction
from coregen.config_model.models.defaults import (
    CliSettings,
    ComponentSettings,
    ContextSettings,
    PathSettings,
    SystemSettings,
    WorkspaceSettings,
)


class TestSystemSettings:
    """Tests for SystemSettings."""

    def test_default_values(self):
        """Should have expected default values."""
        settings = SystemSettings()
        assert settings.config_file_name == ".cgconfig.yaml"
        assert "str" in settings.allowed_extra_field_types
        assert "int" in settings.allowed_extra_field_types
        assert "float" in settings.allowed_extra_field_types
        assert "bool" in settings.allowed_extra_field_types
        assert "list" in settings.allowed_extra_field_types
        assert "dict" in settings.allowed_extra_field_types


class TestWorkspaceSettings:
    """Tests for WorkspaceSettings."""

    def test_default_values(self):
        """Should have expected default values."""
        settings = WorkspaceSettings()
        assert settings.workspace_name == "contexts"
        assert settings.archive_dir == "archive"
        assert settings.workspace_dir == "contexts"
        assert settings.output_dir == "output"
        assert settings.context_config_files == ["**/*-cgvalues.yaml"]
        assert settings.context_type == "context"


class TestContextSettings:
    """Tests for ContextSettings."""

    def test_default_values(self):
        """Should have expected default values."""
        settings = ContextSettings()
        assert settings.environment is None
        assert settings.active is False
        assert settings.commit_dir == "for-commit"
        assert settings.component_type == "component"


class TestComponentSettings:
    """Tests for ComponentSettings."""

    def test_default_values(self):
        """Should have expected default values."""
        settings = ComponentSettings()
        assert settings.active is False
        assert settings.for_commit is False
        assert settings.required is False
        # Default priority should be None
        assert settings.priority is None


class TestPathSettings:
    """Tests for PathSettings."""

    def test_default_values(self):
        """Should have expected default values."""
        settings = PathSettings()
        assert settings.workspace_path == "{root_path}/{workspace_dir}"
        assert settings.archive_path == "{root_path}/{archive_dir}"
        assert settings.output_path == "{root_path}/{output_dir}"
        assert settings.context_path == "{workspace_path}/{name}"
        assert settings.commit_path == "{context_path}/{commit_dir}"
        assert settings.component_path == "{context_path}/{name}"

    def test_invalid_template_raises_error(self):
        """Should raise error for invalid templates."""
        # Missing root_path in workspace_path
        with pytest.raises(ValueError):
            PathSettings(workspace_path="{name}")

        # Missing name in workspace_path
        with pytest.raises(ValueError):
            PathSettings(workspace_path="{root_path}")

        # Missing workspace_path in context_path
        with pytest.raises(ValueError):
            PathSettings(context_path="{name}")

        # Missing context_path in component_path
        with pytest.raises(ValueError):
            PathSettings(component_path="{name}")

        # Missing context_path in commit_path
        with pytest.raises(ValueError):
            PathSettings(commit_path="{commit_dir}")


class TestCliSettings:
    """Tests for CliSettings."""

    def test_default_values(self):
        """Should have expected default values."""
        settings = CliSettings()
        # Test global_ settings
        assert settings.global_options.dry_run is False
        assert settings.global_options.quiet is False
        assert settings.global_options.verbose is False
        assert settings.global_options.no_color is False
        assert (
            settings.global_options.file_action == FileAction.OVERWRITE
        )  # Default is OVERWRITE
        # output_format removed from global options

        # Test config settings
        assert settings.config.config_file_only is False

    def test_get_enum_defaults(self):
        """Should return correct enum defaults."""
        settings = CliSettings()
        defaults = settings.get_enum_defaults()
        assert FileAction in defaults
        assert defaults[FileAction] == FileAction.OVERWRITE  # Default is OVERWRITE
        # OutputFormat removed from global options enum defaults

    def test_get_enum_default(self):
        """Should return the default for a specific enum."""
        settings = CliSettings()
        assert (
            settings.get_enum_default(FileAction) == FileAction.OVERWRITE
        )  # Default is OVERWRITE
        # OutputFormat removed from global options

        # Should raise error for unknown enum
        with pytest.raises(ValueError):
            settings.get_enum_default(str)

    def test_get_bool_defaults(self):
        """Should return dictionary of boolean defaults."""
        settings = CliSettings()
        bool_defaults = settings.get_bool_defaults()
        assert bool_defaults["dry_run"] is False
        assert bool_defaults["quiet"] is False
        assert bool_defaults["verbose"] is False
        assert bool_defaults["no_color"] is False
