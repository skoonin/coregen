"""Tests for file_manager module."""

from pathlib import Path

from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.file_manager import FileManager


def test_file_manager_init():
    """Test initialization with default values."""
    fm = FileManager()
    assert fm.dry_run is False
    assert (
        fm.file_action == FileAction.OVERWRITE
    )  # Default is OVERWRITE as per settings
    assert fm.archive_dir == Path("archive")
    assert fm.quiet is False
    assert fm.verbose is False
    # output_format removed from FileManager
    assert fm.no_color is False


def test_file_manager_init_custom():
    """Test initialization with custom values."""
    archive_dir = Path("custom/archive")
    fm = FileManager(
        archive_dir=archive_dir,
        dry_run=True,
        file_action=FileAction.OVERWRITE,
        quiet=True,
        verbose=True,
        no_color=True,
    )
    assert fm.dry_run is True
    assert fm.file_action == FileAction.OVERWRITE
    assert fm.archive_dir == archive_dir
    assert fm.quiet is True
    assert fm.verbose is True
    # output_format removed from FileManager
    assert fm.no_color is True
