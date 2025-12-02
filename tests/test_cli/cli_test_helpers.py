"""CLI-specific test helpers for CoreGen HPC.

This module provides helpers specifically for testing CLI commands,
including service mocking, command invocation, and result assertions.

Usage:
    from tests.test_cli.cli_test_helpers import (
        mock_cli_service,
        invoke_cli_command,
        assert_cli_success,
    )

    # Mock a service and invoke a command
    with mock_cli_service("coregen.cli.commands.get.get_cli.GetService", "get_elements", result_data):
        result = invoke_cli_command(cli_runner, cli_app, ["get", "c/*"])
        assert_cli_success(result)
"""

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

# ============================================================================
# CLI Service Mocking
# ============================================================================


@contextmanager
def mock_cli_service(
    service_class_path: str,
    method_name: str | None = None,
    return_value: Any = None,
    side_effect: Any = None,
    verify_global_options: bool = True,
):
    """Context manager for mocking CLI service patterns.

    This helper automates the common pattern of:
    1. Mocking a service class
    2. Configuring its return value or side effect
    3. Yielding the mocks for use in tests
    4. Verifying GlobalOptions was passed correctly

    Args:
        service_class_path: Full import path to service class
            (e.g., "coregen.cli.commands.get.get_cli.GetService")
        method_name: Name of the method to mock (e.g., "get_elements")
            If None, only the service class is mocked
        return_value: Value the mocked method should return
        side_effect: Side effect for the mocked method (e.g., exception)
        verify_global_options: Whether to verify GlobalOptions passed (default: True)

    Yields:
        tuple: (mock_service_class, mock_instance)

    Example:
        >>> with mock_cli_service(
        ...     "coregen.cli.commands.get.get_cli.GetService",
        ...     "get_elements",
        ...     {"contexts": ["dev"], "workspaces": [], "components": []}
        ... ) as (mock_class, mock_instance):
        ...     result = cli_runner.invoke(cli_app, ["get", "c/*"])
        ...     assert result.exit_code == 0
        ...     mock_instance.get_elements.assert_called_once()
    """
    with patch(service_class_path) as mock_service_class:
        mock_instance = mock_service_class.return_value

        # Configure the method if specified
        if method_name:
            mock_method = getattr(mock_instance, method_name)
            if side_effect is not None:
                mock_method.side_effect = side_effect
            elif return_value is not None:
                mock_method.return_value = return_value

        yield mock_service_class, mock_instance

        # Post-invocation validations
        if verify_global_options:
            from coregen.cli.global_options import GlobalOptions

            # Verify service was called
            if mock_service_class.called:
                service_kwargs = mock_service_class.call_args.kwargs
                assert (
                    "global_options" in service_kwargs
                ), "Service should be initialized with global_options"
                assert isinstance(
                    service_kwargs["global_options"], GlobalOptions
                ), "global_options should be a GlobalOptions instance"


# ============================================================================
# CLI Command Invocation Helpers
# ============================================================================


def invoke_cli_command(
    cli_runner,
    cli_app,
    args: list[str],
    expected_code: int = 0,
    catch_exceptions: bool = False,
) -> Any:
    """Standardized CLI invocation with validation.

    Args:
        cli_runner: The CliRunner fixture
        cli_app: The CLI app fixture
        args: Command arguments as a list (e.g., ["get", "c/*"])
        expected_code: Expected exit code (default: 0 for success)
        catch_exceptions: Whether to catch exceptions (default: False)

    Returns:
        CLI result object with exit_code, stdout, stderr attributes

    Raises:
        AssertionError: If exit code doesn't match expected value

    Example:
        >>> result = invoke_cli_command(
        ...     cli_runner, cli_app,
        ...     ["detect-changes", "--base-branch", "main"]
        ... )
        >>> assert "component1" in result.stdout
    """
    result = cli_runner.invoke(cli_app, args, catch_exceptions=catch_exceptions)

    assert result.exit_code == expected_code, (
        f"Expected exit code {expected_code}, got {result.exit_code}.\n"
        f"Command: {' '.join(args)}\n"
        f"Output: {result.stdout}\n"
        f"Error: {result.stderr if hasattr(result, 'stderr') else 'N/A'}"
    )

    return result


