"""
Unit tests for the FileManager class.

This file provides comprehensive tests for file management functionality,
following the AAA (Arrange, Act, Assert) pattern and using standardized fixtures.
"""

import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.file_manager import FileManager


@pytest.fixture
def temp_dir() -> Any:
    """Create a temporary directory for file operations testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


class TestFileManagerInitialization:
    """Tests for FileManager initialization and configuration."""

    def test_init_with_defaults(self, mock_settings):
        """Test FileManager initialization with default values."""
        # Arrange & Act
        file_manager = FileManager()

        # Assert
        assert file_manager.dry_run is False
        assert file_manager.file_action == FileAction.ASK
        assert file_manager.quiet is False
        assert file_manager.verbose is False
        assert file_manager.no_color is False
        assert file_manager.timeout_seconds == 30
        assert file_manager.archive_dir == Path("archive")
        assert isinstance(file_manager._created_directories, set)

    def test_init_with_custom_values(self, mock_settings):
        """Test FileManager initialization with custom values."""
        # Arrange
        custom_archive_dir = Path("/custom/archive")

        # Act
        file_manager = FileManager(
            archive_dir=custom_archive_dir,
            dry_run=True,
            file_action=FileAction.OVERWRITE,
            quiet=True,
            verbose=True,
            no_color=True,
            timeout_seconds=60,
        )

        # Assert
        assert file_manager.dry_run is True
        assert file_manager.file_action == FileAction.OVERWRITE
        assert file_manager.quiet is True
        assert file_manager.verbose is True
        assert file_manager.no_color is True
        assert file_manager.timeout_seconds == 60
        assert file_manager.archive_dir == custom_archive_dir

    @pytest.mark.parametrize(
        "file_action",
        [
            FileAction.ASK,
            FileAction.SKIP,
            FileAction.OVERWRITE,
            FileAction.ARCHIVE,
            FileAction.DELETE,
        ],
    )
    def test_init_with_different_file_actions(self, mock_settings, file_action):
        """Test FileManager initialization with different file actions."""
        # Arrange & Act
        file_manager = FileManager(file_action=file_action)

        # Assert
        assert file_manager.file_action == file_action


class TestHandleAction:
    """Tests for the _handle_action method."""

    def test_handle_action_nonexistent_file(self, mock_settings):
        """Test _handle_action with nonexistent file returns True."""
        # Arrange
        file_manager = FileManager()
        nonexistent_path = Path("/nonexistent/file.txt")

        # Act
        result = file_manager._handle_action(nonexistent_path)

        # Assert
        assert result is True

    def test_handle_action_empty_directory(self, mock_settings, temp_dir):
        """Test _handle_action with empty directory returns True."""
        # Arrange
        file_manager = FileManager()
        empty_dir = temp_dir / "empty_dir"
        empty_dir.mkdir()

        # Act
        result = file_manager._handle_action(empty_dir)

        # Assert
        assert result is True

    def test_handle_action_skip_mode(self, mock_settings, mock_console, temp_dir):
        """Test _handle_action with SKIP file action."""
        # Arrange
        file_manager = FileManager(file_action=FileAction.SKIP, quiet=False)
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("content")

        # Act
        result = file_manager._handle_action(test_file)

        # Assert
        assert result is False
        mock_console.debug.assert_called_once_with(f"Skipping: {test_file}")

    def test_handle_action_skip_mode_quiet(self, mock_settings, mock_console, temp_dir):
        """Test _handle_action with SKIP file action in quiet mode."""
        # Arrange
        file_manager = FileManager(file_action=FileAction.SKIP, quiet=True)
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("content")

        # Act
        result = file_manager._handle_action(test_file)

        # Assert
        assert result is False
        mock_console.debug.assert_not_called()

    def test_handle_action_overwrite_mode(self, mock_settings, mock_logger, temp_dir):
        """Test _handle_action with OVERWRITE file action."""
        # Arrange
        file_manager = FileManager(file_action=FileAction.OVERWRITE)
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("content")

        # Act
        result = file_manager._handle_action(test_file)

        # Assert
        assert result is True
        assert not test_file.exists()  # File should be deleted
        mock_logger.debug.assert_called_with(f"Overwriting: {test_file}")

    def test_handle_action_archive_mode(self, mock_settings, mock_console, temp_dir):
        """Test _handle_action with ARCHIVE file action."""
        # Arrange
        archive_dir = temp_dir / "archive"
        file_manager = FileManager(
            file_action=FileAction.ARCHIVE, archive_dir=archive_dir
        )
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("content")

        # Act
        with patch.object(file_manager, "_archive") as mock_archive:
            result = file_manager._handle_action(test_file)

            # Assert
            assert result is True
            mock_console.info.assert_called_once_with(f"Archiving: {test_file}")
            mock_archive.assert_called_once_with(test_file)

    def test_handle_action_archive_mode_no_archive_dir(self, mock_settings, temp_dir):
        """Test _handle_action with ARCHIVE file action but no archive directory."""
        # Arrange
        file_manager = FileManager(file_action=FileAction.ARCHIVE, archive_dir=None)
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("content")

        # Act & Assert
        with pytest.raises(
            ValueError, match="archive_dir must be set for ARCHIVE action"
        ):
            file_manager._handle_action(test_file)

    def test_handle_action_delete_mode(self, mock_settings, mock_logger, temp_dir):
        """Test _handle_action with DELETE file action."""
        # Arrange
        file_manager = FileManager(file_action=FileAction.DELETE)
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("content")

        # Act
        result = file_manager._handle_action(test_file)

        # Assert
        assert result is True
        assert not test_file.exists()  # File should be deleted
        mock_logger.debug.assert_called_with(f"Deleting: {test_file}")


class TestPromptAction:
    """Tests for the _prompt_action method."""

    def test_prompt_action_dry_run(self, mock_settings, mock_console, temp_dir):
        """Test _prompt_action in dry run mode."""
        # Arrange
        file_manager = FileManager(dry_run=True)
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("content")

        # Act
        result = file_manager._prompt_action(test_file)

        # Assert
        assert result is True
        mock_console.info.assert_called_once_with(f"Would prompt for {test_file}")

    @patch("sys.stdin.isatty", return_value=False)
    def test_prompt_action_non_interactive(
        self, mock_isatty, mock_settings, mock_console, temp_dir
    ):
        """Test _prompt_action in non-interactive environment."""
        # Arrange
        file_manager = FileManager(dry_run=False, quiet=False)
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("content")

        # Act
        result = file_manager._prompt_action(test_file)

        # Assert
        assert result is False
        mock_console.info.assert_called_with(
            f"File exists: {test_file} - Non-interactive mode, defaulting to skip"
        )

    def test_prompt_action_quiet_mode(self, mock_settings, mock_console, temp_dir):
        """Test _prompt_action in quiet mode."""
        # Arrange
        file_manager = FileManager(dry_run=False, quiet=True)
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("content")

        # Act
        with patch("sys.stdin.isatty", return_value=True):
            result = file_manager._prompt_action(test_file)

        # Assert
        assert result is False
        mock_console.info.assert_called_with(
            f"File exists: {test_file} - Non-interactive mode, defaulting to skip"
        )

    @patch("sys.stdin.isatty", return_value=True)
    @patch("builtins.input", side_effect=["s"])
    def test_prompt_action_skip_choice(
        self, mock_input, mock_isatty, mock_settings, mock_console, temp_dir
    ):
        """Test _prompt_action with skip choice."""
        # Arrange
        file_manager = FileManager(dry_run=False, quiet=False, timeout_seconds=1)
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("content")

        # Act
        result = file_manager._prompt_action(test_file)

        # Assert
        assert result is False
        mock_console.info.assert_any_call(f"File exists: {test_file}")
        mock_console.info.assert_any_call("Skipping.")

    @patch("sys.stdin.isatty", return_value=True)
    @patch("builtins.input", side_effect=["o"])
    def test_prompt_action_overwrite_choice(
        self, mock_input, mock_isatty, mock_settings, mock_console, temp_dir
    ):
        """Test _prompt_action with overwrite choice."""
        # Arrange
        file_manager = FileManager(dry_run=False, quiet=False, timeout_seconds=1)
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("content")

        # Act
        with patch.object(file_manager, "_delete") as mock_delete:
            result = file_manager._prompt_action(test_file)

            # Assert
            assert result is True
            mock_delete.assert_called_once_with(test_file)

    def test_prompt_action_timeout(self, mock_settings, mock_console, temp_dir):
        """Test _prompt_action with timeout."""
        # Arrange
        file_manager = FileManager(dry_run=False, quiet=False, timeout_seconds=0.1)
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("content")

        # Act
        with (
            patch("sys.stdin.isatty", return_value=True),
            # 10x the 0.1s timeout so loaded CI runners cannot flake the race
            patch("builtins.input", side_effect=lambda _: time.sleep(1.0)),
        ):
            result = file_manager._prompt_action(test_file)

        # Assert
        assert result is False
        mock_console.info.assert_any_call(f"File exists: {test_file}")


class TestArchive:
    """Tests for the _archive method."""

    def test_archive_dry_run(self, mock_settings, mock_console, temp_dir):
        """Test _archive in dry run mode."""
        # Arrange
        archive_dir = temp_dir / "archive"
        file_manager = FileManager(dry_run=True, archive_dir=archive_dir)
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("content")

        # Act
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2023-01-01-12-00-00"
            file_manager._archive(test_file)

        # Assert
        mock_console.info.assert_called_once()
        assert "Archive" in str(mock_console.info.call_args[0][0])
        assert test_file.exists()  # File should still exist in dry run

    def test_archive_successful(self, mock_settings, mock_console, temp_dir):
        """Test successful archive operation."""
        # Arrange
        archive_dir = temp_dir / "archive"
        file_manager = FileManager(dry_run=False, archive_dir=archive_dir)
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("content")

        # Act
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2023-01-01-12-00-00"
            file_manager._archive(test_file)

        # Assert
        assert not test_file.exists()  # Original file should be moved
        mock_console.info.assert_called_once()
        assert "Archived:" in str(mock_console.info.call_args[0][0])

    def test_archive_path_not_relative_to_cwd(
        self, mock_settings, mock_console, mock_logger, temp_dir
    ):
        """Test archive with path not relative to current working directory."""
        # Arrange
        archive_dir = temp_dir / "archive"
        file_manager = FileManager(dry_run=False, archive_dir=archive_dir)

        # Create a temporary file outside the working directory
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_path.write_text("content")

        # Act
        try:
            with patch("datetime.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = (
                    "2023-01-01-12-00-00"
                )
                file_manager._archive(temp_path)

            # Assert
            mock_logger.warning.assert_called_once()
            assert "Could not determine relative path" in str(
                mock_logger.warning.call_args[0][0]
            )
        finally:
            # Cleanup
            if temp_path.exists():
                temp_path.unlink()


class TestDelete:
    """Tests for the _delete method."""

    def test_delete_dry_run(self, mock_settings, temp_dir):
        """Test _delete in dry run mode."""
        # Arrange
        file_manager = FileManager(dry_run=True)
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("content")

        # Act
        file_manager._delete(test_file)

        # Assert
        assert test_file.exists()  # File should still exist in dry run

    def test_delete_file(self, mock_settings, temp_dir):
        """Test deleting a regular file."""
        # Arrange
        file_manager = FileManager(dry_run=False)
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("content")

        # Act
        file_manager._delete(test_file)

        # Assert
        assert not test_file.exists()

    def test_delete_directory(self, mock_settings, mock_logger, temp_dir):
        """Test deleting a directory with contents."""
        # Arrange
        file_manager = FileManager(dry_run=False)
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        # Act
        file_manager._delete(test_dir)

        # Assert
        assert not test_dir.exists()
        mock_logger.debug.assert_called_with(f"Deleted: {test_dir}")

    def test_delete_empty_directory(self, mock_settings, temp_dir):
        """Test deleting an empty directory."""
        # Arrange
        file_manager = FileManager(dry_run=False)
        test_dir = temp_dir / "empty_dir"
        test_dir.mkdir()

        # Act
        file_manager._delete(test_dir)

        # Assert
        # Empty directory should not be deleted by _delete method
        assert test_dir.exists()

    def test_delete_failure(self, mock_settings, mock_logger, temp_dir):
        """Test _delete with permission error."""
        # Arrange
        file_manager = FileManager(dry_run=False)
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("content")

        # Act & Assert
        with patch(
            "pathlib.Path.unlink", side_effect=PermissionError("Permission denied")
        ):
            with pytest.raises(PermissionError):
                file_manager._delete(test_file)
            mock_logger.error.assert_called_once()


class TestCopyFile:
    """Tests for the copy_file method."""

    def test_copy_file_nonexistent_source(self, mock_settings, mock_logger, temp_dir):
        """Test copy_file with nonexistent source file."""
        # Arrange
        file_manager = FileManager()
        source = temp_dir / "nonexistent.txt"
        destination = temp_dir / "destination.txt"

        # Act
        errors = file_manager.copy_file(source, destination)

        # Assert
        assert len(errors) == 1
        assert "Source file does not exist" in errors[0]
        mock_logger.error.assert_called_once()

    def test_copy_file_successful(self, mock_settings, temp_dir):
        """Test successful file copy operation."""
        # Arrange
        file_manager = FileManager(dry_run=False, file_action=FileAction.OVERWRITE)
        source = temp_dir / "source.txt"
        destination = temp_dir / "destination.txt"
        source.write_text("test content")

        # Act
        errors = file_manager.copy_file(source, destination)

        # Assert
        assert len(errors) == 0
        assert destination.exists()
        assert destination.read_text() == "test content"

    def test_copy_file_dry_run(self, mock_settings, mock_console, temp_dir):
        """Test copy_file in dry run mode."""
        # Arrange
        file_manager = FileManager(dry_run=True, verbose=True, quiet=False)
        source = temp_dir / "source.txt"
        destination = temp_dir / "destination.txt"
        source.write_text("test content")

        # Act
        errors = file_manager.copy_file(source, destination)

        # Assert
        assert len(errors) == 0
        assert not destination.exists()  # Should not actually create file
        mock_console.debug.assert_called_with(f"Copied file: {source} -> {destination}")

    def test_copy_file_with_handle_action_skip(self, mock_settings, temp_dir):
        """Test copy_file when _handle_action returns False (skip)."""
        # Arrange
        file_manager = FileManager(file_action=FileAction.SKIP)
        source = temp_dir / "source.txt"
        destination = temp_dir / "destination.txt"
        source.write_text("test content")
        destination.write_text("existing content")  # File exists

        # Act
        errors = file_manager.copy_file(source, destination)

        # Assert
        assert len(errors) == 0
        assert destination.read_text() == "existing content"  # Should remain unchanged


class TestCreateFile:
    """Tests for the create_file method."""

    def test_create_file_basic(self, mock_settings, temp_dir):
        """Test basic file creation."""
        # Arrange
        file_manager = FileManager(dry_run=False, file_action=FileAction.OVERWRITE)
        test_file = temp_dir / "new_file.txt"
        content = "test content"

        # Act
        file_manager.create_file(test_file, content)

        # Assert
        assert test_file.exists()
        assert test_file.read_text() == content

    def test_create_file_dry_run(self, mock_settings, mock_console, temp_dir):
        """Test create_file in dry run mode."""
        # Arrange
        file_manager = FileManager(dry_run=True, verbose=True, quiet=False)
        test_file = temp_dir / "new_file.txt"
        content = "test content"

        # Act
        file_manager.create_file(test_file, content)

        # Assert
        assert not test_file.exists()
        mock_console.debug.assert_called_with(f"Created file: {test_file}")

    def test_create_file_with_permissions(self, mock_settings, temp_dir):
        """Test create_file with source permissions."""
        # Arrange
        file_manager = FileManager(dry_run=False, file_action=FileAction.OVERWRITE)
        source_file = temp_dir / "source.txt"
        test_file = temp_dir / "new_file.txt"
        source_file.write_text("source content")

        # Act
        with patch("shutil.copymode") as mock_copymode:
            file_manager.create_file(test_file, "new content", source_perms=source_file)

            # Assert
            assert test_file.exists()
            mock_copymode.assert_called_once_with(source_file, test_file)

    def test_create_file_handle_action_skip(self, mock_settings, temp_dir):
        """Test create_file when _handle_action returns False."""
        # Arrange
        file_manager = FileManager(file_action=FileAction.SKIP)
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("existing content")

        # Act
        file_manager.create_file(test_file, "new content")

        # Assert
        assert test_file.read_text() == "existing content"  # Should remain unchanged


class TestCreateDirectory:
    """Tests for the create_directory method."""

    def test_create_directory_basic(self, mock_settings, temp_dir):
        """Test basic directory creation."""
        # Arrange
        file_manager = FileManager(dry_run=False)
        test_dir = temp_dir / "new_dir"

        # Act
        file_manager.create_directory(test_dir)

        # Assert
        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_create_directory_dry_run(self, mock_settings, mock_console, temp_dir):
        """Test create_directory in dry run mode."""
        # Arrange
        file_manager = FileManager(dry_run=True, verbose=True, quiet=False)
        test_dir = temp_dir / "new_dir"

        # Act
        file_manager.create_directory(test_dir)

        # Assert
        assert not test_dir.exists()
        mock_console.debug.assert_called_with(f"Created directory: {test_dir}")

    def test_create_directory_already_exists(self, mock_settings, temp_dir):
        """Test create_directory when directory already exists."""
        # Arrange
        file_manager = FileManager(dry_run=False)
        test_dir = temp_dir / "existing_dir"
        test_dir.mkdir()

        # Act
        file_manager.create_directory(test_dir)

        # Assert
        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_create_directory_file_exists(self, mock_settings, temp_dir):
        """Test create_directory when a file exists at the path."""
        # Arrange
        file_manager = FileManager(dry_run=False, file_action=FileAction.OVERWRITE)
        test_path = temp_dir / "existing_file"
        test_path.write_text("file content")

        # Act
        file_manager.create_directory(test_path)

        # Assert
        assert test_path.exists()
        assert test_path.is_dir()  # Should now be a directory


class TestRemoveDirectory:
    """Tests for the remove_directory method."""

    def test_remove_directory_basic(self, mock_settings, mock_logger, temp_dir):
        """Test basic directory removal."""
        # Arrange
        file_manager = FileManager(dry_run=False, quiet=False)
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        # Act
        file_manager.remove_directory(test_dir)

        # Assert
        assert not test_dir.exists()
        mock_logger.debug.assert_any_call(f"Removed directory: {test_dir}")

    def test_remove_directory_dry_run(self, mock_settings, mock_console, temp_dir):
        """Test remove_directory in dry run mode."""
        # Arrange
        file_manager = FileManager(dry_run=True, quiet=False)
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()

        # Act
        file_manager.remove_directory(test_dir)

        # Assert
        assert test_dir.exists()  # Should still exist in dry run
        mock_console.info.assert_called_once()

    def test_remove_directory_nonexistent(self, mock_settings, mock_logger, temp_dir):
        """Test remove_directory with nonexistent directory."""
        # Arrange
        file_manager = FileManager(dry_run=False)
        test_dir = temp_dir / "nonexistent_dir"

        # Act
        file_manager.remove_directory(test_dir)

        # Assert
        mock_logger.debug.assert_called_with(
            f"Directory does not exist, nothing to remove: {test_dir}"
        )

    def test_remove_directory_not_directory(self, mock_settings, mock_logger, temp_dir):
        """Test remove_directory with a file path."""
        # Arrange
        file_manager = FileManager(dry_run=False)
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("content")

        # Act
        file_manager.remove_directory(test_file)

        # Assert
        mock_logger.warning.assert_called_with(f"Path is not a directory: {test_file}")
        assert test_file.exists()  # File should remain

    def test_remove_directory_failure(self, mock_settings, mock_logger, temp_dir):
        """Test remove_directory with permission error."""
        # Arrange
        file_manager = FileManager(dry_run=False)
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()

        # Act & Assert
        with patch("shutil.rmtree", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                file_manager.remove_directory(test_dir)
            mock_logger.error.assert_called_once()


class TestFileManagerIntegrationScenarios:
    """Integration tests for realistic FileManager usage scenarios."""

    def test_complete_file_workflow(self, mock_settings, temp_dir):
        """Test a complete file management workflow."""
        # Arrange
        archive_dir = temp_dir / "archive"
        file_manager = FileManager(
            dry_run=False,
            file_action=FileAction.ARCHIVE,
            archive_dir=archive_dir,
            verbose=True,
            quiet=False,
        )

        source_file = temp_dir / "source.txt"
        dest_file = temp_dir / "destination.txt"
        source_file.write_text("original content")

        # Act - Create, copy, and handle existing file
        file_manager.create_file(dest_file, "new content")

        # Reset and copy with archive action
        dest_file.write_text("existing content")
        errors = file_manager.copy_file(source_file, dest_file)

        # Assert
        assert len(errors) == 0
        assert dest_file.exists()
        assert dest_file.read_text() == "original content"

    def test_dry_run_workflow(self, mock_settings, mock_console, temp_dir):
        """Test complete workflow in dry run mode."""
        # Arrange
        file_manager = FileManager(
            dry_run=True, file_action=FileAction.OVERWRITE, verbose=True, quiet=False
        )

        test_file = temp_dir / "test_file.txt"
        test_dir = temp_dir / "test_dir"

        # Act
        file_manager.create_file(test_file, "content")
        file_manager.create_directory(test_dir)
        file_manager.remove_directory(test_dir)

        # Assert - Nothing should actually be created/modified
        assert not test_file.exists()
        assert not test_dir.exists()

        # But console should show what would be done
        assert mock_console.debug.call_count >= 2
