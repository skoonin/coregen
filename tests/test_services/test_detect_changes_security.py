"""Unit tests for DetectChangesService security-critical methods.

These tests focus on security validation methods that prevent:
- Git command injection attacks via unsafe refs
- Tar path traversal attacks during base branch extraction
"""

import tarfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from coregen.services.detect_changes.detect_changes_service import DetectChangesService


@pytest.fixture
def detect_changes_service():
    """Create a DetectChangesService instance for testing."""
    with patch("coregen.services.detect_changes.detect_changes_service.PathService"):
        service = DetectChangesService()
        return service


class TestGitRefSecurity:
    """Test _is_safe_git_ref() method for command injection prevention."""

    def test_safe_git_ref_valid_branch_name(self, detect_changes_service):
        """Test that valid branch names are accepted."""
        assert detect_changes_service._is_safe_git_ref("main")
        assert detect_changes_service._is_safe_git_ref("develop")
        assert detect_changes_service._is_safe_git_ref("feature/my-feature")
        assert detect_changes_service._is_safe_git_ref("release/v1.0.0")
        assert detect_changes_service._is_safe_git_ref("bugfix/issue-123")

    def test_safe_git_ref_valid_remote_branch(self, detect_changes_service):
        """Test that valid remote branch refs are accepted."""
        assert detect_changes_service._is_safe_git_ref("origin/main")
        assert detect_changes_service._is_safe_git_ref("origin/develop")
        assert detect_changes_service._is_safe_git_ref("upstream/master")

    def test_safe_git_ref_valid_tag(self, detect_changes_service):
        """Test that valid tag names are accepted."""
        assert detect_changes_service._is_safe_git_ref("v1.0.0")
        assert detect_changes_service._is_safe_git_ref("release-2024-01")

    def test_safe_git_ref_valid_sha(self, detect_changes_service):
        """Test that valid commit SHAs are accepted."""
        assert detect_changes_service._is_safe_git_ref("a1b2c3d4e5f6")
        assert detect_changes_service._is_safe_git_ref("1234567890abcdef")

    def test_safe_git_ref_rejects_command_separator(self, detect_changes_service):
        """Test that refs with command separators are rejected."""
        assert not detect_changes_service._is_safe_git_ref("main;rm -rf /")
        assert not detect_changes_service._is_safe_git_ref("main&&echo hack")
        assert not detect_changes_service._is_safe_git_ref("main|cat /etc/passwd")

    def test_safe_git_ref_rejects_command_substitution(self, detect_changes_service):
        """Test that refs with command substitution are rejected."""
        assert not detect_changes_service._is_safe_git_ref("main`whoami`")
        assert not detect_changes_service._is_safe_git_ref("main$(whoami)")
        assert not detect_changes_service._is_safe_git_ref("main$((1+1))")

    def test_safe_git_ref_rejects_redirection(self, detect_changes_service):
        """Test that refs with redirection operators are rejected."""
        assert not detect_changes_service._is_safe_git_ref("main>output.txt")
        assert not detect_changes_service._is_safe_git_ref("main<input.txt")

    def test_safe_git_ref_rejects_path_traversal(self, detect_changes_service):
        """Test that refs with path traversal are rejected."""
        assert not detect_changes_service._is_safe_git_ref("../../../etc/passwd")
        assert not detect_changes_service._is_safe_git_ref("main../../secret")

    def test_safe_git_ref_rejects_control_characters(self, detect_changes_service):
        """Test that refs with control characters are rejected."""
        assert not detect_changes_service._is_safe_git_ref("main\nmalicious")
        assert not detect_changes_service._is_safe_git_ref("main\rmalicious")
        assert not detect_changes_service._is_safe_git_ref("main\0null")

    def test_safe_git_ref_rejects_option_injection(self, detect_changes_service):
        """Test that refs starting with dashes are rejected."""
        assert not detect_changes_service._is_safe_git_ref("-exec rm -rf /")
        assert not detect_changes_service._is_safe_git_ref("--option=value")

    def test_safe_git_ref_rejects_empty_string(self, detect_changes_service):
        """Test that empty ref is rejected."""
        assert not detect_changes_service._is_safe_git_ref("")

    def test_safe_git_ref_rejects_backslash(self, detect_changes_service):
        """Test that refs with backslashes are rejected."""
        assert not detect_changes_service._is_safe_git_ref("main\\escape")


