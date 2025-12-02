"""Tests for Console.header() method."""

from collections.abc import Generator
from unittest.mock import patch

import pytest

from coregen.common.console import Console


class TestConsoleHeader:
    """Test the Console.header() method."""

    @pytest.fixture(autouse=True)
    def reset_console(self) -> Generator[None, None, None]:
        """Reset console state before each test."""
        # Reset class attributes to default state
        Console.quiet_mode = False
        Console._no_color = False
        yield
        # Clean up after test
        Console.quiet_mode = False
        Console._no_color = False

    def test_header_basic(self, capsys):
        """Test basic header output."""
        Console.setup(no_color=True, quiet=False)

        # Call header
        Console.header("Test Header")

        # Check captured output
        captured = capsys.readouterr()
        assert "Test Header" in captured.out

    def test_header_with_empty_string(self, capsys):
        """Test header with empty string."""
        Console.setup(no_color=True, quiet=False)

        Console.header("")

        # Empty string results in empty formatted_message, so nothing is printed
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_header_with_special_characters(self, capsys):
        """Test header with special characters."""
        Console.setup(no_color=True, quiet=False)

        Console.header("Header with special: !@#$%^&*()")

        captured = capsys.readouterr()
        assert "Header with special: !@#$%^&*()" in captured.out

    def test_header_with_unicode(self, capsys):
        """Test header with unicode characters."""
        Console.setup(no_color=True, quiet=False)

        Console.header("Unicode Header: 📊 ✅ ❌")

        captured = capsys.readouterr()
        assert "Unicode Header: 📊 ✅ ❌" in captured.out

    def test_header_ignores_quiet_mode(self, capsys):
        """Test that header ignores quiet mode (always prints)."""
        Console.setup(no_color=True, quiet=True)

        # Call header in quiet mode
        Console.header("Should appear anyway")

        # Headers always print regardless of quiet mode
        captured = capsys.readouterr()
        assert "Should appear anyway" in captured.out

    def test_header_multiple_calls(self, capsys):
        """Test multiple header calls."""
        Console.setup(no_color=True, quiet=False)

        # Call header multiple times
        Console.header("First Header")
        Console.header("Second Header")
        Console.header("Third Header")

        captured = capsys.readouterr()
        assert "First Header" in captured.out
        assert "Second Header" in captured.out
        assert "Third Header" in captured.out
        # Headers should have newlines before them
        assert captured.out.count("\n") >= 3

    def test_header_with_check_pattern_style(self, capsys):
        """Test header usage similar to check-pattern command."""
        Console.setup(no_color=True, quiet=False)

        # Simulate check-pattern style headers
        Console.header("Pattern Matching Summary:")
        Console.header("Applied Filters:")
        Console.header("Matched Contexts:")
        Console.header("Matched Components:")

        captured = capsys.readouterr()
        assert "Pattern Matching Summary:" in captured.out
        assert "Applied Filters:" in captured.out
        assert "Matched Contexts:" in captured.out
        assert "Matched Components:" in captured.out

    @patch("builtins.print")
    def test_header_uses_builtin_print(self, mock_print):
        """Test that header uses builtin print, not Rich console."""
        Console.setup(no_color=True, quiet=False)
        Console.header("Test Message")

        # Verify builtin print was called with formatted message
        mock_print.assert_called_once_with("\nTest Message")

    def test_header_formatting_with_newline(self, capsys):
        """Test that headers add newline prefix for spacing."""
        Console.setup(no_color=True, quiet=False)

        # First print something
        Console.info("Some info")

        # Then header
        Console.header("Header After Info")

        captured = capsys.readouterr()
        # Info should go to stderr (diagnostic), header should go to stdout (data)
        assert "Some info" in captured.err
        assert "\nHeader After Info" in captured.out
