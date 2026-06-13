"""
Base class for generate and get services.

This module provides the base class for generate and get services.
It handles common functionality such as configuration access, filtering,
and path pattern processing.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from coregen.cli.global_options import GlobalOptions

from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.console import Console
from coregen.common.file_manager import FileManager
from coregen.common.filter_service import FilterService
from coregen.common.path_service import PathService
from coregen.common.pattern.facade import PatternMatcher
from coregen.common.workspace_initializer import WorkspaceInitializer
from coregen.config_model.access import ConfigAccess
from coregen.config_model.provider import ConfigurationProvider
from coregen.services.service_base import ServiceBase


class ServicesBase(ServiceBase):
    """Base class for generate and get services.

    This class provides common functionality for both generate and get services.
    It handles configuration access, filtering, and path pattern processing.

    Attributes:
        config_access: Access to configuration elements
        path_service: Service for path resolution
    """

    def __init__(
        self,
        console: Console | None = None,
        file_manager: FileManager | None = None,
        workspace_initializer: WorkspaceInitializer | None = None,
        config_provider: ConfigurationProvider | None = None,
        dry_run: bool = False,
        file_action: FileAction = FileAction.ASK,
        quiet: bool = False,
        verbose: bool = False,
        no_color: bool = False,
        config_file: Path | None = None,
        # Accept GlobalOptions as an alternative to individual options
        global_options: Optional["GlobalOptions"] = None,
    ) -> None:
        """Initialize the service.

        Args:
            console: Optional Console instance
            file_manager: Optional FileManager instance
            workspace_initializer: Optional WorkspaceInitializer instance
            config_provider: Optional ConfigurationProvider instance
            dry_run: If True, show what would be done without making changes
            file_action: Action to take when a file exists
            quiet: If True, suppress non-essential output
            verbose: If True, show detailed output
            no_color: If True, disable colored output
            config_file: Optional path to the configuration file
            global_options: Optional GlobalOptions instance instead of individual options
        """
        # If global_options is provided, pass it to parent which handles extraction
        if global_options is not None:
            super().__init__(
                console=console,
                file_manager=file_manager,
                workspace_initializer=workspace_initializer,
                global_options=global_options,
                config_file=getattr(global_options, "config_file", config_file),
            )
        else:
            super().__init__(
                console=console,
                file_manager=file_manager,
                workspace_initializer=workspace_initializer,
                dry_run=dry_run,
                file_action=file_action,
                quiet=quiet,
                verbose=verbose,
                no_color=no_color,
                config_file=config_file,
            )

        # Initialize configuration provider if not provided
        self._config_provider = config_provider or ConfigurationProvider(
            config_mode=True,
            lenient_validation=True,
            dry_run=self.dry_run,
            file_action=self.file_action,
            quiet=self.quiet,
            verbose=self.verbose,
            no_color=self.no_color,
        )

        # Initialize path service from config provider
        self._path_service = self._config_provider.path_service

        # Initialize config access
        self._config_access: ConfigAccess | None = None

        # Initialize filter service (will be created when needed)
        self._filter_service: FilterService | None = None

        # Update workspace initializer with path service if needed
        if workspace_initializer is None and self._workspace_initializer:
            self._workspace_initializer.path_service = self._path_service

    @property
    def config_provider(self) -> ConfigurationProvider:
        """Get the configuration provider instance."""
        return self._config_provider

    @property
    def path_service(self) -> PathService:
        """Get the path service instance."""
        return self._path_service

    @property
    def global_options(self) -> Optional["GlobalOptions"]:
        """Get the global options instance.

        If global_options wasn't provided in constructor, this will return None.

        Returns:
            GlobalOptions instance or None
        """
        return self._global_options

    @property
    def config_access(self) -> ConfigAccess:
        """Get the config access instance, loading configuration if needed."""
        if self._config_access is None:
            # Load configuration if not already loaded
            if not self._config_provider.has_config():
                self.logger.debug("Loading configuration")

                # If config_file is specified, use it
                if hasattr(self, "config_file") and self.config_file:
                    self.logger.debug(
                        f"Using specified config file: {self.config_file}"
                    )
                    try:
                        self._config_provider.load_config(self.config_file)
                    except FileNotFoundError:
                        # If config file was explicitly specified but not found, fail
                        self.logger.error(
                            f"Specified config file not found: {self.config_file}"
                        )
                        raise
                    except Exception as e:
                        # For other errors, also fail rather than falling back
                        self.logger.error(
                            f"Failed to load specified config file '{self.config_file}': {str(e)}"
                        )
                        raise
                else:
                    # Use default config discovery
                    self._load_default_config()

            # Check for validation errors after configuration is loaded
            if (
                hasattr(self._config_provider, "validation_errors")
                and self._config_provider.validation_errors
            ):
                self.logger.error("Configuration validation failed")
                for error in self._config_provider.validation_errors:
                    self.logger.error(f"  • {error}")
                raise ValueError("Configuration invalid.")

            # Create config access instance
            config = self._config_provider.get_config()
            if config is None:
                raise ValueError("No configuration loaded")
            self._config_access = ConfigAccess(
                config_or_workspaces=config,
                path_service=self._path_service,
            )

        assert self._config_access is not None  # Always set in the if block above
        return self._config_access

    @property
    def filter_service(self) -> FilterService:
        """Get the filter service instance, creating it if needed."""
        if self._filter_service is None:
            self._filter_service = FilterService(
                config_access=self.config_access, logger=self.logger
            )
        assert self._filter_service is not None  # Always set in the if block above
        return self._filter_service

    def _auto_append_recursive_pattern(self, patterns: Any) -> list[str]:
        """Auto-append /* to bare logical type patterns only.

        Only applies to the bare logical type names to avoid breaking any existing patterns:
        - 'workspace' becomes 'workspace/*'
        - 'context' becomes 'context/*'
        - 'component' becomes 'component/*'

        Does NOT modify:
        - Patterns with wildcards (*)
        - Patterns ending with /
        - Any pattern with path components (e.g., 'workspace/aws', 'context/dev')
        - Filesystem patterns (not starting with workspace/, context/, component/)

        Accepts loosely-typed input (None, a bare string, or a list with
        non-string elements) and normalizes it defensively.

        Args:
            patterns: Original patterns (list, single string, or None)

        Returns:
            List of patterns with /* appended where appropriate
        """
        # Input validation
        if not patterns:
            return []

        if not isinstance(patterns, list):
            self.logger.warning(
                f"Expected list of patterns, got {type(patterns)}. Converting to list."
            )
            patterns = [patterns] if patterns else []

        modified_patterns = []

        for pattern in patterns:
            # Validate each pattern is a string
            if not isinstance(pattern, str):
                self.logger.warning(
                    f"Skipping non-string pattern: {pattern} (type: {type(pattern)})"
                )
                continue

            # Skip empty patterns
            if not pattern.strip():
                self.logger.warning("Skipping empty or whitespace-only pattern")
                continue

            pattern = pattern.strip()
            # Skip if pattern already contains wildcards
            if "*" in pattern:
                modified_patterns.append(pattern)
                self.logger.debug(
                    f"Pattern '{pattern}' already contains wildcards, keeping as-is"
                )
                continue

            # Skip if pattern already ends with a slash (indicating directory)
            if pattern.endswith("/"):
                modified_patterns.append(pattern)
                self.logger.debug(f"Pattern '{pattern}' ends with slash, keeping as-is")
                continue

            # Only apply to simple logical patterns
            if self._is_simple_logical_pattern(pattern):
                new_pattern = f"{pattern}/*"
                modified_patterns.append(new_pattern)
                self.logger.debug(
                    f"Auto-appending /* to simple logical pattern: '{pattern}' -> '{new_pattern}'"
                )
            else:
                modified_patterns.append(pattern)
                self.logger.debug(
                    f"Pattern '{pattern}' is complex or filesystem pattern, keeping as-is"
                )

        return modified_patterns

    def _is_simple_logical_pattern(self, pattern: str) -> bool:
        """Check if pattern is a simple logical pattern suitable for auto-append.

        Simple logical patterns are only the bare logical types:
        - 'workspace'
        - 'context'
        - 'component'

        Patterns with any path components (e.g., 'workspace/aws') are left unchanged.

        Args:
            pattern: Pattern to check

        Returns:
            True if pattern should get /* auto-appended
        """
        # Only the bare logical type names get auto-appended
        return pattern in ["workspace", "context", "component"]

    def _load_default_config(self) -> None:
        """Load the default configuration file based on root path discovery."""
        # First try to use the root path from provider
        root_path = self._config_provider.get_root_path()

        if root_path:
            config_file = root_path / self._config_provider.get_config_file_name()
            self.logger.debug(
                f"Attempting to load config from discovered root: {config_file}"
            )
            self._config_provider.load_config(config_file)
        else:
            # Fallback to current directory
            config_file = Path.cwd() / self._config_provider.get_config_file_name()
            self.logger.debug(
                f"Falling back to current directory for config: {config_file}"
            )
            self._config_provider.load_config(config_file)

    def process_path_patterns(self, patterns: list[str]) -> dict[str, Any]:
        """Process glob patterns into configuration elements using PatternMatcher.

        Args:
            patterns: List of path patterns to process

        Returns:
            Dictionary containing matched workspaces, contexts, and components
        """
        # Auto-append /* to simple patterns that don't already have wildcards
        patterns = self._auto_append_recursive_pattern(patterns)

        # Ensure configuration (and contexts) are loaded before matching
        _ = self.config_access
        self.logger.debug(f"Processing path patterns via PatternMatcher: {patterns}")

        # Initialize result containers
        aggregated_result: dict[str, dict[str, Any]] = {
            "workspaces": {},
            "contexts": {},
            "components": {},
        }

        # Log more details in verbose mode
        if self.verbose:
            self.logger.debug(
                "  - Phase 1: Pattern compilation - Converting raw patterns to structured specifications"
            )
            self.logger.debug(
                "  - Phase 2: Pattern execution - Applying specifications to configuration elements"
            )

        # Instantiate the PatternMatcher
        root_path = self.config_provider.get_root_path()
        if not root_path:
            root_path = Path.cwd()

        matcher = PatternMatcher(
            config_access=self.config_access,
            root_path=root_path,
            console=self.console,
            logger=self.logger,
            verbose=self.verbose,
        )

        # Track failed patterns for better error reporting
        failed_patterns = []

        # Process each pattern using the matcher
        for pattern in patterns:
            try:
                # Match the individual pattern
                single_result = matcher.match(pattern)

                # Check if pattern matched anything
                matched_something = (
                    len(single_result["workspaces"]) > 0
                    or len(single_result["contexts"]) > 0
                    or len(single_result["components"]) > 0
                )

                if not matched_something:
                    failed_patterns.append(pattern)
                    if self.verbose:
                        self.logger.debug(
                            f"  - Pattern '{pattern}' did not match any configuration elements"
                        )
                else:
                    if self.verbose:
                        ws_count = len(single_result["workspaces"])
                        ctx_count = len(single_result["contexts"])
                        comp_count = len(single_result["components"])
                        self.logger.debug(
                            f"  - Pattern '{pattern}' matched {ws_count} workspace(s), {ctx_count} context(s), and {comp_count} component(s)"
                        )

                # Merge the results into the aggregated result using robust merge
                self._merge_results(aggregated_result, single_result)

            except Exception as e:
                # Check if this is a pattern parsing error that should fail the command
                error_msg = str(e)
                if "Pattern must start with a recognized prefix" in error_msg:
                    self.console.error(f"Invalid pattern '{pattern}': {error_msg}")
                    self.console.info(
                        "Valid prefixes: w/, c/, cm/ (or long forms: workspace/, context/, component/)"
                    )
                    # Pattern parse errors should fail the command
                    raise ValueError(f"Invalid pattern syntax: {pattern}")
                elif "cannot be empty after prefix" in error_msg:
                    self.console.error(f"Invalid pattern '{pattern}': {error_msg}")
                    # Pattern parse errors should fail the command
                    raise ValueError(f"Invalid pattern syntax: {pattern}")
                else:
                    # Log other errors for debugging
                    self.logger.error(
                        f"Error processing pattern '{pattern}' with PatternMatcher: {error_msg}"
                    )
                failed_patterns.append(pattern)
                # Continue with other patterns
                continue

        self.console.debug(f"Matched {len(aggregated_result['components'])} components")

        # Report on failed patterns once: the all-failed case subsumes the
        # per-pattern count, and the caller reports its own empty-result error
        if failed_patterns and not self.quiet:
            if len(patterns) == len(failed_patterns):
                self.console.warning(
                    f"No configuration elements were matched by any pattern: {failed_patterns}"
                )
            else:
                self.console.warning(
                    f"{len(failed_patterns)} pattern(s) did not match anything: {failed_patterns}"
                )

        # NOTE: User-facing info about matched contexts should be handled by CLI layer
        # Services should only return raw data for the CLI to format and display

        return aggregated_result

    def _merge_results(
        self, aggregated: dict[str, Any], new_result: dict[str, Any]
    ) -> None:
        """Merge new_result into aggregated result dictionaries robustly.

        Handles duplicates by merging dictionary entries.

        Args:
            aggregated: The aggregated result dictionary.
            new_result: The new result dictionary to merge.
        """
        for key in ["workspaces", "contexts", "components"]:
            for sub_key, sub_value in new_result.get(key, {}).items():
                if sub_key in aggregated[key]:
                    self.logger.debug(
                        f"Duplicate {key} '{sub_key}' found. Merging entries."
                    )
                    # If both values are dictionaries, merge them; otherwise, override.
                    if isinstance(aggregated[key][sub_key], dict) and isinstance(
                        sub_value, dict
                    ):
                        aggregated[key][sub_key].update(sub_value)
                    else:
                        aggregated[key][sub_key] = sub_value
                else:
                    aggregated[key][sub_key] = sub_value

    def apply_filters(
        self, elements: dict[str, Any], filters: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Apply filters to configuration elements.

        Args:
            elements: Dictionary of configuration elements
            filters: List of filter specifications

        Returns:
            Filtered dictionary of configuration elements
        """
        return self.filter_service.apply_filters(elements, filters)

    def parse_filter_expression(self, filter_string: str) -> dict[str, Any]:
        """Parse a filter expression into a structured filter specification.

        Args:
            filter_string: Filter expression string

        Returns:
            Filter specification dictionary
        """
        return self.filter_service.parse_filter_expression(filter_string)
