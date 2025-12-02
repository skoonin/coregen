"""
Format type service for applying flat/nested formatting to results.

This module provides a centralized formatting system that can be used across
all services that need to format workspaces, contexts, and components output.
"""

from typing import Any

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
                    components_array = []
                    for comp_key, comp_data in components_dict.items():
                        comp_dict = {}
                        if hasattr(comp_data, "model_dump"):
                            comp_dict = comp_data.model_dump(exclude_defaults=False)
                        elif isinstance(comp_data, dict):
                            comp_dict = dict(comp_data)
                        else:
                            continue

                        # Parse component key for context/name
                        if "/" in comp_key:
                            ctx_name, comp_name = comp_key.split("/", 1)
                            comp_dict["name"] = comp_name
                            comp_dict["context"] = ctx_name
                        else:
                            comp_dict["name"] = comp_key

                        # Ensure workspace is set
                        if "workspace" not in comp_dict:
                            # Try to get workspace from context
                            if ctx_name in result.get("contexts", {}):
                                ctx_data = result["contexts"][ctx_name]
                                if isinstance(ctx_data, dict):
                                    comp_dict["workspace"] = ctx_data.get(
                                        "workspace", "unknown"
                                    )
                                else:
                                    comp_dict["workspace"] = "unknown"
                            else:
                                comp_dict["workspace"] = "unknown"

                        components_array.append(comp_dict)

                    # Components from Context.get_all_components() are already sorted
                    # Just apply field ordering for display
                    sorted_components = [
                        self._order_entity_fields(comp, "component")
                        for comp in components_array
                    ]

                    filtered_result["components"] = sorted_components
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
                components_array = []
                for comp_key, comp_data in filtered_result["components"].items():
                    comp_dict = {}
                    if hasattr(comp_data, "model_dump"):
                        comp_dict = comp_data.model_dump(exclude_defaults=False)
                    elif isinstance(comp_data, dict):
                        comp_dict = dict(comp_data)
                    else:
                        continue

                    # If component key contains context (e.g., "context-name/component-name")
                    if "/" in comp_key:
                        ctx_name, comp_name = comp_key.split("/", 1)
                        comp_dict["name"] = comp_name
                        comp_dict["context"] = ctx_name
                    else:
                        # Ensure name is set
                        if "name" not in comp_dict:
                            comp_dict["name"] = comp_key

                    # Default paths are now set in ConfigProcessor
                    # No need to fix paths here

                    components_array.append(comp_dict)

                # Components from Context.get_all_components() are already sorted
                # Just apply field ordering for display
                components_array = [
                    self._order_entity_fields(comp, "component")
                    for comp in components_array
                ]

                filtered_result["components"] = components_array

            return filtered_result

        return result

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
        self.logger.debug(
            f"Converting data to flat format with type_filter={type_filter}"
        )
        self.logger.debug(f"Input data keys: {list(data.keys())}")

        flat_result: dict[str, list[Any]] = {
            "workspaces": [],
            "contexts": [],
            "components": [],
        }

        # Track processed components to avoid duplicates
        processed_components: set[str] = set()

        # Process workspaces
        if "workspaces" in data and isinstance(data["workspaces"], dict):
            self.logger.debug(f"Processing {len(data['workspaces'])} workspaces")
            for ws_name, ws_data in data["workspaces"].items():
                # Convert model to dict if needed
                if hasattr(ws_data, "model_dump"):
                    flat_ws = ws_data.model_dump(exclude_defaults=False)
                elif isinstance(ws_data, dict):
                    flat_ws = dict(ws_data)  # Copy all fields
                else:
                    continue

                # Remove nested data (contexts) from workspace
                if "contexts" in flat_ws:
                    del flat_ws["contexts"]

                # Ensure name field is set
                flat_ws["name"] = ws_name
                flat_result["workspaces"].append(flat_ws)
                self.logger.debug(f"Added workspace {ws_name} to array")

                # Extract nested contexts
                if "contexts" in ws_data and isinstance(ws_data["contexts"], dict):
                    # Check if contexts are grouped by type (e.g., "cluster": {...})
                    for key, value in ws_data["contexts"].items():
                        if (
                            isinstance(value, dict)
                            and len(value) > 0
                            and all(
                                isinstance(v, dict) or hasattr(v, "model_dump")
                                for v in value.values()
                            )
                        ):
                            # This is a context type grouping, extract the actual contexts
                            for ctx_name, ctx_data in value.items():
                                ctx_dict = {}
                                if hasattr(ctx_data, "model_dump"):
                                    ctx_dict = self._convert_model_to_dict(ctx_data)
                                elif isinstance(ctx_data, dict):
                                    ctx_dict = dict(ctx_data)
                                else:
                                    continue

                                # Remove nested components and component_type field
                                if "components" in ctx_dict:
                                    del ctx_dict["components"]
                                if "component_type" in ctx_dict:
                                    del ctx_dict["component_type"]

                                # Add parent reference and name
                                ctx_dict["name"] = ctx_name
                                ctx_dict["workspace"] = ws_name
                                flat_result["contexts"].append(ctx_dict)
                        else:
                            # Direct context entry
                            ctx_dict = {}
                            if hasattr(value, "model_dump"):
                                ctx_dict = value.model_dump(exclude_defaults=False)
                            elif isinstance(value, dict):
                                ctx_dict = dict(value)
                            else:
                                continue

                            # Remove nested components and component_type field
                            if "components" in ctx_dict:
                                del ctx_dict["components"]
                            if "component_type" in ctx_dict:
                                del ctx_dict["component_type"]

                            # Add parent reference and name
                            ctx_dict["name"] = key
                            ctx_dict["workspace"] = ws_name
                            flat_result["contexts"].append(ctx_dict)

        # Process contexts
        if "contexts" in data and isinstance(data["contexts"], dict):
            for ctx_name, ctx_data in data["contexts"].items():
                # Convert model to dict if needed
                ctx_dict = {}
                if hasattr(ctx_data, "model_dump"):
                    ctx_dict = self._convert_model_to_dict(ctx_data)
                elif isinstance(ctx_data, dict):
                    ctx_dict = dict(ctx_data)  # Copy all fields
                else:
                    continue

                # Extract components before removing them
                ctx_components = ctx_dict.get("components", {})

                # Remove nested data and component_type field
                if "components" in ctx_dict:
                    del ctx_dict["components"]
                if "component_type" in ctx_dict:
                    del ctx_dict["component_type"]

                # Add name and workspace reference if not already present
                ctx_dict["name"] = ctx_name
                # NEW ARCHITECTURE: Context should always have workspace from complete model
                if "workspace" not in ctx_dict:
                    self.logger.warning(f"Context {ctx_name} missing workspace field")
                    ctx_dict["workspace"] = "unknown"

                flat_result["contexts"].append(ctx_dict)

                # Extract nested components
                if ctx_components and isinstance(ctx_components, dict):
                    # Check if components are grouped by type (e.g., "app": {...})
                    for key, value in ctx_components.items():
                        if (
                            isinstance(value, dict)
                            and len(value) > 0
                            and all(
                                isinstance(v, dict) or hasattr(v, "model_dump")
                                for v in value.values()
                            )
                        ):
                            # This is a component type grouping, extract the actual components
                            for comp_name, comp_data in value.items():
                                # Create unique component key to avoid duplicates
                                comp_key = f"{ctx_name}/{comp_name}"
                                if comp_key in processed_components:
                                    continue
                                processed_components.add(comp_key)

                                comp_dict = {}
                                if hasattr(comp_data, "model_dump"):
                                    comp_dict = comp_data.model_dump(
                                        exclude_defaults=False
                                    )
                                elif isinstance(comp_data, dict):
                                    comp_dict = dict(comp_data)
                                else:
                                    continue

                                # Add parent references and name
                                comp_dict["name"] = comp_name
                                comp_dict["context"] = ctx_name
                                # NEW ARCHITECTURE: Use workspace from context
                                comp_dict["workspace"] = ctx_dict["workspace"]

                                # Default paths are now set in ConfigProcessor
                                # No need to fix paths here

                                flat_result["components"].append(comp_dict)
                        else:
                            # Direct component entry
                            comp_key = f"{ctx_name}/{key}"
                            if comp_key in processed_components:
                                continue
                            processed_components.add(comp_key)

                            comp_dict = {}
                            if hasattr(value, "model_dump"):
                                comp_dict = value.model_dump(exclude_defaults=False)
                            elif isinstance(value, dict):
                                comp_dict = dict(value)
                            else:
                                continue

                            # Add parent references and name
                            comp_dict["name"] = key
                            comp_dict["context"] = ctx_name
                            # NEW ARCHITECTURE: Use workspace from context
                            comp_dict["workspace"] = ctx_dict["workspace"]

                            # Default paths are now set in ConfigProcessor
                            # No need to fix paths here

                            flat_result["components"].append(comp_dict)

        # Process components (handle both nested and flat component structures)
        # Only process if not already handled from contexts
        if "components" in data and isinstance(data["components"], dict):
            for comp_key, comp_data in data["components"].items():
                # Check if component already processed from context
                if comp_key in processed_components:
                    continue
                processed_components.add(comp_key)

                if "/" in comp_key:
                    # Component key contains context (e.g., "context-name/component-name")
                    ctx_name, comp_name = comp_key.split("/", 1)

                    comp_dict = {}
                    if hasattr(comp_data, "model_dump"):
                        comp_dict = comp_data.model_dump(exclude_defaults=False)
                    elif isinstance(comp_data, dict):
                        comp_dict = dict(comp_data)
                    else:
                        continue

                    # Add parent references and name
                    comp_dict["name"] = comp_name
                    comp_dict["context"] = ctx_name

                    # Components from filter-first architecture always have workspace field
                    # No need for complex lookups anymore

                    # Default paths are now set in ConfigProcessor
                    # No need to fix paths here

                    flat_result["components"].append(comp_dict)
                else:
                    # Component without context in key - should have context field
                    comp_dict = {}
                    if hasattr(comp_data, "model_dump"):
                        comp_dict = comp_data.model_dump(exclude_defaults=False)
                    elif isinstance(comp_data, dict):
                        comp_dict = dict(comp_data)
                    else:
                        continue

                    # Add name if not present
                    if "name" not in comp_dict:
                        comp_dict["name"] = comp_key

                    # Ensure parent references
                    if "context" not in comp_dict:
                        comp_dict["context"] = "unknown"
                    if "workspace" not in comp_dict:
                        comp_dict["workspace"] = "unknown"

                    # Default paths are now set in ConfigProcessor
                    # No need to fix paths here

                    flat_result["components"].append(comp_dict)

        # Components from multiple contexts in flat format need to be sorted globally
        # since they come from different Context.get_all_components() calls
        # Import here to avoid circular dependency
        from coregen.common.component_sorter_service import ComponentSorterService

        sorter = ComponentSorterService()
        # Workspaces and contexts don't need special sorting
        flat_result["workspaces"] = sorted(
            flat_result["workspaces"], key=lambda x: x.get("name", "")
        )
        flat_result["contexts"] = sorted(
            flat_result["contexts"],
            key=lambda x: (x.get("workspace", ""), x.get("name", "")),
        )
        # Components from multiple contexts need global sorting
        flat_result["components"] = sorter.sort_entities(
            flat_result["components"], entity_type="component"
        )

        # Apply field ordering to each entity
        flat_result["workspaces"] = [
            self._order_entity_fields(ws, "workspace")
            for ws in flat_result["workspaces"]
        ]
        flat_result["contexts"] = [
            self._order_entity_fields(ctx, "context") for ctx in flat_result["contexts"]
        ]
        flat_result["components"] = [
            self._order_entity_fields(comp, "component")
            for comp in flat_result["components"]
        ]

        self.logger.debug(f"Final flat_result keys: {list(flat_result.keys())}")
        for key in flat_result:
            self.logger.debug(f"  {key}: {len(flat_result[key])} items")
        return flat_result

    def _convert_model_to_dict(self, obj: Any) -> Any:
        """Convert a model to dict, excluding dynamic component type fields."""
        if hasattr(obj, "model_dump"):
            # For Context models, exclude dynamic component type fields
            if hasattr(obj, "components") and hasattr(obj, "component_type"):
                # Get all component types from the components dict
                exclude_fields: set[str] = set()
                if isinstance(obj.components, dict):
                    exclude_fields.update(obj.components.keys())

                # Convert to dict excluding these fields
                result = obj.model_dump(exclude_defaults=False, exclude=exclude_fields)
            else:
                # Regular model dump
                result = obj.model_dump(exclude_defaults=False)

            return result
        elif isinstance(obj, dict):
            return dict(obj)
        else:
            return obj

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
        self.logger.debug("Ensuring nested structure for data")

        # Make a copy to avoid modifying the original, preserving entity order
        result = {}
        entity_order = ["workspaces", "contexts", "components"]

        # First add entities in the standard order
        for entity_type in entity_order:
            if entity_type in data:
                if isinstance(data[entity_type], dict):
                    result[entity_type] = dict(data[entity_type])
                else:
                    result[entity_type] = data[entity_type]

        # Then add any other keys that might exist
        for key, value in data.items():
            if key not in entity_order:
                if isinstance(value, dict):
                    result[key] = dict(value)
                else:
                    result[key] = value

        # Process workspaces
        if "workspaces" in result and isinstance(result["workspaces"], dict):
            for ws_name, ws_data in result["workspaces"].items():
                # Convert workspace model to dict if needed
                if not isinstance(ws_data, dict):
                    ws_data = self._convert_model_to_dict(ws_data)
                    result["workspaces"][ws_name] = ws_data

                if isinstance(ws_data, dict) and "contexts" in ws_data:
                    # Check if contexts are grouped by type (e.g., "cluster": {...})
                    flattened_contexts = {}
                    for ctx_key, ctx_data in ws_data["contexts"].items():
                        if isinstance(ctx_data, dict):
                            # If this is a context type grouping (e.g., "cluster": {...})
                            if all(
                                isinstance(v, dict) or hasattr(v, "model_dump")
                                for v in ctx_data.values()
                            ):
                                # This is a context type grouping, extract the actual contexts
                                for ctx_name, ctx in ctx_data.items():
                                    # Convert context model to dict if needed
                                    if not isinstance(ctx, dict):
                                        ctx = self._convert_model_to_dict(ctx)
                                    if isinstance(ctx, dict):
                                        self._flatten_context_components(ctx)
                                        flattened_contexts[ctx_name] = ctx
                            else:
                                # Direct context entry
                                self._flatten_context_components(ctx_data)
                                flattened_contexts[ctx_key] = ctx_data
                    # Replace the grouped contexts with flattened version
                    ws_data["contexts"] = flattened_contexts

        # Process top-level contexts
        if "contexts" in result and isinstance(result["contexts"], dict):
            for ctx_name, ctx_data in result["contexts"].items():
                if isinstance(ctx_data, dict):
                    self._flatten_context_components(ctx_data)
                else:
                    # ctx_data is a Context object, not a dict yet
                    # Convert to dict first
                    if hasattr(ctx_data, "model_dump"):
                        ctx_dict = self._convert_model_to_dict(ctx_data)
                        result["contexts"][ctx_name] = ctx_dict
                        self._flatten_context_components(ctx_dict)

        # Process top-level components
        if "components" in result and isinstance(result["components"], dict):
            # Check if we also have contexts with actual content - if so, nest components into contexts
            if (
                "contexts" in result
                and isinstance(result["contexts"], dict)
                and result["contexts"]
            ):
                # Move components into their respective contexts for nested format
                for comp_key, comp_data in list(result["components"].items()):
                    if "/" in comp_key:
                        # Component key contains context (e.g., "context-name/component-name")
                        ctx_name, comp_name = comp_key.split("/", 1)

                        # Find the context and add the component to it
                        if ctx_name in result["contexts"]:
                            ctx_data = result["contexts"][ctx_name]

                            # Ensure context has components dict
                            if "components" not in ctx_data:
                                ctx_data["components"] = {}

                            # Add component to context
                            if isinstance(comp_data, dict):
                                comp_data_copy = dict(comp_data)
                                comp_data_copy["name"] = comp_name
                                ctx_data["components"][comp_name] = comp_data_copy
                            elif hasattr(comp_data, "model_dump"):
                                comp_dict = self._convert_model_to_dict(comp_data)
                                comp_dict["name"] = comp_name
                                ctx_data["components"][comp_name] = comp_dict

                # After moving components to contexts, apply sorting to each context
                for ctx_name, ctx_data in result["contexts"].items():
                    if isinstance(ctx_data, dict):
                        self._flatten_context_components(ctx_data)

                # Remove the top-level components since they're now nested
                del result["components"]
            else:
                # No contexts, just ensure component references are set
                for comp_key, comp_data in result["components"].items():
                    if "/" in comp_key:
                        # Component key contains context (e.g., "context-name/component-name")
                        ctx_name, comp_name = comp_key.split("/", 1)

                        # Ensure component has parent references
                        if isinstance(comp_data, dict):
                            comp_data["name"] = comp_name
                            comp_data["context"] = ctx_name
                            if "workspace" not in comp_data:
                                comp_data["workspace"] = comp_data.get(
                                    "workspace", "unknown"
                                )
                        elif hasattr(comp_data, "name"):
                            # It's a model object, update attributes if possible
                            if not hasattr(comp_data, "context"):
                                comp_data.context = ctx_name  # type: ignore

        return result

    def _flatten_context_components(self, ctx_data: dict[str, Any]) -> None:
        """Flatten component structure within a context and remove component_type field.

        Args:
            ctx_data: Context dictionary to process (modified in place)
        """
        # Remove component_type field
        if "component_type" in ctx_data:
            del ctx_data["component_type"]

        # Check for direct component type fields (e.g., "app", "infra")
        # These are duplicate data that should be removed
        component_type_fields = []
        for field in ctx_data:
            if field not in [
                "name",
                "workspace",
                "environment",
                "active",
                "components",
                "archive_dir",
                "output_dir",
                "commit_dir",
                "path",
                "internal_path",
                "config_file_path",
                "resolved_paths",
                "skip_validation",
                "workspace_ref",
            ] and isinstance(ctx_data.get(field), dict):
                # Check if this looks like a component type field
                field_data = ctx_data[field]
                if field_data and all(
                    (isinstance(v, dict) and "config" in v) or hasattr(v, "config")
                    for v in field_data.values()
                ):
                    component_type_fields.append(field)

        # Remove duplicate component type fields
        for field in component_type_fields:
            del ctx_data[field]

        # Flatten and sort components structure
        if "components" in ctx_data and isinstance(ctx_data["components"], dict):
            # First, collect all components into a list
            components_list = []

            # Check if any component key looks like a component type (has nested components)
            has_nested_structure = False
            for key, value in ctx_data["components"].items():
                if (
                    isinstance(value, dict)
                    and value
                    and all(
                        (
                            isinstance(v, dict)
                            and ("config" in v or hasattr(v, "config"))
                        )
                        for v in value.values()
                        if isinstance(v, dict)
                    )
                ):
                    has_nested_structure = True
                    break

            # Process components based on structure
            for key, value in ctx_data["components"].items():
                if isinstance(value, dict):
                    # If components are already flat (all top-level keys are component names)
                    # OR if this is a direct component (has 'config' field at top level)
                    if (
                        not has_nested_structure
                        or "config" in value
                        or hasattr(value, "config")
                    ):
                        # This is a direct component
                        comp_dict = (
                            dict(value)
                            if isinstance(value, dict)
                            else self._convert_model_to_dict(value)
                        )
                        comp_dict["name"] = key
                        components_list.append(comp_dict)
                    # Otherwise check if this is a component type grouping
                    # A component type grouping would have components as nested values
                    elif value and all(
                        (isinstance(v, dict) and "config" in v) or hasattr(v, "config")
                        for v in value.values()
                    ):
                        # This is a component type grouping, extract components
                        for comp_name, comp_data in value.items():
                            comp_dict = (
                                comp_data
                                if isinstance(comp_data, dict)
                                else self._convert_model_to_dict(comp_data)
                            )
                            comp_dict["name"] = comp_name
                            components_list.append(comp_dict)
                elif hasattr(value, "model_dump"):
                    # Component is a Pydantic model
                    comp_dict = self._convert_model_to_dict(value)
                    comp_dict["name"] = key
                    components_list.append(comp_dict)

            # Sort components using ComponentSorterService to ensure proper ordering
            # This matches the pattern in flatten_results() and ensures formatters receive sorted data
            from coregen.common.component_sorter_service import ComponentSorterService

            sorter = ComponentSorterService()
            sorted_components = sorter.sort_entities(
                components_list, entity_type="component"
            )

            # Rebuild as regular dict with components in sorted order
            # Using regular dict since Python 3.7+ preserves insertion order
            ordered_components = {}
            for comp in sorted_components:
                comp_name = comp.get("name", "unknown")  # Get name without removing it
                # Remove the temporary name field we added for sorting
                comp_copy = dict(comp)
                if "name" in comp_copy:
                    del comp_copy["name"]
                ordered_components[comp_name] = comp_copy

            ctx_data["components"] = ordered_components

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
