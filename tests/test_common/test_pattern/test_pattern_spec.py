"""Tests for pattern specification module."""

from coregen.common.pattern.pattern_spec import (
    LogicalPatternSpec,
    LogicalPrefixType,
    PatternToken,
    PatternType,
)


def test_pattern_token():
    """Test PatternToken creation and string representation."""
    # Regular token
    token1 = PatternToken(value="aws", is_wildcard=False, is_recursive=False)
    assert token1.value == "aws"
    assert not token1.is_wildcard
    assert not token1.is_recursive
    assert str(token1) == "Token(aws)"

    # Wildcard token
    token2 = PatternToken(value="*", is_wildcard=True, is_recursive=False)
    assert token2.value == "*"
    assert token2.is_wildcard
    assert not token2.is_recursive
    assert str(token2) == "WildcardToken(*)"

    # Recursive token
    token3 = PatternToken(value="**", is_wildcard=True, is_recursive=True)
    assert token3.value == "**"
    assert token3.is_wildcard
    assert token3.is_recursive
    assert str(token3) == "RecursiveToken(**)"


def test_logical_pattern_spec():
    """Test LogicalPatternSpec creation and string representation."""
    tokens = [
        PatternToken(value="workspace", is_wildcard=False, is_recursive=False),
        PatternToken(value="aws", is_wildcard=False, is_recursive=False),
        PatternToken(value="*", is_wildcard=True, is_recursive=False),
    ]

    spec = LogicalPatternSpec(
        raw_pattern="workspace/aws/*",
        pattern_type=PatternType.LOGICAL,
        tokens=tokens,
        prefix_type=LogicalPrefixType.WORKSPACE,
        segments=["aws", "*"],
    )

    assert spec.raw_pattern == "workspace/aws/*"
    assert spec.pattern_type == PatternType.LOGICAL
    assert len(spec.tokens) == 3
    assert spec.prefix_type == LogicalPrefixType.WORKSPACE
    assert spec.segments == ["aws", "*"]

    # Test string representation
    str_repr = str(spec)
    assert "LogicalPatternSpec" in str_repr
    assert "workspace/aws/*" in str_repr
    assert "WORKSPACE" in str_repr


def test_pattern_type_enum():
    """Test PatternType enum values."""
    # Should only have LOGICAL type now
    assert PatternType.LOGICAL.value == 1

    # Verify FILESYSTEM is not present
    pattern_types = [
        attr for attr in dir(PatternType) if not attr.startswith("_") and attr.isupper()
    ]
    assert "FILESYSTEM" not in pattern_types


def test_pattern_spec_is_data_model():
    """Test that PatternSpec classes are data models without matching logic."""
    # PatternSpec classes are now pure data models
    # The matching logic is in the Matcher classes (WorkspaceMatcher, etc.)
    logical_spec = LogicalPatternSpec(
        raw_pattern="workspace/aws",
        pattern_type=PatternType.LOGICAL,
        tokens=[],
        prefix_type=LogicalPrefixType.WORKSPACE,
        segments=["aws"],
    )

    # Verify it's a data model with the expected fields
    assert hasattr(logical_spec, "raw_pattern")
    assert hasattr(logical_spec, "pattern_type")
    assert hasattr(logical_spec, "tokens")
    assert hasattr(logical_spec, "prefix_type")
    assert hasattr(logical_spec, "segments")

    # Verify it doesn't have a matches method (matching is done by Matcher classes)
    assert not hasattr(logical_spec, "matches")
