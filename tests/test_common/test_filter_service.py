"""Unit tests for the FilterService class."""

from typing import Any

import pytest

from coregen.common.filter_service import FilterService


@pytest.fixture
def filter_service(mock_config_access) -> Any:
    """Create FilterService instance with mocked dependencies."""
    return FilterService(mock_config_access)


class TestFilterService:
    """Test the FilterService class."""

    def test_parse_filter_expression_basic(self, filter_service):
        """Test parse_filter_expression with basic expressions."""
        # Test equals expression
        result = filter_service.parse_filter_expression("name=test")
        assert result["property"] == "name"
        assert result["operator"] == "="
        assert result["value"] == "test"
        assert result["entity_type"] is None

        # Test not equals expression
        result = filter_service.parse_filter_expression("active!=false")
        assert result["property"] == "active"
        assert result["operator"] == "!="
        assert result["value"] == "false"

        # Test pattern matching expressions (both operators)
        result = filter_service.parse_filter_expression("name~=test")
        assert result["property"] == "name"
        assert result["operator"] == "~="
        assert result["value"] == "test"

        # Test bash-style =~ operator
        result = filter_service.parse_filter_expression("name=~test")
        assert result["property"] == "name"
        assert result["operator"] == "=~"
        assert result["value"] == "test"

        # Comparison operators keep the value as a string; _compare_values
        # coerces it against the field's actual numeric type at apply time.
        result = filter_service.parse_filter_expression("priority>5")
        assert result["property"] == "priority"
        assert result["operator"] == ">"
        assert result["value"] == "5"

        # Test less than expression
        result = filter_service.parse_filter_expression("priority<10")
        assert result["property"] == "priority"
        assert result["operator"] == "<"
        assert result["value"] == "10"

        # Test greater than or equal expression
        result = filter_service.parse_filter_expression("priority>=5")
        assert result["property"] == "priority"
        assert result["operator"] == ">="
        assert result["value"] == "5"

        # Test less than or equal expression
        result = filter_service.parse_filter_expression("priority<=10")
        assert result["property"] == "priority"
        assert result["operator"] == "<="
        assert result["value"] == "10"

    def test_parse_filter_expression_keeps_value_as_string(self, filter_service):
        """Values are not coerced at parse time (except none/null -> None).
        _compare_values handles type coercion against the field's real type.
        """
        # Boolean-looking values stay strings
        result = filter_service.parse_filter_expression("active=true")
        assert result["value"] == "true"

        result = filter_service.parse_filter_expression("active=false")
        assert result["value"] == "false"

        # Numeric values stay strings
        result = filter_service.parse_filter_expression("count=42")
        assert result["value"] == "42"

        result = filter_service.parse_filter_expression("ratio=3.14")
        assert result["value"] == "3.14"

        # Flag without value still defaults to boolean True (existence check)
        result = filter_service.parse_filter_expression("active")
        assert result["property"] == "active"
        assert result["operator"] == "="
        assert result["value"] is True

    def test_parse_filter_expression_priority_none(self, filter_service):
        """Test priority=none value conversion."""
        # Test priority=none (lowercase)
        result = filter_service.parse_filter_expression("priority=none")
        assert result["property"] == "priority"
        assert result["operator"] == "="
        assert result["value"] is None

        # Test priority=None (mixed case)
        result = filter_service.parse_filter_expression("priority=None")
        assert result["property"] == "priority"
        assert result["operator"] == "="
        assert result["value"] is None

        # Test priority=NONE (uppercase)
        result = filter_service.parse_filter_expression("priority=NONE")
        assert result["property"] == "priority"
        assert result["operator"] == "="
        assert result["value"] is None

        # Test that priority with numeric values works (kept as string)
        result = filter_service.parse_filter_expression("priority=100")
        assert result["property"] == "priority"
        assert result["operator"] == "="
        assert result["value"] == "100"

        # Test config.priority=none
        result = filter_service.parse_filter_expression("config.priority=none")
        assert result["property"] == "config.priority"
        assert result["operator"] == "="
        assert result["value"] is None

        # Test that "none" conversion now applies to ANY property (not just priority)
        result = filter_service.parse_filter_expression("name=none")
        assert result["property"] == "name"
        assert result["operator"] == "="
        assert result["value"] is None  # Converted to None for any field

    def test_parse_filter_expression_empty_property_raises(self, filter_service):
        """A filter with no property before the operator is malformed."""
        import pytest

        with pytest.raises(ValueError):
            filter_service.parse_filter_expression("=value")

    def test_parse_filter_expression_invalid_regex_raises(self, filter_service):
        """An invalid regex pattern is reported at parse time, not silently
        deferred to apply time.
        """
        import pytest

        with pytest.raises(ValueError):
            filter_service.parse_filter_expression("name~=[")

    def test_parse_filter_expression_entity_types(self, filter_service):
        """Test entity type parsing in filter expressions."""
        # Test workspace entity type
        result = filter_service.parse_filter_expression("workspace.name=test")
        assert result["property"] == "name"
        assert result["entity_type"] == "workspace"
        assert result["operator"] == "="
        assert result["value"] == "test"

        # Test context entity type
        result = filter_service.parse_filter_expression("context.environment=prod")
        assert result["property"] == "environment"
        assert result["entity_type"] == "context"
        assert result["operator"] == "="
        assert result["value"] == "prod"

        # Test component entity type
        result = filter_service.parse_filter_expression("component.name=nginx")
        assert result["property"] == "name"
        assert result["entity_type"] == "component"
        assert result["operator"] == "="
        assert result["value"] == "nginx"

        # Test nested properties
        result = filter_service.parse_filter_expression("component.config.active=true")
        assert result["property"] == "config.active"
        assert result["entity_type"] == "component"
        assert result["operator"] == "="
        assert result["value"] == "true"

        # Test without entity type prefix
        result = filter_service.parse_filter_expression("active=false")
        assert result["property"] == "active"
        assert result["entity_type"] is None
        assert result["operator"] == "="
        assert result["value"] == "false"

    def test_compare_values_basic(self, filter_service):
        """Test _compare_values method with basic operators."""
        # Test equals operator
        assert filter_service._compare_values(5, "=", 5) is True
        assert filter_service._compare_values("test", "=", "test") is True
        assert filter_service._compare_values(True, "=", True) is True
        assert filter_service._compare_values(5, "=", 10) is False

        # Test not equals operator
        assert filter_service._compare_values(5, "!=", 10) is True
        assert filter_service._compare_values(5, "!=", 5) is False

        # Test greater than operator
        assert filter_service._compare_values(10, ">", 5) is True
        assert filter_service._compare_values(5, ">", 10) is False

        # Test less than operator
        assert filter_service._compare_values(5, "<", 10) is True
        assert filter_service._compare_values(10, "<", 5) is False

        # Test greater than or equal operator
        assert filter_service._compare_values(10, ">=", 5) is True
        assert filter_service._compare_values(10, ">=", 10) is True
        assert filter_service._compare_values(5, ">=", 10) is False

        # Test less than or equal operator
        assert filter_service._compare_values(5, "<=", 10) is True
        assert filter_service._compare_values(10, "<=", 10) is True
        assert filter_service._compare_values(15, "<=", 10) is False

    def test_compare_values_pattern_matching(self, filter_service):
        """Test _compare_values with regex pattern matching operators (~= and =~)."""
        # Test both operators work the same way
        for operator in ["~=", "=~"]:
            # Substring matching (default behavior using re.search)
            assert filter_service._compare_values("test123", operator, "test") is True
            assert filter_service._compare_values("test", operator, "other") is False

            # Anchored matching
            assert filter_service._compare_values("test123", operator, "^test") is True
            assert filter_service._compare_values("test123", operator, "123$") is True
            assert filter_service._compare_values("test123", operator, "^123") is False

            # Complex patterns
            assert (
                filter_service._compare_values(
                    "prometheus-server", operator, "prom.*server"
                )
                is True
            )
            assert (
                filter_service._compare_values("nginx-123", operator, "nginx-[0-9]+")
                is True
            )

            # Case sensitivity (must be case sensitive)
            assert filter_service._compare_values("Test123", operator, "test") is False

    def test_compare_values_type_conversion(self, filter_service):
        """Test _compare_values with type conversion."""
        # Test type conversion
        assert filter_service._compare_values(5, "=", "5") is True
        assert filter_service._compare_values(True, "=", "true") is True

    def test_compare_values_none_handling(self, filter_service):
        """Test _compare_values with None values."""
        assert filter_service._compare_values(None, "=", None) is True
        assert filter_service._compare_values(None, "!=", "value") is True
        assert filter_service._compare_values(None, "=", "value") is False

    def test_compare_values_none_with_regex(self, filter_service):
        """Test _compare_values with None values and regex operators.

        None values should be converted to empty string for regex matching.
        """
        # None should match patterns that match empty string
        assert filter_service._compare_values(None, "~=", "^$") is True  # Exactly empty
        assert (
            filter_service._compare_values(None, "~=", "^[^0-9]*$") is True
        )  # Zero or more non-digits
        assert (
            filter_service._compare_values(None, "~=", ".*") is True
        )  # Any (including empty)

        # None should NOT match patterns requiring content
        assert (
            filter_service._compare_values(None, "~=", "^[^0-9]+$") is False
        )  # One or more non-digits
        assert (
            filter_service._compare_values(None, "~=", ".+") is False
        )  # One or more chars
        assert (
            filter_service._compare_values(None, "~=", "^none$") is False
        )  # Literal "none"

        # Numeric values should still work correctly with regex
        assert filter_service._compare_values(3, "~=", "^[0-9]+$") is True
        assert filter_service._compare_values(3, "~=", "^[^0-9]*$") is False

    def test_parse_filter_expression_none_null_conversion(self, filter_service):
        """Test that 'none' and 'null' keywords are converted to Python None for any field."""
        # Test with 'none' keyword
        filter_priority_none = filter_service.parse_filter_expression(
            "component.config.priority=none"
        )
        assert filter_priority_none["value"] is None

        filter_description_none = filter_service.parse_filter_expression(
            "component.description=none"
        )
        assert filter_description_none["value"] is None

        # Test with 'null' keyword
        filter_priority_null = filter_service.parse_filter_expression(
            "component.config.priority=null"
        )
        assert filter_priority_null["value"] is None

        filter_description_null = filter_service.parse_filter_expression(
            "component.description=null"
        )
        assert filter_description_null["value"] is None

        # Test with different entity types
        filter_context_none = filter_service.parse_filter_expression(
            "context.custom_field=none"
        )
        assert filter_context_none["value"] is None

        filter_workspace_null = filter_service.parse_filter_expression(
            "workspace.custom_field=null"
        )
        assert filter_workspace_null["value"] is None

    def test_apply_filters_empty(self, filter_service):
        """Test apply_filters with empty filter list."""
        elements = {
            "workspaces": {"ws1": {"name": "ws1"}},
            "contexts": {"ctx1": {"name": "ctx1"}},
            "components": {"comp1": {"name": "comp1"}},
        }

        result = filter_service.apply_filters_complete(elements, [])

        # Should return original elements unchanged
        assert len(result["workspaces"]) == 1
        assert len(result["contexts"]) == 1
        assert len(result["components"]) == 1

    def test_apply_filters_with_filters(self, filter_service, mock_config_access):
        """Test apply_filters with actual filters."""
        elements = {
            "workspaces": {
                "ws1": {"name": "ws1", "active": True},
                "ws2": {"name": "ws2", "active": False},
            },
            "contexts": {},
            "components": {},
        }

        # Mock the workspace filtering
        mock_config_access.find_workspaces.return_value = []

        filters = [{"property": "active", "operator": "=", "value": True}]
        result = filter_service.apply_filters_complete(elements, filters)

        # The actual filtering logic will depend on the elements structure
        # This test mainly ensures the method can be called without errors
        assert "workspaces" in result
        assert "contexts" in result
        assert "components" in result
