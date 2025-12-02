"""Tests for the new pattern prefix system."""

from typing import Any

import pytest

from coregen.common.pattern.pattern_parser import PatternParseError, PatternParser
from coregen.common.pattern.pattern_spec import (
    LogicalPatternSpec,
    LogicalPrefixType,
    PatternType,
)


@pytest.fixture
def setup_prefix_system() -> Any:
    """Set up the test environment."""
    parser = PatternParser()

    return {"parser": parser}


class TestPatternPrefixSystem:
    """Tests for the new pattern prefix system."""

    def test_short_workspace_prefix(self, setup_prefix_system):
        parser = setup_prefix_system["parser"]
        """Test parsing workspace patterns with short prefix."""
        spec = parser.parse("w/aws")

        assert isinstance(spec, LogicalPatternSpec)
        assert spec.pattern_type == PatternType.LOGICAL
        assert spec.prefix_type == LogicalPrefixType.WORKSPACE
        assert spec.segments == ["aws"]

    def test_long_workspace_prefix(self, setup_prefix_system):
        parser = setup_prefix_system["parser"]
        """Test parsing workspace patterns with long prefix."""
        spec = parser.parse("workspace/aws")

        assert isinstance(spec, LogicalPatternSpec)
        assert spec.pattern_type == PatternType.LOGICAL
        assert spec.prefix_type == LogicalPrefixType.WORKSPACE
        assert spec.segments == ["aws"]

    def test_short_context_prefix(self, setup_prefix_system):
        parser = setup_prefix_system["parser"]
        """Test parsing context patterns with short prefix."""
        spec = parser.parse("c/dev-cluster")

        assert isinstance(spec, LogicalPatternSpec)
        assert spec.pattern_type == PatternType.LOGICAL
        assert spec.prefix_type == LogicalPrefixType.CONTEXT
        assert spec.segments == ["dev-cluster"]

    def test_long_context_prefix(self, setup_prefix_system):
        parser = setup_prefix_system["parser"]
        """Test parsing context patterns with long prefix."""
        spec = parser.parse("context/dev-cluster")

        assert isinstance(spec, LogicalPatternSpec)
        assert spec.pattern_type == PatternType.LOGICAL
        assert spec.prefix_type == LogicalPrefixType.CONTEXT
        assert spec.segments == ["dev-cluster"]

    def test_short_component_prefix(self, setup_prefix_system):
        parser = setup_prefix_system["parser"]
        """Test parsing component patterns with short prefix."""
        spec = parser.parse("cm/nginx")

        assert isinstance(spec, LogicalPatternSpec)
        assert spec.pattern_type == PatternType.LOGICAL
        assert spec.prefix_type == LogicalPrefixType.COMPONENT
        assert spec.segments == ["nginx"]

    def test_long_component_prefix(self, setup_prefix_system):
        parser = setup_prefix_system["parser"]
        """Test parsing component patterns with long prefix."""
        spec = parser.parse("component/nginx")

        assert isinstance(spec, LogicalPatternSpec)
        assert spec.pattern_type == PatternType.LOGICAL
        assert spec.prefix_type == LogicalPrefixType.COMPONENT
        assert spec.segments == ["nginx"]

    def test_filesystem_prefixes_rejected(self, setup_prefix_system):
        parser = setup_prefix_system["parser"]
        """Test that filesystem prefixes are properly rejected."""
        filesystem_patterns = [
            "d/contexts/aws",
            "dir/contexts/aws",
            "p/test.yaml",
            "path/to/file",
            "d/contexts/aws/*",
            "dir/contexts/aws/**",
            "p/**/*.yaml",
            "path/contexts/**",
        ]

        for pattern in filesystem_patterns:
            with pytest.raises(
                ValueError, match="Pattern must start with a recognized prefix"
            ):
                parser.parse(pattern)

    def test_logical_patterns_with_wildcards(self, setup_prefix_system):
        parser = setup_prefix_system["parser"]
        """Test logical patterns with wildcards work correctly."""
        spec = parser.parse("w/aws/**")

        assert isinstance(spec, LogicalPatternSpec)
        assert spec.pattern_type == PatternType.LOGICAL
        assert spec.prefix_type == LogicalPrefixType.WORKSPACE

    def test_empty_pattern_after_prefix(self, setup_prefix_system):
        parser = setup_prefix_system["parser"]
        """Test that patterns with just prefixes are handled."""
        # Test with valid prefixes - these now parse successfully as match-all patterns
        valid_prefixes = ["w/", "workspace/", "c/", "context/", "cm/", "component/"]

        for prefix in valid_prefixes:
            # These should parse successfully now
            spec = parser.parse(prefix)
            assert spec is not None
            assert spec.pattern_type == PatternType.LOGICAL

    def test_no_prefix_error(self, setup_prefix_system):
        parser = setup_prefix_system["parser"]
        """Test that patterns without recognized prefixes raise appropriate error."""
        with pytest.raises(PatternParseError) as exc_info:
            parser.parse("contexts/aws")

        error = exc_info.value
        assert "must start with a recognized prefix" in str(error)
        assert "For workspace patterns: w/ or workspace/" in error.suggestions
        assert "For context patterns: c/ or context/" in error.suggestions
        assert "For component patterns: cm/ or component/" in error.suggestions
        # Filesystem patterns should NOT be suggested anymore
        assert "d/" not in error.suggestions
        assert "dir/" not in error.suggestions
        assert "p/" not in error.suggestions
        assert "path/" not in error.suggestions

    def test_invalid_prefix_error(self, setup_prefix_system):
        parser = setup_prefix_system["parser"]
        """Test that invalid prefixes raise appropriate error."""
        with pytest.raises(PatternParseError) as exc_info:
            parser.parse("invalid/pattern")

        assert "must start with a recognized prefix" in str(exc_info.value)

    def test_all_prefix_forms_work_equivalently(self, setup_prefix_system):
        parser = setup_prefix_system["parser"]
        """Test that short and long forms produce equivalent results."""
        # Workspace patterns
        short_w = parser.parse("w/aws")
        long_w = parser.parse("workspace/aws")
        assert short_w.prefix_type == long_w.prefix_type
        assert short_w.segments == long_w.segments

        # Context patterns
        short_c = parser.parse("c/dev")
        long_c = parser.parse("context/dev")
        assert short_c.prefix_type == long_c.prefix_type
        assert short_c.segments == long_c.segments

        # Component patterns
        short_cm = parser.parse("cm/nginx")
        long_cm = parser.parse("component/nginx")
        assert short_cm.prefix_type == long_cm.prefix_type
        assert short_cm.segments == long_cm.segments

        # Verify filesystem patterns are rejected (no longer supported)
        with pytest.raises(ValueError):
            parser.parse("d/path")
        with pytest.raises(ValueError):
            parser.parse("dir/path")
        with pytest.raises(ValueError):
            parser.parse("p/path")
        with pytest.raises(ValueError):
            parser.parse("path/path")
