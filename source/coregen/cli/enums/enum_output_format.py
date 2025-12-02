"""Output format enumerations for all CLI commands.

This module contains both the base OutputFormat enum and command-specific
format enums that restrict choices per command.

IMPORTANT: When adding new command-specific output format enums:

1. Add the new enum class to this file
2. Export it in __init__.py
3. Update the Union type in GlobalOptions.__init__() to include the new enum:

  # In source/coregen/cli/global_options.py
  output_format: Union[
      OutputFormat,
      GetOutputFormat,
      DetectChangesOutputFormat,
      CheckPatternOutputFormat,
      GenerateOutputFormat,
      YourNewOutputFormat,  # <-- Add here
  ]

This ensures type safety across the application while maintaining command-specific
format restrictions in the UI.
"""

import enum


class OutputFormat(str, enum.Enum):
    """Enumeration of all supported output formats.

    Some formats (like matrix and table) only work when explicitly allowed
    in the message's allowed_outputs parameter.

    Attributes:
        TEXT: Plain text output (default)
        JSON: JSON format output
        YAML: YAML format output
        MATRIX: GitHub Actions matrix format
        TABLE: Tabulated format
    """

    TEXT = "text"  # Default format
    JSON = "json"
    YAML = "yaml"
    MATRIX = "matrix"
    TABLE = "table"


class GetOutputFormat(str, enum.Enum):
    """
    Output format options specifically for the get command.

    Only includes formats that the get command supports:
    YAML, JSON, TABLE, MATRIX
    """

    YAML = "yaml"
    JSON = "json"
    TABLE = "table"
    MATRIX = "matrix"


class DetectChangesOutputFormat(str, enum.Enum):
    """
    Output format options specifically for the detect-changes command.

    Only includes formats that detect-changes supports:
    TEXT (default), JSON, YAML, MATRIX, TABLE
    """

    TEXT = "text"
    JSON = "json"
    YAML = "yaml"
    MATRIX = "matrix"
    TABLE = "table"


class CheckPatternOutputFormat(str, enum.Enum):
    """
    Output format options specifically for the check-pattern command.

    Only includes formats that check-pattern supports:
    TABLE (forced, no user choice)
    """

    TABLE = "table"


class GenerateOutputFormat(str, enum.Enum):
    """
    Output format options specifically for the generate command.

    Only includes formats that generate supports:
    TEXT, TABLE
    """

    TEXT = "text"
    TABLE = "table"
