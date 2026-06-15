"""
Unit tests for detect-changes filtering integration.

Tests our integration with FilterService, not FilterService itself.
Focuses on:
- Building the working model correctly (including deleted components)
- Calling FilterService methods correctly
- Mapping filtered results back to ComponentChange objects
"""

from unittest.mock import MagicMock

import pytest

from coregen.services.detect_changes.detect_changes_service import DetectChangesService
from coregen.services.detect_changes.models import (
    ChangeReason,
    ChangeStatus,
    ComponentChange,
    DetectChangesResult,
)


class TestDetectChangesFiltering:
    """Test the _apply_filters_to_results integration with FilterService."""

    @pytest.fixture
    def mock_filter_service(self) -> MagicMock:
        """Create a mock FilterService."""
        mock_service = MagicMock()
        # Default: parse returns a valid filter spec
        mock_service.parse_filter_expression.return_value = {
            "entity_type": "component",
            "property": "config.active",
            "operator": "=",
            "value": "true",
        }
        # Default: apply_filters_complete returns empty filtered model
        mock_service.apply_filters_complete.return_value = {
            "workspaces": {},
            "contexts": {},
            "components": {},
        }
        return mock_service

    @pytest.fixture
    def detect_changes_service(
        self, mock_filter_service: MagicMock
    ) -> DetectChangesService:
        """Create a DetectChangesService instance with mocked dependencies."""
        mock_config_provider = MagicMock()
        service = DetectChangesService(config_provider=mock_config_provider)

        # Mock config_access to provide complete_model
        mock_config_access = MagicMock()
        mock_config_access.get_complete_model.return_value = {
            "workspaces": {},
            "contexts": {},
            "components": {},
        }
        service._config_access = mock_config_access

        # Inject our mock filter service
        service._filter_service = mock_filter_service

        return service

    @pytest.fixture
    def sample_changes(self) -> list[ComponentChange]:
        """Create sample ComponentChange objects for testing."""
        return [
            # Active component
            ComponentChange(
                component_name="redis",
                context_name="dev-env",
                workspace_name="local",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                component_active=True,
                component_priority=3,
                component_required=False,
                environment="dev",
            ),
            # Inactive component
            ComponentChange(
                component_name="nginx",
                context_name="prod-env",
                workspace_name="local",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                component_active=False,
                component_priority=1,
                component_required=False,
                environment="prod",
            ),
            # Deleted component
            ComponentChange(
                component_name="postgres",
                context_name="dev-cluster",
                workspace_name="aws",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
                component_active=False,
                component_priority=2,
                component_required=False,
                environment="dev",
            ),
        ]

    def test_no_filters_returns_all_changes(
        self,
        detect_changes_service: DetectChangesService,
        sample_changes: list[ComponentChange],
    ) -> None:
        """Test that empty filter list returns all changes unchanged."""
        result = DetectChangesResult(changes=sample_changes)

        filtered_result = detect_changes_service._apply_filters_to_results(
            result, [], verbose=False
        )

        assert len(filtered_result.changes) == 3
        assert filtered_result.changes == sample_changes

    def test_builds_working_model_with_deleted_components(
        self,
        detect_changes_service: DetectChangesService,
        sample_changes: list[ComponentChange],
        mock_filter_service: MagicMock,
    ) -> None:
        """Test that deleted components are added to working model for filtering."""
        result = DetectChangesResult(
            changes=sample_changes, deleted=[sample_changes[2]]
        )

        # Configure mock to return a model that includes the deleted component
        mock_filter_service.apply_filters_complete.return_value = {
            "workspaces": {},
            "contexts": {},
            "components": {
                "dev-cluster/postgres": MagicMock(
                    name="postgres", context="dev-cluster", workspace="aws"
                )
            },
        }

        detect_changes_service._apply_filters_to_results(
            result, ["component.config.priority=2"], verbose=False
        )

        # Verify parse_filter_expression was called
        assert mock_filter_service.parse_filter_expression.called

        # Verify apply_filters_complete was called with a working model
        assert mock_filter_service.apply_filters_complete.called
        call_args = mock_filter_service.apply_filters_complete.call_args
        working_model = call_args[0][0]

        # Verify the working model includes the deleted component
        assert "dev-cluster/postgres" in working_model["components"]

        # Verify the deleted component has correct properties
        deleted_component = working_model["components"]["dev-cluster/postgres"]
        assert deleted_component.name == "postgres"
        assert deleted_component.config.active is False
        assert deleted_component.config.priority == 2

    def test_calls_filter_service_parse_filter_expression(
        self,
        detect_changes_service: DetectChangesService,
        sample_changes: list[ComponentChange],
        mock_filter_service: MagicMock,
    ) -> None:
        """Test that we call FilterService.parse_filter_expression for each filter."""
        result = DetectChangesResult(changes=sample_changes)

        filters = ["component.config.active=true", "component.config.priority>1"]
        detect_changes_service._apply_filters_to_results(result, filters, verbose=False)

        # Verify parse_filter_expression was called for each filter
        assert mock_filter_service.parse_filter_expression.call_count == 2
        mock_filter_service.parse_filter_expression.assert_any_call(
            "component.config.active=true"
        )
        mock_filter_service.parse_filter_expression.assert_any_call(
            "component.config.priority>1"
        )

    def test_calls_filter_service_apply_filters_complete(
        self,
        detect_changes_service: DetectChangesService,
        sample_changes: list[ComponentChange],
        mock_filter_service: MagicMock,
    ) -> None:
        """Test that we call FilterService.apply_filters_complete with correct arguments."""
        result = DetectChangesResult(changes=sample_changes)

        filters = ["component.config.active=true"]
        detect_changes_service._apply_filters_to_results(result, filters, verbose=False)

        # Verify apply_filters_complete was called
        assert mock_filter_service.apply_filters_complete.called

        # Verify it was called with working_model and parsed_filters
        call_args = mock_filter_service.apply_filters_complete.call_args
        working_model = call_args[0][0]
        parsed_filters = call_args[0][1]

        # Verify working_model has the expected structure
        assert "workspaces" in working_model
        assert "contexts" in working_model
        assert "components" in working_model

        # Verify parsed_filters is a list
        assert isinstance(parsed_filters, list)
        assert len(parsed_filters) == 1

    def test_maps_filtered_results_back_to_component_changes(
        self,
        detect_changes_service: DetectChangesService,
        sample_changes: list[ComponentChange],
        mock_filter_service: MagicMock,
    ) -> None:
        """Test that filtered component keys are correctly mapped back to ComponentChange objects."""
        result = DetectChangesResult(changes=sample_changes)

        # Configure mock to return only one component (redis in dev-env)
        mock_filter_service.apply_filters_complete.return_value = {
            "workspaces": {},
            "contexts": {},
            "components": {
                "dev-env/redis": MagicMock(
                    name="redis", context="dev-env", workspace="local"
                )
            },
        }

        filtered_result = detect_changes_service._apply_filters_to_results(
            result, ["component.config.active=true"], verbose=False
        )

        # Verify only the matching component is in the result
        assert len(filtered_result.changes) == 1
        assert filtered_result.changes[0].component_name == "redis"
        assert filtered_result.changes[0].context_name == "dev-env"
        assert filtered_result.changes[0].workspace_name == "local"

    def test_multiple_filters_and_logic(
        self,
        detect_changes_service: DetectChangesService,
        sample_changes: list[ComponentChange],
        mock_filter_service: MagicMock,
    ) -> None:
        """Test that multiple filters use AND logic (all must match)."""
        result = DetectChangesResult(changes=sample_changes)

        # Configure mock to simulate AND logic - both filters must match
        # Only redis matches both active=true AND environment=dev
        mock_filter_service.apply_filters_complete.return_value = {
            "workspaces": {},
            "contexts": {},
            "components": {
                "dev-env/redis": MagicMock(
                    name="redis", context="dev-env", workspace="local"
                )
            },
        }

        filters = ["component.config.active=true", "context.environment=dev"]
        filtered_result = detect_changes_service._apply_filters_to_results(
            result, filters, verbose=False
        )

        # Verify parse_filter_expression was called for both filters
        assert mock_filter_service.parse_filter_expression.call_count == 2

        # Verify only redis is in the result (matches both filters)
        assert len(filtered_result.changes) == 1
        assert filtered_result.changes[0].component_name == "redis"

    def test_preserves_deleted_list_in_results(
        self,
        detect_changes_service: DetectChangesService,
        sample_changes: list[ComponentChange],
        mock_filter_service: MagicMock,
    ) -> None:
        """Test that deleted components list is correctly updated after filtering."""
        result = DetectChangesResult(
            changes=sample_changes, deleted=[sample_changes[2]]
        )

        # Configure mock to return only the deleted component
        mock_filter_service.apply_filters_complete.return_value = {
            "workspaces": {},
            "contexts": {},
            "components": {
                "dev-cluster/postgres": MagicMock(
                    name="postgres", context="dev-cluster", workspace="aws"
                )
            },
        }

        filtered_result = detect_changes_service._apply_filters_to_results(
            result, ["component.config.priority=2"], verbose=False
        )

        # Verify deleted component is still in both changes and deleted lists
        assert len(filtered_result.changes) == 1
        assert len(filtered_result.deleted) == 1
        assert filtered_result.deleted[0].component_name == "postgres"
        assert filtered_result.deleted[0].status == ChangeStatus.DELETED

    def test_preserves_required_changes_list(
        self,
        detect_changes_service: DetectChangesService,
        sample_changes: list[ComponentChange],
        mock_filter_service: MagicMock,
    ) -> None:
        """Test that required_changes list is correctly updated after filtering."""
        # Mark redis as required
        result = DetectChangesResult(
            changes=sample_changes, required_changes=[sample_changes[0]]
        )

        # Configure mock to return only redis
        mock_filter_service.apply_filters_complete.return_value = {
            "workspaces": {},
            "contexts": {},
            "components": {
                "dev-env/redis": MagicMock(
                    name="redis", context="dev-env", workspace="local"
                )
            },
        }

        filtered_result = detect_changes_service._apply_filters_to_results(
            result, ["component.config.active=true"], verbose=False
        )

        # Verify required_changes list still contains redis
        assert len(filtered_result.required_changes) == 1
        assert filtered_result.required_changes[0].component_name == "redis"

    def test_handles_filter_parse_error(
        self,
        detect_changes_service: DetectChangesService,
        sample_changes: list[ComponentChange],
        mock_filter_service: MagicMock,
    ) -> None:
        """Test that filter parse errors are properly propagated as ValueError."""
        result = DetectChangesResult(changes=sample_changes)

        # Configure mock to raise an error when parsing
        mock_filter_service.parse_filter_expression.side_effect = Exception(
            "Invalid filter syntax"
        )

        with pytest.raises(ValueError, match="Invalid filter expression"):
            detect_changes_service._apply_filters_to_results(
                result, ["invalid filter"], verbose=False
            )

    def test_component_keys_use_context_component_format(
        self,
        detect_changes_service: DetectChangesService,
        sample_changes: list[ComponentChange],
        mock_filter_service: MagicMock,
    ) -> None:
        """Test that component keys use 'context/component' format (not workspace/context/component)."""
        result = DetectChangesResult(changes=sample_changes)

        detect_changes_service._apply_filters_to_results(
            result, ["component.config.active=true"], verbose=False
        )

        # Verify apply_filters_complete was called
        call_args = mock_filter_service.apply_filters_complete.call_args
        working_model = call_args[0][0]

        # Verify component keys use context/component format
        component_keys = list(working_model["components"].keys())
        for key in component_keys:
            assert "/" in key
            parts = key.split("/")
            # Keys should be context/component (2 parts), not workspace/context/component (3 parts)
            assert len(parts) == 2, f"Expected 'context/component' format, got: {key}"

    def test_regex_filter_on_numeric_priority_field(
        self,
        detect_changes_service: DetectChangesService,
        mock_filter_service: MagicMock,
    ) -> None:
        """Test that regex operators (~=, =~) work correctly on numeric priority fields.

        This is an integration test for the fix that enables regex operators on numeric
        fields by preventing premature type conversion.
        """
        # Create sample changes with various priority values
        changes = [
            ComponentChange(
                component_name="app1",
                context_name="dev",
                workspace_name="local",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                component_active=True,
                component_priority=1,  # Should match pattern "1"
                component_required=False,
                environment="dev",
            ),
            ComponentChange(
                component_name="app10",
                context_name="dev",
                workspace_name="local",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                component_active=True,
                component_priority=10,  # Should match pattern "1" (contains "1")
                component_required=False,
                environment="dev",
            ),
            ComponentChange(
                component_name="app5",
                context_name="dev",
                workspace_name="local",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                component_active=True,
                component_priority=5,  # Should NOT match pattern "1"
                component_required=False,
                environment="dev",
            ),
        ]

        result = DetectChangesResult(changes=changes)

        # Configure mock to simulate regex filtering behavior
        # Pattern "1" should match priorities 1 and 10 (substring match)
        mock_filter_service.parse_filter_expression.return_value = {
            "entity_type": "component",
            "property": "config.priority",
            "operator": "~=",
            "value": "1",  # Pattern should remain as string
        }
        mock_filter_service.apply_filters_complete.return_value = {
            "workspaces": {},
            "contexts": {},
            "components": {
                "dev/app1": MagicMock(name="app1", context="dev", workspace="local"),
                "dev/app10": MagicMock(name="app10", context="dev", workspace="local"),
            },
        }

        filtered_result = detect_changes_service._apply_filters_to_results(
            result, ["component.config.priority~=1"], verbose=False
        )

        # Verify the filter was parsed correctly
        mock_filter_service.parse_filter_expression.assert_called_once_with(
            "component.config.priority~=1"
        )

        # Verify apply_filters_complete was called
        assert mock_filter_service.apply_filters_complete.called

        # Verify only components with priority 1 and 10 are returned (substring match)
        assert len(filtered_result.changes) == 2
        component_names = {change.component_name for change in filtered_result.changes}
        assert component_names == {"app1", "app10"}

        # Verify component with priority 5 was filtered out
        assert "app5" not in component_names
