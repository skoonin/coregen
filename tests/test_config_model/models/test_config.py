"""Tests for config.models.config module."""

import pytest
from pydantic import ValidationError

from coregen.config_model.models.components import Component
from coregen.config_model.models.config import CoregenConfig
from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig


class TestCoregenConfig:
    """Tests for CoregenConfig model."""

    def test_create_config_with_workspaces(self):
        """Should create a config with valid workspaces."""
        config = CoregenConfig(workspaces=[WorkspaceConfig(name="test-workspace")])
        assert len(config.workspaces) == 1
        assert config.workspaces[0].name == "test-workspace"

    def test_create_empty_config_raises_error(self):
        """Should raise error when created without workspaces."""
        with pytest.raises(ValidationError):
            CoregenConfig(workspaces=[])

    def test_settings_property_returns_coregen_settings(self):
        """Should return CoregenSettings instance from settings property."""
        config = CoregenConfig(workspaces=[WorkspaceConfig(name="test-workspace")])
        settings = config.settings
        assert hasattr(settings, "system")
        assert hasattr(settings, "workspace")
        assert hasattr(settings, "context")
        assert hasattr(settings, "component")
        assert hasattr(settings, "paths")
        assert hasattr(settings, "options")

    def test_create_with_nested_structure(self):
        """Should create a config with nested workspace, context, and component structure."""
        # Create a component - use a dict instead of ComponentConfig object to avoid items() call issue
        component = Component(
            name="test-component", config={"active": True, "for_commit": True}
        )

        # Create a context with the component
        context = Context(
            name="test-context",
            environment="dev",
            active=True,
            components={"component": {"test-component": component}},
        )

        # Create a workspace with the context
        workspace = WorkspaceConfig(
            name="test-workspace", contexts={"context": {"test-context": context}}
        )

        # Create the config with the workspace
        config = CoregenConfig(workspaces=[workspace])

        # Verify the structure
        assert len(config.workspaces) == 1
        assert config.workspaces[0].name == "test-workspace"
        assert len(config.workspaces[0].contexts["context"]) == 1
        assert "test-context" in config.workspaces[0].contexts["context"]
        context_obj = config.workspaces[0].contexts["context"]["test-context"]
        assert context_obj.name == "test-context"
        assert context_obj.environment == "dev"
        assert "component" in context_obj.components
        assert "test-component" in context_obj.components["component"]
        component_obj = context_obj.components["component"]["test-component"]
        assert component_obj.name == "test-component"
        assert component_obj.config.active is True
        assert component_obj.config.for_commit is True
