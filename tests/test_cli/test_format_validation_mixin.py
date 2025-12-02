"""Tests for FormatValidationMixin functionality."""

import pytest
import typer

from coregen.cli.enums.enum_output_format import (
    CheckPatternOutputFormat,
    DetectChangesOutputFormat,
    GetOutputFormat,
    OutputFormat,
)
from coregen.cli.format_validation_mixin import FormatValidationMixin


class TestCommand(FormatValidationMixin):
    """Test command class using FormatValidationMixin."""

    SUPPORTED_FORMATS = [OutputFormat.JSON, OutputFormat.YAML]
    DEFAULT_FORMAT = OutputFormat.JSON


class TestFormatValidationMixin:
    """Test the FormatValidationMixin functionality."""

    def test_validate_supported_format(self):
        """Test that supported formats pass validation."""
        cmd = TestCommand()
        # Should not raise
        cmd.validate_output_format(OutputFormat.JSON)
        cmd.validate_output_format(OutputFormat.YAML)

    def test_validate_unsupported_format(self):
        """Test that unsupported formats raise BadParameter."""
        cmd = TestCommand()
        with pytest.raises(typer.BadParameter) as excinfo:
            cmd.validate_output_format(OutputFormat.TABLE)

        assert "Format 'table' not supported" in str(excinfo.value)
        assert "Supported formats: json, yaml" in str(excinfo.value)

    def test_no_format_restrictions(self):
        """Test command with no format restrictions."""

        class UnrestrictedCommand(FormatValidationMixin):
            SUPPORTED_FORMATS = []  # No restrictions
            DEFAULT_FORMAT = OutputFormat.TEXT

        cmd = UnrestrictedCommand()
        # Should not raise for any format
        cmd.validate_output_format(OutputFormat.JSON)
        cmd.validate_output_format(OutputFormat.YAML)
        cmd.validate_output_format(OutputFormat.TABLE)
        cmd.validate_output_format(OutputFormat.TEXT)
        cmd.validate_output_format(OutputFormat.MATRIX)


class TestCommandSpecificEnums:
    """Test command-specific output format enums."""

    def test_get_output_format_enum(self):
        """Test GetOutputFormat enum values."""
        assert GetOutputFormat.YAML.value == "yaml"
        assert GetOutputFormat.JSON.value == "json"
        assert GetOutputFormat.TABLE.value == "table"
        assert GetOutputFormat.MATRIX.value == "matrix"
        # Should have exactly 4 formats
        assert len(GetOutputFormat) == 4

    def test_detect_changes_output_format_enum(self):
        """Test DetectChangesOutputFormat enum values."""
        assert DetectChangesOutputFormat.TEXT.value == "text"
        assert DetectChangesOutputFormat.JSON.value == "json"
        assert DetectChangesOutputFormat.YAML.value == "yaml"
        assert DetectChangesOutputFormat.MATRIX.value == "matrix"
        assert DetectChangesOutputFormat.TABLE.value == "table"
        # Should have exactly 5 formats
        assert len(DetectChangesOutputFormat) == 5

    def test_config_output_format_enum(self):
        """Test that config commands should use OutputFormat directly."""
        # Config commands now use OutputFormat directly for YAML and JSON
        assert OutputFormat.YAML.value == "yaml"
        assert OutputFormat.JSON.value == "json"

    def test_check_pattern_output_format_enum(self):
        """Test CheckPatternOutputFormat enum values."""
        assert CheckPatternOutputFormat.TABLE.value == "table"
        # Should have exactly 1 format
        assert len(CheckPatternOutputFormat) == 1


