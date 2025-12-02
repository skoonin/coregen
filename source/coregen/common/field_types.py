"""
Field type definitions for field discovery and validation.

This module provides the type system used by the field discovery service
to classify and validate different types of fields found in Pydantic models.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FieldType(Enum):
    """Enumeration of supported field types for filtering and validation."""

    STRING = "string"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    DICT = "dict"
    LIST = "list"
    UNKNOWN = "unknown"


@dataclass
class FieldInfo:
    """Information about a discoverable field.

    This class contains metadata about fields discovered through Pydantic
    model introspection, including their types, sources, and validation info.
    """

    name: str
    field_type: FieldType
    source: str  # "model", "custom", "nested"
    description: str | None = None
    nested_path: str | None = None
    default_value: Any | None = None

    def __str__(self) -> str:
        """String representation for debugging."""
        source_desc = f"({self.source})"
        if self.nested_path:
            source_desc = f"({self.source}, nested: {self.nested_path})"
        return f"{self.name}: {self.field_type.value} {source_desc}"
