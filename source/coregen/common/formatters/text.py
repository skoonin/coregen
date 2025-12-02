"""Text formatter for plain text output with optional styling."""

from typing import Any

from rich.text import Text

from .base import BaseFormatter


class TextFormatter(BaseFormatter):
    """Text formatter for plain text output with optional styling."""

    def format(self, content: Any) -> Text:
        """Format content as Rich Text with optional styling."""
        if isinstance(content, str) and content.lower().startswith(
            ("error:", "warning:")
        ):
            style = "red" if content.lower().startswith("error:") else "yellow"
            return Text(str(content), style=style)
        return Text(str(content))
