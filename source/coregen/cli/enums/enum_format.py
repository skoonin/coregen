"""Format enum for output formatting options."""

# enums/format.py

import enum


class Format(str, enum.Enum):
    """
    Common enumeration for output format structure.

    Controls the structure of the output data for commands that support
    structured output (get, config view, detect-changes):
    - FLAT: Separate arrays for workspaces, contexts, and components
    - NESTED: Nested structure where relationships are preserved

    Attributes:
        FLAT: Flat structure with separate arrays for each entity type
        NESTED: Nested structure maintaining hierarchical relationships
    """

    FLAT = "flat"
    NESTED = "nested"

    @classmethod
    def resolve_alias(cls, value: str) -> "Format":
        """Resolve format value to enum.

        Args:
            value: Format value

        Returns:
            Resolved Format enum value
        """
        # Handle case-insensitive matching
        value_lower = value.lower()
        for format_option in cls:
            if format_option.value == value_lower:
                return format_option
        # If no match, let enum handle the error
        return cls(value)
