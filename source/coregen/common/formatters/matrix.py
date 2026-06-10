"""Matrix formatter for GitHub Actions matrix format."""

import json
import logging
from pathlib import Path
from typing import Any

from .base import BaseFormatter

logger = logging.getLogger(__name__)


class MatrixFormatter(BaseFormatter):
    """
    Matrix formatter for GitHub Actions matrix format.

    It formats data specifically for GitHub Actions matrix strategy,
    it must be a flat dictionary and it will wrap it in an `include` array.

    Examples:
        >>> formatter = MatrixFormatter()
        >>> data = {"name": "test", "value": 123}
        >>> print(formatter.format(data))
        {
            "include": [
                {
                    "name": "test",
                    "value": 123
                }
            ]
        }
    """

    def __init__(self) -> None:
        """Initialize the matrix formatter."""
        super().__init__()
        self._format_type_service = None

    @property
    def format_type_service(self) -> Any:
        """Lazy-load format type service to avoid circular imports."""
        if self._format_type_service is None:
            from coregen.common.format_type_service import FormatTypeService

            self._format_type_service = FormatTypeService()
        return self._format_type_service

    def flatten_for_matrix(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Flatten entities for GitHub Actions matrix format with prefixed fields.

        Matrix format requires a flat structure where each entity has all its fields
        prefixed with the entity type (e.g., component_name, context_active).

        Uses precedence-based early returns to eliminate duplicates:
        1. If components exist → return only component matrix items (most specific)
        2. Else if contexts exist → return only context matrix items
        3. Else return workspace matrix items (least specific)

        Args:
            data: Dictionary with workspaces, contexts, components

        Returns:
            List of flattened entities with prefixed fields
        """
        logger.debug("Flattening data for matrix format")

        # First ensure we have flat format
        flat_data = (
            self.format_type_service.flatten_results(data)
            if not self.format_type_service.is_flat_format(data)
            else data
        )

        # If we only have components and they're already in list format, create empty lists for others
        if (
            self.format_type_service.is_flat_format(data)
            and "components" in data
            and isinstance(data["components"], list)
        ):
            if "contexts" not in flat_data:
                flat_data["contexts"] = []
            if "workspaces" not in flat_data:
                flat_data["workspaces"] = []

        # Process based on entities discovered - handle most relevant entity type found

        # 1. Components discovered - if any exist, return only these
        components = flat_data.get("components", [])
        if components:
            logger.debug(
                f"Processing {len(components)} components from discovered entities"
            )
            matrix_items = []
            for comp in components:
                matrix_item = self._build_matrix_item("component", comp, flat_data)
                matrix_items.append(matrix_item)
            return matrix_items

        # 2. Contexts discovered - if any exist and no components, return only these
        contexts = flat_data.get("contexts", [])
        if contexts:
            logger.debug(
                f"Processing {len(contexts)} contexts from discovered entities"
            )
            matrix_items = []
            for ctx in contexts:
                matrix_item = self._build_matrix_item("context", ctx, flat_data)
                matrix_items.append(matrix_item)
            return matrix_items

        # 3. Workspaces discovered - only if no components or contexts exist
        workspaces = flat_data.get("workspaces", [])
        logger.debug(
            f"Processing {len(workspaces)} workspaces from discovered entities"
        )
        matrix_items = []
        for ws in workspaces:
            matrix_item = self._build_matrix_item("workspace", ws, flat_data)
            matrix_items.append(matrix_item)
        return matrix_items

    def _build_matrix_item(
        self, entity_type: str, entity: dict[str, Any], flat_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Build matrix item from entity data with proper field prefixing and command generation.

        Args:
            entity_type: Type of entity ("component", "context", "workspace")
            entity: The entity data dictionary
            flat_data: Full flat data structure for lookups

        Returns:
            Matrix item with prefixed fields and proper command
        """
        matrix_item: dict[str, Any] = {}

        # Add entity fields with prefix
        self._add_prefixed_fields(matrix_item, entity_type, entity)

        # Add related entity fields based on type
        if entity_type == "component":
            # Components need context and workspace fields
            ctx_name = entity.get("context")
            ws_name = entity.get("workspace")

            if ctx_name:
                context = self._find_entity_by_name(
                    flat_data.get("contexts", []), ctx_name
                )
                if context:
                    self._add_prefixed_fields(matrix_item, "context", context)

            if ws_name:
                workspace = self._find_entity_by_name(
                    flat_data.get("workspaces", []), ws_name
                )
                if workspace:
                    self._add_prefixed_fields(matrix_item, "workspace", workspace)

            # Set top-level identifier fields
            matrix_item["component"] = entity.get("name", "")
            matrix_item["context"] = ctx_name or ""
            matrix_item["workspace"] = ws_name or ""
            # Add environment as top-level field from component
            env_value = entity.get("environment")
            matrix_item["environment"] = env_value
            # Also add context_environment for consistency
            matrix_item["context_environment"] = env_value

        elif entity_type == "context":
            # Contexts need workspace fields
            ws_name = entity.get("workspace")
            ctx_name = entity.get("name", "")

            if ws_name:
                workspace = self._find_entity_by_name(
                    flat_data.get("workspaces", []), ws_name
                )
                if workspace:
                    # Skip the workspace name field to avoid duplication
                    workspace_filtered = {
                        k: v
                        for k, v in workspace.items()
                        if k not in ["name", "contexts"]
                    }
                    self._add_prefixed_fields(
                        matrix_item, "workspace", workspace_filtered
                    )

            # Set top-level identifier fields
            matrix_item["context"] = ctx_name
            matrix_item["workspace"] = ws_name or ""

        else:  # workspace
            # Workspaces are standalone
            ws_name = entity.get("name", "")
            matrix_item["workspace"] = ws_name

        # Add command field
        matrix_item["command"] = self._build_command(entity_type, matrix_item)

        return matrix_item

    def _add_prefixed_fields(
        self, matrix_item: dict[str, Any], prefix: str, entity: dict[str, Any]
    ) -> None:
        """Add entity fields to matrix item with proper prefixing and special handling.

        Args:
            matrix_item: Matrix item being built
            prefix: Prefix for field names ("component", "context", "workspace")
            entity: Entity data dictionary
        """
        for key, value in entity.items():
            if prefix == "component" and key == "config" and isinstance(value, dict):
                # Flatten config fields
                for config_key, config_value in value.items():
                    matrix_item[f"{prefix}_{config_key}"] = config_value
            elif (
                prefix == "component"
                and key == "resolved_paths"
                and isinstance(value, dict)
            ):
                # Use absolute paths for matrix output
                for path_key, path_value in value.items():
                    if path_key == "component_path":
                        # Override the config path with resolved absolute path
                        matrix_item["component_path"] = path_value
            elif (
                prefix == "component"
                and key == "dependencies"
                and isinstance(value, list)
            ):
                # Handle dependencies specially
                matrix_item[f"{prefix}_dependencies"] = value
                # Also add individual dependency fields
                for i, dep in enumerate(value, 1):
                    if isinstance(dep, dict):
                        matrix_item[f"{prefix}_dependency_{i:02d}_name"] = dep.get(
                            "name", ""
                        )
                        matrix_item[f"{prefix}_dependency_{i:02d}_path"] = dep.get(
                            "path", ""
                        )
            elif key not in ["components", "contexts"]:  # Skip nested collections
                # Skip environment field for components (added as top-level field instead)
                if prefix == "component" and key == "environment":
                    continue
                matrix_item[f"{prefix}_{key}"] = value

    def _find_entity_by_name(
        self, entities: list[dict[str, Any]], name: str
    ) -> dict[str, Any] | None:
        """Find entity in list by name field.

        Args:
            entities: List of entity dictionaries
            name: Name to search for

        Returns:
            Entity dictionary if found, None otherwise
        """
        for entity in entities:
            if entity.get("name") == name:
                return entity
        return None

    def _build_command(self, entity_type: str, matrix_item: dict[str, Any]) -> str:
        """Build the appropriate command for the entity type.

        Args:
            entity_type: Type of entity ("component", "context", "workspace")
            matrix_item: Matrix item with all fields populated

        Returns:
            Command string for the entity
        """
        if entity_type == "component":
            comp_name = matrix_item.get("component", "")
            ctx_name = matrix_item.get("context", "")
            ws_name = matrix_item.get("workspace", "")

            if comp_name:
                # Always use component pattern with context filter for precision
                if ctx_name:
                    if ws_name:
                        return (
                            f"cm/{comp_name} --filter workspace.name={ws_name} "
                            f"--filter context.name={ctx_name}"
                        )
                    else:
                        return f"cm/{comp_name} --filter context.name={ctx_name}"
                else:
                    # Fallback to just component pattern if no context
                    return f"cm/{comp_name}"

        elif entity_type == "context":
            ctx_name = matrix_item.get("context", "")
            ws_name = matrix_item.get("workspace", "")

            if ctx_name:
                # Use context pattern, optionally with workspace filter
                if ws_name:
                    return f"c/{ctx_name} --filter workspace.name={ws_name}"
                else:
                    return f"c/{ctx_name}"

        else:  # workspace
            ws_name = matrix_item.get("workspace", "")
            if ws_name:
                return f"w/{ws_name}"

        return ""

    def format(self, content: Any) -> str:
        """Format content as GitHub Actions matrix format."""
        try:
            # Convert complex objects to serializable format
            serializable_content = self._convert_to_serializable(content)

            # Check if this is a coregen entity structure
            if isinstance(serializable_content, dict) and any(
                key in serializable_content
                for key in ["workspaces", "contexts", "components"]
            ):
                # Use our own flatten_for_matrix method
                matrix_items = self.flatten_for_matrix(serializable_content)
                result = {"include": matrix_items}
            elif isinstance(serializable_content, list):
                # Handle list content - could be name-only results
                matrix_items = []
                for item in serializable_content:
                    if isinstance(item, str):
                        # Convert string to dict with name field
                        matrix_items.append({"name": item})
                    elif isinstance(item, dict):
                        matrix_items.append(item)
                    else:
                        matrix_items.append({"value": str(item)})
                result = {"include": matrix_items}
            elif (
                not isinstance(serializable_content, dict)
                or "include" not in serializable_content
            ):
                # Single item - wrap in include array
                if isinstance(serializable_content, str):
                    result = {"include": [{"name": serializable_content}]}
                elif isinstance(serializable_content, dict):
                    result = {"include": [serializable_content]}
                else:
                    result = {"include": [{"value": serializable_content}]}
            else:
                result = serializable_content

            return json.dumps(result, indent=2, sort_keys=False, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to format as matrix: {str(e)}")
            raise ValueError(f"Failed to format as matrix: {str(e)}")
