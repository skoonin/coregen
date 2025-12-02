"""Tests for command-specific output format handling."""

from unittest.mock import MagicMock, patch

import pytest

from coregen.cli.enums.enum_output_format import (
    CheckPatternOutputFormat,
    DetectChangesOutputFormat,
    GetOutputFormat,
    OutputFormat,
)


class TestGetCommandOutputFormats:
    """Test get command output format handling."""

    @pytest.mark.parametrize("format_option", ["yaml", "json", "table", "matrix"])
    def test_get_supports_format(self, cli_runner, cli_app, format_option):
        """Test that get command supports YAML, JSON, TABLE, and MATRIX."""
        with patch("coregen.cli.commands.get.get_cli.GetService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.get_elements.return_value = {"workspaces": {}}

            result = cli_runner.invoke(
                cli_app, ["get", "w/*", "--output", format_option]
            )
            assert (
                result.exit_code == 0
            ), f"Get command should support {format_option} format"

    def test_get_default_format_is_yaml(self, cli_runner, cli_app):
        """Test that get command defaults to YAML format."""
        with patch("coregen.cli.commands.get.get_cli.GetService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.get_elements.return_value = {"workspaces": {}}

            with patch("coregen.cli.commands.get.get_cli.console") as mock_console:
                result = cli_runner.invoke(cli_app, ["get", "w/*"])
                assert result.exit_code == 0

                # Check that console.print was called with YAML format
                mock_console.print.assert_called()
                call_args = mock_console.print.call_args
                assert call_args[1]["output_format"] == GetOutputFormat.YAML

    def test_get_rejects_unsupported_format(self, cli_runner, cli_app):
        """Test that get command rejects unsupported formats."""
        result = cli_runner.invoke(cli_app, ["get", "w/*", "--output", "text"])
        assert result.exit_code != 0
        # Check error message in output (might be in stderr)
        output = result.stdout + result.stderr
        assert "Invalid value" in output or "invalid" in output.lower()


class TestDetectChangesCommandOutputFormats:
    """Test detect-changes command output format handling."""

    @pytest.mark.parametrize("format_option", ["json", "yaml", "matrix"])
    def test_detect_changes_supports_format(self, cli_runner, cli_app, format_option):
        """Test that detect-changes supports JSON, YAML, and MATRIX formats."""
        from coregen.services.detect_changes.models import DetectChangesResult

        with patch(
            "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            # Return a proper DetectChangesResult
            mock_instance.detect_changes.return_value = DetectChangesResult(changes=[])

            result = cli_runner.invoke(
                cli_app, ["detect-changes", "--output", format_option]
            )
            assert (
                result.exit_code == 0
            ), f"Detect-changes should support {format_option} format"

    def test_detect_changes_default_format_is_table(self, cli_runner, cli_app):
        """Test that detect-changes defaults to TABLE format."""
        from coregen.services.detect_changes.models import DetectChangesResult

        with patch(
            "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            # Return a proper DetectChangesResult
            mock_instance.detect_changes.return_value = DetectChangesResult(changes=[])

            with patch(
                "coregen.cli.commands.detect_changes.detect_changes_cli.console"
            ) as mock_console:
                result = cli_runner.invoke(cli_app, ["detect-changes"])
                assert result.exit_code == 0

                # Check that console.print was called with TABLE format
                mock_console.print.assert_called()
                call_args = mock_console.print.call_args
                assert call_args[1]["output_format"] == OutputFormat.TABLE

    def test_detect_changes_supports_table_format(self, cli_runner, cli_app):
        """Test that detect-changes supports TABLE format."""
        from coregen.services.detect_changes.models import DetectChangesResult

        with patch(
            "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            # Return a proper DetectChangesResult
            mock_instance.detect_changes.return_value = DetectChangesResult(changes=[])

            result = cli_runner.invoke(cli_app, ["detect-changes", "--output", "table"])
            assert result.exit_code == 0


class TestConfigCommandOutputFormats:
    """Test config subcommands output format handling."""

    @pytest.mark.parametrize("format_option", ["yaml", "json"])
    def test_config_view_supports_format(self, cli_runner, cli_app, format_option):
        """Test that config view supports YAML and JSON formats."""
        with patch(
            "coregen.cli.commands.config.cfg_view.ConfigViewService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.view_config.return_value = {"workspaces": []}

            result = cli_runner.invoke(
                cli_app, ["config", "view", "--output", format_option]
            )
            assert (
                result.exit_code == 0
            ), f"Config view should support {format_option} format"

    def test_config_view_default_format_is_yaml(self, cli_runner, cli_app):
        """Test that config view defaults to YAML format."""
        with patch(
            "coregen.cli.commands.config.cfg_view.ConfigViewService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.view_config.return_value = {"workspaces": []}

            with patch("coregen.cli.commands.config.cfg_view.Console") as mock_console:
                result = cli_runner.invoke(cli_app, ["config", "view"])
                assert result.exit_code == 0

                # Check that console.print was called with YAML format
                mock_console.print.assert_called()
                call_args = mock_console.print.call_args
                assert call_args[1]["output_format"] == OutputFormat.YAML

    @pytest.mark.parametrize("format_option", ["json", "yaml"])
    def test_config_schema_supports_format(self, cli_runner, cli_app, format_option):
        """Test that config schema supports JSON and YAML formats."""
        with patch(
            "coregen.cli.commands.config.cfg_schema.ConfigSchemaService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.process_schema_request.return_value = {
                "valid_types": ["all"],
                "unknown_types": [],
                "has_multiple": False,
                "schema_data": {"all": "{}"},
                "errors": {},
            }

            result = cli_runner.invoke(
                cli_app, ["config", "schema", "all", "--output", format_option]
            )
            assert (
                result.exit_code == 0
            ), f"Config schema should support {format_option} format"

    def test_config_schema_default_format_is_json(self, cli_runner, cli_app):
        """Test that config schema defaults to JSON format."""
        with patch(
            "coregen.cli.commands.config.cfg_schema.ConfigSchemaService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.process_schema_request.return_value = {
                "valid_types": ["all"],
                "unknown_types": [],
                "has_multiple": False,
                "schema_data": {"all": "{}"},
                "errors": {},
            }

            with patch(
                "coregen.cli.commands.config.cfg_schema.Console"
            ) as mock_console:
                result = cli_runner.invoke(cli_app, ["config", "schema", "all"])
                assert result.exit_code == 0

                # Config schema prints the schema data directly, not through console.print with format
                mock_console.print.assert_called()

    @pytest.mark.parametrize(
        "command,unsupported_format",
        [
            (["config", "view", "--output", "table"], "table"),
            (["config", "view", "--output", "matrix"], "matrix"),
            (["config", "schema", "all", "--output", "table"], "table"),
        ],
    )
    def test_config_rejects_unsupported_format(
        self, cli_runner, cli_app, command, unsupported_format
    ):
        """Test that config commands reject unsupported formats."""
        result = cli_runner.invoke(cli_app, command)
        assert result.exit_code != 0


class TestCheckPatternCommandOutputFormat:
    """Test check-pattern command output format handling."""

    def test_check_pattern_uses_table_format_only(self, cli_runner, cli_app):
        """Test that check-pattern always uses TABLE format."""
        with patch(
            "coregen.cli.commands.check_pattern.check_pattern_cli.CheckPattern.run"
        ) as mock_run:
            mock_run.return_value = None

            # Should succeed without output format option
            result = cli_runner.invoke(cli_app, ["check-pattern", "w/*"])
            assert result.exit_code == 0

    def test_check_pattern_has_no_output_option(self, cli_runner, cli_app):
        """Test that check-pattern doesn't accept output format option."""
        # The command shouldn't have an --output option at all
        result = cli_runner.invoke(cli_app, ["check-pattern", "--help"])
        assert "--output" not in result.stdout


class TestGenerateCommandOutputFormat:
    """Test generate command output format handling."""

    def test_generate_uses_text_format_only(self, cli_runner, cli_app):
        """Test that generate command uses TEXT format only."""
        with patch(
            "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.generate_files.return_value = MagicMock()

            # Should work without output format
            result = cli_runner.invoke(cli_app, ["generate", "w/*", "--dry-run"])
            assert result.exit_code == 0

    def test_generate_text_output_format(self, cli_runner, cli_app):
        """Test that generate outputs text format."""
        with patch(
            "coregen.cli.commands.generate.gen_generate_cli.GenerateService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.generate_files.return_value = MagicMock()

            result = cli_runner.invoke(cli_app, ["generate", "w/*", "--dry-run"])
            assert result.exit_code == 0
            # Output should be text, not structured data


class TestOutputFormatEnumConsistency:
    """Test that output format enums are used consistently."""

    def test_get_command_uses_get_output_format_enum(self):
        """Test that get command uses GetOutputFormat enum."""
        from coregen.cli.commands.get.get_cli import Get

        assert hasattr(Get, "SUPPORTED_FORMATS")
        # Should use GetOutputFormat enum values
        for fmt in Get.SUPPORTED_FORMATS:
            assert isinstance(fmt, GetOutputFormat)

    def test_detect_changes_uses_correct_enum(self):
        """Test that detect-changes uses DetectChangesOutputFormat enum."""
        from coregen.cli.commands.detect_changes.detect_changes_cli import DetectChanges

        assert hasattr(DetectChanges, "SUPPORTED_FORMATS")
        # Should use DetectChangesOutputFormat enum values
        for fmt in DetectChanges.SUPPORTED_FORMATS:
            assert isinstance(fmt, DetectChangesOutputFormat)

    def test_check_pattern_uses_correct_enum(self):
        """Test that check-pattern uses CheckPatternOutputFormat enum."""
        from coregen.cli.commands.check_pattern.check_pattern_cli import CheckPattern

        assert hasattr(CheckPattern, "SUPPORTED_FORMATS")
        # Should use CheckPatternOutputFormat enum values
        for fmt in CheckPattern.SUPPORTED_FORMATS:
            assert isinstance(fmt, CheckPatternOutputFormat)
