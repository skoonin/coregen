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