class TestCommandFormatRestrictions:
    """Test that commands have correct format restrictions."""

    def test_get_command_formats(self):
        """Test that get command supports correct formats."""

        class GetCommand(FormatValidationMixin):
            SUPPORTED_FORMATS = [
                GetOutputFormat.YAML,
                GetOutputFormat.JSON,
                GetOutputFormat.TABLE,
                GetOutputFormat.MATRIX,
            ]
            DEFAULT_FORMAT = GetOutputFormat.YAML

        cmd = GetCommand()
        # All formats should pass
        cmd.validate_output_format(GetOutputFormat.YAML)
        cmd.validate_output_format(GetOutputFormat.JSON)
        cmd.validate_output_format(GetOutputFormat.TABLE)
        cmd.validate_output_format(GetOutputFormat.MATRIX)

    def test_detect_changes_command_formats(self):
        """Test that detect-changes command supports correct formats."""

        class DetectChangesCommand(FormatValidationMixin):
            SUPPORTED_FORMATS = [
                DetectChangesOutputFormat.JSON,
                DetectChangesOutputFormat.YAML,
                DetectChangesOutputFormat.MATRIX,
            ]
            DEFAULT_FORMAT = DetectChangesOutputFormat.JSON

        cmd = DetectChangesCommand()
        # Supported formats should pass
        cmd.validate_output_format(DetectChangesOutputFormat.JSON)
        cmd.validate_output_format(DetectChangesOutputFormat.YAML)
        cmd.validate_output_format(DetectChangesOutputFormat.MATRIX)

    def test_config_view_command_formats(self):
        """Test that config view command supports correct formats."""

        class ConfigViewCommand(FormatValidationMixin):
            SUPPORTED_FORMATS = [
                OutputFormat.YAML,
                OutputFormat.JSON,
            ]
            DEFAULT_FORMAT = OutputFormat.YAML

        cmd = ConfigViewCommand()
        # Supported formats should pass
        cmd.validate_output_format(OutputFormat.YAML)
        cmd.validate_output_format(OutputFormat.JSON)

    def test_check_pattern_command_formats(self):
        """Test that check-pattern command supports only TABLE format."""

        class CheckPatternCommand(FormatValidationMixin):
            SUPPORTED_FORMATS = [CheckPatternOutputFormat.TABLE]
            DEFAULT_FORMAT = CheckPatternOutputFormat.TABLE

        cmd = CheckPatternCommand()
        # Only TABLE format should pass
        cmd.validate_output_format(CheckPatternOutputFormat.TABLE)


class TestFormatValidationEdgeCases:
    """Test edge cases for format validation."""

    def test_empty_supported_formats_with_validation(self):
        """Test that empty SUPPORTED_FORMATS means no restrictions."""

        class NoRestrictionsCommand(FormatValidationMixin):
            SUPPORTED_FORMATS = []
            DEFAULT_FORMAT = OutputFormat.TEXT

        cmd = NoRestrictionsCommand()
        # Any format should be allowed
        for format_type in [
            OutputFormat.TEXT,
            OutputFormat.JSON,
            OutputFormat.YAML,
            OutputFormat.TABLE,
            OutputFormat.MATRIX,
        ]:
            cmd.validate_output_format(format_type)  # Should not raise

    def test_single_format_restriction(self):
        """Test command with single format restriction."""

        class SingleFormatCommand(FormatValidationMixin):
            SUPPORTED_FORMATS = [OutputFormat.JSON]
            DEFAULT_FORMAT = OutputFormat.JSON

        cmd = SingleFormatCommand()
        # JSON should pass
        cmd.validate_output_format(OutputFormat.JSON)

        # Others should fail
        with pytest.raises(typer.BadParameter) as excinfo:
            cmd.validate_output_format(OutputFormat.YAML)
        assert "Format 'yaml' not supported" in str(excinfo.value)
        assert "Supported formats: json" in str(excinfo.value)

    def test_cross_enum_validation(self):
        """Test validation with different enum types."""

        class MixedEnumCommand(FormatValidationMixin):
            # Using base OutputFormat enum for validation
            SUPPORTED_FORMATS = [OutputFormat.JSON, OutputFormat.YAML]
            DEFAULT_FORMAT = OutputFormat.JSON

        cmd = MixedEnumCommand()

        # Should validate against the base enum
        cmd.validate_output_format(OutputFormat.JSON)
        cmd.validate_output_format(OutputFormat.YAML)

        # Should fail for unsupported
        with pytest.raises(typer.BadParameter):
            cmd.validate_output_format(OutputFormat.TABLE)
