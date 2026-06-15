"""Unit tests for logging functionality."""

import logging
import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from coregen.common.logger import Logger


@pytest.fixture
def reset_logger() -> Generator[None, None, None]:
    """Reset logger state between tests."""
    Logger._global_level = Logger.NORMAL
    Logger._global_verbosity = "normal"
    Logger.global_level_set = False
    Logger._output_format = None
    yield
    # Clean up after tests
    logging.getLogger().setLevel(logging.WARNING)


@pytest.fixture
def mock_console() -> Any:
    """Mock Rich Console instance.

    NOTE: This fixture intentionally shadows the root mock_console fixture
    because Logger tests require specific patching of rich.console.Console
    and coregen.common.console.Console methods, not just a simple MagicMock.
    """
    # Create a mock console instance
    console = MagicMock()

    # Mock the rich.console.Console class to return our mock console
    with patch("rich.console.Console", return_value=console):
        # Directly patch Console.get_log_console and Console.get_user_console
        with patch(
            "coregen.common.console.Console.get_log_console", return_value=console
        ):
            with patch(
                "coregen.common.console.Console.get_user_console", return_value=console
            ):
                # Also patch RichHandler to avoid real console initialization
                with patch("rich.logging.RichHandler"):
                    yield console


def test_logger_initialization(mock_console):
    """Test logger initialization and name detection."""
    # Test explicit name
    logger = Logger("test_logger")
    assert logger._logger.name == "test_logger"

    # Test automatic name detection
    class TestClass:
        def __init__(self):
            self.logger = Logger()

    test_instance = TestClass()
    assert test_instance.logger._logger.name == "TestClass"


def test_log_levels(mock_console, reset_logger):
    """Test different log level behaviors."""
    # Set up direct handler for reliable testing
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Create our logger
        logger = Logger("test")

        # Replace the internal logger with our mock
        logger._logger = mock_logger

        # Test each level
        levels = [
            (logging.DEBUG, "debug"),
            (logging.INFO, "info"),
            (logging.WARNING, "warning"),
            (logging.ERROR, "error"),
            (logging.CRITICAL, "critical"),
        ]

        for level, method_name in levels:
            message = f"Test {method_name} message"
            getattr(logger, method_name)(message)

            # Check if the corresponding logging method was called
            mock_method = getattr(mock_logger, method_name)
            mock_method.assert_called_once()
            assert message in str(mock_method.call_args)
            mock_method.reset_mock()


def test_environment_override(mock_console):
    """Test environment variable override of log level."""
    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
        Logger._check_environment()
        assert Logger._global_level == logging.DEBUG
        assert Logger._global_verbosity == "env-debug"
        assert Logger.global_level_set is True


def test_logger_configuration(mock_console, reset_logger):
    """Test logger configuration methods."""
    # Use direct mocking of the underlying logger
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Test verbose mode
        with patch(
            "coregen.common.console.Console.setup_for_logger"
        ) as mock_console_setup:
            Logger.configure(verbose=True)
            # Verify Console.setup_for_logger was called with no_color parameter
            # Logger doesn't pass verbose to Console anymore
            mock_console_setup.assert_called_once()
            call_kwargs = mock_console_setup.call_args.kwargs
            assert "no_color" in call_kwargs
            assert call_kwargs["no_color"] is False

        logger = Logger("test")
        logger._logger = mock_logger

        # Test debug call in verbose mode
        logger.debug("Debug message")
        mock_logger.debug.assert_called_once()
        mock_logger.debug.reset_mock()

        # Test quiet mode
        # Logger.configure() doesn't pass quiet to Console anymore
        # It only configures the logger's level, not the console's quiet mode
        Logger.configure(quiet=True)

        # Test info call in quiet mode
        logger.info("Info message")
        mock_logger.info.assert_called_once()
        mock_logger.info.reset_mock()

        # Error messages should work in any mode
        logger.error("Error message")
        mock_logger.error.assert_called_once()


def test_global_level_setting(mock_console, reset_logger):
    """Test global log level setting."""
    Logger.set_global_level("verbose")
    assert Logger._global_level == Logger.VERBOSE

    Logger.set_global_level("quiet")
    assert Logger._global_level == Logger.QUIET

    Logger.set_global_level("normal")
    assert Logger._global_level == Logger.NORMAL


def test_output_format(mock_console, reset_logger):
    """Test output format handling."""
    # Direct mocking approach
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        logger = Logger("test")
        logger._logger = mock_logger

        # Test with different output formats
        formats = [None, "text", "json", "yaml"]
        for fmt in formats:
            # Verify the class method works
            Logger.set_output_format(fmt)
            assert Logger._output_format == (fmt.lower() if fmt else None)

            # Make sure logging still works with different formats
            logger.info("Test message")
            mock_logger.info.assert_called_once()
            mock_logger.info.reset_mock()


def test_color_handling(mock_console, reset_logger):
    """Test color handling settings."""
    # For testing color settings, patch both the getter and setter
    with patch("coregen.common.console.Console.setup_for_logger") as mock_setup:
        with patch("coregen.common.console.Console.get_no_color", return_value=False):
            Logger.set_global_no_color(False)
            # Verify Console.setup_for_logger was called correctly
            mock_setup.assert_called_with(no_color=False)
            assert not Logger.get_global_no_color()

    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        logger = Logger("test")
        logger._logger = mock_logger

        # Test color enabled logging works
        logger.info("Test message")
        mock_logger.info.assert_called_once()
        mock_logger.info.reset_mock()

    # Test with colors disabled
    with patch("coregen.common.console.Console.setup_for_logger") as mock_setup:
        with patch("coregen.common.console.Console.get_no_color", return_value=True):
            Logger.set_global_no_color(True)
            # Verify Console.setup_for_logger was called correctly
            mock_setup.assert_called_with(no_color=True)
            assert Logger.get_global_no_color()


def test_message_formatting(mock_console, reset_logger):
    """Test message formatting in different contexts."""
    # Mock the underlying logger
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        logger = Logger("test")
        logger._logger = mock_logger

        # Test with different message types
        messages = [
            "Simple message",
            "Error: This is an error",
            "Warning: This is a warning",
            {"key": "value"},  # Dictionary should be converted to string
            None,  # None should be handled gracefully
        ]

        for msg in messages:
            logger.info(msg)
            mock_logger.info.assert_called_once()

            # Check the message was formatted correctly
            call_args = mock_logger.info.call_args[0][0]

            if msg is None:
                assert call_args == "None"
            elif isinstance(msg, dict):
                assert str(msg) in call_args
            else:
                assert str(msg) in call_args

            mock_logger.info.reset_mock()


def test_logger_inheritance(mock_console, reset_logger):
    """Test logger hierarchy and inheritance."""
    parent_logger = Logger("parent")
    child_logger = Logger("parent.child")

    # Child should inherit parent's level
    parent_logger.set_level(logging.ERROR)
    child_logger.info("Info message")
    mock_console.print.assert_not_called()

    child_logger.error("Error message")
    mock_console.print.assert_called()


def test_exception_logging(mock_console, reset_logger):
    """Test exception logging with traceback."""
    logger = Logger("test")

    try:
        raise ValueError("Test error")
    except Exception:
        # exc_info will be processed by the Rich handler
        logger.error("An error occurred", exc_info=True)

    # The error (with traceback) must reach the console handler
    mock_console.print.assert_called()


def test_invalid_log_level_handling(mock_console):
    """Test handling of invalid log level in environment variable."""
    with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
        Logger._check_environment()
        # Should fall back to default level
        assert Logger._global_level == Logger.NORMAL
