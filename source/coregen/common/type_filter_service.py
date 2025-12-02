"""
Type filter service for filtering results by entity type.

This module provides a centralized type filtering system that can be used across
all services that need to filter results by entity type (workspace, context, component).
"""

from typing import Any

from coregen.common.logger import Logger


class TypeFilterService:
    """Service for filtering results by entity type with hierarchical rules.

    This service handles:
    - Filtering data by entity type (workspace, context, component)
    - Applying hierarchical rules (workspace includes all, context includes components)
    - Ensuring consistent type filtering across commands

    Hierarchy rules:
    - workspace: includes everything (workspaces, contexts, components)
    - context: includes contexts and their components
    - component: includes only components

    Attributes:
        logger: Logger instance for this service
    """

    def __init__(self, logger: Logger | None = None):
        """Initialize the type filter service.

        Args:
            logger: Optional logger instance, creates new one if not provided
        """
        self.logger = logger or Logger(__name__)

    def filter_by_type(self, data: dict[str, Any], entity_type: str) -> dict[str, Any]:
        """Filter data by entity type with hierarchy.

        Args:
            data: Dictionary with workspaces, contexts, components
            entity_type: Type to filter by (workspace, context, component)

        Returns:
            Filtered dictionary containing only the requested entity types
        """
        self.logger.debug(f"Filtering data by entity type: {entity_type}")

        # Normalize entity type
        entity_type = entity_type.lower() if entity_type else "workspace"

        # Get included types based on hierarchy
        included_types = self.get_included_types(entity_type)

        # Apply filtering based on included types
        return self.apply_hierarchy_filter(data, included_types)

    def get_included_types(self, entity_type: str) -> list[str]:
        """Get list of entity types to include based on hierarchy.

        Args:
            entity_type: The requested entity type

        Returns:
            List of entity types to include in the result
        """
        entity_type = entity_type.lower()

        if entity_type == "workspace":
            # Workspace level includes everything
            return ["workspaces", "contexts", "components"]
        elif entity_type == "context":
            # Context level includes contexts and their components
            return ["contexts", "components"]
        elif entity_type == "component":
            # Component level includes only components
            return ["components"]
        else:
            # Unknown type, default to workspace
            self.logger.warning(
                f"Unknown entity type: {entity_type}, defaulting to workspace"
            )
            return ["workspaces", "contexts", "components"]

    def apply_hierarchy_filter(
        self, data: dict[str, Any], included_types: list[str]
    ) -> dict[str, Any]:
        """Apply hierarchical filtering rules.

        Args:
            data: Original data dictionary
            included_types: List of entity types to include

        Returns:
            Filtered data with only included entity types
        """
        filtered_result = {}

        # Always include these entity type keys for consistency
        for entity_type in ["workspaces", "contexts", "components"]:
            if entity_type in included_types and entity_type in data:
                # Include the data for this entity type
                filtered_result[entity_type] = data[entity_type]
            else:
                # Set to empty structure (dict or list depending on format)
                if entity_type in data:
                    if isinstance(data[entity_type], list):
                        filtered_result[entity_type] = []
                    else:
                        filtered_result[entity_type] = {}
                else:
                    # Default to dict for nested format
                    filtered_result[entity_type] = {}

        # Special handling for context filtering
        if "contexts" in included_types and "workspaces" not in included_types:
            # When filtering by context, we need to also filter out workspaces
            # that don't have any matching contexts
            self._filter_orphaned_workspaces(filtered_result)

        # Special handling for component filtering
        if "components" in included_types and "contexts" not in included_types:
            # When filtering by component only, clear contexts
            if isinstance(filtered_result.get("contexts"), dict):
                filtered_result["contexts"] = {}
            else:
                filtered_result["contexts"] = []

        return filtered_result

    def _filter_orphaned_workspaces(self, data: dict[str, Any]) -> None:
        """Remove workspaces that don't have any contexts after filtering.

        This is used when filtering by context type to ensure we don't
        show empty workspaces.

        Args:
            data: Data dictionary to filter in place
        """
        if "workspaces" in data and isinstance(data["workspaces"], dict):
            # Track which workspaces have contexts
            workspaces_with_contexts = set()

            # Check contexts to see which workspaces they belong to
            if "contexts" in data and isinstance(data["contexts"], dict):
                for context_name, context_data in data["contexts"].items():
                    if isinstance(context_data, dict) and "workspace" in context_data:
                        workspaces_with_contexts.add(context_data["workspace"])

            # Remove workspaces without contexts
            workspaces_to_remove = []
            for workspace_name in data["workspaces"]:
                if workspace_name not in workspaces_with_contexts:
                    workspaces_to_remove.append(workspace_name)

            for workspace_name in workspaces_to_remove:
                del data["workspaces"][workspace_name]
                self.logger.debug(
                    f"Removed workspace '{workspace_name}' (no matching contexts)"
                )

    def get_entity_type_counts(self, data: dict[str, Any]) -> dict[str, int]:
        """Get counts of each entity type in the data.

        Useful for logging and debugging.

        Args:
            data: Data dictionary to count

        Returns:
            Dictionary with counts for each entity type
        """
        counts = {}

        for entity_type in ["workspaces", "contexts", "components"]:
            if entity_type in data:
                if isinstance(data[entity_type], dict):
                    counts[entity_type] = len(data[entity_type])
                elif isinstance(data[entity_type], list):
                    counts[entity_type] = len(data[entity_type])
                else:
                    counts[entity_type] = 0
            else:
                counts[entity_type] = 0

        return counts

    def filter_exclusive(
        self, data: dict[str, Any], entity_type: str
    ) -> dict[str, Any]:
        """Filter data to include ONLY the specified entity type with no parent/child data.

        This method handles both flat and nested data structures:
        - Flat format (multiple entity keys): Returns only the requested entity type
        - Nested format (single entity key): Returns structure with child data removed

        Args:
            data: Dictionary containing entities (can be flat or nested format)
            entity_type: Type to filter by (workspace, context, component)

        Returns:
            Filtered dictionary based on format and entity type
        """
        self.logger.debug(f"Applying exclusive type filter: {entity_type}")

        # Normalize entity type
        entity_type = entity_type.lower() if entity_type else "workspace"

        # Detect structure type and apply appropriate filtering
        if self._is_flat_structure(data):
            return self._filter_flat_structure(data, entity_type)
        else:
            return self._filter_nested_structure(data, entity_type)

    def _is_flat_structure(self, data: dict[str, Any]) -> bool:
        """Detect if data is in flat format (values are lists instead of dicts).

        Args:
            data: Dictionary to check

        Returns:
            True if flat format, False if nested format
        """
        # Check if any of the entity values are lists (flat format)
        for entity_type in ["workspaces", "contexts", "components"]:
            if entity_type in data and isinstance(data[entity_type], list):
                return True
        return False

    def _filter_flat_structure(
        self, data: dict[str, Any], entity_type: str
    ) -> dict[str, Any]:
        """Filter flat format data to include only the specified entity type.

        Args:
            data: Flat format data with lists as values
            entity_type: Type to keep (workspace, context, component)

        Returns:
            Dictionary with only the requested entity type
        """
        self.logger.debug(f"Filtering flat structure for entity type: {entity_type}")

        # Create a new dictionary with only the requested entity type
        filtered_data: dict[str, Any] = {}

        if entity_type == "workspace" and "workspaces" in data:
            filtered_data["workspaces"] = data["workspaces"]
        elif entity_type == "context" and "contexts" in data:
            # For contexts in flat format, we need to handle lists
            if isinstance(data["contexts"], list):
                # Process each context in the list
                filtered_contexts = []
                for context in data["contexts"]:
                    # Convert to dict if needed
                    if hasattr(context, "model_dump"):
                        context_dict = context.model_dump(exclude_defaults=False)
                    elif isinstance(context, dict):
                        context_dict = dict(context)
                    else:
                        filtered_contexts.append(context)
                        continue

                    # Remove nested data for contexts
                    if "app" in context_dict:
                        del context_dict["app"]
                    if "component" in context_dict:
                        del context_dict["component"]
                    if "components" in context_dict:
                        del context_dict["components"]

                    filtered_contexts.append(context_dict)
                filtered_data["contexts"] = filtered_contexts
            else:
                # Fallback for dict format (shouldn't happen in flat format)
                filtered_data["contexts"] = data["contexts"]
        elif entity_type == "component" and "components" in data:
            # Preserve the sorted order from the input data
            filtered_data["components"] = data["components"]
        else:
            self.logger.warning(
                f"Unknown entity type: {entity_type}, returning empty result"
            )

        return filtered_data

    def _filter_nested_structure(
        self, data: dict[str, Any], entity_type: str
    ) -> dict[str, Any]:
        """Filter nested format data by extracting only the requested entity type.

        Args:
            data: Nested format data with single entity type key
            entity_type: Type being filtered (workspace, context, or component)

        Returns:
            Dictionary containing only the requested entity type
        """
        self.logger.debug(f"Filtering nested structure for entity type: {entity_type}")

        # If requesting workspaces, just remove child data
        if entity_type == "workspace":
            result = {}
            for key, entities in data.items():
                if not isinstance(entities, dict):
                    result[key] = entities
                    continue

                result[key] = {}
                for name, entity in entities.items():
                    # Convert model to dict if needed
                    if hasattr(entity, "model_dump"):
                        entity_dict = entity.model_dump(exclude_defaults=False)
                    elif isinstance(entity, dict):
                        entity_dict = dict(entity)
                    else:
                        result[key][name] = entity
                        continue

                    # Remove contexts from workspaces
                    if "contexts" in entity_dict:
                        del entity_dict["contexts"]

                    result[key][name] = entity_dict
            return result

        # For contexts and components, we need to extract from nested structure
        elif entity_type == "context":
            contexts = {}

            # Extract contexts from workspaces
            if "workspaces" in data:
                for ws_name, workspace in data["workspaces"].items():
                    # Convert workspace to dict if it's a model
                    if hasattr(workspace, "model_dump"):
                        workspace = workspace.model_dump(exclude_defaults=False)

                    if isinstance(workspace, dict) and "contexts" in workspace:
                        # Contexts are organized by type (e.g., "cluster", "context")
                        for context_type, type_contexts in workspace[
                            "contexts"
                        ].items():
                            if isinstance(type_contexts, dict):
                                for ctx_name, context in type_contexts.items():
                                    # Convert model to dict if needed
                                    if hasattr(context, "model_dump"):
                                        ctx_dict = context.model_dump(
                                            exclude_defaults=False
                                        )
                                    elif isinstance(context, dict):
                                        ctx_dict = dict(context)
                                    else:
                                        contexts[ctx_name] = context
                                        continue

                                    # Remove child data (components, app, component)
                                    if "components" in ctx_dict:
                                        del ctx_dict["components"]
                                    if "app" in ctx_dict:
                                        del ctx_dict["app"]
                                    if "component" in ctx_dict:
                                        del ctx_dict["component"]

                                    contexts[ctx_name] = ctx_dict

            # Also check if contexts are at the root level
            elif "contexts" in data:
                for ctx_name, context in data["contexts"].items():
                    # Convert model to dict if needed
                    if hasattr(context, "model_dump"):
                        ctx_dict = context.model_dump(exclude_defaults=False)
                    elif isinstance(context, dict):
                        ctx_dict = dict(context)
                    else:
                        contexts[ctx_name] = context
                        continue

                    # Remove child data
                    if "components" in ctx_dict:
                        del ctx_dict["components"]
                    if "app" in ctx_dict:
                        del ctx_dict["app"]
                    if "component" in ctx_dict:
                        del ctx_dict["component"]

                    contexts[ctx_name] = ctx_dict

            return {"contexts": contexts}

        elif entity_type == "component":
            components = {}

            # Extract components from nested structure
            if "workspaces" in data:
                # Components are nested: workspaces -> contexts -> components
                for ws_name, workspace in data["workspaces"].items():
                    # Convert workspace to dict if it's a model
                    if hasattr(workspace, "model_dump"):
                        workspace = workspace.model_dump(exclude_defaults=False)

                    if isinstance(workspace, dict) and "contexts" in workspace:
                        for context_type, type_contexts in workspace[
                            "contexts"
                        ].items():
                            if isinstance(type_contexts, dict):
                                for ctx_name, context in type_contexts.items():
                                    if (
                                        isinstance(context, dict)
                                        and "components" in context
                                    ):
                                        for comp_type, type_components in context[
                                            "components"
                                        ].items():
                                            if isinstance(type_components, dict):
                                                for (
                                                    comp_name,
                                                    component,
                                                ) in type_components.items():
                                                    # Use full path as key
                                                    full_name = (
                                                        f"{ctx_name}/{comp_name}"
                                                    )
                                                    components[full_name] = component

            # Also check if contexts are at root level
            elif "contexts" in data:
                for ctx_name, context in data["contexts"].items():
                    if isinstance(context, dict) and "components" in context:
                        for comp_type, type_components in context["components"].items():
                            if isinstance(type_components, dict):
                                for comp_name, component in type_components.items():
                                    # Use full path as key
                                    full_name = f"{ctx_name}/{comp_name}"
                                    components[full_name] = component

            # Or if components are at root level
            elif "components" in data:
                components = data["components"]

            return {"components": components}

        else:
            self.logger.warning(f"Unknown entity type: {entity_type}")
            return data
