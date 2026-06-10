"""Console output management using Rich."""

import logging
from collections.abc import Generator
from typing import Any, ContextManager, Literal

import rich.console as rich_console
from rich.theme import Theme

from coregen.cli.enums.enum_output_format import OutputFormat
from coregen.common.formatter import Formatter

logger = logging.getLogger(__name__)

# Alias rich.console to avoid class name conflict


class Console:
    """Centralized console output management using Rich.

    This class provides a singleton interface for managing console output using Rich.
    It maintains separate consoles for user output and logging, with consistent
    styling and configuration across the application.

    Console Configuration:
        - setup_for_user(): Called by CLI to configure user-facing output based on CLI flags
        - setup_for_logger(): Called by Logger to configure developer logging output

    The separation ensures:
        - User console verbosity is controlled by CLI flags (-v, -q)
        - Logger verbosity is controlled by LOG_LEVEL environment variable
        - Both share color settings for consistency

    Available styles are:
        info, warning, error, debug, success
    """

    _user_console = None
    _log_console = None
    verbose_mode = False
    quiet_mode = False
    _no_color = False
    dry_run_mode = False
    # Default output format for internal use only
    _default_output_format = OutputFormat.TEXT
    _color_system: Literal["auto", "standard", "256", "truecolor", "windows"] = "auto"
    # Active output format for the current command
    _active_output_format: OutputFormat | None = None
    # Flag to track if user console has been configured
    _is_user_configured = False

    DEFAULT_THEME = {
        "info": "bright_green",
        "warning": "bright_yellow",
        "error": "red bold",
        "debug": "bright_blue",
        "success": "green bold",
        "header": "cyan bold",
        "highlight": "magenta",
        "dim": "bright_black",
        "command": "bright_cyan",
        "path": "bright_blue underline",
        "dry_run": "bright_blue bold",
    }

    @classmethod
    def setup(
        cls,
        no_color: bool | None = None,
        quiet: bool | None = None,
        verbose: bool | None = None,
        dry_run: bool | None = None,
    ) -> None:
        """Configure console output settings.

        This method updates the console configuration and recreates the console
        instances if necessary. It ensures that all console output maintains
        consistent styling and behavior.

        Args:
            no_color: Force disable colors
            quiet: Enable quiet mode (suppress non-error output)
            verbose: Enable verbose output
            dry_run: Enable dry run mode (prepends [DRY RUN] to messages)
        """
        from coregen.config_model.models.settings import get_settings

        settings = get_settings()
        cli_settings = settings.options.global_options
        use_no_color = no_color if no_color is not None else cli_settings.no_color
        use_quiet = quiet if quiet is not None else cli_settings.quiet
        use_verbose = verbose if verbose is not None else cli_settings.verbose
        use_dry_run = dry_run if dry_run is not None else cli_settings.dry_run

        needs_console_update = (
            cls.verbose_mode != use_verbose
            or cls.quiet_mode != use_quiet
            or cls._no_color != use_no_color
            or cls.dry_run_mode != use_dry_run
        )

        cls.verbose_mode = use_verbose
        cls.quiet_mode = use_quiet
        cls._no_color = use_no_color
        cls.dry_run_mode = use_dry_run
        cls._color_system = None if use_no_color else "auto"

        if needs_console_update:
            cls._setup_consoles()
            logger.debug(
                f"Console settings updated: verbose={verbose}, quiet={quiet}, no_color={no_color}, dry_run={dry_run}"
            )

    @classmethod
    def setup_for_user(
        cls,
        no_color: bool | None = None,
        quiet: bool | None = None,
        verbose: bool | None = None,
        dry_run: bool | None = None,
        force: bool = False,
    ) -> None:
        """Configure console for user-facing output.

        This method should be called by the CLI to configure console settings
        for user-facing output. It sets all console options based on CLI flags.

        Args:
            no_color: Force disable colors
            quiet: Enable quiet mode (suppress non-error output)
            verbose: Enable verbose output (show debug messages)
            dry_run: Enable dry run mode (prepends [DRY RUN] to messages)
            force: Force reconfiguration even if already configured
        """
        if cls._is_user_configured and not force:
            logger.debug("User console already configured, skipping setup")
            return

        cls.setup(no_color=no_color, quiet=quiet, verbose=verbose, dry_run=dry_run)
        cls._is_user_configured = True

    @classmethod
    def setup_for_logger(cls, no_color: bool | None = None) -> None:
        """Configure console for logger output.

        This method should be called by Logger to configure console settings
        for developer logging output. It only updates color settings, as logger
        verbosity is controlled by LOG_LEVEL environment variable, not CLI flags.

        Args:
            no_color: Force disable colors (the only setting that affects logger output)
        """
        if no_color is not None:
            # Only update color settings if explicitly provided
            cls._no_color = no_color
            cls._color_system = None if no_color else "auto"

            # Update the consoles if they already exist
            if cls._user_console is not None or cls._log_console is not None:
                cls._setup_consoles()
                logger.debug(
                    f"Console color settings updated for logger: no_color={no_color}"
                )

    @classmethod
    def _setup_consoles(cls) -> None:
        """Internal method to setup/update console instances.

        Creates or updates the user and logging consoles with current settings.
        The user console is used for general output, while the logging console
        is specifically configured for log messages.
        """
        import sys

        # Detect if output is being piped
        is_piped = not sys.stdout.isatty()

        # Setup user output console with fixed theme
        cls._user_console = rich_console.Console(
            theme=Theme(cls.DEFAULT_THEME),
            force_terminal=None,
            color_system=cls._color_system,
            highlight=not cls._no_color,
            soft_wrap=is_piped,  # Disable hard wrapping when piped
        )

        # Setup logging console
        cls._log_console = rich_console.Console(
            theme=Theme(cls.DEFAULT_THEME),
            stderr=True,
            color_system=cls._color_system,
            highlight=not cls._no_color,
        )

    @classmethod
    def _get_dry_run_prefix(cls) -> str:
        """Get the appropriate dry run prefix based on color settings."""
        return "DRY RUN: " if cls._no_color else "[dark_orange3][DRY RUN][/] "

    @classmethod
    def style_context(cls, style: str) -> ContextManager[None]:
        """Context manager for temporary style changes.

        Args:
            style: Style name from the default theme

        Example:
            with console.style_context("error"):
                console.print("This is an error message")
                console.print("This is also an error message")
        """
        from contextlib import contextmanager

        @contextmanager
        def _style_context() -> Generator[None, None, None]:
            previous_style = getattr(cls, "_current_style", None)
            cls._current_style = style
            try:
                yield
            finally:
                cls._current_style = previous_style

        return _style_context()

    @classmethod
    def _format_with_timestamp_if_debug(cls, message: str, level: str = "DEBUG") -> str:
        """Add timestamp to message if in debug mode."""
        # Check if system-wide debug logging is active
        root_logger_level = logging.getLogger().getEffectiveLevel()
        debug_logging_active = root_logger_level <= logging.DEBUG

        if debug_logging_active:
            import datetime

            timestamp = datetime.datetime.now().strftime("%m/%d/%y %H:%M:%S")

            # Format like logger but with USER CONSOLE tag
            if cls._no_color:
                user_console_tag = "[USER CONSOLE]"
            else:
                # Highlighted yellow tag
                user_console_tag = "[yellow][USER CONSOLE][/yellow]"

            # Use consistent spacing for alignment with logger output
            if level == "DEBUG":
                level_display = "DEBUG    "
            elif level == "INFO":
                level_display = "INFO     "
            elif level == "WARN" or level == "WARNING":
                level_display = "WARNING  "
            elif level == "ERROR":
                level_display = "ERROR    "
            elif level == "PRINT":
                level_display = "PRINT    "
            elif level == "SUCCESS":
                level_display = "SUCCESS  "
            else:
                # Default case - ensure 8 characters
                level_display = f"{level:<8}"

            prefix = f"[{timestamp}] {level_display}{user_console_tag} "

            # Don't add another prefix if the message already has this format
            if message.startswith(f"[{timestamp}]"):
                return message

            return f"{prefix}{message}"
        else:
            # No formatting in normal mode
            return message

    @classmethod
    def print(
        cls,
        message: Any,
        style: str | None = None,
        end: str = "\n",
        output_format: OutputFormat | None = None,
    ) -> None:
        """Print message to console."""
        # In quiet mode, only allow:
        # 1. Warning and Error messages
        # 2. Structured data output (when output_format is explicitly provided)
        if (
            cls.quiet_mode
            and not (
                isinstance(message, str) and message.startswith(("Warning:", "Error:"))
            )
            and output_format is None
        ):
            return

        effective_style = style or getattr(cls, "_current_style", None)
        effective_output_format = output_format or cls._default_output_format

        # Prepend [DRY RUN] for non-empty string messages in dry run mode
        if cls.dry_run_mode and isinstance(message, str) and message.strip():
            if not any(
                prefix in message for prefix in ["[DRY RUN]", "DRY RUN:", "[dry run]"]
            ):
                # Use appropriate prefix based on color settings
                dry_run_prefix = cls._get_dry_run_prefix()
                message = f"{dry_run_prefix}{message}"

        # Format message if needed
        if effective_output_format != OutputFormat.TEXT and not (
            isinstance(message, str)
            and any(
                message.startswith(prefix)
                for prefix in [
                    "DEBUG:",
                    "Info:",
                    "Warning:",
                    "Error:",
                    "[DRY RUN]",
                    "DRY RUN:",
                ]
            )
        ):
            try:
                # Convert enum to proper format string
                format_str = (
                    effective_output_format.name.lower()
                    if hasattr(effective_output_format, "name")
                    else str(effective_output_format).lower()
                )

                formatted_message = Formatter.format_output(message, format_str)

                # For structured formats that need to be piped, print directly to stdout
                if format_str in ["json", "yaml", "matrix"] and isinstance(
                    formatted_message, str
                ):
                    # Always print structured output regardless of quiet mode
                    if (
                        cls.dry_run_mode
                        and isinstance(formatted_message, str)
                        and formatted_message.strip()
                    ):
                        # Use plain prefix without markup for direct printing
                        print(f"DRY RUN: {formatted_message}", end=end)
                    else:
                        print(formatted_message, end=end)
                    return

                # Otherwise use Rich console (for TABLE format and other rich content)
                cls.get_user_console().print(formatted_message, end=end)
                return

            except Exception as e:
                logger.error(f"Error formatting output: {e}")
                if not isinstance(message, str):
                    message = str(message)

        # Format with timestamp if in debug mode - use PRINT as the level
        if isinstance(message, str):
            message = cls._format_with_timestamp_if_debug(message, "PRINT")

        # Print message with style for text-based content
        if not cls.quiet_mode or (
            isinstance(message, str)
            and any(
                message.startswith(prefix)
                for prefix in ["Warning:", "Error:", "[DRY RUN]", "DRY RUN:"]
            )
        ):
            # Use markup directly in the printed message
            cls.get_user_console().print(
                message, style=effective_style, end=end, markup=not cls._no_color
            )

    @classmethod
    def info(cls, message: str) -> None:
        """Print info message (only in text output)."""

        # Info messages are text-only, skip if an explicit format was requested
        # This is handled by the command level now
        if not cls.quiet_mode:
            # Skip empty lines or whitespace-only lines
            if (
                cls.dry_run_mode
                and message.strip()
                and not any(
                    prefix in message
                    for prefix in ["[DRY RUN]", "DRY RUN:", "[dry run]"]
                )
            ):
                message = f"{cls._get_dry_run_prefix()}{message}"

            # Format with timestamp if in debug mode
            message = cls._format_with_timestamp_if_debug(message, "INFO")

            cls.get_log_console().print(message, style="info", markup=not cls._no_color)

    @classmethod
    def warning(cls, message: str) -> None:
        """Print warning message."""
        prefix = "Warning: "
        if (
            cls.dry_run_mode
            and message.strip()
            and not any(
                prefix in message for prefix in ["[DRY RUN]", "DRY RUN:", "[dry run]"]
            )
        ):
            prefix = f"{cls._get_dry_run_prefix()}Warning: "

        # Format with timestamp if in debug mode
        formatted_message = cls._format_with_timestamp_if_debug(
            f"{prefix}{message}", "WARN"
        )

        # Always use stderr for diagnostic messages (Unix convention)
        cls.get_log_console().print(
            formatted_message, style="warning", markup=not cls._no_color
        )

    @classmethod
    def error(cls, message: str) -> None:
        """Print error message."""
        prefix = "Error: "
        if (
            cls.dry_run_mode
            and message.strip()
            and not any(
                prefix in message for prefix in ["[DRY RUN]", "DRY RUN:", "[dry run]"]
            )
        ):
            prefix = f"{cls._get_dry_run_prefix()}Error: "

        # Format with timestamp if in debug mode
        formatted_message = cls._format_with_timestamp_if_debug(
            f"{prefix}{message}", "ERROR"
        )

        # Errors always go to stderr
        cls.get_log_console().print(
            formatted_message, style="error", markup=not cls._no_color
        )

    @classmethod
    def debug(cls, message: str) -> None:
        """Print debug message if in verbose mode.

        If not in verbose mode, print info message instead.
        """
        if cls.verbose_mode:
            # Format with timestamp if debug logging is active
            root_logger_level = logging.getLogger().getEffectiveLevel()
            debug_logging_active = root_logger_level <= logging.DEBUG

            if debug_logging_active:
                import datetime

                timestamp = datetime.datetime.now().strftime("%m/%d/%y %H:%M:%S")

                # Format like logger but with USER CONSOLE tag
                if cls._no_color:
                    user_console_tag = "[USER CONSOLE]"
                else:
                    # Highlighted yellow tag
                    user_console_tag = "[yellow][USER CONSOLE][/yellow]"

                # Add dry run prefix if needed
                if (
                    cls.dry_run_mode
                    and message.strip()
                    and not any(
                        p in message for p in ["[DRY RUN]", "DRY RUN:", "[dry run]"]
                    )
                ):
                    if cls._no_color:
                        dry_run_part = "[DRY RUN] "
                    else:
                        dry_run_part = "[dark_orange3][DRY RUN][/] "

                    # Format with timestamp and DRY RUN - fixed spacing with 8 characters for "DEBUG"
                    formatted_message = f"[{timestamp}] DEBUG    {user_console_tag} {dry_run_part}{message}"
                    cls.get_log_console().print(
                        formatted_message, markup=not cls._no_color
                    )
                else:
                    # Format with timestamp only - fixed spacing with 8 characters for "DEBUG"
                    formatted_message = (
                        f"[{timestamp}] DEBUG    {user_console_tag} {message}"
                    )
                    cls.get_log_console().print(
                        formatted_message, markup=not cls._no_color
                    )
            else:
                # Regular debug output without timestamps
                if (
                    cls.dry_run_mode
                    and message.strip()
                    and not any(
                        prefix in message
                        for prefix in ["[DRY RUN]", "DRY RUN:", "[dry run]"]
                    )
                ):
                    if cls._no_color:
                        prefix = "[DRY RUN] DEBUG: "
                    else:
                        prefix = f"{cls._get_dry_run_prefix()}[green_yellow]DEBUG:[/] "
                    cls.get_log_console().print(
                        f"{prefix}{message}",
                        style="debug",
                        markup=not cls._no_color,
                    )
                else:
                    if cls._no_color:
                        prefix = "DEBUG: "
                    else:
                        prefix = "[green_yellow]DEBUG:[/] "
                    cls.get_log_console().print(
                        f"{prefix}{message}",
                        style="debug",
                        markup=not cls._no_color,
                    )

    @classmethod
    def success(cls, message: str) -> None:
        """Print success message."""
        if not cls.quiet_mode:
            # Add dry run prefix if needed
            if (
                cls.dry_run_mode
                and message.strip()
                and not any(
                    prefix in message
                    for prefix in ["[DRY RUN]", "DRY RUN:", "[dry run]"]
                )
            ):
                message = f"{cls._get_dry_run_prefix()}{message}"

            # Format with timestamp if in debug mode
            message = cls._format_with_timestamp_if_debug(message, "SUCCESS")

            cls.get_log_console().print(
                message, style="success", markup=not cls._no_color
            )

    @classmethod
    def header(cls, message: str) -> None:
        """Print a header message that appears in all output formats.

        This is useful for section headers when outputting multiple tables or
        data sections. Unlike info(), this works in all output formats.
        """
        # Always print headers regardless of output format
        # Add newline before header for spacing (except for first output)
        formatted_message = f"\n{message}" if message else ""

        # Use direct print to bypass formatting - headers are always plain text
        if formatted_message:
            print(formatted_message)

    @classmethod
    def get_user_console(cls) -> rich_console.Console:
        """Get the user console, initializing if needed."""
        if cls._user_console is None:
            cls._setup_consoles()
        assert cls._user_console is not None  # _setup_consoles always sets this
        return cls._user_console

    @classmethod
    def get_log_console(cls) -> rich_console.Console:
        """Get the log console, initializing if needed."""
        if cls._log_console is None:
            cls._setup_consoles()
        assert cls._log_console is not None  # _setup_consoles always sets this
        return cls._log_console

    @classmethod
    def get_no_color(cls) -> bool:
        """Get the current no_color setting."""
        return cls._no_color

    @classmethod
    def set_output_format(cls, output_format: OutputFormat | None) -> None:
        """Set the active output format for the current command.

        Args:
            output_format: The output format to set, or None to clear
        """
        cls._active_output_format = output_format
