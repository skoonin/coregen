"""
Pattern Selector

This module provides the PatternSelector class which selects entities from
a complete filtered model based on pattern matching. Unlike PatternMatcher,
this doesn't filter data - it only selects what to return from already-filtered data.

"""

import fnmatch
from typing import Any

from coregen.common.logger import Logger


class PatternSelector:
    """
    Selects entities from a complete filtered model based on pattern.

    Unlike PatternMatcher, this doesn't filter or load data. It works with
    an already-loaded and already-filtered complete model, selecting which
    entities to return based on the pattern.

    This is part of the new filter-first architecture where:
    1. Complete model is loaded
    2. Filters are applied to the complete model
    3. Pattern selector chooses what subset to return
    """

    def __init__(self, logger: Logger | None = None):
        """
        Initialize the pattern selector.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or Logger(__name__)

    def select_by_pattern(
        self, complete_model: dict[str, dict[str, Any]], pattern: str
    ) -> dict[str, dict[str, Any]]:
        """
        Select entities based on pattern from already-filtered complete model.

        The pattern format follows the standard coregen pattern prefixes:
        - "w/*" or "workspace/*" - returns matching workspaces and their full hierarchy
        - "c/*" or "context/*" - returns matching contexts and their components
        - "cm/*" or "component/*" - returns only matching components

        Args:
            complete_model: Complete filtered model with 'workspaces', 'contexts', 'components'
            pattern: Pattern to match (e.g., "cm/*", "c/*-prod", "w/aws")

        Returns:
            Dictionary with selected entities based on pattern type

        Examples:
            - "cm/*" → returns {"components": {...}}
            - "c/*" → returns {"contexts": {...}, "components": {...}}
            - "w/*" → returns full hierarchy
        """
        # Parse pattern to determine type and matching criteria
        pattern_type, pattern_value = self._parse_pattern(pattern)

        self.logger.debug(
            f"Selecting entities with pattern type: {pattern_type}, value: {pattern_value}"
        )

        # Based on pattern type, select appropriate entities
        if pattern_type == "workspace":
            return self._select_workspaces(complete_model, pattern_value)
        elif pattern_type == "context":
            return self._select_contexts(complete_model, pattern_value)
        elif pattern_type == "component":
            return self._select_components(complete_model, pattern_value)
        else:
            # Unknown pattern type - raise error for proper handling
            raise ValueError(
                f"Pattern must start with a recognized prefix. Got: '{pattern}'"
            )

    def _parse_pattern(self, pattern: str) -> tuple[str, str]:
        """
        Parse pattern to extract type and value.

        Args:
            pattern: Pattern string (e.g., "cm/*", "context/dev-*")

        Returns:
            Tuple of (pattern_type, pattern_value)
        """
        # Check for standard prefixes
        if pattern.startswith("w/") or pattern.startswith("workspace/"):
            prefix_len = len("w/") if pattern.startswith("w/") else len("workspace/")
            return "workspace", pattern[prefix_len:]
        elif pattern.startswith("c/") or pattern.startswith("context/"):
            prefix_len = len("c/") if pattern.startswith("c/") else len("context/")
            return "context", pattern[prefix_len:]
        elif pattern.startswith("cm/") or pattern.startswith("component/"):
            prefix_len = len("cm/") if pattern.startswith("cm/") else len("component/")
            return "component", pattern[prefix_len:]
        else:
            # No recognized prefix - this is an error
            return "unknown", pattern

    def _select_workspaces(
        self, complete_model: dict[str, dict[str, Any]], pattern_value: str
    ) -> dict[str, dict[str, Any]]:
        """
        Select workspaces and their full hierarchy based on pattern.

        Args:
            complete_model: Complete model
            pattern_value: Pattern to match workspace names

        Returns:
            Selected entities including full hierarchy
        """
        result: dict[str, dict[str, Any]] = {
            "workspaces": {},
            "contexts": {},
            "components": {},
        }

        # Select matching workspaces
        for ws_name, workspace in complete_model.get("workspaces", {}).items():
            if fnmatch.fnmatch(ws_name, pattern_value):
                result["workspaces"][ws_name] = workspace

                # Include all contexts from this workspace
                for ctx_name, context in complete_model.get("contexts", {}).items():
                    if context.workspace == ws_name:
                        result["contexts"][ctx_name] = context

                        # Include all components from these contexts
                        for comp_key, component in complete_model.get(
                            "components", {}
                        ).items():
                            if comp_key.startswith(f"{ctx_name}/"):
                                result["components"][comp_key] = component

        return result

    def _select_contexts(
        self, complete_model: dict[str, dict[str, Any]], pattern_value: str
    ) -> dict[str, dict[str, Any]]:
        """
        Select contexts and their components based on pattern.

        Args:
            complete_model: Complete model
            pattern_value: Pattern to match context names

        Returns:
            Selected contexts and their components
        """
        result: dict[str, dict[str, Any]] = {
            "workspaces": {},
            "contexts": {},
            "components": {},
        }

        # Select matching contexts
        for ctx_name, context in complete_model.get("contexts", {}).items():
            if fnmatch.fnmatch(ctx_name, pattern_value):
                result["contexts"][ctx_name] = context

                # Include all components from this context
                for comp_key, component in complete_model.get("components", {}).items():
                    if comp_key.startswith(f"{ctx_name}/"):
                        result["components"][comp_key] = component

        return result

    def _select_components(
        self, complete_model: dict[str, dict[str, Any]], pattern_value: str
    ) -> dict[str, dict[str, Any]]:
        """
        Select only components based on pattern.

        Args:
            complete_model: Complete model
            pattern_value: Pattern to match component names

        Returns:
            Selected components only
        """
        result: dict[str, dict[str, Any]] = {
            "workspaces": {},
            "contexts": {},
            "components": {},
        }

        # Select matching components
        for comp_key, component in complete_model.get("components", {}).items():
            # Extract component name from key (format: "context_name/component_name")
            _, comp_name = comp_key.rsplit("/", 1)
            if fnmatch.fnmatch(comp_name, pattern_value):
                result["components"][comp_key] = component

        return result
