"""Unit tests for the validation error grouper.

Pins the grouping/deduplication heuristics extracted from
ConfigurationProvider.load_config so they have a callable test seam.
"""

import pytest

from coregen.config_model.validation_error_grouper import (
    VALIDATION_ERROR_HEADER,
    group_validation_errors,
)


class TestGroupValidationErrors:
    def test_empty_returns_empty(self):
        assert group_validation_errors([]) == []

    def test_single_error_gets_header(self):
        result = group_validation_errors(["Priority must be a positive integer"])

        assert result == [
            VALIDATION_ERROR_HEADER,
            "Priority must be a positive integer",
        ]

    def test_distinct_contexts_kept_separate(self):
        errors = [
            "Priority must be an integer in context alpha: bad",
            "Priority must be an integer in context beta: bad",
        ]

        result = group_validation_errors(errors)

        # Header plus one entry per distinct context key
        assert result[0] == VALIDATION_ERROR_HEADER
        assert result[1:] == errors

    def test_duplicate_errors_collapsed_with_count(self):
        errors = [
            "Priority must be an integer in context alpha: bad",
            "Priority must be an integer in context alpha: bad",
            "Priority must be an integer in context alpha: bad",
        ]

        result = group_validation_errors(errors)

        assert result == [
            VALIDATION_ERROR_HEADER,
            "Priority must be an integer in context alpha: bad (repeated 3 times)",
        ]

    def test_same_context_different_error_types_kept_separate(self):
        errors = [
            "Priority must be a number in context alpha: x",
            "Extra inputs are not permitted in context alpha: y",
        ]

        result = group_validation_errors(errors)

        assert len(result) == 3  # header + 2 distinct error types
        assert VALIDATION_ERROR_HEADER == result[0]

    def test_component_name_parsed_for_grouping(self):
        errors = [
            "is required in context alpha: for component web: field",
            "is required in context alpha: for component api: field",
        ]

        result = group_validation_errors(errors)

        # Different component names => not collapsed
        assert len(result) == 3

    def test_unparseable_strings_grouped_under_unknown(self):
        errors = [
            "totally opaque failure one",
            "totally opaque failure two",
        ]

        result = group_validation_errors(errors)

        # Both map to unknown context/component and error_type "other";
        # collapsed to a single counted entry.
        assert result == [
            VALIDATION_ERROR_HEADER,
            "totally opaque failure one (repeated 2 times)",
        ]

    @pytest.mark.parametrize(
        "message,marker",
        [
            ("a templated value here", "template"),
            ("Priority must be positive", "priority"),
            ("bad component_type given", "component_type"),
            ("Extra inputs are not permitted", "extra"),
            ("value is not valid", "not_valid"),
            ("field is required", "required"),
            ("Schema validation error occurred", "schema"),
        ],
    )
    def test_error_type_classification_separates_groups(self, message, marker):
        # Each distinct classification must not collapse with a generic "other"
        result = group_validation_errors([message, "totally opaque other"])
        assert len(result) == 3  # header + 2 distinct types
