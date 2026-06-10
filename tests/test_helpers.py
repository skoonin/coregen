"""Helper functions and utilities for testing.

This module provides helper functions for creating test data and
managing test utilities across the CoreGen HPC test suite.

Usage:
    from tests.test_helpers import (
        create_component_change,
        create_detect_changes_result,
    )
"""

from pathlib import Path
from typing import Any

from coregen.services.detect_changes.models import ComponentChange, DetectChangesResult

# ============================================================================
# Path Validation Helpers
# ============================================================================


# ============================================================================
# DetectChanges Data Builders
# ============================================================================


def create_component_change(
    component_name: str = "test-component",
    context_name: str = "test-context",
    workspace_name: str = "test-workspace",
    status: Any | None = None,
    reason: Any | None = None,
    environment: str | None = None,
    active: bool = True,
    required: bool = False,
    priority: int | None = None,
    dependencies: list[str] | None = None,
    component_path: Path | None = None,
    context_config_file_path: Path | None = None,
    command: str | None = None,
) -> ComponentChange:
    """Create a ComponentChange instance with sensible defaults.

    Args:
        component_name: Component name (default: "test-component")
        context_name: Context name (default: "test-context")
        workspace_name: Workspace name (default: "test-workspace")
        status: ChangeStatus enum value (default: ChangeStatus.CHANGED)
        reason: ChangeReason enum value (default: ChangeReason.DIRECT)
        environment: Environment name (default: None)
        active: Whether component is active (default: True)
        required: Whether component is required (default: False)
        priority: Component priority (default: None)
        dependencies: List of dependency names (default: [])
        component_path: Path to component (default: None)
        context_config_file_path: Path to context config (default: None)
        command: Generation command (default: None)

    Returns:
        ComponentChange instance

    Example:
        >>> change = create_component_change(
        ...     component_name="api",
        ...     status=ChangeStatus.CHANGED,
        ...     reason=ChangeReason.DIRECT
        ... )
        >>> change.component_name
        'api'
    """
    from coregen.services.detect_changes.models import (
        ChangeReason,
        ChangeStatus,
        ComponentChange,
    )

    # Use defaults if not provided
    if status is None:
        status = ChangeStatus.CHANGED
    if reason is None:
        reason = ChangeReason.DIRECT
    if dependencies is None:
        dependencies = []

    return ComponentChange(
        component_name=component_name,
        context_name=context_name,
        workspace_name=workspace_name,
        status=status,
        reason=reason,
        environment=environment,
        component_active=active,
        component_required=required,
        component_priority=priority,
        component_dependencies=dependencies,
        component_path=component_path,
        context_config_file_path=context_config_file_path,
        command=command,
    )


def create_detect_changes_result(
    changes: list[Any] | None = None,
    required_changes: list[Any] | None = None,
    deleted: list[Any] | None = None,
    total_analyzed: int | None = None,
    total_changed: int | None = None,
    total_deleted: int | None = None,
    total_unchanged: int | None = None,
    total_contexts_affected: int | None = None,
    total_workspaces_affected: int | None = None,
) -> DetectChangesResult:
    """Create a DetectChangesResult with auto-calculated statistics.

    If statistics are not provided, they will be automatically calculated
    from the changes list.

    Args:
        changes: List of ComponentChange instances (default: [])
        required_changes: List of required changes (default: extracted from changes)
        deleted: List of deleted changes (default: extracted from changes)
        total_analyzed: Total components analyzed (default: auto-calculated)
        total_changed: Total changed components (default: auto-calculated)
        total_deleted: Total deleted components (default: auto-calculated)
        total_unchanged: Total unchanged components (default: auto-calculated)
        total_contexts_affected: Total contexts affected (default: auto-calculated)
        total_workspaces_affected: Total workspaces affected (default: auto-calculated)

    Returns:
        DetectChangesResult instance

    Example:
        >>> changes = [
        ...     create_component_change(component_name="api", status=ChangeStatus.CHANGED),
        ...     create_component_change(component_name="db", status=ChangeStatus.CHANGED)
        ... ]
        >>> result = create_detect_changes_result(changes=changes)
        >>> result.total_changed
        2
    """
    from coregen.services.detect_changes.models import ChangeStatus, DetectChangesResult

    if changes is None:
        changes = []

    # Auto-extract required_changes if not provided
    if required_changes is None:
        required_changes = [c for c in changes if c.component_required]

    # Auto-extract deleted if not provided
    if deleted is None:
        deleted = [c for c in changes if c.status == ChangeStatus.DELETED]

    # Auto-calculate statistics if not provided
    if total_changed is None:
        total_changed = len([c for c in changes if c.status == ChangeStatus.CHANGED])

    if total_deleted is None:
        total_deleted = len(deleted)

    if total_analyzed is None:
        # If total_unchanged is provided, use it to calculate total_analyzed
        if total_unchanged is not None:
            total_analyzed = total_changed + total_deleted + total_unchanged
        else:
            # Otherwise, assume we only analyzed the changed/deleted ones
            total_analyzed = total_changed + total_deleted

    if total_unchanged is None:
        total_unchanged = total_analyzed - total_changed - total_deleted

    if total_contexts_affected is None:
        unique_contexts = {c.context_name for c in changes}
        total_contexts_affected = len(unique_contexts)

    if total_workspaces_affected is None:
        unique_workspaces = {c.workspace_name for c in changes}
        total_workspaces_affected = len(unique_workspaces)

    return DetectChangesResult(
        changes=changes,
        required_changes=required_changes,
        deleted=deleted,
        total_analyzed=total_analyzed,
        total_changed=total_changed,
        total_deleted=total_deleted,
        total_unchanged=total_unchanged,
        total_contexts_affected=total_contexts_affected,
        total_workspaces_affected=total_workspaces_affected,
    )


# ============================================================================
# Get Service Data Builders
# ============================================================================


def create_get_elements_result(
    workspaces: list[str] | None = None,
    contexts: list[str] | None = None,
    components: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a GetService.get_elements result structure.

    Args:
        workspaces: List of workspace names (default: [])
        contexts: List of context names (default: [])
        components: List of component names (default: [])
        details: Details dict with component info (default: {"components": {}})

    Returns:
        Dictionary in GetService result format

    Example:
        >>> result = create_get_elements_result(
        ...     contexts=["dev", "prod"],
        ...     components=["api", "db"]
        ... )
        >>> result["contexts"]
        ['dev', 'prod']
    """
    return {
        "workspaces": workspaces or [],
        "contexts": contexts or [],
        "components": components or [],
        "details": details or {"components": {}},
    }
