"""Tests for template context adapter."""

from typing import Any

import pytest

from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context
from coregen.config_model.template_context import TemplateContextAdapter


@pytest.fixture
def sample_context() -> Any:
    """Create a sample context with components."""
    context = Context(
        name="test-cluster",
        environment="dev",
        region="us-west-2",
        # Use cluster as context_type to match the default in the adapter
        context_type="cluster",
        component_type="app",
    )

    # Add a component with nested properties
    # Pass config as a dictionary instead of ComponentConfig instance
    component = Component(
        name="nginx",
        config={"active": True, "for_commit": True, "path": "components/nginx"},
        version="1.20",
        port=80,
        env_vars={"LOG_LEVEL": "info", "MAX_CLIENTS": 100},
    )

    # Add component to context directly using the components dictionary
    if "app" not in context.components:
        context.components["app"] = {}
    context.components["app"]["nginx"] = component

    return context


def test_adapter_initialization(sample_context):
    """Test template context adapter initialization."""
    # Create adapter with default context_type
    adapter = TemplateContextAdapter(sample_context)

    # Should use context's context_type by default
    assert adapter._context_type == "cluster"
    assert adapter._context == sample_context

    # Should have initialized namespaces
    assert hasattr(adapter, "cluster")  # Context namespace
    assert hasattr(adapter, "app")  # Component namespace


def test_namespace_creation(sample_context):
    """Test namespace creation for context and components."""
    adapter = TemplateContextAdapter(sample_context)

    # Context namespace should contain context properties
    context_ns = adapter.cluster
    assert context_ns["name"] == "test-cluster"
    assert context_ns["environment"] == "dev"
    # region should now be included with the fix
    assert context_ns["region"] == "us-west-2"
    assert context_ns["active"] is False
    assert context_ns["commit_dir"] == "for-commit"

    # Component namespace should contain components
    component_ns = adapter.app
    assert "nginx" in component_ns
    assert component_ns["nginx"].name == "nginx"
    assert component_ns["nginx"].version == "1.20"


def test_hyphenated_name_handling():
    """Test handling of hyphenated names in context and component types."""
    # Create context with hyphenated type names
    context = Context(
        name="test-cluster",
        environment="dev",
        context_type="aws-cluster",
        component_type="k8s-app",
    )

    # Create a component with config as a dictionary
    component = Component(
        name="test-app", config={"active": True}  # Simple dictionary config
    )

    # Add component directly to the context's components dictionary
    if "k8s-app" not in context.components:
        context.components["k8s-app"] = {}
    context.components["k8s-app"]["test-app"] = component

    # Create adapter
    adapter = TemplateContextAdapter(context)

    # Hyphenated names are preserved but not transformed to underscores
    # as that feature was deprecated in favor of error messages
    assert hasattr(adapter, "aws-cluster")
    assert hasattr(adapter, "k8s-app")
    assert not hasattr(adapter, "aws_cluster")  # No underscored version
    assert not hasattr(adapter, "k8s_app")  # No underscored version


def test_to_dict_method(sample_context):
    """Test to_dict method returns all namespaces."""
    adapter = TemplateContextAdapter(sample_context)
    result = adapter.to_dict()

    # Should include all namespaces
    assert "cluster" in result
    assert "app" in result

    # Should have correct values
    assert result["cluster"]["name"] == "test-cluster"
    assert "nginx" in result["app"]


def test_get_context_properties(sample_context):
    """Test getting context properties."""
    adapter = TemplateContextAdapter(sample_context)
    properties = adapter.get_context_properties()

    # Should return context namespace
    assert properties["name"] == "test-cluster"
    assert properties["environment"] == "dev"


def test_get_component_types(sample_context):
    """Test getting component types."""
    adapter = TemplateContextAdapter(sample_context)
    components = adapter.get_component_types()

    # Should return dictionary of component types
    assert "app" in components
    assert "nginx" in components["app"]
    assert components["app"]["nginx"].name == "nginx"


def test_extra_fields_handling():
    """Test that extra fields in context are properly included in the namespace."""
    # Create context with extra fields
    context = Context(
        name="test-cluster",
        environment="dev",
        context_type="cluster",
        # Extra fields that should be included
        region="us-east-1",
        account_id="123456789",
        vpc_id="vpc-12345",
        custom_field="custom_value",
    )

    # Create adapter
    adapter = TemplateContextAdapter(context)

    # Check that extra fields are included in the context namespace
    context_ns = adapter.cluster
    assert context_ns["name"] == "test-cluster"
    assert context_ns["environment"] == "dev"
    assert context_ns["region"] == "us-east-1"
    assert context_ns["account_id"] == "123456789"
    assert context_ns["vpc_id"] == "vpc-12345"
    assert context_ns["custom_field"] == "custom_value"

    # Also check in to_dict output
    result = adapter.to_dict()
    assert result["cluster"]["region"] == "us-east-1"
    assert result["cluster"]["account_id"] == "123456789"
    assert result["cluster"]["vpc_id"] == "vpc-12345"
    assert result["cluster"]["custom_field"] == "custom_value"
