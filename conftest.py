"""
Global pytest configuration for Coregen tests.

This file contains fixtures that apply to all test modules in the project.
"""

import shutil
import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add ci-tools to path for build/test utilities only (not covered by pytest pythonpath)
sys.path.insert(0, str(Path(__file__).parent / ".ci-tools"))

from platform_utils import Platform

# Do not monkeypatch PathResolver globally as it breaks specific tests


# Global fixtures for path resolver and related classes
@pytest.fixture
def mock_path_resolver() -> Generator[MagicMock, None, None]:
    """Mock PathResolver to prevent file system operations during tests.

    Only use this fixture when explicitly needed in a test.
    """
    with patch("coregen.common.path_resolver.PathResolver") as mock_resolver:
        # Create a mock instance that will be returned when PathResolver is instantiated
        mock_instance = MagicMock()
        mock_instance._root_path = Path("/mock/root/path")
        mock_resolver.return_value = mock_instance
        yield mock_resolver


@pytest.fixture
def mock_os_getcwd() -> Generator[None, None, None]:
    """Mock os.getcwd() to return a safe value for tests.

    Only use this fixture when explicitly needed in a test.
    """
    with patch("os.getcwd", return_value="/mock/root/path"):
        yield


@pytest.fixture
def mock_path_service() -> MagicMock:
    """Mock PathService to prevent file system operations during tests."""
    mock_service = MagicMock()
    mock_service.resolver = MagicMock()
    mock_service.resolver.root_path = Path("/mock/root/path")
    return mock_service


@pytest.fixture
def mock_config_provider() -> MagicMock:
    """Create a mock configuration provider."""
    mock_provider = MagicMock()
    mock_provider.path_service = MagicMock()
    mock_provider.path_service.resolver = MagicMock()
    mock_provider.path_service.resolver.root_path = Path("/mock/root/path")
    return mock_provider


@pytest.fixture
def mock_logger_class() -> Generator[MagicMock, None, None]:
    """Mock logger class for testing."""
    with patch("coregen.common.logger.Logger") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_dirs() -> Generator[None, None, None]:
    """
    Remove any output or archive directories created during tests.

    This ensures the repository directory stays clean after test runs.
    """
    # Run tests
    yield

    # Directories to clean up
    repo_root = Path(__file__).parent
    dirs_to_clean = [repo_root / "output", repo_root / "archive"]

    # Remove test directories
    for dir_path in dirs_to_clean:
        if dir_path.exists() and dir_path.is_dir():
            try:
                shutil.rmtree(dir_path, ignore_errors=True)
                print(f"Removed test directory: {dir_path}")
            except Exception as e:
                print(f"Error removing directory {dir_path}: {e}")


def pytest_configure(config):
    """Configure pytest with dynamic platform markers."""
    # Register current platform marker dynamically
    current_os = Platform.get_os()
    current_arch = Platform.get_arch()
    Platform.get_platform()

    # Add informative markers
    config.addinivalue_line(
        "markers",
        f"current_platform_{current_os}: automatically applied to tests running on {current_os}",
    )
    config.addinivalue_line(
        "markers",
        f"current_arch_{current_arch}: automatically applied to tests for {current_arch} architecture",
    )


def pytest_collection_modifyitems(config, items):
    """Automatically skip tests based on platform markers."""
    current_os = Platform.get_os()

    for item in items:
        markers = [m.name for m in item.iter_markers()]

        # Skip tests marked for other platforms
        if current_os == "darwin":
            if "platform_linux" in markers:
                item.add_marker(pytest.mark.skip(reason="Linux-only test"))
        elif current_os == "linux":
            if "platform_macos" in markers:
                item.add_marker(pytest.mark.skip(reason="macOS-only test"))
