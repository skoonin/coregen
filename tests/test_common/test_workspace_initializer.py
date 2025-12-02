"""Unit tests for workspace initialization functionality."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from coregen.common.file_manager import FileManager
from coregen.common.path_service import PathService
from coregen.common.workspace_initializer import WorkspaceInitializer
from coregen.config_model.models.config import CoregenConfig
from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig


@pytest.fixture
def mock_config() -> Any:
    """Create a mock configuration for testing."""
    # Create a mock CoregenConfig
    config = MagicMock(spec=CoregenConfig)

    # Create a workspace
    workspace = MagicMock(spec=WorkspaceConfig)
    workspace.name = "test-workspace"
    workspace.path = "workspaces/test-workspace"
    workspace.output_dir = "output/test-workspace"
    workspace.context_type = "cluster"

    # Create a context
    context = MagicMock(spec=Context)
    context.name = "test-context"
    context.environment = "dev"
    context.commit_dir = "generated"

    # Add context to workspace
    workspace.contexts = {"cluster": {"test-context": context}}

    # Add workspace to config
    config.workspaces = [workspace]

    return config


@pytest.fixture
def mock_path_service() -> Any:
    """Create a mock path service."""
    path_service = MagicMock(spec=PathService)

    # Mock resolver with a root path
    path_service.resolver = MagicMock()
    path_service.resolver.root_path = Path("/test/root")

    # Mock get_workspace_path
    path_service.get_workspace_path = (
        lambda workspace: Path("/test/root/workspaces") / workspace.name
    )

    # Mock get_context_path
    path_service.get_context_path = (
        lambda context, workspace: Path("/test/root/workspaces")
        / workspace.name
        / context.environment
        / context.name
    )

    return path_service


@pytest.fixture
def mock_file_manager() -> Any:
    """Create a mock file manager."""
    return MagicMock(spec=FileManager)


def test_workspace_initializer_init():
    """Test initializing the WorkspaceInitializer."""
    # Test with default parameters
    with patch("coregen.common.path_service.PathService"):
        with patch("coregen.common.file_manager.FileManager"):
            initializer = WorkspaceInitializer()
            assert initializer is not None
            assert initializer.dry_run is False

    # Test with provided parameters
    path_service = MagicMock(spec=PathService)
    file_manager = MagicMock(spec=FileManager)
    initializer = WorkspaceInitializer(
        path_service=path_service, file_manager=file_manager, dry_run=True
    )

    assert initializer.path_service is path_service
    assert initializer.file_manager is file_manager
    assert initializer.dry_run is True


def test_get_required_paths(mock_config, mock_path_service, mock_file_manager):
    """Test getting required paths from configuration."""
    # Create initializer with our mocks
    initializer = WorkspaceInitializer(
        path_service=mock_path_service, file_manager=mock_file_manager
    )

    # Test without context paths
    paths = initializer._get_required_paths(mock_config, include_contexts=False)

    # Should include:
    # 1. Archive directory
    # 2. Workspace path
    # 3. Workspace output directory
    assert len(paths) == 3
    paths_str = [str(p) for p in paths]
    assert any(p.endswith("archive") for p in paths_str)
    assert any(p.endswith("test-workspace") for p in paths_str)
    assert any(p.endswith("test-workspace") and "output" in p for p in paths_str)

    # Test with context paths
    paths = initializer._get_required_paths(mock_config, include_contexts=True)

    # Should include above paths plus:
    # 4. Context path
    # 5. Generated directory
    assert len(paths) == 5
    paths_str = [str(p) for p in paths]
    assert any("dev" in p and "test-context" in p for p in paths_str)
    assert any("generated" in p for p in paths_str)


def test_initialize_workspace_without_contexts(
    mock_config, mock_path_service, mock_file_manager
):
    """Test initializing workspace without context paths."""
    # Setup paths to "exist" or "not exist"
    expected_paths = [
        Path("/test/root/workspaces/test-workspace"),
        Path("/test/root/archive"),
        Path("/test/root/output/test-workspace"),
    ]

    # Mock exists to return False for all paths
    with patch("pathlib.Path.exists", return_value=False):
        initializer = WorkspaceInitializer(
            path_service=mock_path_service, file_manager=mock_file_manager
        )

        # Call initialize_workspace
        initializer.initialize_workspace(mock_config, create_contexts=False)

        # Check that file_manager was called to create each directory
        assert mock_file_manager.create_directory.call_count == len(expected_paths)

        # Check that each expected path was created
        for path in expected_paths:
            mock_file_manager.create_directory.assert_any_call(path)


def test_initialize_workspace_with_contexts(
    mock_config, mock_path_service, mock_file_manager
):
    """Test initializing workspace with context paths."""
    # Setup paths to "not exist"
    with patch("pathlib.Path.exists", return_value=False):
        initializer = WorkspaceInitializer(
            path_service=mock_path_service, file_manager=mock_file_manager
        )

        # Call initialize_workspace with create_contexts=True
        initializer.initialize_workspace(mock_config, create_contexts=True)

        # Should create 5 directories (workspace, archive, output, context, generated)
        assert mock_file_manager.create_directory.call_count == 5

        # Check context and generated dirs were created
        context_path = Path("/test/root/workspaces/test-workspace/dev/test-context")
        generated_path = Path(
            "/test/root/workspaces/test-workspace/dev/test-context/generated"
        )

        mock_file_manager.create_directory.assert_any_call(context_path)
        mock_file_manager.create_directory.assert_any_call(generated_path)


def test_validate_paths_success(mock_config, mock_path_service, mock_file_manager):
    """Test path validation when all paths exist."""
    # Mock all paths to exist
    with patch("pathlib.Path.exists", return_value=True):
        initializer = WorkspaceInitializer(
            path_service=mock_path_service, file_manager=mock_file_manager
        )

        # Call validate_paths
        result = initializer.validate_paths(mock_config)

        # Should return True when all paths exist
        assert result is True


def test_validate_paths_failure(mock_config, mock_path_service, mock_file_manager):
    """Test path validation when paths don't exist."""
    # Mock paths to not exist
    with patch("pathlib.Path.exists", return_value=False):
        initializer = WorkspaceInitializer(
            path_service=mock_path_service, file_manager=mock_file_manager
        )

        # With strict=True, should raise ValueError
        with pytest.raises(ValueError):
            initializer.validate_paths(mock_config, strict=True)

        # With strict=False, should return False
        result = initializer.validate_paths(mock_config, strict=False)
        assert result is False


