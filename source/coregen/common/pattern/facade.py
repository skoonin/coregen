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
from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context
from coregen.config_model.models.settings import get_settings
from coregen.config_model.models.workspace import WorkspaceConfig

# Import our new pattern matching components
from .pattern_matcher import PatternMatcherFactory

# Define logical prefixes at the module level for clarity
LOGICAL_PREFIXES = ("workspace/", "context/", "component/")


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

                # Suggest alternative patterns if none matched
                suggestions = self._suggest_alternative_patterns(pattern)
                if suggestions:
                    suggestion_str = ", ".join([f"'{s}'" for s in suggestions])
                    self.logger.debug(f"  - You might try: {suggestion_str}")
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

    def _suggest_alternative_patterns(self, pattern: str) -> list[str]:
        """Suggest alternative patterns that might work when a pattern doesn't match.

        Args:
            pattern: The original pattern that didn't match

        Returns:
            A list of suggested alternative patterns
        """
        suggestions = []

        # If unprefixed pattern with slashes, suggest prefixed version
        if "/" in pattern and not any(pattern.startswith(p) for p in LOGICAL_PREFIXES):
            # Looks like a path pattern, suggest logical alternatives
            parts = pattern.split("/")
            if len(parts) >= 2:
                # Could be workspace/context pattern
                suggestions.append(f"workspace/{pattern}")
            if len(parts) == 1:
                # Could be a simple workspace, context, or component
                suggestions.append(f"workspace/{pattern}")
                suggestions.append(f"context/{pattern}")
                suggestions.append(f"component/{pattern}")

        # If no glob, suggest adding glob
        if "*" not in pattern:
            # For logical patterns
            if pattern.startswith("workspace/"):
                suggestions.append(f"{pattern}/**")
            elif pattern.startswith("context/"):
                suggestions.append(f"{pattern}/**")
            # For filesystem patterns
            elif pattern.endswith("/"):
                suggestions.append(f"{pattern}**")
            else:
                suggestions.append(f"{pattern}/*")

        return suggestions

    def _add_matched_workspace(
        self,
        workspace: WorkspaceConfig,
        result: dict[str, dict[str, Any]],
        add_children: bool = False,
    ) -> None:
        """
        Add a matched workspace to the result dictionary.

        Args:
            workspace: The workspace to add.
            result: The dictionary to populate with matches.
            add_children: Whether to also add the workspace's contexts and components.
        """
        if workspace.name not in result["workspaces"]:
            result["workspaces"][workspace.name] = workspace

            if add_children:
                contexts = self.config_access.get_all_contexts(workspace)
                for ctx_name, ctx in contexts.items():
                    self._add_matched_context(
                        ctx, result, add_children=True, add_parent=False
                    )

    def _add_matched_context(
        self,
        context: Context,
        result: dict[str, dict[str, Any]],
        add_children: bool = False,
        add_parent: bool = True,
    ) -> None:
        """
        Add a matched context to the result dictionary.

        Args:
            context: The context to add.
            result: The dictionary to populate with matches.
            add_children: Whether to also add the context's components.
            add_parent: Whether to also add the context's parent workspace.
        """
        if context.name not in result["contexts"]:
            result["contexts"][context.name] = context

            if add_parent:
                ws = self.config_access._get_workspace_from_context(context)
                if ws:
                    self._add_matched_workspace(ws, result, add_children=False)

            if add_children:
                components = context.get_all_components()
                for comp_name, comp in components.items():
                    self._add_matched_component(comp, context, result, add_parent=False)

    def _add_matched_component(
        self,
        component: Component,
        context: Context,
        result: dict[str, dict[str, Any]],
        add_parent: bool = True,
    ) -> None:
        """
        Add a matched component to the result dictionary.

        Args:
            component: The component to add.
            context: The component's parent context.
            result: The dictionary to populate with matches.
            add_parent: Whether to also add the component's parent context and workspace.
        """
        key = f"{context.name}/{component.name}"
        if key not in result["components"]:
            result["components"][key] = component

            if add_parent:
                self._add_matched_context(
                    context, result, add_children=False, add_parent=True
                )

    def _match_logical_pattern(
        self, pattern: str, result: dict[str, dict[str, Any]]
    ) -> bool:
        """
        Match a logical pattern (with prefix like 'workspace/', 'context/' or 'component/').
        This method is kept for backward compatibility.

        Args:
            pattern: The logical pattern to match.
            result: The dictionary to populate with matches.

        Returns:
            True if any element was matched, False otherwise.
        """
        self.logger.debug(f"Legacy matching for logical pattern: {pattern}")

        # Use our new two-phase matching instead
        try:
            matcher = self.factory.create_matcher(pattern)
            matched = matcher.match(result)
            return matched
        except Exception as e:
            self.logger.error(f"Error in legacy _match_logical_pattern: {str(e)}")
            return False
