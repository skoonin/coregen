"""YAML formatter for human-readable structured data."""

import logging
from typing import Any

import yaml

from .base import BaseFormatter

logger = logging.getLogger(__name__)


class YAMLFormatter(BaseFormatter):
    """YAML formatter for human-readable structured data."""

    def _convert_to_serializable(self, obj: Any) -> Any:
        """Convert Pydantic models and other complex objects to serializable dicts.

        Note: This formatter no longer sorts data. All sorting is handled by
        ComponentSorterService via format_type_service.py before formatting.
        """
        from pathlib import Path

        if hasattr(obj, "model_dump"):
            # Pydantic model - convert to dict
            model_dict = obj.model_dump(exclude_defaults=False)
            return self._convert_to_serializable(model_dict)
        elif isinstance(obj, Path):
            # Convert Path objects to strings
            return str(obj)
        elif hasattr(obj, "__dict__"):
            # Other objects with __dict__ - convert to dict
            obj_dict = {k: v for k, v in obj.__dict__.items()}
            return {k: self._convert_to_serializable(v) for k, v in obj_dict.items()}
        elif isinstance(obj, dict):
            # Recursively process dictionaries, preserving order from input
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            # Recursively process lists/tuples
            return [self._convert_to_serializable(item) for item in obj]
        else:
            # Return primitive types as-is
            return obj

    def format(self, content: Any) -> str:
        """Format content as YAML with proper formatting."""

        # Custom dumper that disables anchors/aliases for cleaner output
        class NoAliasesDumper(yaml.SafeDumper):
            def ignore_aliases(self, data: Any) -> bool:
                return True

        # Convert to serializable format
        serializable_content = self._convert_to_serializable(content)

        # Format as YAML with consistent settings
        yaml_str = yaml.dump(
            serializable_content,
            Dumper=NoAliasesDumper,
            default_flow_style=False,
            allow_unicode=True,
            width=4096,
            sort_keys=False,  # IMPORTANT: Preserve order from input
        )

        # Clean up empty lines and ensure consistent formatting
        lines = yaml_str.split("\n")
        cleaned_lines = []
        prev_was_empty = False

        for line in lines:
            is_empty = not line.strip()
            # Allow single empty lines but not multiple consecutive ones
            if not is_empty or not prev_was_empty:
                cleaned_lines.append(line)
            prev_was_empty = is_empty

        # Join lines and ensure single trailing newline
        result = "\n".join(cleaned_lines)
        if result and not result.endswith("\n"):
            result += "\n"

        return result
