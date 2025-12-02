"""Tests for get CLI commands."""

import pytest

from tests.test_cli.cli_test_helpers import (
    assert_cli_success,
    assert_service_called_with_patterns,
    invoke_cli_command,
    invoke_cli_command_unchecked,
    mock_cli_service,
)
from tests.test_helpers import create_get_elements_result


def test_get_help(cli_runner, cli_app):
    """Test the help command for get."""
    result = cli_runner.invoke(cli_app, ["get", "--help"])
    # Get command exits with 2 for help when no_args_is_help=True
    assert result.exit_code in (0, 2)
    assert "Usage:" in result.stdout


@pytest.mark.parametrize(
    "pattern,resource_type",
    [("c/*", "contexts"), ("cm/*", "components"), ("w/*", "workspaces")],
)
def test_get_resources(cli_runner, cli_app, pattern, resource_type):
    """Test retrieving different types of resources using pattern syntax."""
    # Create appropriate return data based on resource type
    result_data = {}
    if resource_type == "contexts":
        result_data = create_get_elements_result(
            contexts=["aws-context", "gcp-context"]
        )
    elif resource_type == "components":
        result_data = create_get_elements_result(
            components=["metrics-server", "prometheus"],
            details={
                "components": {
                    "metrics-server": {"name": "metrics-server"},
                    "prometheus": {"name": "prometheus"},
                }
            },
        )
    elif resource_type == "workspaces":
        result_data = create_get_elements_result(workspaces=["aws", "gcp"])

    with mock_cli_service(
        "coregen.cli.commands.get.get_cli.GetService", "get_elements", result_data
    ) as (mock_class, mock_instance):
        invoke_cli_command(cli_runner, cli_app, ["get", pattern])
        assert_service_called_with_patterns(mock_instance, "get_elements", [pattern])


@pytest.mark.parametrize("output_format", ["table", "json", "yaml"])
def test_get_with_different_output_formats(cli_runner, cli_app, output_format):
    """Test get command with different output formats."""
    result_data = create_get_elements_result(contexts=["test-context"])

    with mock_cli_service(
        "coregen.cli.commands.get.get_cli.GetService", "get_elements", result_data
    ) as (mock_class, mock_instance):
        result = invoke_cli_command(
            cli_runner, cli_app, ["get", "--output", output_format, "c/*"]
        )
        assert_cli_success(result, mock_instance.get_elements)


def test_get_with_pattern_filter(cli_runner, cli_app):
    """Test get command with a pattern filter."""
    result_data = create_get_elements_result(contexts=["dev-context"])

    with mock_cli_service(
        "coregen.cli.commands.get.get_cli.GetService", "get_elements", result_data
    ) as (mock_class, mock_instance):
        invoke_cli_command(cli_runner, cli_app, ["get", "c/dev-*"])
        assert_service_called_with_patterns(mock_instance, "get_elements", ["c/dev-*"])


def test_get_nonexistent_resource(cli_runner, cli_app):
    """Test error handling when resource doesn't exist."""
    result_data = create_get_elements_result()  # Empty results

    with mock_cli_service(
        "coregen.cli.commands.get.get_cli.GetService", "get_elements", result_data
    ) as (mock_class, mock_instance):
        # Command should still succeed with empty results
        invoke_cli_command(cli_runner, cli_app, ["get", "c/non-existent"])
        assert_service_called_with_patterns(
            mock_instance, "get_elements", ["c/non-existent"]
        )


def test_get_with_service_error(cli_runner, cli_app):
    """Test error handling when service throws an exception."""
    with mock_cli_service(
        "coregen.cli.commands.get.get_cli.GetService",
        "get_elements",
        None,
        side_effect=ValueError("Resource type not supported"),
    ) as (mock_class, mock_instance):
        # Command should exit with error code since service raises exception
        result = invoke_cli_command_unchecked(cli_runner, cli_app, ["get", "c/*"])
        assert result.exit_code != 0
        assert mock_instance.get_elements.called


def test_get_resources_with_verbose(cli_runner, cli_app):
    """Test get command with verbose output."""
    result_data = create_get_elements_result(contexts=["test-context"])

    with mock_cli_service(
        "coregen.cli.commands.get.get_cli.GetService", "get_elements", result_data
    ) as (mock_class, mock_instance):
        result = invoke_cli_command(
            cli_runner, cli_app, ["get", "--verbose", "c/test-context"]
        )
        assert_cli_success(result, mock_instance.get_elements)


def test_get_specific_resource(cli_runner, cli_app):
    """Test retrieving a specific resource by name."""
    result_data = create_get_elements_result(contexts=["specific-context"])

    with mock_cli_service(
        "coregen.cli.commands.get.get_cli.GetService", "get_elements", result_data
    ) as (mock_class, mock_instance):
        invoke_cli_command(cli_runner, cli_app, ["get", "c/specific-context"])
        assert_service_called_with_patterns(
            mock_instance, "get_elements", ["c/specific-context"]
        )


def test_get_with_parent_filter(cli_runner, cli_app):
    """Test get command with parent filtering (e.g. components in a specific context)."""
    result_data = create_get_elements_result(
        components=["test-context/component1"],
        details={
            "components": {
                "test-context/component1": {
                    "name": "component1",
                    "context": "test-context",
                }
            }
        },
    )

    with mock_cli_service(
        "coregen.cli.commands.get.get_cli.GetService", "get_elements", result_data
    ) as (mock_class, mock_instance):
        result = invoke_cli_command(
            cli_runner, cli_app, ["get", "cm/*", "--filter", "context=test-context"]
        )
        # Verify filters were passed to service
        call_kwargs = mock_instance.get_elements.call_args.kwargs
        assert "filters" in call_kwargs
        assert "context=test-context" in call_kwargs["filters"]


def test_get_invalid_resource_type(cli_runner, cli_app):
    """Test error handling with invalid resource type."""
    # Run command with catch_exceptions=True to catch any raised exceptions
    result = cli_runner.invoke(cli_app, ["get", "invalid-type"], catch_exceptions=True)

    # Command should fail with non-zero exit code
    assert result.exit_code != 0
