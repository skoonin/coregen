"""Test fixtures for End-to-End testing.

Common fixtures like cli_runner, cli_app (cli_app_mocked), and reset_console_state
are now available from the root conftest.py. This file contains E2E-specific fixtures.

Note: E2E tests should use cli_app_raw if they need to verify actual console output.
"""

import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from coregen.cli.cli import app


# Mark all tests in the test_e2e directory with the e2e marker
def pytest_collection_modifyitems(items: list) -> None:
    """Mark all tests in this directory with e2e marker."""
    for item in items:
        # If the test is in the test_e2e directory, add the e2e marker
        if "test_e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


# Add the source directory to the path so we can import modules
source_dir = Path(__file__).parent.parent.parent / "source"
sys.path.insert(0, str(source_dir))

# Note: cli_runner, cli_app, and reset_console_state are now provided by root conftest.py
# For E2E tests that need actual output, use cli_app_raw from root conftest.py


@pytest.fixture(autouse=True)
def isolate_working_directory() -> Generator[None, None, None]:
    """Ensure tests don't interfere with each other's working directory."""
    import os

    original_cwd = Path.cwd()
    yield
    # Always restore original working directory after test
    os.chdir(original_cwd)


def _setup_git_repo(repo_dir: Path) -> None:
    """Set up a git repository with proper configuration for tests.

    Args:
        repo_dir: Directory where to initialize the git repository
    """
    # Initialize git repo with main as default branch
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "--local", "user.name", "Test User"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "--local", "user.email", "test@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    # Disable GPG signing for tests
    subprocess.run(
        ["git", "config", "--local", "commit.gpgsign", "false"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )


# Note: cli_runner and cli_app are now provided by the root conftest.py
# E2E tests can use cli_app_raw if they need actual console output


@pytest.fixture
def temp_test_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for E2E test execution.

    The directory will be automatically deleted after tests complete.
    """
    # Create a temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="coregen_e2e_"))
    print(f"Created temporary test directory: {temp_dir}")

    try:
        # Return the path for use in the test
        yield temp_dir
    finally:
        # Clean up the temporary directory
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"Cleaned up temporary test directory: {temp_dir}")
            except Exception as e:
                print(f"Error removing temporary directory {temp_dir}: {e}")


@pytest.fixture
def test_data_dir(temp_test_dir: Path) -> Path:
    """
    Create a copy of the test_data directory in a temporary location.

    Returns the path to the copied test_data directory.
    """
    # Source test data directory
    source_test_data = Path(__file__).parent.parent.parent / "test_data"

    # Create destination directory
    dest_test_data = temp_test_dir / "test_data"
    dest_test_data.mkdir(exist_ok=True)

    # Copy test data content
    shutil.copytree(source_test_data, dest_test_data, dirs_exist_ok=True)

    return dest_test_data


@pytest.fixture
def test_git_repo(temp_test_dir: Path) -> Path:
    """Create a test Git repository in the temporary directory.

    This allows for testing git-dependent functionality like detect-changes.
    """
    repo_dir = temp_test_dir / "git_test_repo"
    repo_dir.mkdir(exist_ok=True)

    # Set up git repository with proper configuration
    _setup_git_repo(repo_dir)

    # Create a test file and commit it
    test_file = repo_dir / "test_file.txt"
    with open(test_file, "w") as f:
        f.write("Initial content\n")

    subprocess.run(
        ["git", "add", "test_file.txt"], cwd=repo_dir, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    return repo_dir


@pytest.fixture
def env_setup(temp_test_dir: Path, test_data_dir: Path) -> dict[str, Any]:
    """
    Set up a full test environment with all necessary components.

    Returns a dictionary with paths and configurations.
    """
    # Create config file for test environment
    config_path = temp_test_dir / ".cgconfig.yaml"
    shutil.copy(test_data_dir / ".cgconfig.yaml", config_path)

    # Return all the paths and configurations
    return {
        "root_dir": temp_test_dir,
        "test_data_dir": test_data_dir,
        "config_path": config_path,
        "contexts_dir": test_data_dir / "contexts",
        "templates_dir": test_data_dir / "common-templates",
    }


@pytest.fixture
def gen_test_env(temp_test_dir: Path, env_setup: dict[str, Any]) -> dict[str, Any]:
    """
    Set up a specific test environment for generation tests using existing test_data.

    This creates a dedicated directory with the necessary structure
    to test component generation, copying from existing test_data rather than creating new templates.
    """
    # Create a generation test directory
    gen_test_dir = temp_test_dir / "gen_test"
    gen_test_dir.mkdir(exist_ok=True)

    # Copy templates from test_data (use the existing ones directly)
    templates_dir = gen_test_dir / "common-templates"  # Use expected directory name
    shutil.copytree(env_setup["templates_dir"], templates_dir, dirs_exist_ok=True)

    # Verify required template directories exist
    metrics_server_dir = templates_dir / "metrics-server"
    prometheus_dir = templates_dir / "prometheus"

    assert (
        metrics_server_dir.exists()
    ), "metrics-server templates not found in test_data"
    assert prometheus_dir.exists(), "prometheus templates not found in test_data"

    # For tests that rely on specific template structure, ensure key template files exist
    required_metrics_templates = [
        "README.md.j2",
        "deployment.yaml.j2",
        "kustomization.yaml.j2",
    ]
    for template in required_metrics_templates:
        template_path = metrics_server_dir / template
        assert (
            template_path.exists()
        ), f"Required template {template} not found in metrics-server directory"

    required_prometheus_templates = [
        "README.md.j2",
        "kube-prometheus-stack-values.yaml.j2",
    ]
    for template in required_prometheus_templates:
        template_path = prometheus_dir / template
        assert (
            template_path.exists()
        ), f"Required template {template} not found in prometheus directory"

    # For the prometheus dependency test, create a dependencies.yml file if it doesn't exist
    dependencies_file = prometheus_dir / "dependencies.yml"
    if not dependencies_file.exists():
        with open(dependencies_file, "w") as f:
            f.write(
                """
dependencies:
  - metrics-server
"""
            )

    # Create contexts directory
    contexts_dir = gen_test_dir / "contexts"
    shutil.copytree(env_setup["contexts_dir"], contexts_dir, dirs_exist_ok=True)

    # Ensure we have required context directories for tests
    aws_cluster_dirs = list(contexts_dir.glob("**/aws-cluster*"))
    cluster_dev_dir = contexts_dir / "context-dev"

    # Add test contexts if needed
    if not aws_cluster_dirs:
        # Create a test aws-cluster-01 context
        aws_cluster_dir = contexts_dir / "aws-cluster-01"
        aws_cluster_dir.mkdir(parents=True, exist_ok=True)

        # Copy values from another context if available, or create minimal one
        if cluster_dev_dir.exists():
            values_files = list(cluster_dev_dir.glob("*-cgvalues.yaml"))
            if values_files:
                target_file = aws_cluster_dir / "aws-cluster-01-cgvalues.yaml"
                content = values_files[0].read_text()
                content = content.replace("name: context-dev", "name: aws-cluster-01")
                with open(target_file, "w") as f:
                    f.write(content)

    # Create a test configuration file
    config_path = gen_test_dir / ".cgconfig.yaml"
    shutil.copy(env_setup["config_path"], config_path)

    # Return the test environment details
    return {
        "root_dir": gen_test_dir,
        "templates_dir": templates_dir,
        "contexts_dir": contexts_dir,
        "config_path": config_path,
    }


@pytest.fixture
def run_cli_command() -> (
    Callable[[str, Path | None, int, dict[str, str] | None], dict[str, Any]]
):
    """Run a CLI command with specified arguments.

    Returns a function that takes a command string, working directory,
    and expected exit code.
    """

    def _run_command(
        cmd: str,
        cwd: Path | None = None,
        expected_code: int = 0,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Run a CLI command and return the result.

        Args:
            cmd: The command to run (e.g., "config view")
            cwd: The working directory to run in (optional)
            expected_code: The expected exit code (default: 0)
            env: Environment variables dictionary (optional)

        Returns:
            Dict with keys: success, exit_code, stdout, stderr
        """
        # Split command into args using shlex to handle quoted arguments properly
        import shlex

        args = shlex.split(cmd)

        # Create a runner that can capture output
        runner = CliRunner()

        # Store original working directory
        original_cwd = Path.cwd()

        # Change to specified working directory if provided
        if cwd:
            import os

            os.chdir(cwd)

        try:
            # Run the command with exception catching enabled to capture error messages
            if env:
                result = runner.invoke(app, args, catch_exceptions=True, env=env)
            else:
                result = runner.invoke(app, args, catch_exceptions=True)
        finally:
            # Always restore original working directory
            import os

            os.chdir(original_cwd)

        # Handle stdout and stderr output
        stdout_output = result.stdout if hasattr(result, "stdout") else ""
        try:
            stderr_output = result.stderr if hasattr(result, "stderr") else ""
        except ValueError:
            # stderr not separately captured, use empty string
            stderr_output = ""

        # REMOVED WORKAROUND: No longer combining stderr with stdout
        # Tests must check both stdout and stderr separately for proper error handling

        # Check exit code - success means matching the expected exit code
        success = result.exit_code == expected_code

        # Print debug info only when tests fail
        if not success:
            print(f"Command failed: {cmd}")
            print(f"Exit code: {result.exit_code}")
            print(f"Stdout: {stdout_output}")
            print(f"Stderr: {stderr_output}")
            if hasattr(result, "exception") and result.exception:
                print(f"Exception: {result.exception}")
                import traceback

                print(
                    f"Traceback: {''.join(traceback.format_exception(type(result.exception), result.exception, result.exception.__traceback__))}"
                )

        return {
            "success": success,
            "exit_code": result.exit_code,
            "stdout": stdout_output,
            "stderr": stderr_output,
        }

    return _run_command
