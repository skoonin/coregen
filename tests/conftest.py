"""Root test fixtures for the entire test suite.

This conftest provides shared fixtures used across all test directories.
Fixtures defined here are automatically discovered by pytest and available
to all test files in the project.

Fixture Scopes:
    - session: Created once per test session (shared across all tests)
    - module: Created once per test module/file
    - function: Created fresh for each test function (default)

For detailed documentation on available fixtures and their usage, see:
    tests/FIXTURES.md
"""

import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer import Typer
from typer.testing import CliRunner

# Add source directory to sys.path for test imports
# This is done at module level (before imports) because the imports below depend on it.
# In production, the package is properly installed, but for test isolation we use
# this approach to avoid requiring package installation in editable mode.
_source_dir = str(Path(__file__).parent.parent / "source")
if _source_dir not in sys.path:
    sys.path.insert(0, _source_dir)

from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.enums.enum_output_format import OutputFormat
from coregen.cli.global_options import GlobalOptions
from coregen.common.console import Console
from coregen.config_model.access import ConfigAccess
from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig

# ============================================================================
# Console State Management
# ============================================================================


@pytest.fixture(autouse=True)
def reset_console_state() -> Generator[None, None, None]:
    """Reset Console static state before each test to ensure isolation.

    This fixture automatically runs before each test to prevent state leakage
    between tests. The Console class uses class-level attributes that must be
    reset to ensure tests are independent.

    Scope: function (runs before each test)
    Autouse: Yes (automatically applied to all tests)
    """
    # Reset all console class attributes to their defaults
    Console._user_console = None
    Console._log_console = None
    Console.verbose_mode = False
    Console.quiet_mode = False
    Console._no_color = False
    Console.dry_run_mode = False
    Console._default_output_format = OutputFormat.TEXT
    Console._color_system = "auto"
    Console._active_output_format = None
    Console._is_user_configured = False
    yield
    # No cleanup needed after test


# ============================================================================
# CLI Test Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def cli_runner() -> CliRunner:
    """Create a CliRunner for testing CLI commands.

    Returns a Typer CliRunner instance configured for testing. Session-scoped
    to reuse the same runner across all tests for performance.

    Scope: session (created once per test run)

    Example:
        def test_help_command(cli_runner, cli_app_mocked):
            result = cli_runner.invoke(cli_app_mocked, ["--help"])
            assert result.exit_code == 0
    """
    return CliRunner()


@pytest.fixture
def cli_app_mocked() -> Generator[Typer, None, None]:
    """Create the CLI app with mocked logger and console for unit testing.

    This fixture provides a version of the CLI app with Console and Logger
    mocked to prevent actual output during tests. Use this for most CLI tests.

    Scope: function (created fresh for each test)

    Example:
        def test_command(cli_runner, cli_app_mocked):
            result = cli_runner.invoke(cli_app_mocked, ["config", "view"])
            assert result.exit_code == 0
    """
    with patch("coregen.common.logger.Logger"), patch("coregen.common.console.Console"):
        from coregen.cli.cli import app

        yield app


@pytest.fixture
def cli_app_raw() -> Typer:
    """Create the CLI app without mocking for end-to-end testing.

    This fixture provides the raw CLI app without any mocking. Use this for
    integration/e2e tests where you need to verify actual console output.

    Scope: function (created fresh for each test)

    Example:
        def test_actual_output(cli_runner, cli_app_raw):
            result = cli_runner.invoke(cli_app_raw, ["--help"])
            assert "Usage:" in result.stdout
    """
    from coregen.cli.cli import app

    return app


@pytest.fixture
def cli_app() -> Generator[Typer, None, None]:
    """Alias for cli_app_mocked for backward compatibility.

    This fixture provides the same mocked CLI app as cli_app_mocked.
    Maintained for backward compatibility with existing tests.

    Scope: function (created fresh for each test)

    Example:
        def test_command(cli_runner, cli_app):
            result = cli_runner.invoke(cli_app, ["config", "view"])
            assert result.exit_code == 0
    """
    with patch("coregen.common.logger.Logger"), patch("coregen.common.console.Console"):
        from coregen.cli.cli import app

        yield app


# ============================================================================
# Global Options Fixtures
# ============================================================================


