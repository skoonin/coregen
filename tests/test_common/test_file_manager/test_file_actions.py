"""Tests for file_manager action handling."""

import shutil
import tempfile
from collections.abc import Generator

# Use the built-in TimeoutError instead
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.file_manager import FileManager


@pytest.fixture
def setup_file_actions() -> Generator[None, None, None]:
    """Set up test environment."""
    # Create a temporary directory for file operations
    temp_dir = Path(tempfile.mkdtemp())

    # Create archive directory
    archive_dir = temp_dir / "archive"
    archive_dir.mkdir()

    # Create test files and directories
    test_file = temp_dir / "test_file.txt"
    with open(test_file, "w") as f:
        f.write("Test content")

    test_dir = temp_dir / "test_dir"
    test_dir.mkdir()
    nested_file = test_dir / "nested.txt"
    with open(nested_file, "w") as f:
        f.write("Nested test content")

    yield {
        "temp_dir": temp_dir,
        "archive_dir": archive_dir,
        "test_file": test_file,
        "test_dir": test_dir,
        "nested_file": nested_file,
    }

    # Teardown: Remove temporary directory and all its contents
    shutil.rmtree(temp_dir)


class TestFileActionHandling:
    """Tests for FileManager action handling."""

    def test_handle_action_skip(self, setup_file_actions):
        """Test _handle_action with SKIP action."""
        archive_dir = setup_file_actions["archive_dir"]
        test_file = setup_file_actions["test_file"]
        temp_dir = setup_file_actions["temp_dir"]

        file_manager = FileManager(
            archive_dir=archive_dir, file_action=FileAction.SKIP, quiet=True
        )

        # Test with existing file - should return False (skip)
        result = file_manager._handle_action(test_file)
        assert result is False
        # Verify file still exists
        assert test_file.exists()

        # Test with non-existing file - should return True (proceed)
        non_existent = temp_dir / "does_not_exist.txt"
        result = file_manager._handle_action(non_existent)
        assert result is True

    def test_handle_action_overwrite(self, setup_file_actions):
        """Test _handle_action with OVERWRITE action."""
        archive_dir = setup_file_actions["archive_dir"]
        test_file = setup_file_actions["test_file"]
        test_dir = setup_file_actions["test_dir"]

        file_manager = FileManager(
            archive_dir=archive_dir, file_action=FileAction.OVERWRITE, quiet=True
        )

        # Test with existing file - should delete and return True
        assert test_file.exists()  # Verify file exists initially
        result = file_manager._handle_action(test_file)
        assert result is True
        assert not test_file.exists()  # File should be deleted

        # Test with directory containing files
        assert test_dir.exists()  # Verify dir exists initially
        result = file_manager._handle_action(test_dir)
        assert result is True
        assert not test_dir.exists()  # Dir should be deleted

    def test_handle_action_archive(self, setup_file_actions):
        """Test _handle_action with ARCHIVE action."""
        archive_dir = setup_file_actions["archive_dir"]
        test_file = setup_file_actions["test_file"]

        file_manager = FileManager(
            archive_dir=archive_dir, file_action=FileAction.ARCHIVE, quiet=True
        )

        # Test with existing file - should archive and return True
        assert test_file.exists()  # Verify file exists initially

        with patch("coregen.common.file_manager.datetime") as mock_datetime:
            # Mock datetime to use a fixed timestamp
            mock_datetime.now.return_value.strftime.return_value = "2025-04-25-12-00-00"

            result = file_manager._handle_action(test_file)

            assert result is True
            assert not test_file.exists()  # Original file should be moved

            # Check if file was archived correctly
            expected_archive_path = archive_dir / "2025-04-25-12-00-00" / test_file.name
            assert expected_archive_path.exists()
            assert expected_archive_path.read_text() == "Test content"

    def test_handle_action_empty_dir(self, setup_file_actions):
        """Test _handle_action with empty directory."""
        archive_dir = setup_file_actions["archive_dir"]
        temp_dir = setup_file_actions["temp_dir"]

        # Create an empty directory
        empty_dir = temp_dir / "empty_dir"
        empty_dir.mkdir()

        file_manager = FileManager(
            archive_dir=archive_dir,
            file_action=FileAction.SKIP,  # Action doesn't matter for empty dirs
            quiet=True,
        )

        # Empty directory should return True regardless of action
        result = file_manager._handle_action(empty_dir)
        assert result is True
        assert empty_dir.exists()  # Directory should still exist

    @patch(
        "coregen.common.file_manager.input", side_effect=["o"]
    )  # Simulate user selecting 'overwrite'
    @patch("sys.stdin.isatty", return_value=True)  # Mock TTY environment
    def test_prompt_action_overwrite(self, mock_isatty, mock_input, setup_file_actions):
        """Test _prompt_action with user selecting overwrite."""
        archive_dir = setup_file_actions["archive_dir"]
        test_file = setup_file_actions["test_file"]

        file_manager = FileManager(
            archive_dir=archive_dir, file_action=FileAction.ASK, quiet=False
        )

        # Mock threading.Timer to prevent actual timeout
        with patch("coregen.common.file_manager.threading.Timer"):
            result = file_manager._prompt_action(test_file)

            assert result is True
            assert not test_file.exists()  # File should be deleted
            mock_input.assert_called_once()

    @patch(
        "coregen.common.file_manager.input", side_effect=["s"]
    )  # Simulate user selecting 'skip'
    @patch("sys.stdin.isatty", return_value=True)  # Mock TTY environment
    def test_prompt_action_skip(self, mock_isatty, mock_input, setup_file_actions):
        """Test _prompt_action with user selecting skip."""
        archive_dir = setup_file_actions["archive_dir"]
        test_file = setup_file_actions["test_file"]

        file_manager = FileManager(
            archive_dir=archive_dir, file_action=FileAction.ASK, quiet=False
        )

        # Mock threading.Timer to prevent actual timeout
        with patch("coregen.common.file_manager.threading.Timer"):
            result = file_manager._prompt_action(test_file)

            assert result is False
            assert test_file.exists()  # File should still exist
            mock_input.assert_called_once()

    @patch(
        "coregen.common.file_manager.input", side_effect=["a"]
    )  # Simulate user selecting 'archive'
    @patch("sys.stdin.isatty", return_value=True)  # Mock TTY environment
    def test_prompt_action_archive(self, mock_isatty, mock_input, setup_file_actions):
        """Test _prompt_action with user selecting archive."""
        archive_dir = setup_file_actions["archive_dir"]
        test_file = setup_file_actions["test_file"]

        file_manager = FileManager(
            archive_dir=archive_dir, file_action=FileAction.ASK, quiet=False
        )

        # Mock threading.Timer for consistent testing
        with (
            patch("coregen.common.file_manager.threading.Timer"),
            patch("coregen.common.file_manager.datetime") as mock_datetime,
        ):

            mock_datetime.now.return_value.strftime.return_value = "2025-04-25-12-00-00"

            result = file_manager._prompt_action(test_file)

            assert result is True
            assert not test_file.exists()  # Original file should be moved

            # Check if file was archived correctly
            expected_archive_path = archive_dir / "2025-04-25-12-00-00" / test_file.name
            assert expected_archive_path.exists()
            assert expected_archive_path.read_text() == "Test content"

            mock_input.assert_called_once()

    def test_prompt_action_dry_run(self, setup_file_actions):
        """Test _prompt_action with dry_run enabled."""
        archive_dir = setup_file_actions["archive_dir"]
        test_file = setup_file_actions["test_file"]

        file_manager = FileManager(
            archive_dir=archive_dir,
            file_action=FileAction.ASK,
            dry_run=True,
            quiet=True,
        )

        # Should not prompt and return True without modifying file
        result = file_manager._prompt_action(test_file)

        assert result is True
        assert test_file.exists()  # File should still exist

    @patch(
        "coregen.common.file_manager.input", side_effect=["invalid", "s"]
    )  # Invalid input then skip
    @patch("sys.stdin.isatty", return_value=True)  # Mock TTY environment
    def test_prompt_action_invalid_input(
        self, mock_isatty, mock_input, setup_file_actions
    ):
        """Test _prompt_action with invalid user input."""
        archive_dir = setup_file_actions["archive_dir"]
        test_file = setup_file_actions["test_file"]

        file_manager = FileManager(
            archive_dir=archive_dir, file_action=FileAction.ASK, quiet=False
        )

        # Mock threading.Timer to prevent actual timeout
        with patch("coregen.common.file_manager.threading.Timer"):
            result = file_manager._prompt_action(test_file)

            assert result is False
            assert test_file.exists()  # File should still exist
            assert mock_input.call_count == 2  # Should be called twice

    def test_prompt_action_timeout(self, setup_file_actions):
        """Test _prompt_action with timeout."""
        archive_dir = setup_file_actions["archive_dir"]
        test_file = setup_file_actions["test_file"]

        file_manager = FileManager(
            archive_dir=archive_dir,
            file_action=FileAction.ASK,
            quiet=True,
            timeout_seconds=1,  # Short timeout for testing
        )

        # The FileManager now uses threading.Timer instead of signals for timeouts
        # We need to ensure the Timer's callback gets called to simulate timeout
        def mock_timer_init(interval, function, *args, **kwargs):
            mock = MagicMock()
            # Call the timeout function immediately
            function()
            # Return a mock with required methods
            mock.start = MagicMock()
            mock.cancel = MagicMock()
            return mock

        # Mock the Timer to call the timeout function
        with patch("coregen.common.file_manager.threading.Timer", mock_timer_init):
            # Since the timeout function will be called immediately, input() won't be called
            result = file_manager._prompt_action(test_file)

            # Timeout should default to skip (false)
            assert result is False
            assert test_file.exists()  # File should still exist

    def test_handle_action_delete(self, setup_file_actions):
        """Test _handle_action with DELETE action."""
        archive_dir = setup_file_actions["archive_dir"]
        test_file = setup_file_actions["test_file"]
        temp_dir = setup_file_actions["temp_dir"]

        file_manager = FileManager(
            archive_dir=archive_dir, file_action=FileAction.DELETE, quiet=True
        )

        # Test with existing file - should delete and return True
        assert test_file.exists()  # Verify file exists initially
        result = file_manager._handle_action(test_file)
        assert result is True
        assert not test_file.exists()  # File should be deleted

        # Create a new test directory with nested file for the next test
        test_dir2 = temp_dir / "test_dir2"
        test_dir2.mkdir()
        nested_file2 = test_dir2 / "nested2.txt"
        with open(nested_file2, "w") as f:
            f.write("Nested test content 2")

        # Test with directory containing files
        assert test_dir2.exists()  # Verify dir exists initially
        assert nested_file2.exists()  # Verify nested file exists
        result = file_manager._handle_action(test_dir2)
        assert result is True
        assert not test_dir2.exists()  # Dir should be deleted
        assert not nested_file2.exists()  # Nested file should also be gone

        # Test with non-existing file - should return True (proceed)
        non_existent = temp_dir / "does_not_exist.txt"
        result = file_manager._handle_action(non_existent)
        assert result is True
