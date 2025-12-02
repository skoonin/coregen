"""
Inactive filter service for filtering out inactive items.

This module provides a centralized inactive filtering system that can be used across
all services that need to filter out inactive workspaces, contexts, and components.
"""

from typing import Any

from coregen.common.logger import Logger


class InactiveFilterService:
    """Service for filtering out inactive items unless include_inactive is True.

    This service handles:
    - Filtering out items with active=false
    - Preserving inactive items when include_inactive is True
    - Handling nested and flat data formats
    - Ensuring consistent inactive filtering across commands

    Attributes:
        logger: Logger instance for this service
    """

    def __init__(self, logger: Logger | None = None):
        """Initialize the inactive filter service.

        Args:
            logger: Optional logger instance, creates new one if not provided
        """
        self.logger = logger or Logger(__name__)

    def filter_inactive(
        self, data: dict[str, Any], include_inactive: bool = False
    ) -> dict[str, Any]:
        """Filter out inactive items unless include_inactive is True.

        By default, items with active=false are excluded from results.
        When include_inactive=True, all items are returned regardless of active status.

        Args:
            data: Dictionary with workspaces, contexts, components
            include_inactive: If True, include items with active=false

        Returns:
            Filtered dictionary with inactive items removed (unless include_inactive=True)
        """
        self.logger.debug(
            f"Filtering inactive items (include_inactive={include_inactive})"
        )

        # If including inactive, return data as-is
        if include_inactive:
            self.logger.debug("Including inactive items in results")
            return data

        # Apply hierarchy-aware filtering recursively
        result = self._filter_data(data)
        # Ensure we return a dict as per the method signature
        if not isinstance(result, dict):
            return {}
        return result

    def _filter_data(self, data: Any) -> Any:
        """Recursively filter any data structure, removing inactive items.

        This approach works on any data structure:
        - For dicts: filters out entries where value has active=false
        - For lists: filters out items with active=false
        - For model objects: preserves them as objects, only filters if inactive
        - For other types: returns as-is

        Args:
            data: Any data structure

        Returns:
            Filtered data with inactive items removed (preserving model objects)
        """
        # Handle model objects - check if inactive but don't convert to dict
        if hasattr(data, "model_dump"):
            # If this model object is inactive, filter it out
            if self._has_active_false(data):
                name = self._get_name(data)
                self.logger.debug(f"Filtering out inactive model object: {name}")
                return None
            # Otherwise, return the model object as-is
            # No need to recursively filter model objects' internal structure
            return data

        if isinstance(data, dict):
            filtered = {}
            for key, value in data.items():
                # Skip if this item is inactive
                if self._has_active_false(value):
                    self.logger.debug(f"Filtering out inactive item: {key}")
                    continue

                # Recursively filter the value
                filtered_value = self._filter_data(value)

                # Only include if there's content after filtering
                if self._has_content(filtered_value):
                    filtered[key] = filtered_value

            return filtered

        elif isinstance(data, list):
            filtered = []
            for item in data:
                # Skip if this item is inactive
                if self._has_active_false(item):
                    name = self._get_name(item)
                    self.logger.debug(f"Filtering out inactive item: {name}")
                    continue

                # Recursively filter the item
                filtered_item = self._filter_data(item)

                # Only include if there's content after filtering
                if self._has_content(filtered_item):
                    filtered.append(filtered_item)

            return filtered

        else:
            # For non-dict/list types, return as-is
            return data

    def _has_active_false(self, data: Any) -> bool:
        """Check if data has active=false at the top level.

        Args:
            data: Data to check

        Returns:
            True if data has active=false, False otherwise
        """
        # Handle model objects
        if hasattr(data, "config") and hasattr(data.config, "active"):
            return not bool(data.config.active)

        if hasattr(data, "active"):
            return not bool(data.active)

        # Handle dicts
        if isinstance(data, dict):
            # Check direct active field
            if "active" in data:
                return not bool(data["active"])

            # Check config.active
            if "config" in data and isinstance(data["config"], dict):
                if "active" in data["config"]:
                    return not bool(data["config"]["active"])

        # Default to active (not filtered)
        return False

    def _has_content(self, data: Any) -> bool:
        """Check if data has meaningful content after filtering.

        Args:
            data: Data to check

        Returns:
            True if data has content, False if it's empty
        """
        if isinstance(data, (dict, list)):
            return len(data) > 0
        return data is not None

    def _get_name(self, data: Any) -> str:
        """Extract name from data for logging purposes.

        Args:
            data: Data to extract name from

        Returns:
            Name string or "unknown"
        """
        if hasattr(data, "name"):
            return str(data.name)

        if isinstance(data, dict) and "name" in data:
            return str(data["name"])

        return "unknown"

    def get_inactive_counts(self, data: dict[str, Any]) -> dict[str, int]:
        """Get counts of inactive items in the data.

        Useful for logging and reporting.

        Args:
            data: Data dictionary to analyze

        Returns:
            Dictionary with counts of inactive items by entity type
        """
        counts = {"workspaces": 0, "contexts": 0, "components": 0}

        # Count inactive items in each entity type
        for entity_type, plural_key in [
            ("workspace", "workspaces"),
            ("context", "contexts"),
            ("component", "components"),
        ]:
            if plural_key in data:
                entities = data[plural_key]
                if isinstance(entities, dict):
                    for entity_data in entities.values():
                        if self._has_active_false(entity_data):
                            counts[plural_key] += 1
                elif isinstance(entities, list):
                    for entity in entities:
                        if self._has_active_false(entity):
                            counts[plural_key] += 1
        self.logger.debug(f"Inactive counts: {counts}")
        return counts

    def filter_complete_model(
        self, complete_model: dict[str, dict[str, Any]], include_inactive: bool = False
    ) -> dict[str, dict[str, Any]]:
        """
        Filter inactive elements from a complete model with parent-child awareness.

        When a context is inactive, all its components are also filtered out.

        Args:
            complete_model: Complete model with 'workspaces', 'contexts', 'components'
            include_inactive: If True, include inactive items

        Returns:
            Filtered complete model
        """
        if include_inactive:
            return complete_model

        # Start with empty result
        result: dict[str, dict[str, Any]] = {
            "workspaces": {},
            "contexts": {},
            "components": {},
        }

        # Filter workspaces (they don't have active flag)
        result["workspaces"] = complete_model.get("workspaces", {}).copy()

        # Filter contexts - keep only active ones
        active_contexts = set()
        for name, context in complete_model.get("contexts", {}).items():
            if getattr(context, "active", True):  # Default to active if no field
                result["contexts"][name] = context
                active_contexts.add(name)

        # Filter components - keep only if component is active AND context is active
        for key, component in complete_model.get("components", {}).items():
            context_name = key.split("/")[0]

            # Skip if context is inactive
            if context_name not in active_contexts:
                continue

            # Skip if component itself is inactive
            component_active = True
            if hasattr(component, "config") and hasattr(component.config, "active"):
                component_active = bool(component.config.active)
            elif hasattr(component, "active"):
                component_active = bool(component.active)

            if component_active:
                result["components"][key] = component

        return result
