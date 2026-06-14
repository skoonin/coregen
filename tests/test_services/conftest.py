"""
Common test fixtures for service layer tests.

This module provides service-specific reusable fixtures for testing services.
Common fixtures like mock_workspace, mock_context, mock_component, mock_console,
sample_config_dict, and service_defaults are now available from the root conftest.py.
"""

from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.file_manager import FileManager
from coregen.common.workspace_initializer import WorkspaceInitializer
from coregen.services.generate.gen_generate_service import GenerateService

# Note: mock_workspace, mock_context, mock_component, mock_console, and
# sample_config_dict are now provided by the root conftest.py


# ============================================================================
# Service-Specific Test Setup Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def mock_paths_for_services(request: Any) -> Generator[None, None, None]:
    """Mock paths for service tests to prevent file system operations.

    This fixture is autouse to ensure service tests don't accidentally access
    the real filesystem. Service layer tests should focus on business logic
    and use mocked filesystem operations.

    To opt-out (for integration tests that need real filesystem access):
        @pytest.mark.integration
        def test_with_real_filesystem():
            # This test will have real filesystem access
            ...

    Note: If you're debugging path-related issues and this mock is interfering,
    add the @pytest.mark.integration marker to your test.

    Args:
        request: pytest request fixture for accessing test metadata

    Yields:
        None
    """
    # Skip mocking for integration tests that need real file system access
    if "integration" in request.keywords:
        yield
        return

    # Mock filesystem operations to prevent accidental file access in unit tests
    with (
        patch("os.getcwd", return_value="/mock/root/path"),
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.resolve", return_value=Path("/mock/root/path")),
    ):
        yield


# Note: mock_path_service is now provided by the root conftest.py
# Note: mock_config_provider is now provided by the root conftest.py


@pytest.fixture
def mock_file_manager() -> MagicMock:
    """Create a mock FileManager for testing.

    Returns:
        MagicMock: A mocked FileManager with file operations
    """
    file_manager = MagicMock(spec=FileManager)
    file_manager.write_file = MagicMock()
    file_manager.read_file = MagicMock()
    file_manager.exists = MagicMock(return_value=False)
    file_manager.dry_run = False
    file_manager.file_action = FileAction.SKIP
    return file_manager


@pytest.fixture
def mock_workspace_initializer(
    mock_path_service: MagicMock, mock_file_manager: MagicMock
) -> MagicMock:
    """Create a mock WorkspaceInitializer for testing.

    Args:
        mock_path_service: Mocked PathService fixture
        mock_file_manager: Mocked FileManager fixture

    Returns:
        MagicMock: A mocked WorkspaceInitializer
    """
    workspace_initializer = MagicMock(spec=WorkspaceInitializer)
    workspace_initializer.initialize_workspace = MagicMock()
    return workspace_initializer


# Note: mock_config_access is now provided by the root conftest.py


@pytest.fixture
def mock_generator_generate() -> MagicMock:
    """Mock Generator.generate method.

    Returns:
        MagicMock: A mock Generator.generate method that returns an empty list
    """
    return MagicMock(return_value=[])


@pytest.fixture
def mock_pattern_matcher() -> MagicMock:
    """Mock PatternMatcher instance.

    Returns:
        MagicMock: A mocked PatternMatcher
    """
    return MagicMock()


@pytest.fixture
def generate_service(
    mock_config_provider: MagicMock,
    mock_workspace: Any,
    mock_context: Any,
    mock_component: Any,
    mock_config_access: MagicMock,
    mock_file_manager: MagicMock,
    mock_generator_generate: MagicMock,
    mock_pattern_matcher: MagicMock,
) -> Generator[GenerateService, None, None]:
    """
    Fully configured GenerateService instance with mocked dependencies.

    This fixture sets up a complete test environment for GenerateService,
    including all necessary mocks and patches.

    Args:
        mock_config_provider: Mocked configuration provider fixture
        mock_workspace: Mocked workspace fixture
        mock_context: Mocked context fixture
        mock_component: Mocked component fixture
        mock_config_access: Mocked configuration access fixture
        mock_file_manager: Mocked file manager fixture
        mock_generator_generate: Mocked Generator.generate method
        mock_pattern_matcher: Mocked PatternMatcher instance

    Yields:
        GenerateService: A fully configured service instance for testing
    """
    # Setup mock workspace
    mock_workspace.name = "test-workspace"
    mock_workspace.output_dir = "/mock/output"

    # Setup mock context
    mock_context.name = "test-context"
    mock_context.environment = "dev"
    mock_context.active = True
    mock_context.path = "/path/to/context"
    mock_context.commit_dir = "generated"
    mock_context.get_all_components = MagicMock(return_value={})

    # Setup mock component
    mock_component.name = "test-component"
    mock_component.config = MagicMock()
    mock_component.config.active = True
    mock_component.config.for_commit = True
    mock_component.config.path = "/path/to/component"
    mock_component.config.required = False
    mock_component.config.dependencies = []
    mock_component.get_dependencies = MagicMock(return_value=[])
    mock_component.resolved_paths = {"component_path": "/mock/component/path"}

    # Mock configuration structure
    mock_contexts = [mock_context]
    mock_workspace.contexts = {"cluster": mock_contexts}
    mock_context.components = {"app": {"test-component": mock_component}}

    # Create mock for config provider (already provided but needs path service setup)
    mock_config_provider.path_service = MagicMock()
    mock_config_provider.path_service.resolver = MagicMock()
    mock_config_provider.path_service.resolver.root_path = Path("/mock/root/path")

    # Create the service with mocks using patches
    with (
        patch("coregen.common.generator.Generator.generate", mock_generator_generate),
        patch(
            "coregen.common.pattern.facade.PatternMatcher",
            return_value=mock_pattern_matcher,
        ),
        patch(
            "coregen.services.service_base.FileManager", return_value=mock_file_manager
        ),
    ):
        # Initialize service with config provider
        service = GenerateService(config_provider=mock_config_provider)

        # Inject our mocks
        service._config_access = mock_config_access

        # Set up process_path_patterns mock
        service.process_path_patterns = MagicMock()
        service.process_path_patterns.return_value = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {"test-context": mock_context},
            "components": {"test-context/test-component": mock_component},
        }

        # Set up _create_template_context mock
        service._create_template_context = MagicMock(return_value={})

        yield service
