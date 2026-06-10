"""
Format type service for applying flat/nested formatting to results.

This module provides a centralized formatting system that can be used across
all services that need to format workspaces, contexts, and components output.
"""

from typing import Any

from coregen.common import format_flat, format_nested
from coregen.common.logger import Logger


class FormatTypeService:
    """Service for applying flat or nested formatting to configuration results.

    This service handles:
    - Converting between flat and nested formats for YAML/JSON output
    - Ensuring consistent formatting across get, config view, and detect-changes commands
    - Separating entity types in flat format with proper structure

    Attributes:
        logger: Logger instance for this service
    """

    def __init__(self, logger: Logger | None = None):
        """Initialize the format service.

        Args:
            logger: Optional logger instance, creates new one if not provided
        """
        self.logger = logger or Logger(__name__)

    def apply_format(
        self,
        data: dict[str, Any],
        format_type: str,
        type_filter: str | None = None,
        entity_resolution: Any | None = None,
    ) -> dict[str, Any]:
        """Apply flat or nested formatting to results.

        Args:
            data: Dictionary with workspaces, contexts, components
            format_type: Either "flat" or "nested"
            type_filter: Optional entity type filter (affects nested data inclusion)
            entity_resolution: Optional entity resolution to filter entity types

        Returns:
            Formatted dictionary based on format_type
        """
        self.logger.debug(
            f"Applying {format_type} format to data with type_filter={type_filter}"
        )

        if format_type.lower() == "flat":
            result = self.flatten_results(data, type_filter)

            # Apply exclusive type filtering for flat format when type_filter is specified
            if type_filter:
                from coregen.common.type_filter_service import TypeFilterService

                type_filter_service = TypeFilterService(self.logger)
                result = type_filter_service.filter_exclusive(result, type_filter)
        else:
            # Nested is the default format, ensure proper structure
            result = self.ensure_nested_structure(data)

        # Apply entity resolution filtering if provided
        if entity_resolution and hasattr(entity_resolution, "included_entities"):
            filtered_result = {}
            # Process entity types in consistent order
            entity_order = ["workspaces", "contexts", "components"]

            # Special handling for nested format when only components are requested
            if (
                format_type.lower() == "nested"
                and entity_resolution.included_entities == {"components"}
            ):
                # Check if components are already at the top level (from cm/* patterns)
                # or need to be extracted from nested contexts (from c/* or w/* patterns)
                components_dict = {}

                # First, check if components are already in the top-level components dict
                if "components" in result and result["components"]:
                    # Components are already at the top level (e.g., from cm/* patterns)
                    components_dict = result["components"]
                elif "contexts" in result and result["contexts"]:
                    # Extract components from nested contexts (e.g., from c/* patterns)
                    for ctx_name, ctx_data in result["contexts"].items():
                        if isinstance(ctx_data, dict) and "components" in ctx_data:
                            for comp_name, comp_data in ctx_data["components"].items():
                                # Use context/component format for key
                                comp_key = f"{ctx_name}/{comp_name}"
                                components_dict[comp_key] = comp_data

                if components_dict:
                    # Convert to array, sort, and set in result
                    # This ensures consistent sorting when --type component is used
                    filtered_result["components"] = (
                        self._components_dict_to_sorted_array(
                            components_dict, result, resolve_workspace=True
                        )
                    )
            else:
                # Standard entity resolution filtering
                for entity_type in entity_order:
                    if entity_type not in result:
                        continue

                    # Special case: For nested format with context queries (c/*),
                    # don't include top-level components - they should only appear nested
                    if (
                        entity_type == "components"
                        and format_type.lower() == "nested"
                        and "contexts" in entity_resolution.included_entities
                        and "workspaces" not in entity_resolution.included_entities
                    ):
                        # Skip top-level components for context-only queries in nested format
                        continue

                    if entity_type in entity_resolution.included_entities:
                        filtered_result[entity_type] = result[entity_type]

            # Add any other entity types that might exist but aren't in our standard order
            for entity_type in result:
                if (
                    entity_type not in entity_order
                    and entity_type in entity_resolution.included_entities
                ):
                    filtered_result[entity_type] = result[entity_type]

            # Special handling: when components are the ONLY entity type,
            # convert them to array format (nested and flat are the same for components)
            if (
                entity_resolution.included_entities == {"components"}
                and "components" in filtered_result
                and isinstance(filtered_result["components"], dict)
            ):
                # Convert components dict to array format
                filtered_result["components"] = self._components_dict_to_sorted_array(
                    filtered_result["components"], result, resolve_workspace=False
                )

            return filtered_result

        return result

    def _components_dict_to_sorted_array(
        self,
        components_dict: dict[str, Any],
        result: dict[str, Any],
        resolve_workspace: bool,
    ) -> list[dict[str, Any]]:
        """Convert a components dict to a field-ordered array.

        Shared by the two entity-resolution branches that turn a
        components-only result into array form. Both coerce models to dicts,
        parse the ``context/name`` key, and apply field ordering. The
        ``resolve_workspace`` flag selects the richer extraction branch
        behavior (look up a missing workspace from the parent context and
        always derive the name from the key) versus the lighter branch that
        only fills a missing name.

        Args:
            components_dict: Mapping of component key to model or dict.
            result: The surrounding result, used for parent-context lookups.
            resolve_workspace: When True, resolve a missing workspace from the
                parent context and always set name from the key.

        Returns:
            List of field-ordered component dicts.
        """
        components_array: list[dict[str, Any]] = []
        for comp_key, comp_data in components_dict.items():
            comp_dict: dict[str, Any] = {}
            if hasattr(comp_data, "model_dump"):
                comp_dict = comp_data.model_dump(exclude_defaults=False)
            elif isinstance(comp_data, dict):
                comp_dict = dict(comp_data)
            else:
                continue

            ctx_name = ""
            if "/" in comp_key:
                ctx_name, comp_name = comp_key.split("/", 1)
                comp_dict["name"] = comp_name
                comp_dict["context"] = ctx_name
            elif resolve_workspace:
                comp_dict["name"] = comp_key
            elif "name" not in comp_dict:
                comp_dict["name"] = comp_key

            if resolve_workspace and "workspace" not in comp_dict:
                # Try to get workspace from the parent context
                if ctx_name in result.get("contexts", {}):
                    ctx_data = result["contexts"][ctx_name]
                    if isinstance(ctx_data, dict):
                        comp_dict["workspace"] = ctx_data.get("workspace", "unknown")
                    else:
                        comp_dict["workspace"] = "unknown"
                else:
                    comp_dict["workspace"] = "unknown"

            components_array.append(comp_dict)

        # Components from Context.get_all_components() are already sorted;
        # just apply field ordering for display.
        return [
            self._order_entity_fields(comp, "component") for comp in components_array
        ]

    def flatten_results(
        self,
        data: dict[str, Any],
        type_filter: str | None = None,
    ) -> dict[str, Any]:
        """Convert nested data to flat format with pure arrays.

        In flat format, entity types are separated at the top level as arrays.
        Each entity is self-contained with parent references.

        Args:
            data: Nested configuration data
            type_filter: Optional entity type filter that controls what's included

        Returns:
            Flattened dictionary with arrays:
            {
                "workspaces": [...],  # Array of workspace objects
                "contexts": [...],    # Array of context objects with workspace field
                "components": [...]   # Array of component objects with workspace and context fields
            }
        """
        return format_flat.flatten_results(
            data,
            type_filter,
            self.logger,
            self._order_entity_fields,
            self._convert_model_to_dict,
        )

    def _convert_model_to_dict(self, obj: Any) -> Any:
        """Convert a model to dict, excluding dynamic component type fields."""
        return format_flat.convert_model_to_dict(obj)

    def ensure_nested_structure(self, data: dict[str, Any]) -> dict[str, Any]:
        """Ensure data has proper nested structure.

        The nested format maintains the hierarchical relationship between
        entities. This is the default format for most operations.

        With prefix-based filtering, we may receive partial entity sets
        (e.g., only contexts and components for c/* patterns). This method
        preserves whatever entities are present without adding empty ones.

        Args:
            data: Dictionary that may or may not be properly nested

        Returns:
            Dictionary with proper nested structure
        """
        return format_nested.ensure_nested_structure(
            data,
            self.logger,
            self._convert_model_to_dict,
            self._flatten_context_components,
        )

    def _flatten_context_components(self, ctx_data: dict[str, Any]) -> None:
        """Flatten component structure within a context and remove component_type field.

        Args:
            ctx_data: Context dictionary to process (modified in place)
        """
        format_nested.flatten_context_components(ctx_data, self._convert_model_to_dict)

    def is_flat_format(self, data: dict[str, Any]) -> bool:
        """Check if data is in flat format.

        Args:
            data: Dictionary to check

        Returns:
            True if data appears to be in flat format (lists instead of dicts)
        """
        # Check if the main entity types are lists instead of dictionaries
        for entity_type in ["workspaces", "contexts", "components"]:
            if entity_type in data and isinstance(data[entity_type], list):
                return True
        return False

    def _order_entity_fields(
        self, entity: dict[str, Any], entity_type: str
    ) -> dict[str, Any]:
        """Order entity fields with priority fields first.

        Args:
            entity: Entity dictionary to order
            entity_type: Type of entity (workspace, context, component)

        Returns:
            Ordered dictionary with priority fields first
        """
        priority_fields = ["name"]

        if entity_type == "component":
            priority_fields.extend(["context", "workspace"])
        elif entity_type == "context":
            priority_fields.append("workspace")

        ordered = {}

        # Add priority fields first in order
        for field in priority_fields:
            if field in entity:
                ordered[field] = entity[field]

        # Add remaining fields alphabetically
        for key in sorted(entity.keys()):
            if key not in ordered:
                ordered[key] = entity[key]

        return ordered
