"""Nested-format conversion for configuration results.

Holds the nested-format projection of :class:`FormatTypeService`: ensuring a
proper hierarchical workspace/context/component structure and flattening the
component substructure within a context. The public entry points on the service
delegate here, passing their own (patchable) helper methods so test seams on the
service instance are preserved.
"""

from collections.abc import Callable
from typing import Any

from coregen.common.logger import Logger


def ensure_nested_structure(
    data: dict[str, Any],
    logger: Logger,
    convert_model: Callable[[Any], Any],
    flatten_context_components: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    """Ensure data has proper nested structure.

    The nested format maintains the hierarchical relationship between
    entities. This is the default format for most operations.

    With prefix-based filtering, we may receive partial entity sets
    (e.g., only contexts and components for c/* patterns). This method
    preserves whatever entities are present without adding empty ones.

    Args:
        data: Dictionary that may or may not be properly nested
        logger: Logger for debug output
        convert_model: Callback converting a model/dict (context-aware)
        flatten_context_components: Callback flattening a context's components

    Returns:
        Dictionary with proper nested structure
    """
    logger.debug("Ensuring nested structure for data")

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
                ws_data = convert_model(ws_data)
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
                                    ctx = convert_model(ctx)
                                if isinstance(ctx, dict):
                                    flatten_context_components(ctx)
                                    flattened_contexts[ctx_name] = ctx
                        else:
                            # Direct context entry
                            flatten_context_components(ctx_data)
                            flattened_contexts[ctx_key] = ctx_data
                # Replace the grouped contexts with flattened version
                ws_data["contexts"] = flattened_contexts

    # Process top-level contexts
    if "contexts" in result and isinstance(result["contexts"], dict):
        for ctx_name, ctx_data in result["contexts"].items():
            if isinstance(ctx_data, dict):
                flatten_context_components(ctx_data)
            else:
                # ctx_data is a Context object, not a dict yet
                # Convert to dict first
                if hasattr(ctx_data, "model_dump"):
                    ctx_dict = convert_model(ctx_data)
                    result["contexts"][ctx_name] = ctx_dict
                    flatten_context_components(ctx_dict)

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
                            comp_dict = convert_model(comp_data)
                            comp_dict["name"] = comp_name
                            ctx_data["components"][comp_name] = comp_dict

            # After moving components to contexts, apply sorting to each context
            for ctx_name, ctx_data in result["contexts"].items():
                if isinstance(ctx_data, dict):
                    flatten_context_components(ctx_data)

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
                            comp_data.context = ctx_name

    return result


def flatten_context_components(
    ctx_data: dict[str, Any],
    convert_model: Callable[[Any], Any],
) -> None:
    """Flatten component structure within a context and remove component_type field.

    Args:
        ctx_data: Context dictionary to process (modified in place)
        convert_model: Callback converting a model/dict (context-aware)
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
                    (isinstance(v, dict) and ("config" in v or hasattr(v, "config")))
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
                        dict(value) if isinstance(value, dict) else convert_model(value)
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
                            else convert_model(comp_data)
                        )
                        comp_dict["name"] = comp_name
                        components_list.append(comp_dict)
            elif hasattr(value, "model_dump"):
                # Component is a Pydantic model
                comp_dict = convert_model(value)
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
