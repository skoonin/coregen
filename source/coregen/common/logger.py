"""Logging utility that provides hierarchical logging with different verbosity levels."""

import inspect
import logging
import os
from typing import Any

from rich.logging import RichHandler

from coregen.common.console import Console


class Logger:
    """
    A customizable logging utility that integrates Python's built-in logging with Rich console output.

    This class provides:
    - Automatic name detection from calling context
    - Rich console integration with consistent styling
    - Configurable verbosity levels (quiet, normal, verbose)
    - Message formatting support
    - Environment variable support via LOG_LEVEL

    Class Attributes:
        QUIET (int): Shows only errors (logging.ERROR)
        NORMAL (int): Shows warnings and above (logging.WARNING)
        VERBOSE (int): Shows all messages (logging.DEBUG)

    Args:
        name (str, optional): Logger name. If None, automatically detected from calling context

    Example:
        >>> logger = Logger("my_module")
        >>> logger.debug("Starting process")  # Only shown with LOG_LEVEL=DEBUG
        >>> logger.warning("Resource usage high")  # Shown in normal and verbose modes
    """

    # Define standard logging levels
    QUIET = logging.ERROR  # Show only errors (40)
    NORMAL = logging.WARNING  # Show warnings and above (30)
    VERBOSE = logging.DEBUG  # Show everything (10)

    # Class variables for global state
    _global_level = NORMAL
    _global_verbosity = "normal"
    global_level_set = False
    _output_format = None

    # Map string log levels to numeric values
    _LOG_LEVEL_MAP = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        # Add aliases for convenience
        "VERBOSE": logging.DEBUG,
        "WARN": logging.WARNING,
    }

    @classmethod
    def _check_environment(cls) -> None:
        """Check environment variables for logging configuration."""
        # Get LOG_LEVEL from environment, with CG_LOG_LEVEL as fallback
        # If not set, configure logger to be completely silent by setting a very high level
        env_level = os.environ.get("CG_LOG_LEVEL", os.environ.get("LOG_LEVEL", None))

        if env_level:
            # Convert to uppercase for case-insensitive comparison
            env_level = env_level.upper()

            # Check if it's a valid level
            if env_level in cls._LOG_LEVEL_MAP:
                # Set the global level
                cls._global_level = cls._LOG_LEVEL_MAP[env_level]
                cls._global_verbosity = "env-" + env_level.lower()
                cls.global_level_set = True

                # Initialize root logger with this level
                logging.basicConfig(
                    level=cls._global_level,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    handlers=[RichHandler(console=Console.get_log_console())],
                )

                # Print notification about environment override
                Console.warning(
                    f"Logger level set to {env_level} from environment variable"
                )
            else:
                Console.warning(
                    f"Invalid LOG_LEVEL '{env_level}'. Using default level."
                )
                # Fall back to default NORMAL level
                cls._global_level = cls.NORMAL
        else:
            # No LOG_LEVEL is set - make loggers completely silent by using a very high level
            cls._global_level = 100  # Higher than CRITICAL (50)
            cls._global_verbosity = "silent"
            cls.global_level_set = True

            # Initialize root logger to be silent
            logging.basicConfig(
                level=cls._global_level,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=[RichHandler(console=Console.get_log_console())],
            )

    def __init__(self, name: str = None):
        """Initialize logger with name and Rich console integration.

        Args:
            name: Logger name. If None, automatically detected from calling context.
        """
        # Auto-detect name from calling context if not provided
        if name is None:
            frame = inspect.currentframe().f_back
            if "self" in frame.f_locals:
                name = frame.f_locals["self"].__class__.__name__
            else:
                name = frame.f_globals["__name__"].split(".")[-1]

        # Get or create logger - logging.getLogger handles singleton behavior
        self._logger = logging.getLogger(name)
        self._logger.propagate = False

        # Clear any existing handlers
        if self._logger.hasHandlers():
            self._logger.handlers.clear()

        # Setup Rich handler with Console integration
        console_handler = RichHandler(
            console=Console.get_log_console(),
            rich_tracebacks=True,
            show_time=True,
            show_path=False,
            markup=False,
            omit_repeated_times=False,
            tracebacks_word_wrap=True,
            tracebacks_show_locals=False,  # change to true for debugging
            enable_link_path=True,
            show_level=True,
        )

        console_handler.setFormatter(logging.Formatter("[ %(name)s ] %(message)s"))
        self._logger.addHandler(console_handler)
        self._logger.setLevel(self._global_level)

    def set_level(self, level: int) -> None:
        """Set the logging level for this logger instance."""
        self._logger.setLevel(level)
        for handler in self._logger.handlers:
            handler.setLevel(level)

    def get_logger(self) -> logging.Logger:
        """Get the underlying logger instance."""
        return self._logger

    def __getattr__(self, name: str) -> Any:
        """Forward any unknown attributes to the underlying logger."""
        return getattr(self._logger, name)

    def _format_message(
        self,
        message: str,
        output_format: str | None = None,
        allowed_outputs: list[str] | None = None,
    ) -> str:
        """Format the message according to output format settings."""
        # For logger messages, we should always return plain text
        # Log messages should never be formatted as JSON/YAML even if output_format is set
        return str(message)

    def debug(
        self,
        message: str,
        output_format: str | None = None,
        allowed_outputs: list[str] | None = None,
    ) -> None:
        """Log a debug message. Only shown with LOG_LEVEL=DEBUG."""
        self._logger.debug(
            self._format_message(message, output_format, allowed_outputs)
        )

    def info(
        self,
        message: str,
        output_format: str | None = None,
        allowed_outputs: list[str] | None = None,
    ) -> None:
        """Log an info message. Only shown when LOG_LEVEL=INFO or lower."""
        self._logger.info(self._format_message(message, output_format, allowed_outputs))

    def warning(
        self,
        message: str,
        output_format: str | None = None,
        allowed_outputs: list[str] | None = None,
    ) -> None:
        """Log a warning message. Shown in normal and verbose modes."""
        self._logger.warning(
            self._format_message(message, output_format, allowed_outputs)
        )

    def error(
        self,
        message: str,
        output_format: str | None = None,
        allowed_outputs: list[str] | None = None,
        exc_info: bool = False,
    ) -> None:
        """Log an error message."""
        self._logger.error(
            self._format_message(message, output_format, allowed_outputs),
            exc_info=exc_info,
        )

    def critical(
        self,
        message: str,
        output_format: str | None = None,
        allowed_outputs: list[str] | None = None,
    ) -> None:
        """Log a critical message. Always shown."""
        self._logger.critical(
            self._format_message(message, output_format, allowed_outputs)
        )

    @classmethod
    def configure(
        cls,
        verbose: bool = False,
        quiet: bool = False,
        no_color: bool = False,
        output_format: str | None = None,
    ) -> None:
        """Configure all loggers with new settings.

        Args:
            verbose: Enable verbose output for Console (not affecting Logger level)
            quiet: Enable quiet mode
            no_color: Disable colored output
            output_format: Format for output messages
        """
        # Only set logger verbosity level if not already set by environment
        if not cls.global_level_set:
            # Use normal Logger level if nothing else specified
            verbosity = "quiet" if quiet else "normal"
            level_map = {"quiet": cls.QUIET, "normal": cls.NORMAL}
            cls._global_level = level_map.get(verbosity.lower(), cls.NORMAL)
            cls._global_verbosity = verbosity

            # Update all existing loggers with this level
            for logger_name in logging.Logger.manager.loggerDict:
                logger = logging.getLogger(logger_name)
                logger.setLevel(cls._global_level)
                for handler in logger.handlers:
                    handler.setLevel(cls._global_level)

        # Update Console settings for logger output only
        # Logger only needs to respect no_color setting for readable output
        # User console verbosity is controlled separately by CLI
        Console.setup_for_logger(no_color=no_color)

    @classmethod
    def set_global_level(cls, verbosity: str) -> None:
        """Set the logging level globally without affecting Console verbosity."""
        cls._global_verbosity = verbosity
        level_map = {"quiet": cls.QUIET, "normal": cls.NORMAL, "verbose": cls.VERBOSE}
        cls._global_level = level_map.get(verbosity.lower(), cls.NORMAL)
        cls.global_level_set = True

        # Update all existing loggers
        for logger_name in logging.Logger.manager.loggerDict:
            logger = logging.getLogger(logger_name)
            logger.setLevel(cls._global_level)
            for handler in logger.handlers:
                handler.setLevel(cls._global_level)

    @classmethod
    def set_output_format(cls, format_name: str | None) -> None:
        """Set the program-wide output format."""
        cls._output_format = format_name.lower() if format_name else None

    @classmethod
    def set_global_no_color(cls, no_color: bool) -> None:
        """Set whether to disable colored output globally."""
        # Delegate color handling to Console for logger output only
        Console.setup_for_logger(no_color=no_color)

    @classmethod
    def get_global_no_color(cls) -> bool:
        """Get the global no_color setting."""
        return Console.get_no_color()


# Call _check_environment when module is imported
Logger._check_environment()
