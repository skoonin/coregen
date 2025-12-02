"""
Global options management for CLI commands.

This module provides a standardized way to handle global options
across all CLI commands in the application.

## Purpose

The GlobalOptions class centralizes handling of global CLI options to ensure
consistency across commands and services. It helps with:

1. Providing default values from settings
2. Handling option overrides from CLI arguments
3. Ensuring consistent config_file path handling
4. Simplifying service initialization

## Usage in Commands

In commands, you can use GlobalOptions.from_context() to get options:

```python
from coregen.cli.global_options import GlobalOptions
global_options = GlobalOptions.from_context(ctx)
options_dict = global_options.to_dict()
```

## Usage in Services

Services can receive a GlobalOptions instance and use it:

```python
def __init__(self, global_options=None, **kwargs):
    # Use GlobalOptions values
    if global_options:
        self.dry_run = global_options.dry_run
        self.config_file = global_options.config_file
```

## Implementation Guide

For a detailed implementation guide, see:
docs/global-options-implementation-guide.md
"""

from pathlib import Path
from typing import Any, TypeVar

import typer

from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.logger import Logger
from coregen.config_model.models.settings import get_settings

# Get settings instance at module level for default values
settings = get_settings()
logger = Logger(__name__)

T = TypeVar("T", bound="GlobalOptions")


class GlobalOptions:
    """
    Standardized handling of global options across the application.

    This class provides a consistent way to access global CLI options
    from any part of the application. It ensures options are properly
    initialized with defaults from settings and allows overriding
    from CLI arguments.

    Attributes:
        dry_run: If True, show what would be done without making changes
        file_action: Action to take when a file exists
        quiet: If True, suppress non-essential output
        verbose: If True, show detailed output
        no_color: If True, disable colored output
        config_file: Path to the configuration file
        debug: If True, enable debug output
    """

    def __init__(
        self,
        dry_run: bool = settings.options.global_options.dry_run,
        file_action: FileAction = settings.options.global_options.file_action,
        quiet: bool = settings.options.global_options.quiet,
        verbose: bool = settings.options.global_options.verbose,
        no_color: bool = settings.options.global_options.no_color,
        config_file: Path | None = settings.options.global_options.config_file,
        debug: bool = False,
    ) -> None:
        """
        Initialize global options with defaults from settings.

        Args:
            dry_run: If True, show what would be done without making changes
            file_action: Action to take when a file exists
            quiet: If True, suppress non-essential output
            verbose: If True, show detailed output
            no_color: If True, disable colored output
            config_file: Path to the configuration file
            debug: If True, enable debug output
        """
        self.dry_run = dry_run
        self.file_action = file_action
        self.quiet = quiet
        self.verbose = verbose
        self.no_color = no_color
        self.config_file = config_file
        self.debug = debug

    @classmethod
    def _convert_to_path(cls, value: Any) -> Path | None:
        """Convert string to Path if needed.

        Args:
            value: The value to convert (can be str, Path, or None)

        Returns:
            Path object or None
        """
        if value and isinstance(value, str):
            logger.debug(f"Converting config_file from string to Path: {value}")
            return Path(value)
        if isinstance(value, Path):
            return value
        return None

    @classmethod
    def from_context(cls: type[T], ctx: typer.Context) -> T:
        """
        Create a GlobalOptions instance from a Typer context.

        Args:
            ctx: Typer context containing options

        Returns:
            GlobalOptions instance with values from context
        """
        if not ctx.obj:
            logger.debug("Context has no obj, using defaults from settings")
            return cls()

        # Debug dump of context contents to help with troubleshooting
        logger.debug(f"Creating GlobalOptions from context obj: {ctx.obj}")
        logger.debug(
            f"config_file from ctx.obj: {ctx.obj.get('config_file', 'NOT_FOUND')}"
        )

        # Create options from context with defaults from settings
        config_file_value = ctx.obj.get(
            "config_file", settings.options.global_options.config_file
        )
        # Convert to Path using the helper method
        config_file_value = cls._convert_to_path(config_file_value)

        return cls(
            dry_run=ctx.obj.get("dry_run", settings.options.global_options.dry_run),
            file_action=ctx.obj.get(
                "file_action", settings.options.global_options.file_action
            ),
            quiet=ctx.obj.get("quiet", settings.options.global_options.quiet),
            verbose=ctx.obj.get("verbose", settings.options.global_options.verbose),
            no_color=ctx.obj.get("no_color", settings.options.global_options.no_color),
            config_file=config_file_value,
            debug=ctx.obj.get("debug", False),
        )

    @classmethod
    def from_dict(cls: type[T], options_dict: dict[str, Any]) -> T:
        """
        Create a GlobalOptions instance from a dictionary.

        Args:
            options_dict: Dictionary containing option values

        Returns:
            GlobalOptions instance with values from dictionary
        """
        logger.debug(f"Creating GlobalOptions from dict: {options_dict}")

        # Create options from dictionary with defaults from settings
        config_file_value = options_dict.get(
            "config_file", settings.options.global_options.config_file
        )
        # Convert to Path using the helper method
        config_file_value = cls._convert_to_path(config_file_value)

        return cls(
            dry_run=options_dict.get(
                "dry_run", settings.options.global_options.dry_run
            ),
            file_action=options_dict.get(
                "file_action", settings.options.global_options.file_action
            ),
            quiet=options_dict.get("quiet", settings.options.global_options.quiet),
            verbose=options_dict.get(
                "verbose", settings.options.global_options.verbose
            ),
            no_color=options_dict.get(
                "no_color", settings.options.global_options.no_color
            ),
            config_file=config_file_value,
            debug=options_dict.get("debug", False),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert GlobalOptions to a dictionary.

        Returns:
            Dictionary representation of options
        """
        return {
            "dry_run": self.dry_run,
            "file_action": self.file_action,
            "quiet": self.quiet,
            "verbose": self.verbose,
            "no_color": self.no_color,
            "config_file": self.config_file,
            "debug": self.debug,
        }

    def update(self, **kwargs: Any) -> None:
        """
        Update options with provided values.

        Args:
            **kwargs: Option values to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.debug(f"Updated option {key} to {value}")
            else:
                logger.warning(f"Attempted to set unknown option: {key}")

    def __str__(self) -> str:
        """Return string representation of options."""
        return (
            f"GlobalOptions(dry_run={self.dry_run}, "
            f"file_action={self.file_action}, "
            f"quiet={self.quiet}, "
            f"verbose={self.verbose}, "
            f"no_color={self.no_color}, "
            f"config_file={self.config_file}, "
            f"debug={self.debug})"
        )
