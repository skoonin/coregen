"""JSON formatter for machine-readable structured data."""

import json
import logging
from pathlib import Path
from typing import Any

from .base import BaseFormatter

logger = logging.getLogger(__name__)


class JSONFormatter(BaseFormatter):
    """JSON formatter for machine-readable structured data."""

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