@pytest.fixture
def global_options() -> GlobalOptions:
    """Create a GlobalOptions instance with default values.

    Provides a standard GlobalOptions object for testing. Customize by
    creating your own in tests or modifying the returned instance.

    Scope: function (fresh instance per test)

    Example:
        def test_with_options(global_options):
            global_options.dry_run = True
            assert global_options.dry_run is True
    """
    return GlobalOptions(
        dry_run=False,
        file_action=FileAction.ASK,
        quiet=False,
        verbose=False,
        no_color=False,
        config_file=None,
        debug=False,
    )


@pytest.fixture
def service_defaults() -> dict[str, Any]:
    """Get default values for service initialization.

    Returns a dictionary with common default values used when initializing
    services. Useful for ensuring consistent service configuration in tests.

    Scope: function (fresh dict per test)

    Example:
        def test_service_init(service_defaults):
            service = MyService(**service_defaults)
            assert service.dry_run is False
    """
    return {
        "dry_run": False,
        "file_action": FileAction.SKIP,
        "output_format": OutputFormat.TEXT,
        "quiet": False,
        "verbose": False,
        "no_color": False,
        "debug": False,
    }


# ============================================================================
# Configuration Model Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_workspace() -> MagicMock:
    """Create a mock WorkspaceConfig for testing.

    Provides a MagicMock configured to behave like a WorkspaceConfig instance.
    Includes common attributes with sensible defaults.

    Scope: function (fresh mock per test)

    Example:
        def test_workspace(mock_workspace):
            mock_workspace.name = "production"
            service = SomeService(mock_workspace)
            assert service.workspace_name == "production"
    """
    workspace = MagicMock(spec=WorkspaceConfig)
    workspace.name = "test-workspace"
    workspace.output_dir = "/mock/output"
    workspace.contexts = {}
    workspace.type = "kubernetes"
    return workspace


@pytest.fixture
def mock_context() -> MagicMock:
    """Create a mock Context for testing.

    Provides a MagicMock configured to behave like a Context instance.
    Includes common attributes with sensible defaults.

    Scope: function (fresh mock per test)

    Example:
        def test_context(mock_context):
            mock_context.environment = "production"
            assert mock_context.environment == "production"
    """
    context = MagicMock(spec=Context)
    context.name = "test-context"
    context.environment = "dev"
    context.active = True
    context.path = "/path/to/context"
    context.commit_dir = "generated"
    context.type = "cluster"
    context.components = {}
    context.get_all_components = MagicMock(return_value={"test-component": None})
    return context


@pytest.fixture
def mock_component() -> MagicMock:
    """Create a mock Component for testing.

    Provides a MagicMock configured to behave like a Component instance.
    Includes common attributes with sensible defaults.

    Scope: function (fresh mock per test)

    Example:
        def test_component(mock_component):
            mock_component.name = "api-service"
            assert mock_component.name == "api-service"
    """
    component = MagicMock(spec=Component)
    component.name = "test-component"
    component.type = "service"
    component.config = MagicMock()
    component.config.active = True
    component.config.for_commit = True
    component.config.path = "/path/to/component"
    component.config.type = "service"
    component.path = "/path/to/component"
    component.resolved_paths = {"component_path": "/mock/component/path"}
    return component


# ============================================================================
# Service Infrastructure Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_console() -> MagicMock:
    """Create a mock Console for testing.

    Provides a MagicMock of the Console class with all methods mocked.
    Useful for verifying console output calls without actually printing.

    Scope: function (fresh mock per test)

    Example:
        def test_console_output(mock_console):
            service = MyService(console=mock_console)
            service.do_something()
            mock_console.info.assert_called_once()
    """
    console = MagicMock(spec=Console)
    console.info = MagicMock()
    console.error = MagicMock()
    console.warning = MagicMock()
    console.success = MagicMock()
    console.debug = MagicMock()
    console.print = MagicMock()
    console.setup = MagicMock()
    return console


@pytest.fixture
def mock_logger() -> Generator[MagicMock, None, None]:
    """Create a mock Logger for testing.

    Provides a context manager that mocks the Logger class to prevent actual
    logging during tests. The mock instance is yielded for assertions.

    Scope: function (fresh mock per test)

    Example:
        def test_logging(mock_logger):
            # Logger is already mocked by this fixture
            my_function_that_logs()
            # Verify logging calls if needed
    """
    with (
        patch("coregen.common.logger.Logger") as mock,
        patch("coregen.cli.global_options.logger") as mock_go_logger,
    ):
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        # Configure module-level logger mocks to be the same instance
        # This ensures tests can use mock_logger.debug(), mock_logger.warning(), etc.
        mock_go_logger.debug = MagicMock()
        mock_go_logger.info = MagicMock()
        mock_go_logger.warning = MagicMock()
        mock_go_logger.error = MagicMock()
        # Yield the module-level logger mock for tests that use it directly
        yield mock_go_logger


