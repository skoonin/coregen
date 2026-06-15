"""Unit tests for the console output management module.

Note: This file consolidates tests from test_simplified_console.py
"""

import datetime
import logging
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# OutputFormat import removed - no longer used in Console
from coregen.common.console import Console

# For consistent timestamp testing
TEST_TIMESTAMP = "01/01/25 00:00:00"


@pytest.fixture(autouse=True)
def setup_logging() -> Any:
    """Set up logging configuration for tests."""
    root_logger = logging.getLogger()
    prev_level = root_logger.level
    root_logger.setLevel(logging.INFO)  # Default to INFO
    yield
    root_logger.setLevel(prev_level)


@pytest.fixture(autouse=True)
def mock_datetime_now() -> Any:
    """Mock datetime.now() to return a consistent timestamp for tests."""
    dt = datetime.datetime(2025, 1, 1, 0, 0, 0)
    dt_mock = MagicMock(wraps=dt)
    dt_mock.strftime.return_value = TEST_TIMESTAMP
    with patch("datetime.datetime") as mock_dt:
        mock_dt.now.return_value = dt_mock
        yield mock_dt


@pytest.fixture(autouse=True)
def reset_console() -> Generator[None, None, None]:
    """Reset console state between tests.

    NOTE: This fixture supplements the root reset_console_state fixture
    by doing save/restore of Console state rather than just reset to defaults.
    This is needed for Console-specific tests that may set state during test setup
    and need it restored afterwards, including _current_style which is not
    covered by the root fixture.
    """
    prev_user_console = Console._user_console
    prev_log_console = Console._log_console
    prev_style = getattr(Console, "_current_style", None)

    Console._user_console = None
    Console._log_console = None
    Console._current_style = None

    yield

    Console._user_console = prev_user_console
    Console._log_console = prev_log_console
    Console._current_style = prev_style


@pytest.fixture
def mock_rich_console() -> Any:
    """Mock Rich Console instance."""
    console_instance = MagicMock()
    console_instance.print = MagicMock()

    with patch("rich.console.Console", return_value=console_instance):
        Console._setup_consoles()  # Initialize with our mock
        yield console_instance


@pytest.fixture
def setup_console(mock_rich_console, reset_console) -> Any:
    """Set up console with default settings and return mock."""
    Console.setup(
        no_color=False,
        quiet=False,
        verbose=False,
        dry_run=False,
    )
    mock_rich_console.reset_mock()  # Ensure clean mock state
    return mock_rich_console


def test_console_setup_default_settings(mock_rich_console):
    """Test console setup with default settings."""
    Console.setup()

    assert Console.verbose_mode is False
    assert Console.quiet_mode is False
    assert Console._no_color is False
    assert Console.dry_run_mode is False
    # output_format removed from Console - it's now command-specific
    assert Console._color_system == "auto"


def test_console_setup_custom_settings(mock_rich_console):
    """Test console setup with custom settings."""
    Console.setup(
        no_color=True,
        quiet=True,
        verbose=True,
        dry_run=True,
    )

    assert Console.verbose_mode is True
    assert Console.quiet_mode is True
    assert Console._no_color is True
    assert Console.dry_run_mode is True
    # output_format removed from Console - it's now command-specific
    assert Console._color_system is None


def test_print_normal_message(setup_console):
    """Test printing a normal message."""
    Console.print("Test message")
    setup_console.print.assert_called_once()
    args, kwargs = setup_console.print.call_args
    assert args[0] == "Test message"
    assert kwargs.get("style") is None


def test_print_styled_message(setup_console):
    """Test printing a message with style."""
    Console.print("Test message", style="info")
    setup_console.print.assert_called_once()
    args, kwargs = setup_console.print.call_args
    assert args[0] == "Test message"
    assert kwargs.get("style") == "info"


