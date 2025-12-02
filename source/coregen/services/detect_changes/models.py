"""
Data models for detect-changes command.

This module defines the data structures used by the detect-changes command
for representing component changes between branches.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ChangeStatus(str, Enum):
    """Status of a component change."""

    CHANGED = "changed"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


class ChangeReason(str, Enum):
    """Reason for a component being marked as changed."""

    DIRECT = "direct"  # Component files were directly modified
    REQUIRED_CASCADE = (
        "required_cascade"  # Component affected by a required component change
    )
    DELETED = "deleted"  # Component was removed


@dataclass
class ComponentChange:
    """Represents a change to a component."""

    # Component identification
    component_name: str
    context_name: str
    workspace_name: str

    # Change information
    status: ChangeStatus
    reason: ChangeReason

    # Context environment
    environment: str | None = None

    # Component metadata (from configuration)
    component_active: bool = True
    component_required: bool = False
    component_priority: int | None = None
    component_dependencies: list[str] = field(default_factory=list)
    component_path: Path | None = None

    # Context metadata
    context_config_file_path: Path | None = None

    # Generation command
    command: str | None = None

    # Short names for convenience
    @property
    def component(self) -> str:
        """Short component identifier."""
        return self.component_name

    @property
    def context(self) -> str:
        """Short context identifier."""
        return self.context_name

    @property
    def workspace(self) -> str:
        """Short workspace identifier."""
        return self.workspace_name

    def to_dict(self, table_format: bool = False) -> dict[str, Any]:
        """Convert to dictionary for output formatting.

        Args:
            table_format: If True, format context_config_file_path as "Link" text

        Returns:
            Dictionary representation
        """
        # Handle context_config_file_path formatting
        context_config_path = None
        if self.context_config_file_path:
            if table_format:
                # For table format, just show "Link" text if path exists
                context_config_path = "Link"
            else:
                # For other formats, show the full path
                context_config_path = str(self.context_config_file_path)

        # For deleted components, do not report a generated component_path
        component_path_value = (
            None
            if self.status == ChangeStatus.DELETED
            else (str(self.component_path) if self.component_path else None)
        )

        result = {
            "component_name": self.component_name,
            "command": self.command,
            "component_active": self.component_active,
            "component_path": component_path_value,
            "component_priority": self.component_priority,
            "component_dependencies": self.component_dependencies,
            "component_required": self.component_required,
            "component": self.component,
            "context_name": self.context_name,
            "context": self.context,
            "context_config_file_path": context_config_path,
            "context_environment": self.environment,
            "environment": self.environment,
            "reason": self.reason.value,
            "status": self.status.value,
            "workspace_name": self.workspace_name,
            "workspace": self.workspace,
        }
        return result


@dataclass
class DetectChangesResult:
    """Result of detect-changes analysis."""

    # All changes (including deleted)
    changes: list[ComponentChange] = field(default_factory=list)

    # Subsets for convenience
    required_changes: list[ComponentChange] = field(default_factory=list)
    deleted: list[ComponentChange] = field(default_factory=list)

    # Statistics
    total_analyzed: int = 0
    total_changed: int = 0
    total_deleted: int = 0
    total_unchanged: int = 0
    total_contexts_affected: int = 0
    total_workspaces_affected: int = 0

    def to_dict(self, include_required_changes: bool = False) -> dict[str, Any]:
        """Convert to dictionary for output formatting.

        Args:
            include_required_changes: If True, include required_changes array in output

        Returns:
            Dictionary with changes and deleted arrays, optionally including required_changes
        """
        result = {
            "changes": [c.to_dict() for c in self.changes],
            "deleted": [d.to_dict() for d in self.deleted],
        }

        if include_required_changes:
            result["required_changes"] = [c.to_dict() for c in self.required_changes]

        return result

    def to_matrix_format(self) -> dict[str, Any]:
        """Convert to GitHub Actions matrix format."""
        return {"include": [c.to_dict(table_format=False) for c in self.changes]}

    def to_name_only_format(self, changed_only: bool = False) -> Any:
        """Convert to name-only format.

        Args:
            changed_only: If True, only include changed components (exclude deleted)

        Returns:
            List of component names if changed_only, otherwise dict with categories
        """
        if changed_only:
            # Return flat list of changed component names
            return sorted(
                {
                    c.component_name
                    for c in self.changes
                    if c.status == ChangeStatus.CHANGED
                }
            )
        else:
            # Return categorized dict
            return {
                "changed": sorted(
                    {
                        c.component_name
                        for c in self.changes
                        if c.status == ChangeStatus.CHANGED
                    }
                ),
                "required": sorted({c.component_name for c in self.required_changes}),
                "deleted": sorted({c.component_name for c in self.deleted}),
            }
