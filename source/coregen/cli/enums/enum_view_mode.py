"""
Enum for view modes used in configuration commands.

This enum defines the available view modes for the config view command.
"""

from enum import Enum
from typing import TypeVar

T = TypeVar("T", bound="ViewMode")


class ViewMode(str, Enum):
    """
    Enum for view modes used in configuration commands.

    Available view modes:
    - RAW: Display raw configuration data
    - DISCOVERED: Display discovered configuration
    - RESOLVED: Display resolved configuration with variables
    - ENHANCED: Display enhanced configuration with additional context
    """

    RAW = "raw"
    DISCOVERED = "discovered"
    RESOLVED = "resolved"
    ENHANCED = "enhanced"

    @classmethod
    def from_string(cls: type[T], value: str) -> T | None:
        """
        Convert a string to a ViewMode enum value.

        Args:
            value (str): String to convert

        Returns:
            Optional[ViewMode]: Corresponding enum value, None if not found
        """
        try:
            return cls(value.lower())
        except ValueError:
            return None

    @classmethod
    def get_values(cls: type[T]) -> dict[str, T]:
        """
        Get a dictionary of all enum values.

        Returns:
            Dict[str, ViewMode]: Dictionary of all enum values
        """
        return {e.value: e for e in cls}

    def __str__(self) -> str:
        """Return string representation."""
        return self.value
