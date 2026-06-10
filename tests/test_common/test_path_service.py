"""Unit tests for path service functionality."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from coregen.common.path_service import PathService


@pytest.fixture
def test_workspace() -> Any:
    """Sample workspace configuration."""

    class Workspace:
        name = "test-workspace"
        context_type = "standard"
        workspace_dir = None

    return Workspace()


@pytest.fixture
def test_context() -> Any:
    """Sample context configuration."""

    class Context:
        name = "dev"
        environment = "development"
        commit_dir = "generated"
        _config_file_path = None

    return Context()


@pytest.fixture
def test_component() -> Any:
    """Sample component configuration."""

    class ComponentConfig:
        for_commit = True
        path = None

    class Component:
        name = "service-a"
        config = ComponentConfig()

    return Component()


@pytest.fixture
def mock_resolver() -> Any:
    """Mock path resolver instance."""
    resolver = MagicMock()
    resolver.root_path = Path(".")
    return resolver


@pytest.fixture
def service(mock_resolver) -> Any:
    """Path service instance with mocked resolver."""
    return PathService(resolver=mock_resolver)


def test_workspace_path_resolution(service, test_workspace, mock_resolver):
    """Test workspace path resolution."""
    service.get_workspace_path(test_workspace)

    mock_resolver.set_workspace_path.assert_called_with(
        workspace_name=test_workspace.name, custom_path=None
    )


def test_context_path_resolution(service, test_context, test_workspace, mock_resolver):
    """Test context path resolution."""
    service.get_context_path(test_context, test_workspace)

    mock_resolver.set_context_path.assert_called_with(
        workspace_name=test_workspace.name,
        context_name=test_context.name,
        environment=test_context.environment,
        workspace_config={"context_type": test_workspace.context_type},
        config_file_path=None,
    )


def test_component_path_resolution(
    service, test_component, test_context, test_workspace, mock_resolver
):
    """Test component path resolution."""
    service.get_component_path(test_component, test_context, test_workspace)

    # Should first get context path
    mock_resolver.set_context_path.assert_called_with(
        workspace_name=test_workspace.name,
        context_name=test_context.name,
        environment=test_context.environment,
        workspace_config={"context_type": test_workspace.context_type},
        config_file_path=None,
    )

    # Then resolve component path
    mock_resolver.get_component_path.assert_called_with(
        workspace_name=test_workspace.name,
        context_name=test_context.name,
        component_name=test_component.name,
        custom_path=None,
    )


def test_resolve_workspace_paths(service, test_workspace, mock_resolver):
    """Test resolving all workspace-related paths."""
    paths = service.resolve_workspace_paths(test_workspace)

    mock_resolver.set_workspace_path.assert_called_with(
        workspace_name=test_workspace.name, custom_path=None
    )
    assert "workspace_path" in paths


def test_resolve_context_paths(service, test_context, test_workspace, mock_resolver):
    """Test resolving all context-related paths."""
    mock_resolver.get_commit_dir.return_value = Path("generated")
    paths = service.resolve_context_paths(test_context, test_workspace)

    assert "context_path" in paths
    assert "commit_dir" in paths


def test_resolve_component_paths(
    service, test_component, test_context, test_workspace, mock_resolver
):
    """Test resolving all component-related paths."""
    paths = service.resolve_component_paths(
        test_component, test_context, test_workspace
    )

    # Should first set context
    mock_resolver.set_context_path.assert_called()

    # Should get component path
    mock_resolver.get_component_path.assert_called()

    # Since component is for_commit, should also get commit path
    mock_resolver.get_commit_path.assert_called_with(
        workspace_name=test_workspace.name,
        context_name=test_context.name,
        component_name=test_component.name,
    )

    assert "component_path" in paths
    assert "commit_path" in paths


def test_custom_component_path(
    service, test_component, test_context, test_workspace, mock_resolver
):
    """Test component path resolution with custom path."""
    test_component.config.path = "/custom/path"
    # Custom paths are resolved through the resolver, which enforces
    # root-directory containment (M2): assert the delegation, not verbatim use.
    mock_resolver.get_component_path.return_value = Path("/root/custom/path")
    paths = service.resolve_component_paths(
        test_component, test_context, test_workspace
    )

    mock_resolver.get_component_path.assert_called_with(
        workspace_name=test_workspace.name,
        context_name=test_context.name,
        component_name=test_component.name,
        custom_path="/custom/path",
    )
    assert paths["component_path"] == Path("/root/custom/path")


def test_resolve_template_path(service, mock_resolver):
    """Test template path resolution."""
    variables = {"name": "test"}
    service.resolve_template_path("template.j2", variables)

    mock_resolver.resolve_template.assert_called_with("template.j2", variables, None)


def test_error_handling(service, mock_resolver):
    """Test error handling for invalid inputs."""
    # Test None workspace
    with pytest.raises(AttributeError):
        service.get_workspace_path(None)

    # Test None context
    with pytest.raises(AttributeError):
        service.get_context_path(None, None)

    # Test None component
    with pytest.raises(AttributeError):
        service.get_component_path(None, None, None)

    # Test resolver errors
    mock_resolver.set_workspace_path.side_effect = ValueError("Invalid path")
    with pytest.raises(ValueError, match="Invalid path"):
        service.get_workspace_path(MagicMock(name="workspace", spec=["name"]))


def test_root_path_setting(service, mock_resolver):
    """Test setting root path."""
    root = Path("/custom/root")
    service.set_root_path(root)
    assert mock_resolver.root_path == root


def test_make_path_relative(service):
    """Test relative path conversion."""
    cwd = Path.cwd()
    test_path = cwd / "test" / "path"

    rel_path = service.make_path_relative(test_path)
    assert rel_path == "test/path"

    # Test path outside cwd
    outside_path = Path("/outside/cwd")
    abs_path = service.make_path_relative(outside_path)
    assert abs_path == str(outside_path)
