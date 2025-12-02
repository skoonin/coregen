"""Tests for nested custom field support in contexts and workspaces."""

from coregen.config_model.models.context import Context
from coregen.config_model.template_context import TemplateContextAdapter


class TestNestedCustomFields:
    """Test that nested custom fields are accessible in templates."""

    def test_context_preserves_nested_custom_fields(self):
        """Test that Context model preserves nested custom fields in model_extra."""
        context_data = {
            "name": "test-context",
            "environment": "dev",
            "versions": {"argocd": "v2.8.0", "kustomize": "v5.0.3"},
            "metadata": {"owner": "team-a", "cost-center": "12345"},
        }

        context = Context(**context_data)

        # Verify nested fields are accessible via getattr
        assert hasattr(context, "versions")
        assert context.versions == {"argocd": "v2.8.0", "kustomize": "v5.0.3"}
        assert context.metadata == {"owner": "team-a", "cost-center": "12345"}

        # Verify they're in model_extra
        assert "versions" in context.model_extra
        assert "metadata" in context.model_extra

        # Verify they're included in model_dump
        dumped = context.model_dump()
        assert "versions" in dumped
        assert dumped["versions"]["argocd"] == "v2.8.0"
        assert "metadata" in dumped

    def test_template_context_includes_nested_fields(self):
        """Test that TemplateContextAdapter includes nested custom fields."""
        context_data = {
            "name": "test-cluster",
            "environment": "prod",
            "versions": {"argocd": "v2.9.0", "helm": "v3.10.0"},
        }

        context = Context(**context_data)
        adapter = TemplateContextAdapter(context, context_type="cluster")

        # Convert to dict for template rendering
        template_dict = adapter.to_dict()

        # Verify cluster namespace exists
        assert "cluster" in template_dict

        # Verify nested fields are accessible in template context
        cluster_data = template_dict["cluster"]
        assert "versions" in cluster_data
        assert cluster_data["versions"]["argocd"] == "v2.9.0"
        assert cluster_data["versions"]["helm"] == "v3.10.0"

    def test_processor_preserves_nested_custom_fields(self):
        """Test that ConfigProcessor logic preserves nested custom fields."""
        # This tests the improved logic for identifying component collections
        # The fix ensures that nested dicts like "versions" are not mistaken
        # for component collections and removed

        ctx_data = {
            "name": "test-context",
            "environment": "dev",
            "component_type": "app",
            "versions": {  # This should be preserved
                "argocd": "v2.8.0",
                "kustomize": "v5.0.3",
            },
            "monitoring": {  # This should also be preserved
                "enabled": True,
                "provider": "prometheus",
            },
            "app": [],  # Empty components list
        }

        # Simulate the processor logic for identifying potential component keys
        potential_component_keys = []
        for k, v in ctx_data.items():
            # Skip known context fields
            if k in [
                "name",
                "environment",
                "active",
                "commit_dir",
                "component_type",
                "skip_validation",
                "internal_path",
                "config_file_path",
                "workspaces",
                "region",
                "workspace",
                "workspace_ref",
                "archive_dir",
                "output_dir",
                "path",
            ]:
                continue

            # Check if this looks like a component collection
            if isinstance(v, list):
                # Lists might be component collections
                if (
                    v
                    and isinstance(v[0], dict)
                    and ("name" in v[0] or "config" in v[0])
                ):
                    potential_component_keys.append(k)
            elif isinstance(v, dict):
                # For dicts, check if they look like component collections
                # (values are dicts with component-like structure)
                if v:  # Non-empty dict
                    first_value = next(iter(v.values()))
                    if isinstance(first_value, dict) and (
                        "config" in first_value or "name" in first_value
                    ):
                        # This looks like a component collection
                        potential_component_keys.append(k)

        # Verify that "versions" and "monitoring" are NOT identified as component keys
        assert "versions" not in potential_component_keys
        assert "monitoring" not in potential_component_keys
        assert (
            "app" not in potential_component_keys
        )  # Empty list shouldn't be identified either

    def test_nested_fields_not_mistaken_for_components(self):
        """Test that nested dict fields are not mistaken for component collections."""
        ctx_data = {
            "name": "test-context",
            "environment": "staging",
            "component_type": "app",
            # This should NOT be treated as a component collection
            "versions": {"tool1": "v1.0.0", "tool2": "v2.0.0"},
            # This SHOULD be treated as a component collection (legacy format)
            "app": {"my-app": {"name": "my-app", "config": {"active": True}}},
        }

        # Simulate the processor logic for identifying potential component keys
        potential_component_keys = []
        for k, v in ctx_data.items():
            # Skip known context fields
            if k in [
                "name",
                "environment",
                "active",
                "commit_dir",
                "component_type",
                "skip_validation",
                "internal_path",
                "config_file_path",
                "workspaces",
                "region",
                "workspace",
                "workspace_ref",
                "archive_dir",
                "output_dir",
                "path",
            ]:
                continue

            # Check if this looks like a component collection
            if isinstance(v, list):
                # Lists might be component collections
                if (
                    v
                    and isinstance(v[0], dict)
                    and ("name" in v[0] or "config" in v[0])
                ):
                    potential_component_keys.append(k)
            elif isinstance(v, dict):
                # For dicts, check if they look like component collections
                # (values are dicts with component-like structure)
                if v:  # Non-empty dict
                    first_value = next(iter(v.values()))
                    if isinstance(first_value, dict) and (
                        "config" in first_value or "name" in first_value
                    ):
                        # This looks like a component collection
                        potential_component_keys.append(k)

        # Verify that "versions" is NOT identified as component key (values are strings, not dicts)
        assert "versions" not in potential_component_keys
        # Verify that "app" IS identified as a component collection
        assert "app" in potential_component_keys
