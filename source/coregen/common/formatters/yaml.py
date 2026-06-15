"""YAML formatter for human-readable structured data."""

import logging
from typing import Any

import yaml

from .base import BaseFormatter

logger = logging.getLogger(__name__)


class YAMLFormatter(BaseFormatter):
    """YAML formatter for human-readable structured data."""

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
