"""Tests for file_manager file operations."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.file_manager import FileManager


@pytest.fixture
def file_ops_setup() -> Generator[None, None, None]:
    """Set up test environment for file operations."""
    # Create a temporary directory for file operations
    temp_dir = Path(tempfile.mkdtemp())

    # Create a standard file manager for testing
    file_manager = FileManager(
        archive_dir=temp_dir / "archive",
        dry_run=False,
        file_action=FileAction.OVERWRITE,
        quiet=True,
    )

    # Create test files and directories
    test_file = temp_dir / "test_file.txt"
    with open(test_file, "w") as f:
        f.write("Test content")

    test_dir = temp_dir / "test_dir"
    test_dir.mkdir()

    yield {
        "temp_dir": temp_dir,
        "file_manager": file_manager,
        "test_file": test_file,
        "test_dir": test_dir,
    }

    # Teardown - clean up test environment
    shutil.rmtree(temp_dir)


class TestFileOperations:
    """Tests for FileManager file operations."""

    def test_create_file(self, file_ops_setup):
        """Test create_file method."""
        temp_dir = file_ops_setup["temp_dir"]
        file_manager = file_ops_setup["file_manager"]
        # Test creating a new file
        new_file = temp_dir / "new_file.txt"
        content = "New file content"

        file_manager.create_file(new_file, content)

        # Verify the file was created with the correct content
        assert new_file.exists()
        assert new_file.read_text() == content

    def test_create_file_overwrites_existing(self, file_ops_setup):
        """Test create_file overwrites existing file with OVERWRITE action."""
        file_manager = file_ops_setup["file_manager"]
        test_file = file_ops_setup["test_file"]
        # First verify our test_file exists and has content
        assert test_file.exists()
        assert test_file.read_text() == "Test content"

        # Now overwrite it
        new_content = "Overwritten content"
        file_manager.create_file(test_file, new_content)

        # Verify the file was overwritten with new content
        assert test_file.exists()
        assert test_file.read_text() == new_content

    def test_create_file_with_dry_run(self, file_ops_setup):
        """Test create_file with dry_run does not modify filesystem."""
        temp_dir = file_ops_setup["temp_dir"]
        # Create file manager with dry_run enabled
        dry_run_manager = FileManager(
            archive_dir=temp_dir / "archive",
            dry_run=True,
            file_action=FileAction.OVERWRITE,
            quiet=True,
        )

        # Test creating a new file with dry_run
        new_file = temp_dir / "dry_run_file.txt"
        content = "This file should not be created"

        dry_run_manager.create_file(new_file, content)

        # Verify the file was NOT created
        assert not new_file.exists()

    def test_copy_file(self, file_ops_setup):
        """Test copy_file method."""
        temp_dir = file_ops_setup["temp_dir"]
        file_manager = file_ops_setup["file_manager"]
        test_file = file_ops_setup["test_file"]
        # Define source and destination
        source = test_file
        destination = temp_dir / "copied_file.txt"

        # Copy the file
        file_manager.copy_file(source, destination)

        # Verify the file was copied correctly
        assert destination.exists()
        assert destination.read_text() == source.read_text()

    def test_copy_file_overwrites_existing(self, file_ops_setup):
        """Test copy_file overwrites existing destination with OVERWRITE action."""
        temp_dir = file_ops_setup["temp_dir"]
        file_manager = file_ops_setup["file_manager"]
        test_file = file_ops_setup["test_file"]
        # Create a destination file with different content
        destination = temp_dir / "existing_dest.txt"
        with open(destination, "w") as f:
            f.write("Original destination content")

        # Copy over it
        file_manager.copy_file(test_file, destination)

        # Verify it was overwritten with source content
        assert destination.exists()
        assert destination.read_text() == test_file.read_text()

    def test_copy_file_source_not_found(self, file_ops_setup):
        """Test copy_file handles errors when source doesn't exist."""
        temp_dir = file_ops_setup["temp_dir"]
        file_manager = file_ops_setup["file_manager"]
        non_existent = temp_dir / "does_not_exist.txt"
        destination = temp_dir / "will_not_be_created.txt"

        # copy_file returns a list of errors rather than raising exceptions
        errors = file_manager.copy_file(non_existent, destination)

        # Should contain an error about the source not existing
        assert len(errors) > 0
        assert "Source file does not exist" in errors[0]
        assert str(non_existent) in errors[0]

        # Verify destination was not created
        assert not destination.exists()

    def test_create_directory(self, file_ops_setup):
        """Test create_directory method."""
        temp_dir = file_ops_setup["temp_dir"]
        file_manager = file_ops_setup["file_manager"]
        # Test creating a new directory
        new_dir = temp_dir / "new_dir"

        file_manager.create_directory(new_dir)

        # Verify the directory was created
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_create_directory_with_parents(self, file_ops_setup):
        """Test create_directory creates parent directories."""
        temp_dir = file_ops_setup["temp_dir"]
        file_manager = file_ops_setup["file_manager"]
        # Test creating a nested directory
        nested_dir = temp_dir / "parent" / "child" / "nested"

        file_manager.create_directory(nested_dir)

        # Verify the nested directory and its parents were created
        assert nested_dir.exists()
        assert nested_dir.is_dir()
        assert (temp_dir / "parent").exists()
        assert (temp_dir / "parent" / "child").exists()

    def test_create_directory_already_exists(self, file_ops_setup):
        """Test create_directory with already existing directory."""
        file_manager = file_ops_setup["file_manager"]
        test_dir = file_ops_setup["test_dir"]
        # Directory already exists
        existing_dir = test_dir

        # Should not raise an exception
        file_manager.create_directory(existing_dir)

        # Verify the directory still exists
        assert existing_dir.exists()
        assert existing_dir.is_dir()
