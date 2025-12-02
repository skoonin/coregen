"""Tests for detect-changes CLI commands."""

from unittest.mock import patch

import pytest

from coregen.cli.global_options import GlobalOptions
from tests.test_cli.cli_test_helpers import (
    assert_cli_success,
    invoke_cli_command,
    mock_cli_service,
)
from tests.test_helpers import create_component_change, create_detect_changes_result


def test_detect_changes_help(cli_runner, cli_app):
    """Test the help command for detect-changes."""
    result = cli_runner.invoke(cli_app, ["detect-changes", "--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout


def test_detect_changes_basic(cli_runner, cli_app):
    """Test basic detect-changes command."""
    changes = [
        create_component_change(component_name="component1"),
        create_component_change(component_name="component2"),
    ]
    result_data = create_detect_changes_result(changes=changes)

    with mock_cli_service(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService",
        "detect_changes",
        result_data,
    ) as (mock_class, mock_instance):
        result = invoke_cli_command(
            cli_runner, cli_app, ["detect-changes", "--output", "json"]
        )
        assert_cli_success(result, mock_instance.detect_changes)
        # Verify detect_changes method was called with base_branch
        call_kwargs = mock_instance.detect_changes.call_args.kwargs
        assert "base_branch" in call_kwargs


def test_detect_changes_no_changes(cli_runner, cli_app):
    """Test detect-changes when no changes are found."""
    result_data = create_detect_changes_result(
        changes=[], total_analyzed=10, total_unchanged=10
    )

    with mock_cli_service(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService",
        "detect_changes",
        result_data,
    ) as (mock_class, mock_instance):
        result = invoke_cli_command(
            cli_runner, cli_app, ["detect-changes", "--output", "json"]
        )
        assert_cli_success(result)
        call_kwargs = mock_instance.detect_changes.call_args.kwargs
        assert "base_branch" in call_kwargs


@pytest.mark.parametrize("git_ref", ["HEAD~1", "main", "origin/main"])
def test_detect_changes_with_git_refs(cli_runner, cli_app, git_ref):
    """Test detect-changes with different git references."""
    changes = [create_component_change(component_name="component1")]
    result_data = create_detect_changes_result(changes=changes)

    with mock_cli_service(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService",
        "detect_changes",
        result_data,
    ) as (mock_class, mock_instance):
        result = invoke_cli_command(
            cli_runner,
            cli_app,
            ["detect-changes", "--base-branch", git_ref, "--output", "json"],
        )
        assert_cli_success(result)

        # Verify git reference was passed to detect_changes method as base_branch
        base_branch_arg = mock_instance.detect_changes.call_args.kwargs["base_branch"]
        assert base_branch_arg == git_ref
        # The new implementation doesn't use head_ref anymore


def test_detect_changes_without_git_repo(cli_runner, cli_app):
    """Test detect-changes when no git repository exists."""
    with patch(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
    ) as mock_service_class:
        # Configure the mock to simulate missing git repo
        mock_instance = mock_service_class.return_value
        mock_instance.detect_changes.side_effect = RuntimeError("Not a git repository")

        # Invoke command
        result = cli_runner.invoke(cli_app, ["detect-changes", "--output", "json"])

        # Command should fail, but we don't check error message since it may be in stderr
        assert result.exit_code != 0

        # Verify service was initialized with GlobalOptions
        mock_service_class.assert_called_once()
        service_kwargs = mock_service_class.call_args.kwargs
        assert "global_options" in service_kwargs
        assert isinstance(service_kwargs["global_options"], GlobalOptions)


@pytest.mark.parametrize("output_format", ["json", "yaml", "matrix"])
def test_detect_changes_output_formats(cli_runner, cli_app, output_format):
    """Test detect-changes with different output formats."""
    with patch(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
    ) as mock_service_class:
        # Import the models we need
        from coregen.services.detect_changes.models import (
            ChangeReason,
            ChangeStatus,
            ComponentChange,
            DetectChangesResult,
        )

        # Configure the mock
        mock_instance = mock_service_class.return_value
        changes = [
            ComponentChange(
                component_name="component1",
                context_name="context",
                workspace_name="workspace",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
            )
        ]
        mock_instance.detect_changes.return_value = DetectChangesResult(
            changes=changes,
            total_analyzed=1,
            total_changed=1,
        )

        # Invoke command with output format
        result = cli_runner.invoke(
            cli_app, ["detect-changes", "--output", output_format]
        )

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify service was initialized with GlobalOptions
        mock_service_class.assert_called_once()
        service_kwargs = mock_service_class.call_args.kwargs
        assert "global_options" in service_kwargs

        global_options = service_kwargs["global_options"]
        assert isinstance(global_options, GlobalOptions)

        # Output format is now handled at command level, not in GlobalOptions
        # The command should have passed it to the service method directly
        # Check that detect_changes was called
        mock_instance.detect_changes.assert_called_once()

        # Verify base_branch is present (required parameter)
        call_kwargs = mock_instance.detect_changes.call_args.kwargs
        assert "base_branch" in call_kwargs
        # The new implementation doesn't use head_ref anymore


def test_detect_changes_with_paths_filter(cli_runner, cli_app):
    """Test detect-changes with paths filter."""
    with patch(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
    ) as mock_service_class:
        # Import the models we need
        from coregen.services.detect_changes.models import (
            ChangeReason,
            ChangeStatus,
            ComponentChange,
            DetectChangesResult,
        )

        # Configure the mock
        mock_instance = mock_service_class.return_value
        changes = [
            ComponentChange(
                component_name="component1",
                context_name="aws",
                workspace_name="contexts",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
            )
        ]
        mock_instance.detect_changes.return_value = DetectChangesResult(
            changes=changes,
            total_analyzed=1,
            total_changed=1,
        )

        # Invoke command with filter instead of paths
        # The CLI doesn't support a --paths option directly, use --filter which is supported
        result = cli_runner.invoke(
            cli_app,
            ["detect-changes", "--filter", "workspace.name=aws", "--output", "json"],
        )

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify service was initialized with GlobalOptions
        mock_service_class.assert_called_once()
        service_kwargs = mock_service_class.call_args.kwargs
        assert "global_options" in service_kwargs
        assert isinstance(service_kwargs["global_options"], GlobalOptions)

        # Verify filter was passed to the detect_changes method
        method_args = mock_instance.detect_changes.call_args.kwargs
        assert "filters" in method_args
        assert method_args["filters"] == ["workspace.name=aws"]

        # Check that detect_changes was called with the base_branch parameter
        assert "base_branch" in method_args
        # The new implementation doesn't use head_ref anymore


def test_detect_changes_with_include_inactive(cli_runner, cli_app):
    """Test detect-changes with include-inactive option."""
    with patch(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
    ) as mock_service_class:
        # Import the models we need
        from coregen.services.detect_changes.models import (
            ChangeReason,
            ChangeStatus,
            ComponentChange,
            DetectChangesResult,
        )

        # Configure the mock
        mock_instance = mock_service_class.return_value
        changes = [
            ComponentChange(
                component_name="component1",
                context_name="aws",
                workspace_name="contexts",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                component_active=False,  # Inactive component
            )
        ]
        mock_instance.detect_changes.return_value = DetectChangesResult(
            changes=changes,
            total_analyzed=1,
            total_changed=1,
        )

        # Invoke command with include-inactive option
        result = cli_runner.invoke(
            cli_app, ["detect-changes", "--include-inactive", "--output", "json"]
        )

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify service was initialized with GlobalOptions
        mock_service_class.assert_called_once()
        service_kwargs = mock_service_class.call_args.kwargs
        assert "global_options" in service_kwargs
        assert isinstance(service_kwargs["global_options"], GlobalOptions)

        # Verify include_inactive was passed to the detect_changes method
        method_args = mock_instance.detect_changes.call_args.kwargs
        assert "include_inactive" in method_args
        assert method_args["include_inactive"] is True

        # Check that detect_changes was called with the required parameters
        assert "base_branch" in method_args
        # The new implementation doesn't use head_ref anymore


def test_detect_changes_with_filters(cli_runner, cli_app):
    """Test detect-changes with component filters."""
    with patch(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
    ) as mock_service_class:
        # Import the models we need
        from coregen.services.detect_changes.models import (
            ChangeReason,
            ChangeStatus,
            ComponentChange,
            DetectChangesResult,
        )

        # Configure the mock
        mock_instance = mock_service_class.return_value
        changes = [
            ComponentChange(
                component_name="component1",
                context_name="context",
                workspace_name="workspace",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
            )
        ]
        mock_instance.detect_changes.return_value = DetectChangesResult(
            changes=changes,
            total_analyzed=1,
            total_changed=1,
        )

        # Invoke command with filter
        result = cli_runner.invoke(
            cli_app,
            ["detect-changes", "--filter", "environment=dev", "--output", "json"],
        )

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify service was initialized with GlobalOptions
        mock_service_class.assert_called_once()
        service_kwargs = mock_service_class.call_args.kwargs
        assert "global_options" in service_kwargs
        assert isinstance(service_kwargs["global_options"], GlobalOptions)

        # Verify filter was passed to service
        method_args = mock_instance.detect_changes.call_args.kwargs
        assert "filters" in method_args
        assert method_args["filters"] == ["environment=dev"]

        # Verify base_branch is present (required parameter)
        assert "base_branch" in method_args
        # The new implementation doesn't use head_ref anymore


def test_detect_changes_service_integration(cli_runner, cli_app):
    """Test that detect-changes command properly integrates with the service layer."""
    with patch(
        "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
    ) as mock_service_class:
        # Import the models we need
        from coregen.services.detect_changes.models import (
            ChangeReason,
            ChangeStatus,
            ComponentChange,
            DetectChangesResult,
        )

        # Configure the mock
        mock_instance = mock_service_class.return_value
        changes = [
            ComponentChange(
                component_name="component1",
                context_name="context",
                workspace_name="workspace",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
            )
        ]
        mock_instance.detect_changes.return_value = DetectChangesResult(
            changes=changes,
            total_analyzed=1,
            total_changed=1,
        )

        # Run with various options to test they're passed through
        result = cli_runner.invoke(
            cli_app,
            [
                "detect-changes",
                "--verbose",
                "--no-color",
                "--output",
                "json",
                "--base-branch",
                "HEAD~1",
            ],
        )

        # Verify command ran successfully
        assert result.exit_code == 0

        # Check that service was instantiated correctly
        mock_service_class.assert_called_once()

        # Get the keyword arguments used to initialize the service
        service_kwargs = mock_service_class.call_args.kwargs

        # Verify GlobalOptions was passed to the service
        assert "global_options" in service_kwargs
        global_options = service_kwargs["global_options"]
        assert isinstance(global_options, GlobalOptions)

        # Verify options were correctly set in GlobalOptions
        assert global_options.verbose is True
        assert global_options.no_color is True
        # Output format is now handled at command level, not in GlobalOptions

        # Verify base_branch was passed to detect_changes method
        detect_changes_kwargs = mock_instance.detect_changes.call_args.kwargs
        assert detect_changes_kwargs.get("base_branch") == "HEAD~1"
        # The new implementation doesn't use head_ref anymore


def test_detect_changes_matrix_changed_only_filters_deleted(cli_runner, cli_app):
    """Test that --changed-only flag filters out deleted components in matrix output.

    This test verifies that when using --output matrix --changed-only, only components
    with status 'changed' are included in the matrix output.
    """
    from unittest.mock import MagicMock

    from coregen.services.detect_changes.models import (
        ChangeReason,
        ChangeStatus,
        ComponentChange,
        DetectChangesResult,
    )

    # Create changes with both changed and deleted components
    changed_component = ComponentChange(
        component_name="api-service",
        context_name="dev",
        workspace_name="apps",
        status=ChangeStatus.CHANGED,
        reason=ChangeReason.DIRECT,
    )
    deleted_component = ComponentChange(
        component_name="legacy-service",
        context_name="dev",
        workspace_name="apps",
        status=ChangeStatus.DELETED,
        reason=ChangeReason.DELETED,
    )

    mock_result = DetectChangesResult(
        changes=[changed_component, deleted_component],
        deleted=[deleted_component],
        total_analyzed=2,
        total_changed=1,
        total_deleted=1,
    )

    # Mock console to capture what gets printed
    captured_output = []

    def capture_print(data, **kwargs):
        captured_output.append(data)

    with (
        patch(
            "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
        ) as mock_service_class,
        patch(
            "coregen.cli.commands.detect_changes.detect_changes_cli.console"
        ) as mock_console,
    ):
        mock_service_class.return_value.detect_changes.return_value = mock_result
        mock_console.print = MagicMock(side_effect=capture_print)
        mock_console.set_output_format = MagicMock()
        mock_console.error = MagicMock()

        # Invoke with --changed-only and matrix output
        result = cli_runner.invoke(
            cli_app, ["detect-changes", "--output", "matrix", "--changed-only"]
        )

        assert result.exit_code == 0

        # Verify console.print was called with filtered matrix data
        assert len(captured_output) == 1
        matrix_data = captured_output[0]

        # Verify matrix structure
        assert "include" in matrix_data

        # Verify only changed components are included, not deleted
        assert len(matrix_data["include"]) == 1
        assert matrix_data["include"][0]["component_name"] == "api-service"
        assert matrix_data["include"][0]["status"] == "changed"

        # Ensure deleted component is NOT present
        component_names = [c["component_name"] for c in matrix_data["include"]]
        assert "legacy-service" not in component_names


def test_detect_changes_matrix_deleted_only_filters_changed(cli_runner, cli_app):
    """Test that --deleted-only flag filters out changed components in matrix output.

    This test verifies that when using --output matrix --deleted-only, only components
    with status 'deleted' are included in the matrix output.
    """
    from unittest.mock import MagicMock

    from coregen.services.detect_changes.models import (
        ChangeReason,
        ChangeStatus,
        ComponentChange,
        DetectChangesResult,
    )

    # Create changes with both changed and deleted components
    changed_component = ComponentChange(
        component_name="api-service",
        context_name="dev",
        workspace_name="apps",
        status=ChangeStatus.CHANGED,
        reason=ChangeReason.DIRECT,
    )
    deleted_component = ComponentChange(
        component_name="legacy-service",
        context_name="dev",
        workspace_name="apps",
        status=ChangeStatus.DELETED,
        reason=ChangeReason.DELETED,
    )

    mock_result = DetectChangesResult(
        changes=[changed_component, deleted_component],
        deleted=[deleted_component],
        total_analyzed=2,
        total_changed=1,
        total_deleted=1,
    )

    # Mock console to capture what gets printed
    captured_output = []

    def capture_print(data, **kwargs):
        captured_output.append(data)

    with (
        patch(
            "coregen.cli.commands.detect_changes.detect_changes_cli.DetectChangesService"
        ) as mock_service_class,
        patch(
            "coregen.cli.commands.detect_changes.detect_changes_cli.console"
        ) as mock_console,
    ):
        mock_service_class.return_value.detect_changes.return_value = mock_result
        mock_console.print = MagicMock(side_effect=capture_print)
        mock_console.set_output_format = MagicMock()
        mock_console.error = MagicMock()

        # Invoke with --deleted-only and matrix output
        result = cli_runner.invoke(
            cli_app, ["detect-changes", "--output", "matrix", "--deleted-only"]
        )

        assert result.exit_code == 0

        # Verify console.print was called with filtered matrix data
        assert len(captured_output) == 1
        matrix_data = captured_output[0]

        # Verify matrix structure
        assert "include" in matrix_data

        # Verify only deleted components are included, not changed
        assert len(matrix_data["include"]) == 1
        assert matrix_data["include"][0]["component_name"] == "legacy-service"
        assert matrix_data["include"][0]["status"] == "deleted"

        # Ensure changed component is NOT present
        component_names = [c["component_name"] for c in matrix_data["include"]]
        assert "api-service" not in component_names
