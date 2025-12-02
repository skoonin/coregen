"""Tests for config.creator module."""

import pytest

from coregen.config_model.creator import ConfigCreator


class TestConfigCreator:
    """Tests for ConfigCreator."""

    def test_create_config(self):
        """Should create a config with default workspace."""
        creator = ConfigCreator()
        config = creator.create_config()

        assert "workspaces" in config
        assert len(config["workspaces"]) == 1
        assert "name" in config["workspaces"][0]
        assert (
            config["workspaces"][0]["name"] == creator.settings.workspace.workspace_name
        )

    def test_create_config_with_name(self):
        """Should create a config with specified workspace name."""
        creator = ConfigCreator()
        config = creator.create_config("custom-workspace")

        assert "workspaces" in config
        assert len(config["workspaces"]) == 1
        assert "name" in config["workspaces"][0]
        assert config["workspaces"][0]["name"] == "custom-workspace"

    def test_create_workspace(self):
        """Should create a workspace with default values."""
        creator = ConfigCreator()
        workspace = creator.create_workspace("test-workspace")

        assert workspace["name"] == "test-workspace"
        assert "context_type" in workspace
        assert "context_config_files" in workspace
        assert "archive_dir" in workspace
        assert "output_dir" in workspace
        assert "contexts" in workspace

    def test_create_workspace_with_custom_dir(self):
        """Should create a workspace with custom directory."""
        creator = ConfigCreator()
        workspace = creator.create_workspace(
            "test-workspace", workspace_dir="custom/dir"
        )

        assert workspace["name"] == "test-workspace"
        assert workspace["workspace_dir"] == "custom/dir"

    def test_create_workspace_with_empty_name(self):
        """Should raise error when name is empty."""
        creator = ConfigCreator()
        with pytest.raises(ValueError):
            creator.create_workspace("")

    def test_create_workspace_with_empty_dir(self):
        """Should accept empty workspace_dir."""
        creator = ConfigCreator()
        # In the actual implementation, empty workspace_dir is treated as None
        # and doesn't raise an error, so we just verify it works
        workspace = creator.create_workspace("test-workspace", workspace_dir="")
        assert workspace["name"] == "test-workspace"
        assert "workspace_dir" not in workspace

    def test_create_context(self):
        """Should create a context with default values."""
        creator = ConfigCreator()
        context = creator.create_context("test-context", "dev")

        assert context["name"] == "test-context"
        assert context["environment"] == "dev"
        assert "component_type" in context
        assert "active" in context
        assert "commit_dir" in context
        assert "components" in context

    def test_create_context_with_custom_values(self):
        """Should create a context with custom values."""
        creator = ConfigCreator()
        context = creator.create_context(
            "test-context", "prod", component_type="service", path="custom/path"
        )

        assert context["name"] == "test-context"
        assert context["environment"] == "prod"
        assert context["component_type"] == "service"
        assert context["path"] == "custom/path"

    def test_create_context_with_empty_name(self):
        """Should raise error when name is empty."""
        creator = ConfigCreator()
        with pytest.raises(ValueError):
            creator.create_context("", "dev")

    def test_create_context_with_empty_environment(self):
        """Should raise error when environment is empty."""
        creator = ConfigCreator()
        with pytest.raises(ValueError):
            creator.create_context("test-context", "")

    def test_create_context_with_empty_component_type(self):
        """Should accept empty component_type."""
        creator = ConfigCreator()
        # In the implementation, an empty component_type is treated as None
        # and the default value is used instead
        context = creator.create_context("test-context", "dev", component_type="")
        assert context["name"] == "test-context"
        assert context["component_type"] == creator.settings.context.component_type

    def test_create_context_with_empty_path(self):
        """Should accept empty path."""
        creator = ConfigCreator()
        # In the implementation, empty path doesn't raise an error
        context = creator.create_context("test-context", "dev", path="")
        assert context["name"] == "test-context"
        assert "path" not in context

    def test_create_component(self):
        """Should create a component with default values."""
        creator = ConfigCreator()
        component = creator.create_component("test-component")

        assert component["name"] == "test-component"
        assert "config" in component
        assert "active" in component["config"]
        assert "required" in component["config"]
        assert "for_commit" in component["config"]
        assert "dependencies" in component["config"]

    def test_create_component_with_custom_path(self):
        """Should create a component with custom path."""
        creator = ConfigCreator()
        component = creator.create_component("test-component", path="custom/path")

        assert component["name"] == "test-component"
        assert component["config"]["path"] == "custom/path"

    def test_create_component_with_empty_name(self):
        """Should raise error when name is empty."""
        creator = ConfigCreator()
        with pytest.raises(ValueError):
            creator.create_component("")

    def test_create_component_with_empty_path(self):
        """Should accept empty path."""
        creator = ConfigCreator()
        # In the implementation, empty path doesn't raise an error
        component = creator.create_component("test-component", path="")
        assert component["name"] == "test-component"
        assert "path" not in component["config"]

    def test_add_context_to_workspace(self):
        """Should add a context to a workspace."""
        creator = ConfigCreator()
        workspace = creator.create_workspace("test-workspace")
        context = creator.create_context("test-context", "dev")

        updated_workspace = creator.add_context_to_workspace(workspace, context)

        context_type = workspace.get(
            "context_type", creator.settings.workspace.context_type
        )
        assert "contexts" in updated_workspace
        assert context_type in updated_workspace["contexts"]
        assert "test-context" in updated_workspace["contexts"][context_type]

    def test_add_context_to_workspace_invalid_workspace(self):
        """Should raise error when workspace is invalid."""
        creator = ConfigCreator()
        workspace = {}  # Missing 'name'
        context = creator.create_context("test-context", "dev")

        with pytest.raises(ValueError):
            creator.add_context_to_workspace(workspace, context)

    def test_add_context_to_workspace_invalid_context(self):
        """Should raise error when context is invalid."""
        creator = ConfigCreator()
        workspace = creator.create_workspace("test-workspace")
        context = {"environment": "dev"}  # Missing 'name'

        with pytest.raises(ValueError):
            creator.add_context_to_workspace(workspace, context)

    def test_add_context_to_workspace_missing_environment(self):
        """Should raise error when context is missing environment."""
        creator = ConfigCreator()
        workspace = creator.create_workspace("test-workspace")
        context = {"name": "test-context"}  # Missing 'environment'

        with pytest.raises(ValueError):
            creator.add_context_to_workspace(workspace, context)

    def test_add_component_to_context(self):
        """Should add a component to a context."""
        creator = ConfigCreator()
        context = creator.create_context("test-context", "dev")
        component = creator.create_component("test-component")

        updated_context = creator.add_component_to_context(context, component)

        component_type = context.get(
            "component_type", creator.settings.context.component_type
        )
        assert "components" in updated_context
        assert component_type in updated_context["components"]
        assert "test-component" in updated_context["components"][component_type]

    def test_add_component_to_context_invalid_context(self):
        """Should raise error when context is invalid."""
        creator = ConfigCreator()
        context = {}  # Missing 'name'
        component = creator.create_component("test-component")

        with pytest.raises(ValueError):
            creator.add_component_to_context(context, component)

    def test_add_component_to_context_invalid_component(self):
        """Should raise error when component is invalid."""
        creator = ConfigCreator()
        context = creator.create_context("test-context", "dev")
        component = {"name": "test-component"}  # Missing 'config'

        with pytest.raises(ValueError):
            creator.add_component_to_context(context, component)
