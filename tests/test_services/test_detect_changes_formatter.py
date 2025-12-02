"""Unit tests for DetectChangesFormatter.

This module tests the DetectChangesFormatter which handles formatting of
detect-changes output in various formats (text, JSON, YAML, matrix).
"""

import json
from pathlib import Path

import yaml

from coregen.services.detect_changes.formatters import DetectChangesFormatter
from coregen.services.detect_changes.models import ChangeReason, ChangeStatus
from tests.test_helpers import create_component_change, create_detect_changes_result


class TestDetectChangesFormatter:
    """Test suite for DetectChangesFormatter."""

    # ============================================================================
    # Text Format Tests
    # ============================================================================

    def test_format_text_with_changes(self) -> None:
        """Test text formatting with standard changes."""
        changes = [
            create_component_change(
                component_name="api",
                context_name="dev",
                workspace_name="app",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                active=True,
                required=False,
                priority=1,
                component_path=Path("/app/api"),
            ),
            create_component_change(
                component_name="db",
                context_name="dev",
                workspace_name="app",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.REQUIRED_CASCADE,
                active=True,
                required=True,
                priority=2,
            ),
        ]
        result = create_detect_changes_result(changes=changes)

        output = DetectChangesFormatter.format_text(result)

        assert "CHANGED COMPONENTS" in output
        assert "Name: api" in output
        assert "Name: db" in output
        assert "Status: changed" in output
        assert "Reason: direct" in output
        assert "Reason: required_cascade" in output
        assert "SUMMARY" in output
        assert "Changed: 2 components" in output
        assert "Direct changes: 1" in output
        assert "Required cascade: 1" in output

    def test_format_text_with_deleted_components(self) -> None:
        """Test text formatting with deleted components."""
        deleted_changes = [
            create_component_change(
                component_name="legacy-api",
                context_name="prod",
                workspace_name="app",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
                context_config_file_path=Path("/app/config.yaml"),
            ),
        ]
        result = create_detect_changes_result(
            changes=deleted_changes,
            deleted=deleted_changes,
        )

        output = DetectChangesFormatter.format_text(result)

        assert "DELETED COMPONENTS" in output
        assert "Name: legacy-api" in output
        assert "Workspace: app" in output
        assert "Context: prod" in output
        assert "Context Config: /app/config.yaml" in output
        assert "SUMMARY" in output
        assert "Deleted: 1 components" in output

    def test_format_text_no_changes(self) -> None:
        """Test text formatting when there are no changes."""
        result = create_detect_changes_result()

        output = DetectChangesFormatter.format_text(result)

        assert output == "No changes detected.\n"

    def test_format_text_name_only_changed(self) -> None:
        """Test text formatting with name_only=True and changed_only=True."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
            ),
            create_component_change(
                component_name="db",
                status=ChangeStatus.CHANGED,
            ),
            # Duplicate to test deduplication
            create_component_change(
                component_name="api",
                context_name="different-context",
                status=ChangeStatus.CHANGED,
            ),
        ]
        result = create_detect_changes_result(changes=changes)

        output = DetectChangesFormatter.format_text(
            result,
            name_only=True,
            changed_only=True,
        )

        # Should be simple list of unique names
        assert output == "api\ndb"

    def test_format_text_name_only_deleted(self) -> None:
        """Test text formatting with name_only=True and deleted_only=True."""
        deleted_changes = [
            create_component_change(
                component_name="old-service",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
            create_component_change(
                component_name="deprecated-api",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
        ]
        result = create_detect_changes_result(
            changes=deleted_changes,
            deleted=deleted_changes,
        )

        output = DetectChangesFormatter.format_text(
            result,
            name_only=True,
            deleted_only=True,
        )

        assert output == "old-service\ndeprecated-api"

    def test_format_text_name_only_all_with_status(self) -> None:
        """Test text formatting with name_only=True showing all changes with status."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
                required=False,
            ),
            create_component_change(
                component_name="db",
                status=ChangeStatus.CHANGED,
                required=True,
            ),
        ]
        result = create_detect_changes_result(changes=changes)

        output = DetectChangesFormatter.format_text(result, name_only=True)

        assert "api changed" in output
        assert "db changed required" in output

    # ============================================================================
    # JSON Format Tests
    # ============================================================================

    def test_format_json_with_changes(self) -> None:
        """Test JSON formatting with standard changes."""
        changes = [
            create_component_change(
                component_name="api",
                context_name="dev",
                workspace_name="app",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
            ),
        ]
        result = create_detect_changes_result(changes=changes)

        output = DetectChangesFormatter.format_json(result)
        data = json.loads(output)

        assert "changes" in data
        assert len(data["changes"]) == 1
        assert data["changes"][0]["component_name"] == "api"
        assert data["changes"][0]["status"] == "changed"
        assert data["changes"][0]["reason"] == "direct"

    def test_format_json_no_changes(self) -> None:
        """Test JSON formatting when there are no changes."""
        result = create_detect_changes_result()

        output = DetectChangesFormatter.format_json(result)
        data = json.loads(output)

        assert data == {"message": "No changes detected"}

    def test_format_json_name_only(self) -> None:
        """Test JSON formatting with name_only=True."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
            ),
            create_component_change(
                component_name="db",
                status=ChangeStatus.CHANGED,
            ),
            # Duplicate
            create_component_change(
                component_name="api",
                context_name="prod",
                status=ChangeStatus.CHANGED,
            ),
        ]
        result = create_detect_changes_result(changes=changes)

        output = DetectChangesFormatter.format_json(result, name_only=True)
        data = json.loads(output)

        # Should be categorized with changed/required/deleted
        assert "changed" in data
        assert "required" in data
        assert "deleted" in data
        assert sorted(data["changed"]) == ["api", "db"]

    def test_format_json_changed_only(self) -> None:
        """Test JSON formatting with changed_only=True."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
            ),
        ]
        deleted = [
            create_component_change(
                component_name="old-service",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
        ]
        all_changes = changes + deleted
        result = create_detect_changes_result(
            changes=all_changes,
            deleted=deleted,
        )

        output = DetectChangesFormatter.format_json(result, changed_only=True)
        data = json.loads(output)

        assert "changes" in data
        assert len(data["changes"]) == 1
        assert "deleted" not in data

    def test_format_json_deleted_only(self) -> None:
        """Test JSON formatting with deleted_only=True."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
            ),
        ]
        deleted = [
            create_component_change(
                component_name="old-service",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
        ]
        all_changes = changes + deleted
        result = create_detect_changes_result(
            changes=all_changes,
            deleted=deleted,
        )

        output = DetectChangesFormatter.format_json(result, deleted_only=True)
        data = json.loads(output)

        assert "deleted" in data
        assert len(data["deleted"]) == 1
        assert "changes" not in data

    # ============================================================================
    # YAML Format Tests
    # ============================================================================

    def test_format_yaml_with_changes(self) -> None:
        """Test YAML formatting with standard changes."""
        changes = [
            create_component_change(
                component_name="api",
                context_name="dev",
                workspace_name="app",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
            ),
        ]
        result = create_detect_changes_result(changes=changes)

        output = DetectChangesFormatter.format_yaml(result)
        data = yaml.safe_load(output)

        assert "changes" in data
        assert len(data["changes"]) == 1
        assert data["changes"][0]["component_name"] == "api"
        assert data["changes"][0]["status"] == "changed"

    def test_format_yaml_no_changes(self) -> None:
        """Test YAML formatting when there are no changes."""
        result = create_detect_changes_result()

        output = DetectChangesFormatter.format_yaml(result)
        data = yaml.safe_load(output)

        assert data == {"message": "No changes detected"}

    # ============================================================================
    # Matrix Format Tests
    # ============================================================================

    def test_format_matrix_with_changes(self) -> None:
        """Test matrix (GitHub Actions) formatting with changes."""
        changes = [
            create_component_change(
                component_name="api",
                context_name="dev",
                workspace_name="app",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
            ),
            create_component_change(
                component_name="db",
                context_name="dev",
                workspace_name="app",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.REQUIRED_CASCADE,
            ),
        ]
        result = create_detect_changes_result(changes=changes)

        output = DetectChangesFormatter.format_matrix(result)
        data = json.loads(output)

        assert "include" in data
        assert len(data["include"]) == 2
        assert data["include"][0]["component_name"] == "api"
        assert data["include"][1]["component_name"] == "db"

    def test_format_matrix_changed_only(self) -> None:
        """Test matrix formatting with changed_only filter."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
            ),
        ]
        deleted = [
            create_component_change(
                component_name="old-service",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
        ]
        all_changes = changes + deleted
        result = create_detect_changes_result(
            changes=all_changes,
            deleted=deleted,
        )

        output = DetectChangesFormatter.format_matrix(result, changed_only=True)
        data = json.loads(output)

        assert "include" in data
        # Should only include changed items
        assert len(data["include"]) == 1
        assert data["include"][0]["status"] == "changed"

    # ============================================================================
    # Edge Cases and Data Structure Tests
    # ============================================================================

    def test_component_details_formatting(self) -> None:
        """Test detailed component information in text output."""
        changes = [
            create_component_change(
                component_name="api",
                context_name="dev",
                workspace_name="app",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                active=True,
                required=True,
                priority=5,
                dependencies=["db", "cache"],
                component_path=Path("/app/api"),
                context_config_file_path=Path("/app/config.yaml"),
                command="coregen generate api",
            ),
        ]
        result = create_detect_changes_result(changes=changes)

        output = DetectChangesFormatter.format_text(result)

        # Verify all component details are present
        assert "Workspace: app" in output
        assert "Context: dev" in output
        assert "Status: changed" in output
        assert "Reason: direct" in output
        assert "Active: true" in output
        assert "Required: true" in output
        assert "Priority: 5" in output
        assert "Path: /app/api" in output
        assert "Context Config: /app/config.yaml" in output
        assert "Command: coregen generate api" in output

    def test_empty_result_consistency_across_formats(self) -> None:
        """Test that empty results are handled consistently across all formats."""
        result = create_detect_changes_result()

        # Text format
        text_output = DetectChangesFormatter.format_text(result)
        assert text_output == "No changes detected.\n"

        # JSON format
        json_output = DetectChangesFormatter.format_json(result)
        json_data = json.loads(json_output)
        assert json_data == {"message": "No changes detected"}

        # YAML format
        yaml_output = DetectChangesFormatter.format_yaml(result)
        yaml_data = yaml.safe_load(yaml_output)
        assert yaml_data == {"message": "No changes detected"}

        # Matrix format (should have empty include array)
        matrix_output = DetectChangesFormatter.format_matrix(result)
        matrix_data = json.loads(matrix_output)
        assert "include" in matrix_data
        assert len(matrix_data["include"]) == 0

    def test_format_text_changed_only_filter(self) -> None:
        """Test text formatting with changed_only filter."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
            ),
        ]
        deleted = [
            create_component_change(
                component_name="old-service",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
        ]
        all_changes = changes + deleted
        result = create_detect_changes_result(
            changes=all_changes,
            deleted=deleted,
        )

        output = DetectChangesFormatter.format_text(result, changed_only=True)

        # Should only show changed components, not deleted
        assert "Name: api" in output
        assert "old-service" not in output
        assert "DELETED COMPONENTS" not in output

    def test_format_text_deleted_only_filter(self) -> None:
        """Test text formatting with deleted_only filter."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
            ),
        ]
        deleted = [
            create_component_change(
                component_name="old-service",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
        ]
        all_changes = changes + deleted
        result = create_detect_changes_result(
            changes=all_changes,
            deleted=deleted,
        )

        output = DetectChangesFormatter.format_text(result, deleted_only=True)

        # Should only show deleted components, not changed
        assert "old-service" in output
        assert "DELETED COMPONENTS" in output
        assert "CHANGED COMPONENTS" not in output
        assert "api" not in output

    def test_format_yaml_name_only_changed(self) -> None:
        """Test YAML formatting with name_only and changed_only filters."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
            ),
            create_component_change(
                component_name="db",
                status=ChangeStatus.CHANGED,
            ),
            # Duplicate
            create_component_change(
                component_name="api",
                context_name="prod",
                status=ChangeStatus.CHANGED,
            ),
        ]
        result = create_detect_changes_result(changes=changes)

        output = DetectChangesFormatter.format_yaml(
            result,
            name_only=True,
            changed_only=True,
        )
        data = yaml.safe_load(output)

        # Should be a simple list of unique component names
        assert isinstance(data, list)
        assert sorted(data) == ["api", "db"]

    def test_format_yaml_name_only_deleted(self) -> None:
        """Test YAML formatting with name_only and deleted_only filters."""
        deleted_changes = [
            create_component_change(
                component_name="old-service",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
            create_component_change(
                component_name="deprecated-api",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
        ]
        result = create_detect_changes_result(
            changes=deleted_changes,
            deleted=deleted_changes,
        )

        output = DetectChangesFormatter.format_yaml(
            result,
            name_only=True,
            deleted_only=True,
        )
        data = yaml.safe_load(output)

        # Should be a simple list of deleted component names
        assert isinstance(data, list)
        assert sorted(data) == ["deprecated-api", "old-service"]

    def test_format_yaml_changed_only(self) -> None:
        """Test YAML formatting with changed_only filter."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
            ),
        ]
        deleted = [
            create_component_change(
                component_name="old-service",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
        ]
        all_changes = changes + deleted
        result = create_detect_changes_result(
            changes=all_changes,
            deleted=deleted,
        )

        output = DetectChangesFormatter.format_yaml(result, changed_only=True)
        data = yaml.safe_load(output)

        assert "changes" in data
        assert len(data["changes"]) == 1
        assert "deleted" not in data

    def test_format_yaml_deleted_only(self) -> None:
        """Test YAML formatting with deleted_only filter."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
            ),
        ]
        deleted = [
            create_component_change(
                component_name="old-service",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
        ]
        all_changes = changes + deleted
        result = create_detect_changes_result(
            changes=all_changes,
            deleted=deleted,
        )

        output = DetectChangesFormatter.format_yaml(result, deleted_only=True)
        data = yaml.safe_load(output)

        assert "deleted" in data
        assert len(data["deleted"]) == 1
        assert "changes" not in data

    def test_format_json_name_only_changed(self) -> None:
        """Test JSON formatting with name_only and changed_only filters."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
            ),
            create_component_change(
                component_name="db",
                status=ChangeStatus.CHANGED,
            ),
        ]
        result = create_detect_changes_result(changes=changes)

        output = DetectChangesFormatter.format_json(
            result,
            name_only=True,
            changed_only=True,
        )
        data = json.loads(output)

        # Should be a simple list of unique component names
        assert isinstance(data, list)
        assert sorted(data) == ["api", "db"]

    def test_format_json_name_only_deleted(self) -> None:
        """Test JSON formatting with name_only and deleted_only filters."""
        deleted_changes = [
            create_component_change(
                component_name="old-service",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
        ]
        result = create_detect_changes_result(
            changes=deleted_changes,
            deleted=deleted_changes,
        )

        output = DetectChangesFormatter.format_json(
            result,
            name_only=True,
            deleted_only=True,
        )
        data = json.loads(output)

        # Should be a simple list of deleted component names
        assert isinstance(data, list)
        assert data == ["old-service"]

    def test_format_matrix_deleted_only(self) -> None:
        """Test matrix formatting with deleted_only filter."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
            ),
        ]
        deleted = [
            create_component_change(
                component_name="old-service",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
        ]
        all_changes = changes + deleted
        result = create_detect_changes_result(
            changes=all_changes,
            deleted=deleted,
        )

        output = DetectChangesFormatter.format_matrix(result, deleted_only=True)
        data = json.loads(output)

        assert "include" in data
        # Should only include deleted items
        assert len(data["include"]) == 1
        assert data["include"][0]["status"] == "deleted"

    def test_format_text_summary_with_context_workspace_counts(self) -> None:
        """Test text summary includes context and workspace counts."""
        changes = [
            create_component_change(
                component_name="api",
                context_name="dev",
                workspace_name="app",
                status=ChangeStatus.CHANGED,
            ),
            create_component_change(
                component_name="db",
                context_name="prod",
                workspace_name="data",
                status=ChangeStatus.CHANGED,
            ),
        ]
        result = create_detect_changes_result(changes=changes)

        output = DetectChangesFormatter.format_text(result)

        assert "Affected contexts: 2" in output
        assert "Affected workspaces: 2" in output

    def test_format_text_component_without_optional_fields(self) -> None:
        """Test text formatting handles components with minimal fields."""
        changes = [
            create_component_change(
                component_name="minimal",
                context_name="dev",
                workspace_name="app",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                priority=None,
                component_path=None,
                context_config_file_path=None,
                command=None,
            ),
        ]
        result = create_detect_changes_result(changes=changes)

        output = DetectChangesFormatter.format_text(result)

        # Should not fail and should show basic fields
        assert "Name: minimal" in output
        assert "Status: changed" in output
        assert "Active: true" in output
        # Optional fields should not appear or should show as false/null
        assert "Priority:" not in output

    def test_format_yaml_name_only_all_categories(self) -> None:
        """Test YAML name_only without filters shows all categories."""
        changes = [
            create_component_change(
                component_name="api",
                status=ChangeStatus.CHANGED,
                required=True,
            ),
        ]
        deleted = [
            create_component_change(
                component_name="old-service",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            ),
        ]
        all_changes = changes + deleted
        result = create_detect_changes_result(
            changes=all_changes,
            deleted=deleted,
        )

        output = DetectChangesFormatter.format_yaml(result, name_only=True)
        data = yaml.safe_load(output)

        # Should have all three categories
        assert "changed" in data
        assert "required" in data
        assert "deleted" in data
        assert "api" in data["changed"]
        assert "old-service" in data["deleted"]
