"""Main Formatter class with output format subclasses."""

import logging
from typing import Any

from rich.text import Text

from .formatters.json import JSONFormatter
from .formatters.matrix import MatrixFormatter
from .formatters.table import TableFormatter
from .formatters.text import TextFormatter
from .formatters.yaml import YAMLFormatter

logger = logging.getLogger(__name__)


class Formatter:
    """Main Formatter class with subclasses for each output format."""

    # Expose formatter classes as nested classes
    Text = TextFormatter
    JSON = JSONFormatter
    YAML = YAMLFormatter
    Matrix = MatrixFormatter
    Table = TableFormatter

    # Static method for backward compatibility and main entry point
    @staticmethod
    def format_output(content: Any, output_format: str = "text") -> Any:
        """Format content according to specified format.

        Args:
            content: Content to format
            output_format: Format to use (text, json, yaml, matrix, table)

        Returns:
            Formatted output according to the specified format
        """
        format_classes = {
            "text": Formatter.Text,
            "json": Formatter.JSON,
            "yaml": Formatter.YAML,
            "matrix": Formatter.Matrix,
            "table": Formatter.Table,
        }

        logger.debug(f"Formatting output as: {output_format}")

        formatter_class = format_classes.get(output_format.lower())
        if formatter_class is None:
            logger.warning(
                f"Unknown output format '{output_format}', defaulting to text"
            )
            return Text(str(content))

        formatter = formatter_class()
        try:
            return formatter.format(content)
        except Exception as e:
            error_message = f"Error formatting as {output_format}: {str(e)}\nOriginal content: {str(content)[:100]}..."
            logger.error(f"Error in format_output({output_format}): {e}")
            return Text(error_message, style="red")
