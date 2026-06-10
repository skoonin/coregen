"""
Name filter service for extracting only names from results.

This module provides a centralized name filtering system that can be used across
all services that need to extract just the names from configuration results.
"""

from typing import Any

from coregen.common.logger import Logger


class NameFilterService:
    """Service for filtering results to contain only names.

    This service handles:
    - Extracting names from full configuration data
    - Deduplicating component names across contexts
    - Checking if data is already in name-only format
    - Ensuring consistent name-only output across commands

    Attributes:
        logger: Logger instance for this service
    """

    def __init__(self, logger: Logger | None = None):
        """Initialize the name filter service.

        Args:
            logger: Optional logger instance, creates new one if not provided
        """
        self.logger = logger or Logger(__name__)

    def filter_names_only(self, data: dict[str, Any]) -> dict[str, Any]:
        """Extract only names from all entity types.

        Converts full configuration data to simple arrays of names.
        Component names are deduplicated across contexts.

        Args:
            data: Dictionary with full configuration data

        Returns:
            Dictionary with only names:
            {
                "workspaces": ["workspace1", "workspace2", ...],
                "contexts": ["context1", "context2", ...],
                "components": ["component1", "component2", ...]  # deduplicated
            }
        """
        self.logger.debug("Filtering data to names only")

        filtered = {}

        # Extract workspace names
        if "workspaces" in data and data["workspaces"]:
            if isinstance(data["workspaces"], dict):
                # Nested format
                filtered["workspaces"] = sorted(list(data["workspaces"].keys()))
            elif isinstance(data["workspaces"], list):
                # Flat format - extract name field
                names = []
                for ws in data["workspaces"]:
                    if isinstance(ws, dict) and "name" in ws:
                        names.append(ws["name"])
                    elif isinstance(ws, str):
                        names.append(ws)
                filtered["workspaces"] = sorted(names)
        else:
            filtered["workspaces"] = []

        # Extract context names
        if "contexts" in data and data["contexts"]:
            if isinstance(data["contexts"], dict):
                # Nested format
                filtered["contexts"] = sorted(list(data["contexts"].keys()))
            elif isinstance(data["contexts"], list):
                # Flat format - extract name field
                names = []
                for ctx in data["contexts"]:
                    if isinstance(ctx, dict) and "name" in ctx:
                        names.append(ctx["name"])
                    elif isinstance(ctx, str):
                        names.append(ctx)
                filtered["contexts"] = sorted(names)
        else:
            filtered["contexts"] = []

        # Extract component names (deduplicated)
        if "components" in data and data["components"]:
            component_names = set()

            if isinstance(data["components"], dict):
                # Nested format - keys are "context/component"
                for component_key in data["components"].keys():
                    component_name = self._extract_component_name(component_key)
                    component_names.add(component_name)
            elif isinstance(data["components"], list):
                # Flat format - extract name field
                for comp in data["components"]:
                    if isinstance(comp, dict) and "name" in comp:
                        component_names.add(comp["name"])
                    elif isinstance(comp, str):
                        # If it's a string, extract component name
                        component_name = self._extract_component_name(comp)
                        component_names.add(component_name)

            filtered["components"] = sorted(list(component_names))
        else:
            filtered["components"] = []

        return filtered

    def is_name_only_format(self, data: dict[str, Any]) -> bool:
        """Check if data is already in name-only format.

        Args:
            data: Dictionary to check

        Returns:
            True if data contains only arrays of strings (names)
        """
        # Check if all entity types are lists of strings
        for entity_type in ["workspaces", "contexts", "components"]:
            if entity_type in data:
                if not isinstance(data[entity_type], list):
                    return False
                # Check if all items are strings
                for item in data[entity_type]:
                    if not isinstance(item, str):
                        return False
        return True

    def _extract_component_name(self, component_key: str) -> str:
        """Extract component name from a component key.

        Component keys in nested format are "context/component_name".
        This method extracts just the component name part.

        Args:
            component_key: Key that may contain context/component format

        Returns:
            Just the component name
        """
        if "/" in component_key:
            # Extract component name from "context/component" format
            return component_key.split("/", 1)[1]
        else:
            # Already just the component name
            return component_key

    def transform_for_output(
        self,
        data: dict[str, Any],
        entity_type: str | None = None,
        patterns: list[str] | None = None,
    ) -> list[str] | dict[str, Any]:
        """Transform name-only data for final output based on entity type or patterns.

        This method centralizes the logic for converting name-only dictionaries
        to flat arrays based on the primary entity type requested.

        Args:
            data: Dictionary with name-only arrays (from filter_names_only)
            entity_type: Optional entity type ('workspace', 'context', 'component')
            patterns: Optional patterns to help determine primary entity type

        Returns:
            Either a flat array of names (when a specific type is identified)
            or the original dict (when no specific type or 'all')
        """
        # If not name-only format, return as-is
        if not self.is_name_only_format(data):
            self.logger.debug("Data is not in name-only format, returning as-is")
            return data

        # Determine which entity type to return
        if entity_type and entity_type in ["workspace", "context", "component"]:
            # Map singular to plural
            entity_map = {
                "workspace": "workspaces",
                "context": "contexts",
                "component": "components",
            }
            mapped_type = entity_map.get(entity_type)
            if mapped_type and mapped_type in data:
                self.logger.debug(
                    f"Returning {mapped_type} array for entity type: {entity_type}"
                )
                return data[mapped_type]  # type: ignore[no-any-return]

        # Try to determine from patterns if no specific type
        if not entity_type and patterns:
            if any(p.startswith(("w/", "workspace/")) for p in patterns):
                return data.get("workspaces", [])  # type: ignore[no-any-return]
            elif any(p.startswith(("c/", "context/")) for p in patterns):
                return data.get("contexts", [])  # type: ignore[no-any-return]
            elif any(p.startswith(("cm/", "component/")) for p in patterns):
                return data.get("components", [])  # type: ignore[no-any-return]

        # If no specific type identified, find the one with most items
        if not entity_type or entity_type == "all":
            max_count = 0
            selected = data  # Default to returning the full dict

            for entity_key in ["workspaces", "contexts", "components"]:
                if entity_key in data and len(data[entity_key]) > max_count:
                    max_count = len(data[entity_key])
                    selected = data[entity_key]

            # Only return array if there's a clear primary type
            if max_count > 0 and isinstance(selected, list):
                return selected

        # Default: return the full dictionary
        return data