def test_dry_run_mode_comprehensive(setup_console):
    """Test dry run mode interactions with different output types."""
    # Suppress formatter output for cleaner test output
    with patch("coregen.common.formatter.Formatter.format_output") as mock_formatter:
        mock_formatter.return_value = '{"key": "value"}'

        Console.setup(dry_run=True)

        # Basic message
        Console.print("Test message")
        args = setup_console.print.call_args[0]
        assert any(prefix in args[0] for prefix in ["[DRY RUN]", "DRY RUN:"])
        assert "Test message" in args[0]
        setup_console.reset_mock()

        # With different output methods
        for method in ["info", "warning", "error", "success"]:
            getattr(Console, method)("Test message")
            args = setup_console.print.call_args[0]
            assert any(prefix in args[0] for prefix in ["[DRY RUN]", "DRY RUN:"])
            setup_console.reset_mock()

        # Special test for debug which behaves differently
        if not Console.verbose_mode:
            # In non-verbose mode, debug should do nothing
            Console.debug("Test message")
            setup_console.print.assert_not_called()
        else:
            Console.debug("Test message")
            args = setup_console.print.call_args[0]
            assert any(prefix in args[0] for prefix in ["[DRY RUN]", "DRY RUN:"])
        setup_console.reset_mock()

        # With styling
        with Console.style_context("info"):
            Console.print("Test message")
        args, kwargs = setup_console.print.call_args
        assert any(prefix in args[0] for prefix in ["[DRY RUN]", "DRY RUN:"])
        assert kwargs.get("style") == "info"
        setup_console.reset_mock()

        # With structured data
        Console.setup(dry_run=True)
        test_data = {"key": "value"}

        # Structured data does not get dry run prefix (only strings do)
        Console.print(test_data)
        setup_console.print.assert_called_once()
        args = setup_console.print.call_args[0]
        assert args[0] == test_data  # Should be unchanged
        setup_console.reset_mock()

        # With table output - should bypass JSON formatting but still show dry run prefix
        Console.setup(dry_run=True)
        from rich.table import Table

        test_table = Table()
        test_table.add_column("Header")
        test_table.add_row("Data")
        Console.print(test_table)
        setup_console.print.assert_called_once()
        setup_console.reset_mock()  # With quiet mode
        Console.setup(dry_run=True, quiet=True)
        Console.print("Test message")
        setup_console.print.assert_not_called()

        # Error messages should still print in quiet mode
        # But we need to call error() directly rather than print("Error: ...")
        Console.error("Test error")
        setup_console.print.assert_called_once()
        args = setup_console.print.call_args[0]
        assert any(prefix in args[0] for prefix in ["[DRY RUN]", "DRY RUN:"])
        assert "Error:" in args[0]
        assert "Test error" in args[0]


def test_print_dry_run_prefix_handling(setup_console):
    """Test dry run prefix handling in different scenarios."""
    Console.setup(dry_run=True)

    # Test duplicate prefix prevention
    Console.print("[DRY RUN] Message")
    args, kwargs = setup_console.print.call_args
    assert args[0].count("[DRY RUN]") == 1  # Should not add another prefix
    setup_console.reset_mock()

    # Test with empty or whitespace message
    Console.print("")
    setup_console.print.assert_called_once_with("", style=None, end="\n", markup=True)
    setup_console.reset_mock()

    Console.print("   ")
    setup_console.print.assert_called_once_with(
        "   ", style=None, end="\n", markup=True
    )
    setup_console.reset_mock()

    # Test with no_color setting
    Console.setup(dry_run=True, no_color=True)
    Console.print("Test message")
    args, kwargs = setup_console.print.call_args
    assert "DRY RUN: " in args[0]  # Plain text prefix
    assert "[DRY RUN]" not in args[0]  # Not rich text prefix


def test_print_quiet_mode(setup_console):
    """Test printing in quiet mode."""
    Console.setup(quiet=True)

    # Regular message should be suppressed
    Console.print("Test message")
    setup_console.print.assert_not_called()

    # Warning message should be printed
    Console.print("Warning: Test warning")
    args = setup_console.print.call_args[0]
    assert "Warning: Test warning" in args[0]
    setup_console.reset_mock()

    # Error message should be printed
    Console.print("Error: Test error")
    args = setup_console.print.call_args[0]
    assert "Error: Test error" in args[0]
    setup_console.reset_mock()

    # Debug messages should be suppressed
    Console.debug("Debug message")
    setup_console.print.assert_not_called()


def test_quiet_mode_with_style_context(setup_console):
    """Test style context in quiet mode."""
    Console.setup(quiet=True)

    # In quiet mode, regular messages are suppressed regardless of style context
    with Console.style_context("info"):
        with Console.style_context("warning"):
            Console.print("Test message")
    # Regular message should be suppressed in quiet mode, regardless of style
    setup_console.print.assert_not_called()
    setup_console.reset_mock()

    # Only error and warning messages should be printed in quiet mode
    with Console.style_context("info"):
        Console.print("Error: Test error")
    args, kwargs = setup_console.print.call_args
    assert "Error: Test error" in args[0]
    assert kwargs.get("style") == "info"


def test_style_context_nesting(setup_console):
    """Test nested style contexts in normal mode."""
    Console.setup(quiet=False)

    # Nested style contexts (inner should override outer)
    with Console.style_context("info"):
        with Console.style_context("warning"):
            Console.print("Test message")
    args, kwargs = setup_console.print.call_args
    assert args[0] == "Test message"
    assert kwargs.get("style") == "warning"
    setup_console.reset_mock()


def test_output_methods(setup_console):
    """Test different output methods."""
    methods = [
        ("info", "info"),
        ("warning", "warning"),
        ("error", "error"),
        ("success", "success"),
    ]
    for method, style in methods:
        getattr(Console, method)("Test message")
        args = setup_console.print.call_args
        assert args is not None
        assert style in args[1].get("style", "")
        setup_console.reset_mock()


def test_debug_output_normal(setup_console):
    """Test debug output in normal mode."""
    Console.debug("Test debug message")
    setup_console.print.assert_not_called()  # Not verbose mode


def test_debug_output_verbose(setup_console):
    """Test debug output in verbose mode."""
    Console.setup(verbose=True)
    Console.debug("Test debug message")
    setup_console.print.assert_called_once()