def invoke_cli_command_unchecked(
    cli_runner,
    cli_app,
    args: list[str],
    catch_exceptions: bool = True,
) -> Any:
    """Invoke CLI command without exit code validation.

    Use this when you want to test error conditions and need to
    inspect the exit code yourself.

    Args:
        cli_runner: The CliRunner fixture
        cli_app: The CLI app fixture
        args: Command arguments as a list
        catch_exceptions: Whether to catch exceptions (default: True)

    Returns:
        CLI result object

    Example:
        >>> result = invoke_cli_command_unchecked(
        ...     cli_runner, cli_app,
        ...     ["get", "invalid-pattern"]
        ... )
        >>> assert result.exit_code != 0
    """
    return cli_runner.invoke(cli_app, args, catch_exceptions=catch_exceptions)


# ============================================================================
# CLI Result Assertions
# ============================================================================


def assert_cli_success(result, mock_service: MagicMock | None = None):
    """Assert CLI command succeeded.

    Args:
        result: CLI result object from invoke
        mock_service: Optional mock service to verify was called

    Raises:
        AssertionError: If exit code != 0 or service wasn't called

    Example:
        >>> result = cli_runner.invoke(cli_app, ["get", "c/*"])
        >>> assert_cli_success(result, mock_instance)
    """
    assert result.exit_code == 0, (
        f"CLI command failed with exit code {result.exit_code}.\n"
        f"Output: {result.stdout}"
    )

    if mock_service:
        assert mock_service.called, "Expected service to be called but it wasn't"


def assert_cli_success_with_output(
    result,
    expected_in_output: list[str] | None = None,
    expected_not_in_output: list[str] | None = None,
):
    """Assert CLI success with output validation.

    Args:
        result: CLI result object from invoke
        expected_in_output: List of strings that should appear in stdout
        expected_not_in_output: List of strings that should NOT appear in stdout

    Raises:
        AssertionError: If exit code != 0 or output doesn't match

    Example:
        >>> assert_cli_success_with_output(
        ...     result,
        ...     expected_in_output=["component1", "CHANGED"],
        ...     expected_not_in_output=["ERROR"]
        ... )
    """
    assert result.exit_code == 0, (
        f"CLI command failed with exit code {result.exit_code}.\n"
        f"Output: {result.stdout}"
    )

    if expected_in_output:
        for text in expected_in_output:
            assert text in result.stdout, (
                f"Expected '{text}' in output but it was not found.\n"
                f"Output: {result.stdout}"
            )

    if expected_not_in_output:
        for text in expected_not_in_output:
            assert text not in result.stdout, (
                f"Expected '{text}' NOT in output but it was found.\n"
                f"Output: {result.stdout}"
            )


def assert_cli_failure(
    result,
    expected_code: int | None = None,
    expected_error_text: str | None = None,
):
    """Assert CLI command failed.

    Args:
        result: CLI result object from invoke
        expected_code: Specific exit code to expect (if None, any non-zero is OK)
        expected_error_text: Text expected in output/error

    Raises:
        AssertionError: If command succeeded or error doesn't match

    Example:
        >>> result = invoke_cli_command_unchecked(
        ...     cli_runner, cli_app, ["get", "invalid"]
        ... )
        >>> assert_cli_failure(result, expected_error_text="Invalid pattern")
    """
    assert result.exit_code != 0, (
        f"Expected CLI command to fail but it succeeded.\n" f"Output: {result.stdout}"
    )

    if expected_code is not None:
        assert result.exit_code == expected_code, (
            f"Expected exit code {expected_code}, got {result.exit_code}.\n"
            f"Output: {result.stdout}"
        )

    if expected_error_text:
        output = result.stdout
        if hasattr(result, "stderr") and result.stderr:
            output += result.stderr

        assert expected_error_text in output, (
            f"Expected error text '{expected_error_text}' not found in output.\n"
            f"Output: {output}"
        )


def assert_service_called_with_patterns(
    mock_service,
    method_name: str,
    expected_patterns: list[str],
):
    """Assert service method was called with specific patterns.

    Args:
        mock_service: The mock service instance
        method_name: Name of the method to check
        expected_patterns: List of patterns expected in the call

    Raises:
        AssertionError: If patterns don't match

    Example:
        >>> assert_service_called_with_patterns(
        ...     mock_instance,
        ...     "get_elements",
        ...     ["c/*", "cm/api"]
        ... )
    """
    mock_method = getattr(mock_service, method_name)
    mock_method.assert_called_once()

    call_kwargs = mock_method.call_args.kwargs
    assert "patterns" in call_kwargs, "Expected 'patterns' argument in method call"

    actual_patterns = call_kwargs["patterns"]
    assert (
        actual_patterns == expected_patterns
    ), f"Expected patterns {expected_patterns}, got {actual_patterns}"
