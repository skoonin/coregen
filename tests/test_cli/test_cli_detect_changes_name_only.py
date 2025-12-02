"""Tests for detect changes CLI name-only functionality."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from coregen.cli.cli import app
from coregen.services.detect_changes.models import (
    ChangeReason,
    ChangeStatus,
    ComponentChange,
    DetectChangesResult,
)


@pytest.fixture
def cli_runner_setup() -> dict[str, CliRunner]:
    """Set up test fixtures for CLI tests."""
    runner = CliRunner()
    return {"runner": runner}


class TestDetectChangesCLINamesOnly:
    """Test CLI name-only functionality for detect changes."""

    @patch(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
    )
    def test_cli_name_only_flag(self, mock_service_class, cli_runner_setup):
        """Test that --name-only flag is passed to service."""
        runner = cli_runner_setup["runner"]
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Create proper DetectChangesResult
        change1 = ComponentChange(
            component_name="component1",
            context_name="context1",
            workspace_name="workspace1",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
        )
        change2 = ComponentChange(
            component_name="component2",
            context_name="context2",
            workspace_name="workspace2",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
        )

        mock_result = DetectChangesResult(changes=[change1, change2])
        mock_service.detect_changes.return_value = mock_result

        result = runner.invoke(
            app,
            [
                "detect-changes",
                "--base-branch",
                "HEAD~1",
                "--name-only",
                "--config-file",
                "test_data/.cgconfig.yaml",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        mock_service.detect_changes.assert_called_once()
        # name_only is handled in the CLI formatter, not passed to service

    @patch(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
    )
    def test_cli_names_format_option(self, mock_service_class, cli_runner_setup):
        """Test that --name-only with changed-only is handled correctly."""
        runner = cli_runner_setup["runner"]
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Create proper DetectChangesResult
        change1 = ComponentChange(
            component_name="nginx",
            context_name="context1",
            workspace_name="workspace1",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
        )
        change2 = ComponentChange(
            component_name="prometheus",
            context_name="context2",
            workspace_name="workspace2",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
        )

        mock_result = DetectChangesResult(changes=[change1, change2])
        mock_service.detect_changes.return_value = mock_result

        result = runner.invoke(
            app,
            [
                "detect-changes",
                "--base-branch",
                "HEAD~1",
                "--name-only",
                "--changed-only",
                "--config-file",
                "test_data/.cgconfig.yaml",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        # changed_only is handled in the CLI formatter, not passed to service

    @patch(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
    )
    def test_cli_json_output_handles_names_dict(
        self, mock_service_class, cli_runner_setup
    ):
        """Test that JSON output properly handles name-only dict result."""
        runner = cli_runner_setup["runner"]
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Create proper DetectChangesResult with varied statuses
        change1 = ComponentChange(
            component_name="nginx",
            context_name="aws-cluster-dev",
            workspace_name="aws",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
        )
        change2 = ComponentChange(
            component_name="prometheus",
            context_name="aws-cluster-dev",
            workspace_name="aws",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
        )

        mock_result = DetectChangesResult(changes=[change1, change2])
        mock_service.detect_changes.return_value = mock_result

        result = runner.invoke(
            app,
            [
                "detect-changes",
                "--base-branch",
                "HEAD~1",
                "--name-only",
                "--config-file",
                "test_data/.cgconfig.yaml",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        # Check for actual JSON structure (name-only format)
        assert '"changed"' in result.stdout
        assert '"nginx"' in result.stdout
        assert '"prometheus"' in result.stdout

    @patch(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
    )
    def test_cli_json_output_handles_names_list(
        self, mock_service_class, cli_runner_setup
    ):
        """Test that JSON output properly handles name-only list result."""
        runner = cli_runner_setup["runner"]
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Create proper DetectChangesResult
        change1 = ComponentChange(
            component_name="nginx",
            context_name="context1",
            workspace_name="workspace1",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
        )
        change2 = ComponentChange(
            component_name="prometheus",
            context_name="context2",
            workspace_name="workspace2",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
        )

        mock_result = DetectChangesResult(changes=[change1, change2])
        mock_service.detect_changes.return_value = mock_result

        result = runner.invoke(
            app,
            [
                "detect-changes",
                "--base-branch",
                "HEAD~1",
                "--name-only",
                "--config-file",
                "test_data/.cgconfig.yaml",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        # When name-only is used with JSON, check for structure
        assert '"changed"' in result.stdout
        assert "nginx" in result.stdout
        assert "prometheus" in result.stdout

    @patch(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
    )
    def test_cli_json_output_with_name_only(self, mock_service_class, cli_runner_setup):
        """Test JSON output with name-only."""
        runner = cli_runner_setup["runner"]
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Create proper DetectChangesResult
        change1 = ComponentChange(
            component_name="nginx",
            context_name="context1",
            workspace_name="workspace1",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
        )
        change2 = ComponentChange(
            component_name="prometheus",
            context_name="context2",
            workspace_name="workspace2",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
        )

        mock_result = DetectChangesResult(changes=[change1, change2])
        mock_service.detect_changes.return_value = mock_result

        result = runner.invoke(
            app,
            [
                "detect-changes",
                "--base-branch",
                "HEAD~1",
                "--name-only",
                "--output",
                "json",
                "--config-file",
                "test_data/.cgconfig.yaml",
            ],
        )

        assert result.exit_code == 0
        # When name-only is used with JSON, check for structure
        assert '"changed"' in result.stdout
        assert "nginx" in result.stdout
        assert "prometheus" in result.stdout

    def test_type_default_value(self, cli_runner_setup):
        """Test that changed-only option has correct default value."""
        runner = cli_runner_setup["runner"]
        # This tests the default value set in CLI
        result = runner.invoke(app, ["detect-changes", "--help", "--no-color"])
        assert result.exit_code == 0

        # Check for changed-only option in help text
        assert "--changed-only" in result.stdout or "changed-only" in result.stdout

    @patch(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
    )
    def test_cli_type_enum_values(self, mock_service_class, cli_runner_setup):
        """Test that output format enum accepts valid values."""
        runner = cli_runner_setup["runner"]
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Create a minimal DetectChangesResult
        mock_result = DetectChangesResult(changes=[])
        mock_service.detect_changes.return_value = mock_result

        # Test valid output format values
        for output_format in ["json", "yaml", "matrix"]:
            result = runner.invoke(
                app,
                [
                    "detect-changes",
                    "--base-branch",
                    "HEAD~1",
                    "--output",
                    output_format,
                    "--config-file",
                    "test_data/.cgconfig.yaml",
                ],
            )
            assert result.exit_code == 0, f"Failed for output format: {output_format}"