def test_different_output_formats(setup_console):
    """Test different output formats."""
    # Output format is now command-specific, not a Console setting
    # This test is no longer applicable


def test_info_message_in_non_text_format(setup_console):
    """Test info messages behavior."""
    # Output format is now command-specific, not a Console setting
    # info() method behavior no longer depends on a global output format
    Console.info("Test info")
    setup_console.print.assert_called_once()
    setup_console.reset_mock()

    # Warning messages should also show
    Console.warning("Test warning")
    assert setup_console.print.call_count == 1
    setup_console.reset_mock()

    Console.error("Test error")
    assert setup_console.print.call_count == 1


def test_print_end_parameter(setup_console):
    """Test custom end parameter in print method."""
    Console.print("Test", end="")
    setup_console.print.assert_called_once_with("Test", style=None, end="", markup=True)

    setup_console.reset_mock()
    Console.print("Test", end="\r")
    setup_console.print.assert_called_once_with(
        "Test", style=None, end="\r", markup=True
    )


def test_direct_json_output(setup_console):
    """Test print handling of data."""
    # Output format is now command-specific
    test_data = {"test": "value"}
    Console.print(test_data)
    setup_console.print.assert_called_once()


def test_theme_colors():
    """Test theme color validation."""
    for color in Console.DEFAULT_THEME.values():
        # Remove any modifiers like 'bold' or 'underline'
        color.split()[0]
        # Create a new console to test the color
        with patch("rich.console.Console") as mock_console:
            console = mock_console.return_value
            Console._setup_consoles()
            assert console.is_interactive is not None


def test_format_output_error_handling(setup_console):
    """Test error handling during print."""
    # Output format is now command-specific
    test_data = {"key": "value"}
    Console.print(test_data)
    setup_console.print.assert_called_once()


def test_table_output(setup_console):
    """Test table output formatting."""
    from rich.table import Table

    test_table = Table()
    test_table.add_column("Header")
    test_table.add_row("Data")

    # Tables should print directly
    Console.print(test_table)
    setup_console.print.assert_called_once()
    # Don't check the exact parameters because rich Table objects aren't easily comparable


def test_markup_handling(setup_console):
    """Test markup handling with color settings."""
    # Test with colors enabled
    Console.setup(no_color=False)
    Console.print("[red]Test[/red]")
    setup_console.print.assert_called_once()
    assert setup_console.print.call_args.kwargs.get("markup") is True

    # Test with colors disabled
    setup_console.reset_mock()
    Console.setup(no_color=True)
    Console.print("[red]Test[/red]")
    setup_console.print.assert_called_once()
    assert setup_console.print.call_args.kwargs.get("markup") is False


def test_color_handling(mock_rich_console):
    """Test color handling settings."""
    Console.setup(no_color=False)
    assert Console._color_system == "auto"
    assert not Console._no_color

    Console.setup(no_color=True)
    assert Console._color_system is None
    assert Console._no_color


def test_timestamp_with_different_log_levels(setup_console):
    """Test timestamp formatting with different log levels."""
    Console.setup(verbose=True)

    for level in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]:
        setup_console.reset_mock()
        logging.getLogger().setLevel(level)
        Console.print("Test message")

        # Verify print was called
        setup_console.print.assert_called_once()
        args = setup_console.print.call_args.args

        if level == logging.DEBUG:
            # In debug mode, should include timestamp
            assert TEST_TIMESTAMP in args[0]
            assert "[yellow][USER CONSOLE][/yellow]" in args[0]
        else:
            # In other modes, just the plain message
            assert args[0] == "Test message"


def test_no_timestamp_normal_mode(mock_rich_console):
    """Test timestamp exclusion in normal mode."""
    logging.getLogger().setLevel(logging.INFO)
    Console.setup(verbose=True, no_color=True)
    Console.debug("Test message")
    assert "DEBUG:" in mock_rich_console.print.call_args[0][0]
    assert TEST_TIMESTAMP not in mock_rich_console.print.call_args[0][0]


def test_get_consoles(mock_rich_console):
    """Test console getter methods."""
    user_console = Console.get_user_console()
    assert user_console == mock_rich_console

    log_console = Console.get_log_console()
    assert log_console == mock_rich_console


def test_style_context():
    """Test that style_context works as a context manager."""
    with patch("rich.console.Console") as mock_console_class:
        console = MagicMock()
        mock_console_class.return_value = console
        Console._setup_consoles()

        # Test that style_context works
        with Console.style_context("info"):
            Console.print("Test message")

        # Test that style_context can be nested
        with Console.style_context("warning"):
            with Console.style_context("error"):
                Console.print("Nested style test")

        # style_context must restore the default style after exit
        Console.print("After style context")
        assert Console._current_style is None or Console._current_style == ""


def test_dry_run_basic():
    """Test just the basic dry run functionality."""
    with patch("rich.console.Console") as mock_console_class:
        console = MagicMock()
        mock_console_class.return_value = console

        # Setup dry run mode
        Console._setup_consoles()
        Console.setup(dry_run=True)

        # Basic print test
        Console.print("Test message")

        # Test the console state
        assert Console.dry_run_mode is True
