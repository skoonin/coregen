"""Grouping and deduplication of configuration validation errors.

Validation produces a flat list of free-text error strings, often with many
near-duplicates differing only by which context/component they originate from.
This module collapses that list into a deduplicated, human-readable set by
parsing context/component/error-type hints out of each message.

The logic is heuristic string parsing extracted from
``ConfigurationProvider.load_config`` so it can be unit tested in isolation.
"""

from typing import Any

# Header prepended to a non-empty grouped result, surfaced to the user.
VALIDATION_ERROR_HEADER = (
    "Configuration contains validation errors. "
    "See below for details and how to fix them."
)


def _classify_error_type(error: str) -> str:
    """Map an error message to a coarse error-type label used for grouping."""
    if "template" in error or "templated" in error:
        return "invalid_field_template"
    if "Priority must be" in error:
        return "invalid_priority"
    if "component_type" in error:
        return "invalid_component_type"
    if "Extra inputs are not permitted" in error:
        return "extra_fields"
    if "is not valid" in error:
        return "invalid_value"
    if "is required" in error:
        return "missing_required_field"
    if "Schema validation error" in error:
        return "schema_validation"
    return "other"


def group_validation_errors(errors: list[str]) -> list[str]:
    """Group and deduplicate validation error messages.

    Errors are keyed by parsed context name, component name, and error type.
    The first occurrence of each key is kept; repeats are collapsed and
    annotated with a count. A descriptive header is prepended when any error
    remains.

    Args:
        errors: Raw validation error messages.

    Returns:
        Deduplicated messages with a leading header, or an empty list when no
        errors were supplied.
    """
    if not errors:
        return []

    grouped_errors: dict[str, str | dict[str, Any]] = {}

    for error in errors:
        # Extract context and component info for grouping
        context_name = "unknown context"
        component_name = "unknown component"

        # Extract context name using simple string parsing
        if "in context " in error:
            parts = error.split("in context ", 1)
            if len(parts) > 1:
                context_name = parts[1].split(":", 1)[0].strip()

        # Extract component name if present
        if "component " in error:
            parts = error.split("component ", 1)
            if len(parts) > 1:
                component_name = parts[1].split(":", 1)[0].strip()

        error_type = _classify_error_type(error)

        # Composite key for precise grouping of similar errors
        key = f"{context_name}:{component_name}:{error_type}"

        # Store first occurrence of each unique error type
        if key not in grouped_errors:
            grouped_errors[key] = error
        # Count occurrences for summary
        elif isinstance(grouped_errors[key], dict):
            grouped_errors[key]["count"] += 1  # type: ignore[index, operator]
        else:
            # Convert to dictionary on second occurrence
            first_error = grouped_errors[key]
            grouped_errors[key] = {"error": first_error, "count": 2}

    unique_errors: list[str] = []
    for error_data in grouped_errors.values():
        if isinstance(error_data, dict):
            unique_errors.append(
                f"{error_data['error']} (repeated {error_data['count']} times)"
            )
        else:
            unique_errors.append(error_data)

    if unique_errors:
        unique_errors.insert(0, VALIDATION_ERROR_HEADER)

    return unique_errors
