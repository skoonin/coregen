"""Table formatter for structured data display."""

from typing import Any

from rich.box import ROUNDED
from rich.table import Table

from .base import BaseFormatter


class TableFormatter(BaseFormatter):
    """Table formatter for structured data display."""

    def _is_entity_collection(self, content: dict) -> bool:
        """Check if this dict contains entity collections (workspaces, contexts, components)."""
        entity_types = {"workspaces", "contexts", "components"}
        return any(key in entity_types for key in content.keys())

    def _format_entity_collection(self, content: dict) -> Table:
        """Format entity collections as a proper table."""
        # Count how many entity types we have
        entity_types = []
        if "workspaces" in content and content["workspaces"]:
            entity_types.append("workspaces")
        if "contexts" in content and content["contexts"]:
            entity_types.append("contexts")
        if "components" in content and content["components"]:
            entity_types.append("components")

        if not entity_types:
            table = Table(
                show_header=True,
                header_style="bold cyan",
                box=ROUNDED,
                border_style="blue",
            )
            table.add_column("Info", style="dim")
            table.add_row("No entities found")
            return table

        # Check contexts length - handle both dict and list formats
        contexts_data = content.get("contexts", {})
        if isinstance(contexts_data, list):
            contexts_count = len(contexts_data)
        else:
            contexts_count = len(contexts_data)

        # Decision logic for what to show:
        # 1. If we have multiple contexts with components (from glob patterns like c/*), show components table
        # 2. If we have only one entity type AND it's not a mixed query result, show its detailed table
        # 3. If we have exactly 1 context and 0 or more components, show detailed view
        # 4. Otherwise show summary table

        # Check if we have components from glob patterns (like c/*)
        has_components = "components" in entity_types

        # For glob patterns that return contexts with components at root level, show components table
        # This handles patterns like c/* which return multiple contexts and their components
        # Also handles single context queries that have components at root level
        if has_components:
            # Components at root level - show components table (for glob patterns or single context with components)
            entity_type = "components"
            entities = content["components"]
        elif len(entity_types) == 1 and entity_types[0] == "workspaces":
            # Only workspaces - show workspaces table (e.g., w/* shows workspaces table)
            entity_type = "workspaces"
            entities = content["workspaces"]
        elif (
            len(entity_types) <= 2
            and "contexts" in entity_types
            and contexts_count == 1
        ):
            # Single context - show its components if available, otherwise show context
            # Check if components are available at root level (flat format) or nested
            component_list = []

            # First check if components are at root level (flat format)
            if "components" in content and content["components"]:
                # Components are at root level - use them directly
                component_list = content["components"]
            else:
                # Try to extract from nested format
                # Handle both dict and list formats for contexts
                if isinstance(content["contexts"], dict):
                    context_data = list(content["contexts"].values())[0]
                    context_name = list(content["contexts"].keys())[0]
                elif (
                    isinstance(content["contexts"], list)
                    and len(content["contexts"]) == 1
                ):
                    context_data = content["contexts"][0]
                    context_name = context_data.get("name", "unknown")
                else:
                    context_data = {}
                    context_name = "unknown"

                # Extract components from nested context
                if "components" in context_data and context_data["components"]:
                    for comp_type, components in context_data["components"].items():
                        if isinstance(components, dict):
                            for comp_name, comp_data in components.items():
                                comp_dict = (
                                    comp_data if isinstance(comp_data, dict) else {}
                                )
                                # Add identifiers
                                comp_dict["name"] = comp_name
                                comp_dict["context"] = context_name
                                comp_dict["workspace"] = context_data.get(
                                    "workspace", ""
                                )
                                # Extract config if nested
                                if "config" in comp_dict:
                                    config = comp_dict["config"]
                                    if isinstance(config, dict):
                                        comp_dict.update(config)
                                component_list.append(comp_dict)

            # If we found components, show them; otherwise show context
            if component_list:
                # Show components table for this single context
                entity_type = "components"
                entities = component_list
            else:
                # No components, show context summary
                entity_type = entity_types[0]
                entities = content[entity_type]
        else:
            # Multiple entity types or multiple entities - show summary
            table = Table(
                show_header=True,
                header_style="bold cyan",
                box=ROUNDED,
                border_style="blue",
                title="Entity Summary",
                title_justify="left",
            )
            table.add_column("Entity Type", style="cyan bold")
            table.add_column("Count", style="yellow", justify="center")

            for entity_type in ["workspaces", "contexts", "components"]:
                if entity_type in content and content[entity_type]:
                    count = len(content[entity_type])
                    table.add_row(entity_type.title(), str(count))

            return table

        table = Table(
            show_header=True,
            header_style="bold cyan",
            box=ROUNDED,
            border_style="blue",
            title=f"{entity_type.title()} Table",
            title_justify="left",
        )

        # Convert dict to list if needed (for nested format)
        if isinstance(entities, dict):
            entity_list = []
            for name, entity_data in entities.items():
                if isinstance(entity_data, dict):
                    entity_data = dict(entity_data)  # Make a copy
                    entity_data["name"] = name
                    entity_list.append(entity_data)
                else:
                    # Handle model objects
                    if hasattr(entity_data, "model_dump"):
                        entity_dict = entity_data.model_dump(exclude_defaults=False)
                    else:
                        entity_dict = {"name": name}
                    entity_dict["name"] = name
                    entity_list.append(entity_dict)
            entities = entity_list

        # Now format as a list table
        if entities and isinstance(entities, list) and isinstance(entities[0], dict):
            # Define columns based on entity type
            if entity_type == "workspaces":
                columns = [
                    "name",
                    "archive_dir",
                    "context_config_files",
                    "context_type",
                    "output_dir",
                    "workspace_dir",
                ]
            elif entity_type == "contexts":
                columns = [
                    "name",
                    "workspace",
                    "environment",
                    "active",
                    "commit_dir",
                ]
            else:  # components
                # First show identity columns, then config fields
                columns = [
                    "name",
                    "context",
                    "workspace",
                    "environment",
                ]
                # Add config fields if they exist in a config object
                config_fields = [
                    "active",
                    "for_commit",
                    "required",
                    "priority",
                    "path",
                    "dependencies",
                ]
                # Check if we have config nested structure
                if entities and "config" in entities[0]:
                    # Config fields are nested under "config"
                    columns.extend([f"config.{field}" for field in config_fields])
                else:
                    # Config fields might be at top level
                    columns.extend(config_fields)

            # Filter columns to only those that exist in the data
            available_columns = set()
            for entity in entities:
                available_columns.update(entity.keys())
                # Also check for nested config fields
                if "config" in entity and isinstance(entity["config"], dict):
                    available_columns.update(
                        [f"config.{k}" for k in entity["config"].keys()]
                    )

            # Keep columns that are available (including nested ones)
            filtered_columns = []
            for col in columns:
                if "." in col:
                    # For nested fields, check if the parent exists
                    if col in available_columns:
                        filtered_columns.append(col)
                else:
                    if col in available_columns:
                        filtered_columns.append(col)
            columns = filtered_columns

            # Add columns to table
            for col in columns:
                # Format column header (handle nested fields)
                display_name = col.split(".")[-1].title() if "." in col else col.title()

                if col == "name":
                    table.add_column(display_name, style="cyan bold", no_wrap=True)
                elif (
                    col.endswith("active")
                    or col.endswith("for_commit")
                    or col.endswith("required")
                ):
                    table.add_column(display_name, style="green", justify="center")
                elif col.endswith("priority"):
                    table.add_column(display_name, style="yellow", justify="center")
                elif col.endswith("path"):
                    table.add_column(display_name, style="magenta")
                elif col.endswith("dependencies"):
                    table.add_column(display_name, style="cyan")
                else:
                    table.add_column(display_name, style="white")

            # Add special column for component count if showing contexts
            if entity_type == "contexts":
                table.add_column("Components", style="blue", justify="center")

            # Add rows
            for entity in entities:
                row_values = []
                for col in columns:
                    # Handle nested config fields
                    if "." in col:
                        parts = col.split(".")
                        value = entity
                        for part in parts:
                            if isinstance(value, dict):
                                value = value.get(part, "")
                            else:
                                value = ""
                                break
                    else:
                        value = entity.get(col, "")

                    if isinstance(value, bool):
                        formatted_value = (
                            "[green]✓[/green]" if value else "[red]✗[/red]"
                        )
                    elif value is None:
                        formatted_value = "[dim]None[/dim]"
                    elif isinstance(value, (int, float)):
                        formatted_value = f"[yellow]{value}[/yellow]"
                    elif isinstance(value, list):
                        # Handle lists (like dependencies)
                        if value and isinstance(value[0], dict) and "name" in value[0]:
                            # List of objects with name field
                            names = [item["name"] for item in value]
                            formatted_value = ", ".join(names)
                        elif col == "context_config_files" and value:
                            # Show actual file patterns for context_config_files
                            formatted_value = ", ".join(str(item) for item in value)
                        else:
                            # For other lists, show count
                            formatted_value = str(len(value)) + " items"
                    else:
                        formatted_value = str(value)
                    row_values.append(formatted_value)

                # Add component count for contexts
                if entity_type == "contexts" and "components" in entity:
                    comp_count = 0
                    if isinstance(entity["components"], dict):
                        # Components are organized by type (e.g., "app", "service")
                        # Note: Each context has only one component_type, so typically only one key exists
                        for _, components in entity["components"].items():
                            if isinstance(components, dict):
                                comp_count += len(components)
                    row_values.append(f"[blue]{comp_count}[/blue]")

                table.add_row(*row_values)

        return table

    def format(self, content: Any) -> Table:
        """Format content as a Rich table with enhanced display."""
        try:
            table = Table(
                show_header=True,
                header_style="bold cyan",
                box=ROUNDED,
                border_style="blue",
            )

            if isinstance(content, dict):
                # Check if this is an entity collection
                if self._is_entity_collection(content):
                    return self._format_entity_collection(content)
                table.add_column("Property", style="cyan", no_wrap=True)
                table.add_column("Value", style="white")

                for key, value in content.items():
                    if isinstance(value, (dict, list)):
                        if isinstance(value, dict):
                            display_value = f"{{dict: {len(value)} keys}}"
                        else:
                            display_value = f"[list: {len(value)} items]"
                    elif isinstance(value, bool):
                        display_value = (
                            f"[green]{value}[/green]"
                            if value
                            else f"[red]{value}[/red]"
                        )
                    elif isinstance(value, (int, float)):
                        display_value = f"[yellow]{value}[/yellow]"
                    else:
                        display_value = str(value)

                    table.add_row(str(key), display_value)

            elif isinstance(content, (list, tuple)) and content:
                if isinstance(content[0], dict):
                    headers = []
                    all_keys = set()
                    for item in content:
                        all_keys.update(item.keys())

                    common_keys = ["name", "id", "type", "status", "active", "value"]
                    for key in common_keys:
                        if key in all_keys:
                            headers.append(key)
                            all_keys.remove(key)

                    headers.extend(sorted(all_keys))

                    for header in headers:
                        if header in ["name", "id"]:
                            table.add_column(
                                str(header).title(), style="cyan bold", no_wrap=True
                            )
                        elif header in ["status", "active"]:
                            table.add_column(
                                str(header).title(), style="green", justify="center"
                            )
                        elif header in ["priority"]:
                            table.add_column(
                                str(header).title(), style="yellow", justify="center"
                            )
                        else:
                            table.add_column(str(header).title(), style="white")

                    for item in content:
                        row_values = []
                        for header in headers:
                            value = item.get(header, "")
                            if isinstance(value, bool):
                                formatted_value = (
                                    "[green]✓[/green]" if value else "[red]✗[/red]"
                                )
                            elif isinstance(value, (int, float)):
                                formatted_value = f"[yellow]{value}[/yellow]"
                            elif isinstance(value, (dict, list)):
                                formatted_value = f"[dim]{type(value).__name__}[/dim]"
                            else:
                                formatted_value = str(value)
                            row_values.append(formatted_value)
                        table.add_row(*row_values)

                elif isinstance(content[0], (list, tuple)):
                    headers, *rows = content
                    for i, header in enumerate(headers):
                        style = "cyan bold" if i == 0 else "cyan"
                        header_str = str(header)
                        # Center the Priority column when present
                        if header_str.lower() in {"pri", "priority"}:
                            table.add_column(header_str, style=style, justify="center")
                        else:
                            table.add_column(header_str, style=style)
                    for row in rows:
                        table.add_row(*[str(cell) for cell in row])

                else:
                    table.add_column("Value", style="white")
                    for item in content:
                        table.add_row(str(item))
            else:
                table.add_column("Value", style="white")
                table.add_row(str(content))

            return table
        except Exception as e:
            raise ValueError(f"Failed to format as table: {str(e)}") from e
