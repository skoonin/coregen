"""Tests for detect-changes models with environment field support."""

from pathlib import Path

from coregen.services.detect_changes.models import (
    ChangeReason,
    ChangeStatus,
    ComponentChange,
    DetectChangesResult,
)


class TestComponentChangeEnvironment:
    """Test ComponentChange environment field handling."""

    def test_component_change_with_environment(self):
        """Test ComponentChange correctly stores environment field."""
        change = ComponentChange(
            component_name="test-component",
            context_name="test-context",
            workspace_name="test-workspace",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
            environment="production",
        )

        assert change.environment == "production"

    def test_component_change_environment_in_dict(self):
        """Test environment field appears in to_dict output."""
        change = ComponentChange(
            component_name="test-component",
            context_name="test-context",
            workspace_name="test-workspace",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
            environment="development",
        )

        result = change.to_dict()

        # Both context_environment and environment should be present
        assert "context_environment" in result
        assert "environment" in result
        assert result["context_environment"] == "development"
        assert result["environment"] == "development"

    def test_component_change_no_environment(self):
        """Test ComponentChange handles missing environment gracefully."""
        change = ComponentChange(
            component_name="test-component",
            context_name="test-context",
            workspace_name="test-workspace",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
            # No environment specified
        )

        assert change.environment is None

        result = change.to_dict()
        assert result["context_environment"] is None
        assert result["environment"] is None

    def test_component_change_table_format_with_environment(self):
        """Test environment fields in table format output."""
        change = ComponentChange(
            component_name="nginx",
            context_name="aws-cluster-prod",
            workspace_name="aws-workspace",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
            environment="prod",
            context_config_file_path=Path("/test/path/config.yaml"),
        )

        # Table format should include environment fields
        table_dict = change.to_dict(table_format=True)

        assert table_dict["environment"] == "prod"
        assert table_dict["context_environment"] == "prod"
        # In table format, path should show as "Link"
        assert table_dict["context_config_file_path"] == "Link"

    def test_deleted_component_with_environment(self):
        """Test deleted components still report environment."""
        change = ComponentChange(
            component_name="deleted-component",
            context_name="test-context",
            workspace_name="test-workspace",
            status=ChangeStatus.DELETED,
            reason=ChangeReason.DELETED,
            environment="staging",
            component_path=Path("/some/path"),  # Should be None in output
        )

        result = change.to_dict()

        # Environment should still be reported for deleted components
        assert result["environment"] == "staging"
        assert result["context_environment"] == "staging"
        # Component path should be None for deleted components
        assert result["component_path"] is None


class TestDetectChangesResultEnvironment:
    """Test DetectChangesResult with environment fields."""

    def test_result_to_matrix_format_with_environments(self):
        """Test matrix format includes environment fields."""
        changes = [
            ComponentChange(
                component_name="component1",
                context_name="context-dev",
                workspace_name="workspace1",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                environment="dev",
            ),
            ComponentChange(
                component_name="component2",
                context_name="context-prod",
                workspace_name="workspace2",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.REQUIRED_CASCADE,
                environment="prod",
            ),
        ]

        result = DetectChangesResult(changes=changes)
        matrix = result.to_matrix_format()

        assert "include" in matrix
        assert len(matrix["include"]) == 2

        # Check first component has environment fields
        first = matrix["include"][0]
        assert first["environment"] == "dev"
        assert first["context_environment"] == "dev"

        # Check second component has environment fields
        second = matrix["include"][1]
        assert second["environment"] == "prod"
        assert second["context_environment"] == "prod"

    def test_result_mixed_environments(self):
        """Test result with mixed environment values."""
        changes = [
            ComponentChange(
                component_name="comp1",
                context_name="ctx1",
                workspace_name="ws1",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                environment="production",
            ),
            ComponentChange(
                component_name="comp2",
                context_name="ctx2",
                workspace_name="ws1",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                environment=None,  # No environment
            ),
            ComponentChange(
                component_name="comp3",
                context_name="ctx3",
                workspace_name="ws2",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
                environment="staging",
            ),
        ]

        result = DetectChangesResult(
            changes=changes,
            deleted=[changes[2]],
        )

        # Check to_dict includes all environment values
        dict_result = result.to_dict()

        assert dict_result["changes"][0]["environment"] == "production"
        assert dict_result["changes"][1]["environment"] is None
        assert dict_result["changes"][2]["environment"] == "staging"

        # Deleted components should also have environment
        assert dict_result["deleted"][0]["environment"] == "staging"


class TestDetectChangesResultRequiredChanges:
    """Test DetectChangesResult.to_dict() with include_required_changes parameter."""

    def test_to_dict_without_required_changes_by_default(self):
        """Test to_dict() excludes required_changes array by default."""
        changes = [
            ComponentChange(
                component_name="component1",
                context_name="context1",
                workspace_name="workspace1",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
            ),
        ]
        required_changes = [
            ComponentChange(
                component_name="required-component",
                context_name="context1",
                workspace_name="workspace1",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                component_required=True,
            ),
        ]

        result = DetectChangesResult(
            changes=changes,
            required_changes=required_changes,
        )

        # Default behavior - no required_changes in output
        dict_result = result.to_dict()

        assert "changes" in dict_result
        assert "deleted" in dict_result
        assert "required_changes" not in dict_result

    def test_to_dict_with_required_changes_when_enabled(self):
        """Test to_dict() includes required_changes array when flag is True."""
        changes = [
            ComponentChange(
                component_name="component1",
                context_name="context1",
                workspace_name="workspace1",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
            ),
        ]
        required_changes = [
            ComponentChange(
                component_name="required-component",
                context_name="context1",
                workspace_name="workspace1",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                component_required=True,
            ),
        ]

        result = DetectChangesResult(
            changes=changes,
            required_changes=required_changes,
        )

        # With flag enabled - required_changes should be in output
        dict_result = result.to_dict(include_required_changes=True)

        assert "changes" in dict_result
        assert "deleted" in dict_result
        assert "required_changes" in dict_result
        assert len(dict_result["required_changes"]) == 1
        assert (
            dict_result["required_changes"][0]["component_name"] == "required-component"
        )

    def test_to_dict_with_empty_required_changes(self):
        """Test to_dict() handles empty required_changes array correctly."""
        changes = [
            ComponentChange(
                component_name="component1",
                context_name="context1",
                workspace_name="workspace1",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
            ),
        ]

        result = DetectChangesResult(
            changes=changes,
            required_changes=[],  # Empty array
        )

        # With flag enabled - should include empty array
        dict_result = result.to_dict(include_required_changes=True)

        assert "required_changes" in dict_result
        assert dict_result["required_changes"] == []

        # Without flag - should not include key at all
        dict_result_no_flag = result.to_dict(include_required_changes=False)

        assert "required_changes" not in dict_result_no_flag
