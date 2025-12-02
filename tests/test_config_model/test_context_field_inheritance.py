"""
Test field inheritance from workspace to context.

Tests that contexts properly inherit fields (like archive_dir, output_dir, and custom fields)
from their parent workspace when those fields are not explicitly set on the context.
"""

from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig


class TestContextFieldInheritance:
    """Test context field inheritance from workspace."""

    def test_inherit_archive_dir_when_not_set(self):
        """Test that context inherits archive_dir when not set."""
        # Create workspace with archive_dir
        workspace = WorkspaceConfig(
            name="test-workspace", archive_dir="workspace-archive"
        )

        # Create context without archive_dir
        context = Context(name="test-context", workspace_ref=workspace)

        # Need to explicitly call inherit_workspace_fields for inheritance
        context.inherit_workspace_fields()

        # Should inherit archive_dir from workspace
        assert context.archive_dir == "workspace-archive"

    def test_inherit_output_dir_when_not_set(self):
        """Test that context inherits output_dir when not set."""
        # Create workspace with output_dir
        workspace = WorkspaceConfig(
            name="test-workspace", output_dir="workspace-output"
        )

        # Create context without output_dir
        context = Context(name="test-context", workspace_ref=workspace)

        # Need to explicitly call inherit_workspace_fields for inheritance
        context.inherit_workspace_fields()

        # Should inherit output_dir from workspace
        assert context.output_dir == "workspace-output"

    def test_context_override_workspace_fields(self):
        """Test that context can override workspace fields."""
        # Create workspace with fields
        workspace = WorkspaceConfig(
            name="test-workspace",
            archive_dir="workspace-archive",
            output_dir="workspace-output",
        )

        # Create context with explicit values
        context = Context(
            name="test-context",
            archive_dir="context-archive",
            output_dir="context-output",
            workspace_ref=workspace,
        )

        # Call inherit_workspace_fields - but should keep explicit values
        context.inherit_workspace_fields()

        # Should use context values, not inherit
        assert context.archive_dir == "context-archive"
        assert context.output_dir == "context-output"

    def test_inherit_custom_fields_from_workspace_extra(self):
        """Test that context inherits custom fields from workspace model_extra."""
        # Create workspace with custom fields
        workspace = WorkspaceConfig(
            name="test-workspace",
            cloud_provider="aws",  # This goes to model_extra
            custom_region="us-west-2",  # This goes to model_extra
        )

        # Create context without custom fields
        context = Context(name="test-context", workspace_ref=workspace)

        # Need to explicitly call inherit_workspace_fields for inheritance
        context.inherit_workspace_fields()

        # Should inherit custom fields from workspace
        assert hasattr(context, "model_extra")
        assert context.model_extra is not None
        assert context.model_extra.get("cloud_provider") == "aws"
        assert context.model_extra.get("custom_region") == "us-west-2"

    def test_context_custom_fields_override_workspace(self):
        """Test that context custom fields override workspace custom fields."""
        # Create workspace with custom fields
        workspace = WorkspaceConfig(
            name="test-workspace", cloud_provider="aws", region="us-east-1"
        )

        # Create context with some custom fields
        context = Context(
            name="test-context",
            region="us-west-2",  # Override workspace region
            environment_type="dev",  # New field not in workspace
            workspace_ref=workspace,
        )

        # Call inherit_workspace_fields to get cloud_provider
        context.inherit_workspace_fields()

        # Should use context value for region, inherit cloud_provider
        assert context.model_extra.get("region") == "us-west-2"
        assert context.model_extra.get("cloud_provider") == "aws"
        assert context.model_extra.get("environment_type") == "dev"

    def test_no_inheritance_without_workspace(self):
        """Test that context works normally without workspace reference."""
        # Create context without workspace
        context = Context(name="test-context", archive_dir="explicit-archive")

        # Should use explicit values, no inheritance
        assert context.archive_dir == "explicit-archive"
        assert context.output_dir is None  # Not inherited

    def test_partial_inheritance(self):
        """Test inheritance of some fields but not others."""
        # Create workspace
        workspace = WorkspaceConfig(
            name="test-workspace",
            archive_dir="workspace-archive",
            output_dir="workspace-output",
        )

        # Create context with only one field set
        context = Context(
            name="test-context",
            archive_dir="context-archive",  # Explicit value
            # output_dir not set - should inherit
            workspace_ref=workspace,
        )

        # Call inherit_workspace_fields for inheritance
        context.inherit_workspace_fields()

        # Should use explicit archive_dir, inherit output_dir
        assert context.archive_dir == "context-archive"
        assert context.output_dir == "workspace-output"

    def test_preserve_workspace_reference(self):
        """Test that workspace reference is preserved for explicit access."""
        # Create workspace
        workspace = WorkspaceConfig(
            name="test-workspace", archive_dir="workspace-archive"
        )

        # Create context
        context = Context(name="test-context", workspace_ref=workspace)

        # Should preserve workspace reference
        assert context.workspace_ref is workspace
        assert context.workspace_ref.name == "test-workspace"
        assert context.workspace_ref.archive_dir == "workspace-archive"
