"""Flat-format conversion for configuration results.

Holds the flat-format projection of :class:`FormatTypeService`: the logic that
turns nested workspace/context/component data into top-level arrays. The public
entry point on the service delegates here, passing its own (patchable) helper
methods so test seams on the service instance are preserved.
"""

from collections.abc import Callable
from typing import Any

from coregen.common.logger import Logger


def convert_model_to_dict(obj: Any) -> Any:
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


def flatten_results(
    data: dict[str, Any],
    type_filter: str | None,
    logger: Logger,
    order_entity_fields: Callable[[dict[str, Any], str], dict[str, Any]],
    convert_model: Callable[[Any], Any],
) -> dict[str, Any]:
    """Convert nested data to flat format with pure arrays.

    In flat format, entity types are separated at the top level as arrays.
    Each entity is self-contained with parent references.

    Args:
        data: Nested configuration data
        type_filter: Optional entity type filter that controls what's included
        logger: Logger for debug output
        order_entity_fields: Callback applying display field ordering
        convert_model: Callback converting a model/dict (context-aware)

    Returns:
        Flattened dictionary with arrays:
        {
            "workspaces": [...],  # Array of workspace objects
            "contexts": [...],    # Array of context objects with workspace field
            "components": [...]   # Array of component objects with workspace and context fields
        }
    """
    logger.debug(f"Converting data to flat format with type_filter={type_filter}")
    logger.debug(f"Input data keys: {list(data.keys())}")

    flat_result: dict[str, list[Any]] = {
        "workspaces": [],
        "contexts": [],
        "components": [],
    }

    # Track processed components to avoid duplicates
    processed_components: set[str] = set()

    # Process workspaces
    if "workspaces" in data and isinstance(data["workspaces"], dict):
        logger.debug(f"Processing {len(data['workspaces'])} workspaces")
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
            logger.debug(f"Added workspace {ws_name} to array")

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
                                ctx_dict = convert_model(ctx_data)
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
                ctx_dict = convert_model(ctx_data)
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
                logger.warning(f"Context {ctx_name} missing workspace field")
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
                                comp_dict = comp_data.model_dump(exclude_defaults=False)
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
        order_entity_fields(ws, "workspace") for ws in flat_result["workspaces"]
    ]
    flat_result["contexts"] = [
        order_entity_fields(ctx, "context") for ctx in flat_result["contexts"]
    ]
    flat_result["components"] = [
        order_entity_fields(comp, "component") for comp in flat_result["components"]
    ]

    logger.debug(f"Final flat_result keys: {list(flat_result.keys())}")
    for key in flat_result:
        logger.debug(f"  {key}: {len(flat_result[key])} items")
    return flat_result