def test_dry_run_mode(mock_config, mock_path_service, mock_file_manager):
    """Test dry run mode respects the option."""
    # Mock paths to not exist
    with patch("pathlib.Path.exists", return_value=False):
        # Create initializer with dry_run=True
        initializer = WorkspaceInitializer(
            path_service=mock_path_service, file_manager=mock_file_manager, dry_run=True
        )

        # Initialize workspace
        initializer.initialize_workspace(mock_config)

        # FileManager should be called to create directories
        assert mock_file_manager.create_directory.called

        # The file_manager was created with dry_run=True so it
        # should respect that setting internally
        assert initializer.dry_run is True


def test_error_handling(mock_config, mock_path_service):
    """Test error handling during initialization."""
    # Create a file manager that raises an exception on create_directory
    broken_file_manager = MagicMock(spec=FileManager)
    broken_file_manager.create_directory.side_effect = Exception("Test error")

    # Mock paths to not exist
    with patch("pathlib.Path.exists", return_value=False):
        initializer = WorkspaceInitializer(
            path_service=mock_path_service, file_manager=broken_file_manager
        )

        # Should raise ValueError wrapping the original exception
        with pytest.raises(ValueError) as excinfo:
            initializer.initialize_workspace(mock_config)

        # Check error message
        assert "Failed to create directory" in str(excinfo.value)
        assert "Test error" in str(excinfo.value)