@pytest.fixture
def mock_config_access(
    mock_workspace: MagicMock, mock_context: MagicMock, mock_component: MagicMock
) -> MagicMock:
    """Create a mock ConfigAccess for testing.

    Provides a MagicMock configured to behave like ConfigAccess with proper
    lookup tables and find/get methods. Pre-populated with test fixtures.

    Scope: function (fresh mock per test)

    Example:
        def test_config_access(mock_config_access):
            workspaces = mock_config_access.find_workspaces(["test-*"])
            assert len(workspaces) > 0
    """
    config_access = MagicMock(spec=ConfigAccess)

    # Setup internal lookup tables used by services
    config_access._workspace_lookup = {"test-workspace": mock_workspace}
    config_access._context_lookup = {"test-workspace": {"test-context": mock_context}}
    config_access._component_lookup = {
        "test-workspace": {"test-context": {"test-component": mock_component}}
    }

    # Mock find methods - return config objects, not strings
    config_access.find_workspaces = MagicMock(return_value=[mock_workspace])
    config_access.find_contexts = MagicMock(return_value=[mock_context])
    config_access.find_components = MagicMock(return_value=[mock_component])

    # Mock get methods
    config_access.get_workspaces = MagicMock(return_value=[mock_workspace])
    config_access.get_workspace = MagicMock(return_value=mock_workspace)
    config_access.get_context = MagicMock(return_value=mock_context)
    config_access.get_component = MagicMock(return_value=mock_component)

    return config_access


@pytest.fixture
def mock_path_service() -> MagicMock:
    """Create a mock PathService for testing.

    Provides a MagicMock configured to behave like a PathService instance.

    Scope: function (fresh mock per test)
    """
    from coregen.common.path_service import PathService

    path_service = MagicMock(spec=PathService)
    path_service.get_root_path = MagicMock(return_value=Path("/mock/root"))
    path_service.get_workspace_path = MagicMock(return_value=Path("/mock/workspace"))
    path_service.get_context_path = MagicMock(return_value=Path("/mock/context"))
    path_service.get_component_path = MagicMock(return_value=Path("/mock/component"))
    return path_service


@pytest.fixture
def mock_config_provider(mock_path_service: MagicMock) -> MagicMock:
    """Create a mock ConfigurationProvider for testing.

    Provides a MagicMock configured to behave like a ConfigurationProvider instance.

    Scope: function (fresh mock per test)
    """
    from coregen.config_model.provider import ConfigurationProvider

    config_provider = MagicMock(spec=ConfigurationProvider)
    config_provider.path_service = mock_path_service
    config_provider.get_config = MagicMock()
    config_provider.has_config = MagicMock(return_value=True)
    return config_provider


@pytest.fixture
def mock_settings() -> Generator[MagicMock, None, None]:
    """Create a mock Settings object for testing.

    Provides a comprehensive mock of the get_settings() return value with
    all common configuration attributes. This fixture patches get_settings
    across all modules that import it.

    The mock includes:
    - Global options (dry_run, file_action, quiet, verbose, no_color, etc.)
    - Workspace configuration (archive_dir)
    - Default values matching the application defaults

    Scope: function (fresh mock per test)

    Example:
        def test_with_settings(mock_settings):
            # Settings are already mocked via get_settings()
            mock_settings.options.global_options.dry_run = True
            my_function_that_uses_settings()
    """
    with patch(
        "coregen.config_model.models.settings.get_settings"
    ) as mock_get_settings:
        mock_settings_obj = MagicMock()
        # Set default values for global options
        mock_settings_obj.options.global_options.dry_run = False
        mock_settings_obj.options.global_options.file_action = FileAction.OVERWRITE
        mock_settings_obj.options.global_options.quiet = False
        mock_settings_obj.options.global_options.verbose = False
        mock_settings_obj.options.global_options.no_color = False
        mock_settings_obj.options.global_options.config_file = Path(".cgconfig.yaml")
        mock_settings_obj.options.global_options.color_system = "auto"
        mock_settings_obj.options.global_options.output_format = OutputFormat.TEXT

        # Set workspace defaults
        mock_settings_obj.workspace.archive_dir = "archive"

        # Configure the patch to return the mock
        mock_get_settings.return_value = mock_settings_obj

        yield mock_settings_obj
