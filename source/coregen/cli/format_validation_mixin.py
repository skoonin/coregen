"""Format validation mixin for CLI commands."""

from typing import Any, ClassVar

import typer

from coregen.cli.enums.enum_output_format import OutputFormat


class FormatValidationMixin:
    """Mixin to provide format validation for CLI commands.

    Commands using this mixin should define:
    - SUPPORTED_FORMATS: List of supported OutputFormat values
    - DEFAULT_FORMAT: Default OutputFormat value (optional, sourced from defaults.py)
    """

    SUPPORTED_FORMATS: ClassVar[list[Any]] = []
    DEFAULT_FORMAT: ClassVar[Any] = OutputFormat.TEXT

    def validate_output_format(self, output_format: Any) -> None:
        """Validate that the output format is supported by this command.

        Args:
            output_format: The requested output format

        Raises:
            typer.BadParameter: If the format is not supported by this command
        """
        # If no supported formats defined, allow all formats
        if not self.SUPPORTED_FORMATS:
            return

        # Check if the requested format is supported
        if output_format not in self.SUPPORTED_FORMATS:
            supported = ", ".join(f.value for f in self.SUPPORTED_FORMATS)
            raise typer.BadParameter(
                f"Format '{output_format.value}' not supported for this command. "
                f"Supported formats: {supported}"
            )
