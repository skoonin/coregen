"""
Facade module that provides the PatternMatcher class implementation.

This module implements the PatternMatcher class using our new two-phase pattern matching
approach while maintaining the same interface for backward compatibility.
"""

from pathlib import Path
from typing import Any

from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.config_model.access import ConfigAccess
from coregen.config_model.models.settings import get_settings

# Import our new pattern matching components
from .pattern_matcher import PatternMatcherFactory


class PatternMatcher:
    """Handles matching of patterns (filesystem or logical) to config elements."""

    def __init__(
        self,
        config_access: ConfigAccess,
        root_path: Path,
        console: Console,
        logger: Logger,
        verbose: bool | None = None,
    ):
        """
        Initialize the PatternMatcher.

        Args:
            config_access: The configuration access object
            root_path: The root path for resolving filesystem patterns (typically the config file's directory)
            console: The console output handler
            logger: The logger for debug information
            verbose: If True, show detailed output. None means use settings default.

        Note:
            All patterns must now use logical prefixes (w/, c/, cm/ or their long forms).
            Filesystem patterns are no longer supported.
        """
        self.config_access = config_access
        self.root_path = root_path
        self.console = console
        self.logger = logger

        # Get settings for default values
        settings = get_settings()
        cli_settings = settings.options.global_options

        # Use parameter if provided, otherwise use settings default
        self.verbose = verbose if verbose is not None else cli_settings.verbose

        # Create factory to build pattern matchers
        self.factory = PatternMatcherFactory(config_access, root_path, console, logger)

    def match(self, pattern: str) -> dict[str, dict[str, Any]]:
        """Match a single pattern (filesystem or logical) to config elements.

        All patterns MUST start with a prefix: 'workspace/', 'context/', or 'component/'
        (or their short forms: w/, c/, cm/).

        Supports standard and recursive glob patterns ('*', '**').

        Args:
            pattern: The pattern string to match.

        Returns:
            Dictionary containing matched workspaces, contexts, and components.
        """
        self.logger.debug(f"PatternMatcher: Processing pattern: {pattern}")

        # Log glob type
        if "**" in pattern:
            self.logger.debug(
                f"PatternMatcher: Processing recursive glob pattern: {pattern}"
            )
        elif "*" in pattern:
            self.logger.debug(f"PatternMatcher: Processing glob pattern: {pattern}")

        # Create empty result container
        result: dict[str, dict[str, Any]] = {
            "workspaces": {},
            "contexts": {},
            "components": {},
        }

        try:
            # Use the new two-phase matching approach
            # Phase 1: Pattern is parsed and compiled by the factory
            # Phase 2: The appropriate matcher is executed against the pattern
            matcher = self.factory.create_matcher(pattern)
            matcher.match(result)

            # Log match results
            matched_something = (
                len(result["workspaces"]) > 0
                or len(result["contexts"]) > 0
                or len(result["components"]) > 0
            )

            if matched_something:
                self.logger.debug(f"Pattern '{pattern}' matched successfully.")

                # Add additional debugging info at verbose level
                if self.verbose:
                    ws_names = list(result["workspaces"].keys())
                    ctx_names = list(result["contexts"].keys())
                    comp_count = len(result["components"])
                    self.logger.debug(
                        f"  - Matched {len(ws_names)} workspace(s): {ws_names}"
                    )
                    self.logger.debug(
                        f"  - Matched {len(ctx_names)} context(s): {ctx_names}"
                    )
                    self.logger.debug(f"  - Matched {comp_count} component(s)")
            else:
                self.logger.debug(f"Pattern '{pattern}' did not match any elements.")
                self.logger.debug(f"  - No matches found for pattern: '{pattern}'")
        except Exception as e:
            self.logger.error(f"Error matching pattern '{pattern}': {str(e)}")
            if self.verbose:
                self.logger.debug(f"  - Error details: {str(e)}")

            # Re-raise pattern parsing errors so they can be handled by the caller
            error_msg = str(e)
            if (
                "Pattern must start with a recognized prefix" in error_msg
                or "cannot be empty after prefix" in error_msg
            ):
                raise e  # Re-raise pattern parse errors

            # For other errors, just log and return empty result

        return result
