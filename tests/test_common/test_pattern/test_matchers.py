"""Tests for pattern matchers module."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from coregen.common.pattern.matchers import (
    ComponentMatcher,
    ContextMatcher,
    Matcher,
    WorkspaceMatcher,
)
from coregen.common.pattern.pattern_spec import (
    LogicalPatternSpec,
    LogicalPrefixType,
    PatternSpec,
    PatternType,
)


@pytest.fixture
def setup_matcher() -> Any:
    """Set up test environment."""
    # Create mock objects for testing
    mock_config_access = MagicMock()
    mock_spec = MagicMock(spec=PatternSpec)

    # Create test result container
    result = {"workspaces": {}, "contexts": {}, "components": {}}

    return {
        "mock_config_access": mock_config_access,
        "mock_spec": mock_spec,
        "result": result,
    }


class TestMatcher:
    """Tests for base Matcher class."""

    def test_add_matched_workspace(self, setup_matcher):
        """Test adding a matched workspace to the result."""
        mock_config_access = setup_matcher["mock_config_access"]
        mock_spec = setup_matcher["mock_spec"]
        result = setup_matcher["result"]

        # Create concrete subclass for testing abstract base class
        class TestMatcherImpl(Matcher):
            def match(self, result):
                return True

        # Create test matcher
        matcher = TestMatcherImpl(mock_spec, mock_config_access)

        # Create mock workspace
        mock_workspace = MagicMock()
        mock_workspace.name = "test-ws"

        # Test adding without children
        matcher._add_matched_workspace(mock_workspace, result, add_children=False)
        assert "test-ws" in result["workspaces"]
        assert result["workspaces"]["test-ws"] == mock_workspace

        # Verify get_all_contexts wasn't called (no children added)
        mock_config_access.get_all_contexts.assert_not_called()


@pytest.fixture
def setup_workspace_matcher() -> Any:
    """Set up test environment."""
    # Create mock objects for testing
    mock_config_access = MagicMock()

    # Create test spec
    workspace_spec = LogicalPatternSpec(
        raw_pattern="workspace/aws",
        pattern_type=PatternType.LOGICAL,
        tokens=[],
        prefix_type=LogicalPrefixType.WORKSPACE,
        segments=["aws"],
    )

    # Create test result container
    result = {"workspaces": {}, "contexts": {}, "components": {}}

    return {
        "mock_config_access": mock_config_access,
        "workspace_spec": workspace_spec,
        "result": result,
    }


class TestWorkspaceMatcher:
    """Tests for WorkspaceMatcher class."""

    def test_match_single_workspace(self, setup_workspace_matcher):
        """Test matching a single workspace."""
        mock_config_access = setup_workspace_matcher["mock_config_access"]
        workspace_spec = setup_workspace_matcher["workspace_spec"]
        result = setup_workspace_matcher["result"]

        # Create matcher
        matcher = WorkspaceMatcher(workspace_spec, mock_config_access)

        # Set up mock return values
        mock_workspace = MagicMock()
        mock_workspace.name = "aws"

        mock_config_access.find_workspaces.return_value = [mock_workspace]
        mock_config_access.get_all_contexts.return_value = {}

        # Test matching
        match_result = matcher.match(result)

        # Verify results
        assert match_result is True
        assert "aws" in result["workspaces"]
        mock_config_access.find_workspaces.assert_called_once_with("aws")

    def test_match_workspace_with_wildcard(self, setup_workspace_matcher):
        """Test matching workspaces with wildcards."""
        mock_config_access = setup_workspace_matcher["mock_config_access"]
        result = setup_workspace_matcher["result"]

        # Create matcher with wildcard pattern
        wildcard_spec = LogicalPatternSpec(
            raw_pattern="workspace/aws*",
            pattern_type=PatternType.LOGICAL,
            tokens=[],
            prefix_type=LogicalPrefixType.WORKSPACE,
            segments=["aws*"],  # Wildcard pattern
        )
        matcher = WorkspaceMatcher(wildcard_spec, mock_config_access)

        # Set up mock return values - multiple workspaces that match the pattern
        mock_workspace1 = MagicMock()
        mock_workspace1.name = "aws-dev"
        mock_workspace2 = MagicMock()
        mock_workspace2.name = "aws-prod"
        mock_workspace3 = MagicMock()
        mock_workspace3.name = "gcp-dev"  # Should not match

        mock_config_access.find_workspaces.return_value = [
            mock_workspace1,
            mock_workspace2,
        ]
        mock_config_access.get_all_contexts.return_value = {}

        # Test matching
        match_result = matcher.match(result)

        # Verify results
        assert match_result is True
        assert "aws-dev" in result["workspaces"]
        assert "aws-prod" in result["workspaces"]
        assert "gcp-dev" not in result["workspaces"]

        # Verify the find_workspaces was called with the right pattern
        mock_config_access.find_workspaces.assert_called_once_with("aws*")


@pytest.fixture
def setup_context_matcher() -> Any:
    """Set up test environment."""
    # Create mock objects for testing
    mock_config_access = MagicMock()

    # Create test spec
    context_spec = LogicalPatternSpec(
        raw_pattern="context/aws-cluster-dev",
        pattern_type=PatternType.LOGICAL,
        tokens=[],
        prefix_type=LogicalPrefixType.CONTEXT,
        segments=["aws-cluster-dev"],
    )

    # Create test result container
    result = {"workspaces": {}, "contexts": {}, "components": {}}

    return {
        "mock_config_access": mock_config_access,
        "context_spec": context_spec,
        "result": result,
    }


class TestContextMatcher:
    """Tests for ContextMatcher class."""

    def test_match_single_context(self, setup_context_matcher):
        """Test matching a single context."""
        mock_config_access = setup_context_matcher["mock_config_access"]
        context_spec = setup_context_matcher["context_spec"]
        result = setup_context_matcher["result"]

        # Create matcher
        matcher = ContextMatcher(context_spec, mock_config_access)

        # Set up mock return values
        mock_context = MagicMock()
        mock_context.name = "aws-cluster-dev"
        mock_context.get_all_components.return_value = {}

        mock_workspace = MagicMock()
        mock_workspace.name = "aws"

        mock_config_access.find_contexts.return_value = [mock_context]
        mock_config_access._get_workspace_from_context.return_value = mock_workspace

        # Test matching
        match_result = matcher.match(result)

        # Verify results
        assert match_result is True
        assert "aws-cluster-dev" in result["contexts"]
        assert "aws" in result["workspaces"]
        mock_config_access.find_contexts.assert_called_once_with("aws-cluster-dev")

    def test_match_context_with_wildcard(self, setup_context_matcher):
        """Test matching contexts with wildcards."""
        mock_config_access = setup_context_matcher["mock_config_access"]
        result = setup_context_matcher["result"]

        # Create matcher with wildcard pattern
        wildcard_spec = LogicalPatternSpec(
            raw_pattern="context/*-dev",
            pattern_type=PatternType.LOGICAL,
            tokens=[],
            prefix_type=LogicalPrefixType.CONTEXT,
            segments=["*-dev"],  # Wildcard pattern matching any dev context
        )
        matcher = ContextMatcher(wildcard_spec, mock_config_access)

        # Set up mock return values - multiple contexts that match the pattern
        mock_context1 = MagicMock()
        mock_context1.name = "aws-cluster-dev"
        mock_context1.get_all_components.return_value = {}

        mock_context2 = MagicMock()
        mock_context2.name = "gcp-cluster-dev"
        mock_context2.get_all_components.return_value = {}

        mock_context3 = MagicMock()
        mock_context3.name = "aws-cluster-prod"  # Should not match
        mock_context3.get_all_components.return_value = {}

        # Mock the workspaces for each context
        mock_workspace1 = MagicMock()
        mock_workspace1.name = "aws"

        mock_workspace2 = MagicMock()
        mock_workspace2.name = "gcp"

        mock_config_access.find_contexts.return_value = [
            mock_context1,
            mock_context2,
        ]
        mock_config_access._get_workspace_from_context.side_effect = lambda ctx: {
            "aws-cluster-dev": mock_workspace1,
            "gcp-cluster-dev": mock_workspace2,
        }.get(ctx.name)

        # Test matching
        match_result = matcher.match(result)

        # Verify results
        assert match_result is True
        assert "aws-cluster-dev" in result["contexts"]
        assert "gcp-cluster-dev" in result["contexts"]
        assert "aws-cluster-prod" not in result["contexts"]
        assert "aws" in result["workspaces"]
        assert "gcp" in result["workspaces"]

        # Verify the find_contexts was called with the right pattern
        mock_config_access.find_contexts.assert_called_once_with("*-dev")


@pytest.fixture
def setup_component_matcher() -> Any:
    """Set up test environment."""
    # Create mock objects for testing
    mock_config_access = MagicMock()

    # Create test spec
    component_spec = LogicalPatternSpec(
        raw_pattern="component/prometheus",
        pattern_type=PatternType.LOGICAL,
        tokens=[],
        prefix_type=LogicalPrefixType.COMPONENT,
        segments=["prometheus"],
    )

    # Create test result container
    result = {"workspaces": {}, "contexts": {}, "components": {}}

    return {
        "mock_config_access": mock_config_access,
        "component_spec": component_spec,
        "result": result,
    }


class TestComponentMatcher:
    """Tests for ComponentMatcher class."""

    def test_match_single_component(self, setup_component_matcher):
        """Test matching a single component."""
        mock_config_access = setup_component_matcher["mock_config_access"]
        component_spec = setup_component_matcher["component_spec"]
        result = setup_component_matcher["result"]

        # Create matcher
        matcher = ComponentMatcher(component_spec, mock_config_access)

        # Set up mock return values
        mock_component = MagicMock()
        mock_component.name = "prometheus"

        mock_context = MagicMock()
        mock_context.name = "aws-cluster-dev"

        mock_workspace = MagicMock()
        mock_workspace.name = "aws"

        mock_config_access.find_components.return_value = [mock_component]
        mock_config_access._find_context_with_component.return_value = mock_context
        mock_config_access._get_workspace_from_context.return_value = mock_workspace

        # Test matching
        match_result = matcher.match(result)

        # Verify results
        assert match_result is True
        assert "aws-cluster-dev/prometheus" in result["components"]
        assert "aws-cluster-dev" in result["contexts"]
        mock_config_access.find_components.assert_called_once_with("prometheus")

    def test_match_component_with_wildcard(self, setup_component_matcher):
        """Test matching components with wildcards."""
        mock_config_access = setup_component_matcher["mock_config_access"]
        result = setup_component_matcher["result"]

        # Create matcher with wildcard pattern
        wildcard_spec = LogicalPatternSpec(
            raw_pattern="component/*metrics*",
            pattern_type=PatternType.LOGICAL,
            tokens=[],
            prefix_type=LogicalPrefixType.COMPONENT,
            segments=[
                "*metrics*"
            ],  # Wildcard pattern matching any component with metrics in the name
        )
        matcher = ComponentMatcher(wildcard_spec, mock_config_access)

        # Set up mock return values - multiple components that match the pattern
        mock_component1 = MagicMock()
        mock_component1.name = "metrics-server"

        mock_component2 = MagicMock()
        mock_component2.name = "prometheus-metrics"

        mock_component3 = MagicMock()
        mock_component3.name = "nginx"  # Should not match

        # Mock the contexts for each component
        mock_context1 = MagicMock()
        mock_context1.name = "aws-cluster-dev"

        mock_context2 = MagicMock()
        mock_context2.name = "aws-cluster-prod"

        # Mock the workspaces for each context
        mock_workspace = MagicMock()
        mock_workspace.name = "aws"

        mock_config_access.find_components.return_value = [
            mock_component1,
            mock_component2,
        ]  # Define how _find_context_with_component should behave

        def find_context_side_effect(comp):
            return {
                "metrics-server": mock_context1,
                "prometheus-metrics": mock_context2,
            }.get(comp.name)

        mock_config_access._find_context_with_component.side_effect = (
            find_context_side_effect
        )
        mock_config_access._get_workspace_from_context.return_value = mock_workspace

        # Test matching
        match_result = matcher.match(result)

        # Verify results
        assert match_result is True
        assert "aws-cluster-dev/metrics-server" in result["components"]
        assert "aws-cluster-prod/prometheus-metrics" in result["components"]
        assert "aws" in result["workspaces"]
        assert "aws-cluster-dev" in result["contexts"]
        assert "aws-cluster-prod" in result["contexts"]

        # Verify the find_components was called with the right pattern
        mock_config_access.find_components.assert_called_once_with("*metrics*")
