"""
Output formatters for detect-changes command.

This module provides formatters for different output formats
supported by the detect-changes command.
"""

from typing import Any

from coregen.common.formatters.json import JSONFormatter
from coregen.common.formatters.matrix import MatrixFormatter
from coregen.common.formatters.yaml import YAMLFormatter
from coregen.services.detect_changes.models import DetectChangesResult


class DetectChangesFormatter:
    """Base formatter for detect-changes output."""

    @staticmethod
    def format_text(
        result: DetectChangesResult,
        name_only: bool = False,
        changed_only: bool = False,
        deleted_only: bool = False,
    ) -> str:
        """Format result as text.

        Args:
            result: Detection result
            name_only: Output only names
            changed_only: Show only changed components
            deleted_only: Show only deleted components

        Returns:
            Formatted text output
        """
        # Check if there are no changes
        if not result.changes and not result.deleted:
            return "No changes detected.\n"

        output = []

        if name_only:
            if changed_only:
                # Simple list of changed component names - preserve order from sorter
                names = [
                    c.component_name
                    for c in result.changes
                    if c.status.value == "changed"
                ]
                # Remove duplicates while preserving order
                seen = set()
                unique_names = []
                for name in names:
                    if name not in seen:
                        seen.add(name)
                        unique_names.append(name)
                return "\n".join(unique_names)
            elif deleted_only:
                # Simple list of deleted component names - preserve order from sorter
                names = [c.component_name for c in result.deleted]
                # Remove duplicates while preserving order
                seen = set()
                unique_names = []
                for name in names:
                    if name not in seen:
                        seen.add(name)
                        unique_names.append(name)
                return "\n".join(unique_names)
            else:
                # Show all with status indicators - preserve order from sorter
                lines = []
                for change in result.changes:
                    status_parts = [change.status.value]
                    if change.component_required:
                        status_parts.append("required")
                    lines.append(f"{change.component_name} {' '.join(status_parts)}")
                return "\n".join(lines)

        # Full text format
        if not deleted_only:
            # Group changes by status
            changed_items = [c for c in result.changes if c.status.value == "changed"]
            if changed_items:
                output.append("CHANGED COMPONENTS")
                output.append("=" * 50)
                # Preserve order from sorter (already sorted by ComponentSorterService)
                for change in changed_items:
                    output.append("")
                    output.append(f"Name: {change.component_name}")
                    output.append("-" * 30)
                    output.extend(
                        DetectChangesFormatter._format_component_details(change)
                    )

        # Skip the required_changes section as it's redundant with the changed components
        # The required status is already shown in the component details

        if result.deleted and not changed_only:
            if output:  # Add spacing if there's previous content
                output.append("")
            output.append("DELETED COMPONENTS")
            output.append("=" * 50)
            # Preserve order from sorter (already sorted by ComponentSorterService)
            for change in result.deleted:
                output.append("")
                output.append(f"Name: {change.component_name}")
                output.append("-" * 30)
                output.append(f"  Workspace: {change.workspace_name}")
                output.append(f"  Context: {change.context_name}")
                if change.context_config_file_path:
                    output.append(
                        f"  Context Config: {change.context_config_file_path}"
                    )

        # Add summary if not filtering
        if not (name_only or changed_only or deleted_only):
            output.append("")
            output.append("")
            output.append("SUMMARY")
            output.append("=" * 50)

            # Count direct vs cascade
            direct_changes = len(
                [
                    c
                    for c in result.changes
                    if c.reason.value == "direct" and c.status.value == "changed"
                ]
            )
            cascade_changes = len(
                [c for c in result.changes if c.reason.value == "required_cascade"]
            )

            if result.total_changed > 0:
                output.append(f"Changed: {result.total_changed} components")
                if direct_changes > 0:
                    output.append(f"  Direct changes: {direct_changes}")
                if cascade_changes > 0:
                    output.append(f"  Required cascade: {cascade_changes}")

            if result.total_deleted > 0:
                output.append(f"Deleted: {result.total_deleted} components")

            if result.total_changed == 0 and result.total_deleted == 0:
                output.append("No changes detected")

            if result.total_contexts_affected > 0:
                output.append(f"Affected contexts: {result.total_contexts_affected}")
            if result.total_workspaces_affected > 0:
                output.append(
                    f"Affected workspaces: {result.total_workspaces_affected}"
                )

        return "\n".join(output) + "\n"

    @staticmethod
    def _format_component_details(change: Any) -> list[str]:
        """Format component details for text output."""
        lines = []
        lines.append(f"  Workspace: {change.workspace_name}")
        lines.append(f"  Context: {change.context_name}")
        lines.append(f"  Status: {change.status.value}")
        lines.append(f"  Reason: {change.reason.value}")
        lines.append(f"  Active: {'true' if change.component_active else 'false'}")
        lines.append(f"  Required: {'true' if change.component_required else 'false'}")
        if change.component_priority is not None:
            lines.append(f"  Priority: {change.component_priority}")
        if change.component_path:
            lines.append(f"  Path: {change.component_path}")
        if change.context_config_file_path:
            lines.append(f"  Context Config: {change.context_config_file_path}")
        if change.command:
            lines.append(f"  Command: {change.command}")
        return lines

    @staticmethod
    def format_yaml(
        result: DetectChangesResult,
        name_only: bool = False,
        changed_only: bool = False,
        deleted_only: bool = False,
    ) -> str:
        """Format result as YAML using common YAMLFormatter.

        Args:
            result: Detection result
            name_only: Output only names
            changed_only: Show only changed components
            deleted_only: Show only deleted components

        Returns:
            Formatted YAML output
        """
        yaml_formatter = YAMLFormatter()

        if name_only:
            if changed_only:
                # Simple list of changed component names - preserve order from sorter
                names = [
                    c.component_name
                    for c in result.changes
                    if c.status.value == "changed"
                ]
                # Remove duplicates while preserving order
                seen = set()
                unique_names = []
                for name in names:
                    if name not in seen:
                        seen.add(name)
                        unique_names.append(name)
                return yaml_formatter.format(unique_names)
            elif deleted_only:
                # Simple list of deleted component names - preserve order from sorter
                names = [c.component_name for c in result.deleted]
                # Remove duplicates while preserving order
                seen = set()
                unique_names = []
                for name in names:
                    if name not in seen:
                        seen.add(name)
                        unique_names.append(name)
                return yaml_formatter.format(unique_names)
            else:
                # Categorized names
                data = result.to_name_only_format(changed_only=False)
                return yaml_formatter.format(data)

        # Filter results based on options
        data = result.to_dict()

        if changed_only:
            data["changes"] = [c for c in data["changes"] if c["status"] == "changed"]
            data.pop("deleted", None)
        elif deleted_only:
            data = {"deleted": data.get("deleted", [])}

        # Keep arrays present when empty for a stable machine-readable schema
        if not data.get("changes") and not data.get("deleted"):
            data["message"] = "No changes detected"

        return yaml_formatter.format(data)

    @staticmethod
    def format_json(
        result: DetectChangesResult,
        name_only: bool = False,
        changed_only: bool = False,
        deleted_only: bool = False,
    ) -> str:
        """Format result as JSON using common JSONFormatter.

        Args:
            result: Detection result
            name_only: Output only names
            changed_only: Show only changed components
            deleted_only: Show only deleted components

        Returns:
            Formatted JSON output
        """
        json_formatter = JSONFormatter()

        if name_only:
            if changed_only:
                # Simple list of changed component names - preserve order from sorter
                names = [
                    c.component_name
                    for c in result.changes
                    if c.status.value == "changed"
                ]
                # Remove duplicates while preserving order
                seen = set()
                unique_names = []
                for name in names:
                    if name not in seen:
                        seen.add(name)
                        unique_names.append(name)
                return json_formatter.format(unique_names)
            elif deleted_only:
                # Simple list of deleted component names - preserve order from sorter
                names = [c.component_name for c in result.deleted]
                # Remove duplicates while preserving order
                seen = set()
                unique_names = []
                for name in names:
                    if name not in seen:
                        seen.add(name)
                        unique_names.append(name)
                return json_formatter.format(unique_names)
            else:
                # Categorized names
                data = result.to_name_only_format(changed_only=False)
                return json_formatter.format(data)

        # Filter results based on options
        data = result.to_dict()

        if changed_only:
            data["changes"] = [c for c in data["changes"] if c["status"] == "changed"]
            data.pop("deleted", None)
        elif deleted_only:
            data = {"deleted": data.get("deleted", [])}

        # Keep arrays present when empty for a stable machine-readable schema
        if not data.get("changes") and not data.get("deleted"):
            data["message"] = "No changes detected"

        return json_formatter.format(data)

    @staticmethod
    def format_matrix(
        result: DetectChangesResult,
        name_only: bool = False,
        changed_only: bool = False,
        deleted_only: bool = False,
    ) -> str:
        """Format result as GitHub Actions matrix using common MatrixFormatter.

        Args:
            result: Detection result
            name_only: Output only names (ignored for matrix)
            changed_only: Show only changed components
            deleted_only: Show only deleted components

        Returns:
            Formatted matrix JSON output
        """
        matrix_formatter = MatrixFormatter()

        # Convert detect-changes result to matrix format
        # The common MatrixFormatter expects data that can be converted to include format
        matrix_data = result.to_matrix_format()

        # Filter based on options
        if changed_only:
            matrix_data["include"] = [
                c for c in matrix_data["include"] if c["status"] == "changed"
            ]
        elif deleted_only:
            matrix_data["include"] = [
                c for c in matrix_data["include"] if c["status"] == "deleted"
            ]

        return matrix_formatter.format(matrix_data)
