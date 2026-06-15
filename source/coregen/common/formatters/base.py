"""Base formatter class."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseFormatter(ABC):
    """Abstract base class for all formatters."""

    def _convert_to_serializable(self, obj: Any) -> Any:
        """Convert Pydantic models and other complex objects to serializable dicts.

        Note: This formatter no longer sorts data. All sorting is handled by
        ComponentSorterService via format_type_service.py before formatting.
        """
        if hasattr(obj, "model_dump"):
            # Pydantic model - convert to dict and recursively process
            model_dict = obj.model_dump(exclude_defaults=False)
            return self._convert_to_serializable(model_dict)
        elif isinstance(obj, Path):
            # Convert Path objects to strings
            return str(obj)
        elif hasattr(obj, "__dict__"):
            # Other objects with __dict__ - convert to dict
            return {
                k: self._convert_to_serializable(v) for k, v in obj.__dict__.items()
            }
        elif isinstance(obj, dict):
            # Recursively convert dictionary values, preserving order from input
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            # Recursively convert list/tuple items
            return [self._convert_to_serializable(item) for item in obj]
        else:
            # Return as-is for basic types
            return obj

    @abstractmethod
    def format(self, content: Any) -> Any:
        """Format content according to the specific formatter type."""
