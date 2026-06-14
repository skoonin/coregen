"""Comprehensive edge case tests for regex filter fix.

Tests verify that regex operators (~= and =~) work correctly with:
- Numeric values (integers, floats, zero, negative)
- Regex special characters and patterns
- Invalid regex patterns
- Boolean and None values
- Multi-filter combinations
- String field regression
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from coregen.common.filter_service import FilterService
from coregen.config_model.access import ConfigAccess


@pytest.fixture
def setup_regex_filter() -> Any:
    """Set up test fixture."""
    mock_config_access = MagicMock(spec=ConfigAccess)
    filter_service = FilterService(mock_config_access)
    return {
        "mock_config_access": mock_config_access,
        "filter_service": filter_service,
    }


class TestRegexFilterEdgeCases:
    """Comprehensive edge case tests for regex filter operators."""

    # ===== Numeric Edge Cases =====

    def test_regex_on_numeric_zero(self, setup_regex_filter):
        """Test regex matching on zero value."""

        filter_service = setup_regex_filter["filter_service"]

        # Parse should keep "0" as string for regex operators
        result = filter_service.parse_filter_expression("priority~=0")
        assert result["operator"] == "~="
        assert result["value"] == "0"  # Should be string, not int

        # Compare should convert actual value to string and match
        assert filter_service._compare_values(0, "~=", "0") is True
        assert filter_service._compare_values(10, "~=", "0") is True  # Contains 0
        assert filter_service._compare_values(5, "~=", "0") is False  # No 0

    def test_regex_on_negative_numbers(self, setup_regex_filter):
        """Test regex matching on negative numbers."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("priority~=-1")
        assert result["operator"] == "~="
        assert result["value"] == "-1"  # Should be string

        assert filter_service._compare_values(-1, "~=", "-1") is True
        assert filter_service._compare_values(-10, "~=", "-1") is True  # Contains -1
        assert filter_service._compare_values(1, "~=", "-1") is False

    def test_regex_on_float_patterns(self, setup_regex_filter):
        """Test regex matching on float patterns."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("value~=1.5")
        assert result["operator"] == "~="
        assert result["value"] == "1.5"  # Should be string

        assert filter_service._compare_values(1.5, "~=", "1.5") is True
        assert filter_service._compare_values(1.55, "~=", "1.5") is True  # Contains 1.5
        assert filter_service._compare_values(2.0, "~=", "1.5") is False

    def test_regex_on_large_numbers(self, setup_regex_filter):
        """Test regex matching on large numbers."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("priority~=999999")
        assert result["operator"] == "~="
        assert result["value"] == "999999"  # Should be string

        assert filter_service._compare_values(999999, "~=", "999999") is True
        assert (
            filter_service._compare_values(9999990, "~=", "999999") is True
        )  # Contains

    def test_regex_empty_string_pattern(self, setup_regex_filter):
        """Test regex with empty string pattern."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("priority~=^$")
        assert result["operator"] == "~="
        assert result["value"] == "^$"

        # Empty string pattern should not match non-empty strings
        assert filter_service._compare_values("", "~=", "^$") is True
        assert filter_service._compare_values("test", "~=", "^$") is False

    # ===== Regex Special Characters =====

    def test_regex_character_classes(self, setup_regex_filter):
        r"""Test regex with character classes like \d+."""
        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("priority~=\\d+")
        assert result["operator"] == "~="
        assert result["value"] == "\\d+"

        # Should match any numeric string
        assert filter_service._compare_values(123, "~=", "\\d+") is True
        assert filter_service._compare_values(0, "~=", "\\d+") is True
        assert filter_service._compare_values("test", "~=", "\\d+") is False

    def test_regex_quantifiers(self, setup_regex_filter):
        """Test regex with quantifiers like {2}."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("priority~=[0-9]{2}")
        assert result["operator"] == "~="
        assert result["value"] == "[0-9]{2}"

        # Should match two consecutive digits
        assert filter_service._compare_values(10, "~=", "[0-9]{2}") is True
        assert filter_service._compare_values(99, "~=", "[0-9]{2}") is True
        assert filter_service._compare_values(5, "~=", "[0-9]{2}") is False
        assert filter_service._compare_values(123, "~=", "[0-9]{2}") is True  # Contains

    def test_regex_alternation(self, setup_regex_filter):
        """Test regex with alternation (1|2|3)."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("priority~=(1|2|3)")
        assert result["operator"] == "~="
        assert result["value"] == "(1|2|3)"

        # Should match any of the alternates
        assert filter_service._compare_values(1, "~=", "(1|2|3)") is True
        assert filter_service._compare_values(2, "~=", "(1|2|3)") is True
        assert filter_service._compare_values(3, "~=", "(1|2|3)") is True
        assert filter_service._compare_values(4, "~=", "(1|2|3)") is False
        assert (
            filter_service._compare_values(12, "~=", "(1|2|3)") is True
        )  # Contains 1 or 2

    def test_regex_escaped_special_chars(self, setup_regex_filter):
        """Test regex with escaped special characters."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("name~=test\\.yaml")
        assert result["operator"] == "~="
        assert result["value"] == "test\\.yaml"

        # Should match literal dot
        assert filter_service._compare_values("test.yaml", "~=", "test\\.yaml") is True
        assert filter_service._compare_values("testyaml", "~=", "test\\.yaml") is False

    def test_regex_complex_patterns(self, setup_regex_filter):
        """Test complex regex patterns with anchors and wildcards."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("name~=^test-.*-prod$")
        assert result["operator"] == "~="
        assert result["value"] == "^test-.*-prod$"

        # Should match start, middle wildcard, and end
        assert (
            filter_service._compare_values("test-app-prod", "~=", "^test-.*-prod$")
            is True
        )
        assert (
            filter_service._compare_values("test-service-prod", "~=", "^test-.*-prod$")
            is True
        )
        assert (
            filter_service._compare_values("test-prod", "~=", "^test-.*-prod$") is False
        )  # Missing middle
        assert (
            filter_service._compare_values("test-app-dev", "~=", "^test-.*-prod$")
            is False
        )  # Wrong end

    # ===== Invalid Patterns =====

    def test_regex_invalid_unclosed_bracket(self, setup_regex_filter):
        """Test invalid regex with unclosed bracket."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("priority~=[")
        assert result["operator"] == "~="
        assert result["value"] == "["

        # Invalid pattern should raise ValueError with clear message
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            filter_service._compare_values(1, "~=", "[")

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            filter_service._compare_values("test", "~=", "[")

    def test_regex_invalid_unclosed_parenthesis(self, setup_regex_filter):
        """Test invalid regex with unclosed parenthesis."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("priority~=(")
        assert result["operator"] == "~="
        assert result["value"] == "("

        # Invalid pattern should raise ValueError with clear message
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            filter_service._compare_values(1, "~=", "(")

    def test_regex_invalid_quantifier(self, setup_regex_filter):
        """Test invalid regex with improper quantifier."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("priority~=*")
        assert result["operator"] == "~="
        assert result["value"] == "*"

        # Invalid pattern should raise ValueError with clear message
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            filter_service._compare_values(1, "~=", "*")

    # ===== Boolean and None Values =====

    def test_regex_on_boolean_true(self, setup_regex_filter):
        """Test regex matching on boolean true value."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("active~=true")
        assert result["operator"] == "~="
        assert result["value"] == "true"  # Should be string

        # Boolean True is converted to string "True" (capital T) for regex
        # So pattern "true" (lowercase) won't match
        assert filter_service._compare_values(True, "~=", "True") is True
        assert (
            filter_service._compare_values(True, "~=", "true") is False
        )  # Case-sensitive
        # But case-insensitive pattern works
        assert filter_service._compare_values(True, "~=", "(?i)true") is True

    def test_regex_on_boolean_false(self, setup_regex_filter):
        """Test regex matching on boolean false value."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("active~=false")
        assert result["operator"] == "~="
        assert result["value"] == "false"  # Should be string

        # Boolean False is converted to string "False" (capital F)
        assert filter_service._compare_values(False, "~=", "False") is True
        assert (
            filter_service._compare_values(False, "~=", "false") is False
        )  # Case-sensitive
        # But case-insensitive pattern works
        assert filter_service._compare_values(False, "~=", "(?i)false") is True

    def test_regex_on_none_value(self, setup_regex_filter):
        """Test regex matching on None value."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("priority~=none")
        assert result["operator"] == "~="
        # For regex operators, "none" should remain a string, not be converted to None
        assert result["value"] == "none"

        # For regex operators, None values are converted to empty string "" for matching
        # This means:
        # - The pattern "none" will NOT match None (because "" doesn't contain "none")
        # - The pattern "^$" WILL match None (because "" matches the empty string pattern)
        assert filter_service._compare_values(None, "~=", "none") is False
        assert filter_service._compare_values(None, "~=", "^$") is True

        # But non-None values can match "None" pattern if the string representation matches
        # (This is an edge case but shows the conversion works)
        assert filter_service._compare_values("None", "~=", "None") is True

    # ===== Cross-Operator Consistency =====

    def test_non_regex_operators_coerce_at_compare_time(self, setup_regex_filter):
        """Non-regex operators keep the value as a string at parse time;
        _compare_values coerces the right operand to the left operand's type.
        """

        filter_service = setup_regex_filter["filter_service"]

        # Parse keeps the value as a string (no parse-time coercion)
        result = filter_service.parse_filter_expression("priority=5")
        assert result["operator"] == "="
        assert result["value"] == "5"

        # Type conversion: right operand is converted to match left operand's type
        # So "5" (string) won't be converted when comparing with int 5
        assert (
            filter_service._compare_values(5, "=", "5") is True
        )  # Right converted to int
        assert (
            filter_service._compare_values(5, ">", "3") is True
        )  # Right converted to int
        assert (
            filter_service._compare_values(10, "<", "20") is True
        )  # Right converted to int

    def test_regex_vs_equality_different_behavior(self, setup_regex_filter):
        """Verify regex operators behave differently from equality."""

        filter_service = setup_regex_filter["filter_service"]

        # Equality: exact match with type conversion
        assert filter_service._compare_values(1, "=", "1") is True
        assert filter_service._compare_values(10, "=", "1") is False

        # Regex: substring match, no type conversion needed
        assert filter_service._compare_values(1, "~=", "1") is True
        assert filter_service._compare_values(10, "~=", "1") is True  # Contains "1"

    def test_both_regex_operators_work_identically(self, setup_regex_filter):
        """Verify ~= and =~ operators work the same way."""

        filter_service = setup_regex_filter["filter_service"]

        test_cases = [
            (1, "1", True),
            (10, "1", True),
            (5, "1", False),
            ("test", "test", True),
            ("test123", "test", True),
            ("abc", "test", False),
        ]

        for value, pattern, expected in test_cases:
            result1 = filter_service._compare_values(value, "~=", pattern)
            result2 = filter_service._compare_values(value, "=~", pattern)
            assert result1 == result2 == expected, f"Failed for {value} vs {pattern}"

    # ===== String Field Regression =====

    def test_string_regex_still_works(self, setup_regex_filter):
        """Ensure string regex matching still works after fix."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("component.name~=aws")
        assert result["operator"] == "~="
        assert result["value"] == "aws"

        # String matching should work as before
        assert filter_service._compare_values("aws-eks", "~=", "aws") is True
        assert filter_service._compare_values("eks-cluster", "~=", "aws") is False

    def test_string_complex_patterns(self, setup_regex_filter):
        """Test complex string patterns still work."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("name~=^[a-z]+$")
        assert result["operator"] == "~="
        assert result["value"] == "^[a-z]+$"

        # Should match lowercase letters only
        assert filter_service._compare_values("test", "~=", "^[a-z]+$") is True
        assert filter_service._compare_values("Test", "~=", "^[a-z]+$") is False
        assert filter_service._compare_values("test123", "~=", "^[a-z]+$") is False

    def test_string_substring_matching(self, setup_regex_filter):
        """Test substring matching on strings."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression("context.environment~=prod")
        assert result["operator"] == "~="
        assert result["value"] == "prod"

        # Should match substring
        assert filter_service._compare_values("production", "~=", "prod") is True
        assert filter_service._compare_values("prod-us", "~=", "prod") is True
        assert filter_service._compare_values("development", "~=", "prod") is False


class TestMultiFilterCombinations:
    """Test combinations of filters including regex operators."""

    def test_regex_and_equality_combination(self, setup_regex_filter):
        """Test using regex and equality in combination (simulated AND logic)."""

        filter_service = setup_regex_filter["filter_service"]

        # Parse both filters
        filter1 = filter_service.parse_filter_expression("priority~=1")
        filter2 = filter_service.parse_filter_expression("active=true")

        # Test component that should match both
        assert (
            filter_service._compare_values(1, filter1["operator"], filter1["value"])
            is True
        )
        assert (
            filter_service._compare_values(True, filter2["operator"], filter2["value"])
            is True
        )

    def test_regex_and_comparison_combination(self, setup_regex_filter):
        """Test using regex and numeric comparison together."""

        filter_service = setup_regex_filter["filter_service"]

        filter1 = filter_service.parse_filter_expression("priority>0")
        filter2 = filter_service.parse_filter_expression("name~=test")

        # Priority comparison should work
        assert (
            filter_service._compare_values(5, filter1["operator"], filter1["value"])
            is True
        )
        # Regex should work
        assert (
            filter_service._compare_values(
                "test-app", filter2["operator"], filter2["value"]
            )
            is True
        )


class TestPerformanceEdgeCases:
    """Test performance edge cases with complex patterns."""

    def test_complex_alternation_pattern(self, setup_regex_filter):
        """Test pattern with many alternations."""

        filter_service = setup_regex_filter["filter_service"]

        result = filter_service.parse_filter_expression(
            "priority~=(1|2|3|4|5|10|20|30|40|50)"
        )
        assert result["operator"] == "~="

        # Should match quickly
        assert (
            filter_service._compare_values(1, "~=", "(1|2|3|4|5|10|20|30|40|50)")
            is True
        )
        assert (
            filter_service._compare_values(99, "~=", "(1|2|3|4|5|10|20|30|40|50)")
            is False
        )

    def test_deeply_nested_groups(self, setup_regex_filter):
        """Test pattern with nested groups."""

        filter_service = setup_regex_filter["filter_service"]

        pattern = "^(test-(app|service)-(dev|prod|staging))$"
        result = filter_service.parse_filter_expression(f"name~={pattern}")
        assert result["operator"] == "~="

        # Should handle nested groups correctly
        assert filter_service._compare_values("test-app-dev", "~=", pattern) is True
        assert filter_service._compare_values("test-app-qa", "~=", pattern) is False
