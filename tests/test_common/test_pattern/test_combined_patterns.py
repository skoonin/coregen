"""
Tests for combined pattern handling in the pattern parser and matcher.

These tests verify that patterns like "context/aws**" are correctly handled
by splitting them into ["aws", "**"] segments and matching them accordingly.
"""

from pathlib import Path
from typing import Any

import pytest

from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.common.pattern.facade import PatternMatcher
from coregen.common.pattern.pattern_parser import PatternParser
from coregen.config_model.access import ConfigAccess
from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig


class TestCombinedPatterns:
    """Test cases for combined patterns like 'context/aws**'."""

    @pytest.fixture
    def pattern_parser(self) -> Any:
        """Create a pattern parser for testing."""
        return PatternParser()

    @pytest.fixture
    def test_workspaces(self) -> Any:
        """Create test workspaces with contexts for testing pattern matching."""
        # Create AWS workspace
        aws_workspace = WorkspaceConfig(name="aws", workspace_dir="test_data/clusters")
        aws_workspace.contexts = {"cluster": {}}

        # Create AWS contexts
        for name in ["aws-cluster-01", "aws-cluster-dev"]:
            context = Context(name=name, environment="dev")
            context.components = {
                "service": {
                    "nginx": Component(name="nginx"),
                    "api": Component(name="api"),
                    "db": Component(name="db"),
                }
            }
            aws_workspace.contexts["cluster"][name] = context

        # Add prod context
        prod_context = Context(name="aws-cluster-prod", environment="prod")
        prod_context.components = {
            "service": {
                "nginx": Component(name="nginx"),
                "api": Component(name="api"),
                "db": Component(name="db"),
            }
        }
        aws_workspace.contexts["cluster"]["aws-cluster-prod"] = prod_context

        # Create local workspace
        local_workspace = WorkspaceConfig(
            name="local", workspace_dir="test_data/contexts"
        )
        local_workspace.contexts = {"context": {}}

        # Create local contexts
        for name, env in [("context-dev", "dev"), ("context-prod", "prod")]:
            context = Context(name=name, environment=env)
            context.components = {
                "service": {
                    "nginx": Component(name="nginx"),
                    "prometheus": Component(name="prometheus"),
                    "metrics-server": Component(name="metrics-server"),
                }
            }
            local_workspace.contexts["context"][name] = context

        return [aws_workspace, local_workspace]

    @pytest.fixture
    def config_access(self, test_workspaces) -> Any:
        """Create a ConfigAccess instance with test workspaces."""
        return ConfigAccess(test_workspaces)

    @pytest.fixture
    def pattern_matcher(self, config_access) -> Any:
        """Create a PatternMatcher instance for testing."""
        logger = Logger("test")
        console = Console()
        root_path = Path.cwd()
        return PatternMatcher(config_access, root_path, console, logger)

    def test_parse_combined_pattern(self, pattern_parser):
        """Test that patterns like 'context/aws**' are parsed correctly."""
        # Test parsing a combined pattern
        pattern = "context/aws**"
        spec = pattern_parser.parse(pattern)

        # Verify the raw pattern was transformed
        assert spec.raw_pattern == "context/aws/**"

        # Verify segments were split correctly
        assert spec.segments == ["aws", "**"]

        # Compare with the explicitly correct pattern
        explicit_pattern = "context/aws/**"
        explicit_spec = pattern_parser.parse(explicit_pattern)

        # Both patterns should produce the same segments
        assert explicit_spec.segments == spec.segments

    def test_parse_simple_pattern(self, pattern_parser):
        """Test that normal patterns like 'context/aws*' are parsed correctly."""
        # Test parsing a simple wildcard pattern
        pattern = "context/aws*"
        spec = pattern_parser.parse(pattern)

        # Verify no transformation occurred
        assert spec.raw_pattern == pattern

        # Verify segments were split correctly
        assert spec.segments == ["aws*"]

    def test_match_combined_pattern(self, pattern_matcher, config_access):
        """Test that patterns like 'context/aws**' match the expected contexts."""
        # Test matching a combined pattern
        pattern = "context/aws**"
        result = pattern_matcher.match(pattern)

        # Verify the combined pattern matches all AWS contexts
        assert len(result["contexts"]) == 3
        assert "aws-cluster-prod" in result["contexts"]
        assert "aws-cluster-dev" in result["contexts"]
        assert "aws-cluster-01" in result["contexts"]

    def test_match_explicit_pattern(self, pattern_matcher, config_access):
        """Test that patterns like 'context/aws/**' match the expected contexts."""
        # Test matching an explicit pattern with the same meaning
        pattern = "context/aws/**"
        result = pattern_matcher.match(pattern)

        # Verify the explicit pattern matches all AWS contexts
        assert len(result["contexts"]) == 3
        assert "aws-cluster-prod" in result["contexts"]
        assert "aws-cluster-dev" in result["contexts"]
        assert "aws-cluster-01" in result["contexts"]

    def test_match_simple_wildcard(self, pattern_matcher, config_access):
        """Test that patterns like 'context/aws*' match the expected contexts."""
        # Test matching a simple wildcard pattern
        pattern = "context/aws*"
        result = pattern_matcher.match(pattern)

        # Verify the simple wildcard matches all AWS contexts
        assert len(result["contexts"]) == 3
        assert "aws-cluster-prod" in result["contexts"]
        assert "aws-cluster-dev" in result["contexts"]
        assert "aws-cluster-01" in result["contexts"]

    def test_match_exact_pattern(self, pattern_matcher, config_access):
        """Test that patterns like 'context/aws' match the expected contexts."""
        # Test matching an exact pattern (no wildcards)
        pattern = "context/aws"
        result = pattern_matcher.match(pattern)

        # Verify the exact pattern matches all AWS contexts due to prefix matching
        assert len(result["contexts"]) == 3
        assert "aws-cluster-prod" in result["contexts"]
        assert "aws-cluster-dev" in result["contexts"]
        assert "aws-cluster-01" in result["contexts"]

    def test_find_contexts_directly(self, config_access):
        """Test the ConfigAccess.find_contexts method with different patterns."""
        # Test with an exact pattern from the pattern matcher context
        # This would typically expand to "aws*" with our fix
        contexts = config_access.find_contexts("aws")

        # Should match all AWS contexts
        assert len(contexts) == 3
        assert any(ctx.name == "aws-cluster-prod" for ctx in contexts)
        assert any(ctx.name == "aws-cluster-dev" for ctx in contexts)
        assert any(ctx.name == "aws-cluster-01" for ctx in contexts)

        # Test with an explicit wildcard pattern
        contexts = config_access.find_contexts("aws*")

        # Should match all AWS contexts
        assert len(contexts) == 3
        assert any(ctx.name == "aws-cluster-prod" for ctx in contexts)
        assert any(ctx.name == "aws-cluster-dev" for ctx in contexts)
        assert any(ctx.name == "aws-cluster-01" for ctx in contexts)
