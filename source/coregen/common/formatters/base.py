"""Base formatter class."""

from abc import ABC, abstractmethod
from typing import Any


class BaseFormatter(ABC):
    """Abstract base class for all formatters."""

    @abstractmethod
    def format(self, content: Any) -> Any:
        """Format content according to the specific formatter type."""