@pytest.mark.integration
class TestTarExtractionSecurity:
    """Test _safe_extract() method for path traversal prevention."""

    def test_safe_extract_normal_files(self, detect_changes_service, tmp_path):
        """Test that normal files are extracted successfully."""
        # Create a mock tar file with normal paths
        mock_tar = MagicMock(spec=tarfile.TarFile)

        # Create mock members for normal files
        member1 = Mock()
        member1.name = "file1.txt"
        member1.issym.return_value = False
        member1.islnk.return_value = False
        member1.isfile.return_value = True
        member1.isdir.return_value = False

        member2 = Mock()
        member2.name = "subdir/file2.txt"
        member2.issym.return_value = False
        member2.islnk.return_value = False
        member2.isfile.return_value = True
        member2.isdir.return_value = False

        member3 = Mock()
        member3.name = "another/deep/path/file3.txt"
        member3.issym.return_value = False
        member3.islnk.return_value = False
        member3.isfile.return_value = True
        member3.isdir.return_value = False

        mock_tar.__iter__ = Mock(return_value=iter([member1, member2, member3]))

        # Mock the extract method
        mock_tar.extract = MagicMock()

        # Should not raise any exception
        detect_changes_service._safe_extract(mock_tar, tmp_path)

        # Verify all members were extracted
        assert mock_tar.extract.call_count == 3

    def test_safe_extract_rejects_absolute_path(self, detect_changes_service, tmp_path):
        """Test that absolute paths are rejected."""
        mock_tar = MagicMock(spec=tarfile.TarFile)

        # Create mock member with absolute path
        member = Mock()
        member.name = "/etc/passwd"

        mock_tar.__iter__ = Mock(return_value=iter([member]))
        mock_tar.extract = MagicMock()

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Unsafe path in archive"):
            detect_changes_service._safe_extract(mock_tar, tmp_path)

        # Extract should not have been called
        mock_tar.extract.assert_not_called()

    def test_safe_extract_rejects_parent_traversal(
        self, detect_changes_service, tmp_path
    ):
        """Test that parent directory traversal is rejected."""
        mock_tar = MagicMock(spec=tarfile.TarFile)

        # Create mock member with path traversal
        member = Mock()
        member.name = "../../../etc/passwd"

        mock_tar.__iter__ = Mock(return_value=iter([member]))
        mock_tar.extract = MagicMock()

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Unsafe path in archive"):
            detect_changes_service._safe_extract(mock_tar, tmp_path)

        # Extract should not have been called
        mock_tar.extract.assert_not_called()

    def test_safe_extract_rejects_symlink_traversal(
        self, detect_changes_service, tmp_path
    ):
        """Test that symlink-based traversal is rejected."""
        mock_tar = MagicMock(spec=tarfile.TarFile)

        # Create mock member that tries to escape via relative path
        member = Mock()
        member.name = "subdir/../../outside/file.txt"

        mock_tar.__iter__ = Mock(return_value=iter([member]))
        mock_tar.extract = MagicMock()

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Unsafe path in archive"):
            detect_changes_service._safe_extract(mock_tar, tmp_path)

        # Extract should not have been called
        mock_tar.extract.assert_not_called()

    def test_safe_extract_rejects_mixed_safe_and_unsafe(
        self, detect_changes_service, tmp_path
    ):
        """Test that extraction stops when unsafe path is encountered."""
        mock_tar = MagicMock(spec=tarfile.TarFile)

        # Create mix of safe and unsafe members
        safe_member1 = Mock()
        safe_member1.name = "safe1.txt"
        safe_member1.issym.return_value = False
        safe_member1.islnk.return_value = False
        safe_member1.isfile.return_value = True
        safe_member1.isdir.return_value = False

        unsafe_member = Mock()
        unsafe_member.name = "../../escape.txt"

        safe_member2 = Mock()
        safe_member2.name = "safe2.txt"

        # Unsafe member is in the middle
        mock_tar.__iter__ = Mock(
            return_value=iter([safe_member1, unsafe_member, safe_member2])
        )
        mock_tar.extract = MagicMock()

        # Should raise RuntimeError when hitting unsafe path
        with pytest.raises(RuntimeError, match="Unsafe path in archive"):
            detect_changes_service._safe_extract(mock_tar, tmp_path)

        # Only the first safe member should have been extracted
        assert mock_tar.extract.call_count == 1
        mock_tar.extract.assert_called_once_with(safe_member1, tmp_path)

    def test_safe_extract_handles_dot_segments(self, detect_changes_service, tmp_path):
        """Test that paths with dot segments that stay inside base are allowed."""
        mock_tar = MagicMock(spec=tarfile.TarFile)

        # Create mock member with dot segments but stays inside base
        member = Mock()
        member.name = "subdir/../otherdir/file.txt"  # Resolves to otherdir/file.txt
        member.issym.return_value = False
        member.islnk.return_value = False
        member.isfile.return_value = True
        member.isdir.return_value = False

        mock_tar.__iter__ = Mock(return_value=iter([member]))
        mock_tar.extract = MagicMock()

        # This should work because the resolved path (otherdir/file.txt) is still under tmp_path
        # The security check correctly allows it
        detect_changes_service._safe_extract(mock_tar, tmp_path)

        # Verify the member was extracted
        mock_tar.extract.assert_called_once_with(member, tmp_path)
