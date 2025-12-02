"""Tests for pattern parser module."""

from typing import Any

import pytest

from coregen.common.pattern.pattern_parser import PatternParser
from coregen.common.pattern.pattern_spec import (
    LogicalPatternSpec,
    LogicalPrefixType,
    PatternType,
)


@pytest.fixture
def setup_pattern_parser() -> Any:
    """Set up the test environment."""
    parser = PatternParser()
    return {
        "parser": parser,
    }


class TestPatternParser:
    """Tests for the PatternParser class."""

    def test_empty_pattern(self, setup_pattern_parser):
        """Test parsing an empty pattern."""

        parser = setup_pattern_parser["parser"]

        with pytest.raises(ValueError):
            parser.parse("")

    def test_parse_workspace_pattern(self, setup_pattern_parser):
        """Test parsing a workspace pattern."""

        parser = setup_pattern_parser["parser"]

        spec = parser.parse("workspace/aws")

        assert isinstance(spec, LogicalPatternSpec)
        assert spec.pattern_type == PatternType.LOGICAL
        assert spec.prefix_type == LogicalPrefixType.WORKSPACE
        assert spec.segments == ["aws"]
        assert len(spec.tokens) == 2
        assert spec.tokens[0].value == "workspace"
        assert spec.tokens[1].value == "aws"

    def test_parse_workspace_pattern_with_wildcard(self, setup_pattern_parser):
        """Test parsing a workspace pattern with wildcards."""

        parser = setup_pattern_parser["parser"]

        spec = parser.parse("workspace/*/dev")

        assert isinstance(spec, LogicalPatternSpec)
        assert spec.pattern_type == PatternType.LOGICAL
        assert spec.prefix_type == LogicalPrefixType.WORKSPACE
        assert spec.segments == ["*", "dev"]
        assert len(spec.tokens) == 3
        assert spec.tokens[1].value == "*"
        assert spec.tokens[1].is_wildcard

    def test_parse_workspace_pattern_with_recursive(self, setup_pattern_parser):
        """Test parsing a workspace pattern with recursive wildcard."""

        parser = setup_pattern_parser["parser"]

        spec = parser.parse("workspace/aws/**")

        assert isinstance(spec, LogicalPatternSpec)
        assert spec.pattern_type == PatternType.LOGICAL
        assert spec.prefix_type == LogicalPrefixType.WORKSPACE
        assert spec.segments == ["aws", "**"]
        assert len(spec.tokens) == 3
        assert spec.tokens[2].value == "**"
        assert spec.tokens[2].is_wildcard
        assert spec.tokens[2].is_recursive

    def test_parse_context_pattern(self, setup_pattern_parser):
        """Test parsing a context pattern."""

        parser = setup_pattern_parser["parser"]

        spec = parser.parse("context/aws-cluster-dev")

        assert isinstance(spec, LogicalPatternSpec)
        assert spec.pattern_type == PatternType.LOGICAL
        assert spec.prefix_type == LogicalPrefixType.CONTEXT
        assert spec.segments == ["aws-cluster-dev"]

    def test_parse_component_pattern(self, setup_pattern_parser):
        """Test parsing a component pattern."""

        parser = setup_pattern_parser["parser"]

        spec = parser.parse("component/prometheus")

        assert isinstance(spec, LogicalPatternSpec)
        assert spec.pattern_type == PatternType.LOGICAL
        assert spec.prefix_type == LogicalPrefixType.COMPONENT
        assert spec.segments == ["prometheus"]

    def test_parse_pattern_without_prefix(self, setup_pattern_parser):
        """Test parsing a pattern without a valid prefix raises error."""

        parser = setup_pattern_parser["parser"]

        with pytest.raises(
            ValueError, match="Pattern must start with a recognized prefix"
        ):
            parser.parse("contexts/aws")

    def test_parse_filesystem_patterns_rejected(self, setup_pattern_parser):
        """Test that filesystem patterns are rejected."""

        parser = setup_pattern_parser["parser"]

        filesystem_patterns = [
            "d/contexts/aws",
            "p/test.yaml",
            "dir/workspaces",
            "path/to/file",
        ]

        for pattern in filesystem_patterns:
            with pytest.raises(
                ValueError, match="Pattern must start with a recognized prefix"
            ):
                parser.parse(pattern)

    def test_tokenize_with_special_characters(self, setup_pattern_parser):
        """Test tokenizing patterns with special characters."""

        parser = setup_pattern_parser["parser"]

        spec = parser.parse("w/aws-[dev,prod]/*")

        assert isinstance(spec, LogicalPatternSpec)
        assert spec.pattern_type == PatternType.LOGICAL
        assert spec.prefix_type == LogicalPrefixType.WORKSPACE
        assert len(spec.segments) == 2
        assert spec.segments[0] == "aws-[dev,prod]"
        assert spec.segments[1] == "*"

        # Check tokens contain the wildcard
        assert any(token.is_wildcard for token in spec.tokens)
