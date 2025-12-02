"""JSON formatter for machine-readable structured data."""

import json
import logging
from pathlib import Path
from typing import Any

from .base import BaseFormatter

logger = logging.getLogger(__name__)


class JSONFormatter(BaseFormatter):
    """JSON formatter for machine-readable structured data."""

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

    def format(self, content: Any) -> str:
        """Format content as JSON with proper indentation."""
        try:
            if not isinstance(content, str):
                # Convert complex objects to serializable format
                serializable_content = self._convert_to_serializable(content)
                json_str = json.dumps(
                    serializable_content,
                    indent=2,
                    sort_keys=False,  # IMPORTANT: Preserve order from input
                    ensure_ascii=False,
                )
            else:
                try:
                    parsed = json.loads(content)
                    json_str = json.dumps(
                        parsed,
                        indent=2,
                        sort_keys=False,  # IMPORTANT: Preserve order from input
                        ensure_ascii=False,
                    )
                except json.JSONDecodeError:
                    json_str = content

            # Ensure consistent newline at the end
            if json_str and not json_str.endswith("\n"):
                json_str += "\n"

            return json_str
        except Exception as e:
            logger.error(f"Failed to format JSON: {e}")
            return str(content)
