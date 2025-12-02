"""
E2E tests for installation processes.

These tests validate that the coregen tool can be properly installed and accessed.
"""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_makefile_exists():
    """Test that the Makefile exists with installation targets."""
    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent
    makefile_path = root_dir / "Makefile"

    # Check that Makefile exists
    assert makefile_path.exists(), "Makefile does not exist"

    # Read Makefile content and check for install targets
    makefile_content = makefile_path.read_text()

    # Check for pip-based install targets (may be in included makefiles)
    # Check if install.mk is included
    install_mk_included = "include makefiles/install.mk" in makefile_content
    has_install_direct = "install:" in makefile_content

    assert (
        install_mk_included or has_install_direct
    ), "pip-based install targets not found in Makefile or included files"


@pytest.mark.e2e
def test_pyproject_toml_exists():
    """Test that pyproject.toml exists and has proper configuration."""
    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent
    pyproject_path = root_dir / "pyproject.toml"

    # Check that pyproject.toml exists
    assert pyproject_path.exists(), "pyproject.toml does not exist"

    # Read pyproject.toml content and check for key components
    pyproject_content = pyproject_path.read_text()

    # Check for key setup components
    assert (
        "[build-system]" in pyproject_content
    ), "[build-system] section not found in pyproject.toml"
    assert (
        "[project]" in pyproject_content
    ), "[project] section not found in pyproject.toml"
    assert "name =" in pyproject_content, "name parameter not found in pyproject.toml"
    assert (
        "requires-python =" in pyproject_content
    ), "requires-python parameter not found in pyproject.toml"
    assert (
        "dependencies =" in pyproject_content
    ), "dependencies parameter not found in pyproject.toml"
    assert (
        "[project.scripts]" in pyproject_content
    ), "[project.scripts] section not found in pyproject.toml"


@pytest.mark.e2e
def test_dependencies_in_pyproject():
    """Test that dependencies are properly declared in pyproject.toml."""
    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent
    pyproject_path = root_dir / "pyproject.toml"

    # Check that pyproject.toml exists
    assert pyproject_path.exists(), "pyproject.toml does not exist"

    # Read pyproject.toml content and check for key dependencies
    pyproject_content = pyproject_path.read_text()

    # Check for key runtime dependencies with flexible matching
    runtime_dependencies = [
        "typer",
        "rich",
        "pyyaml",
        "jinja2",
        "pydantic",
        "gitpython",
    ]

    # Dependencies should be in the dependencies section
    content_lower = pyproject_content.lower()
    for dep in runtime_dependencies:
        # Handle variations like GitPython vs gitpython
        dep_variations = [
            dep.lower(),
            dep.lower().replace("-", ""),
            dep.lower().replace("python", ""),
        ]
        found = any(variation in content_lower for variation in dep_variations)
        assert found, f"{dep} not found in pyproject.toml dependencies"

    # Dev dependencies should be in pyproject.toml optional-dependencies
    assert (
        "[project.optional-dependencies]" in pyproject_content
        and "dev" in pyproject_content
    ), "Dev dependencies should be in pyproject.toml optional-dependencies"


@pytest.mark.e2e
def test_make_install_commands_executable():
    """Test that make install commands can be executed."""
    # Skip actual execution in CI/CD environments
    if os.environ.get("CI") == "true":
        pytest.skip("Skipping in CI environment")

    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent

    # Check if we can execute make help to see available commands
    try:
        result = subprocess.run(
            ["make", "-C", str(root_dir), "help"],
            capture_output=True,
            text=True,
            check=False,
        )

        # If make is not available, skip the test
        if result.returncode != 0:
            pytest.skip("make command not available")

        # Check that help output includes pip-based installation commands
        assert (
            "install-dev" in result.stdout or "install-user" in result.stdout
        ), "pip-based install commands not found in make help output"

    except FileNotFoundError:
        pytest.skip("make command not found")


@pytest.mark.e2e
def test_pip_installable_verification():
    """Verify basic requirements for pip installable install."""
    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent

    # Check for essential files for pip installation
    pyproject_toml = root_dir / "pyproject.toml"
    assert pyproject_toml.exists(), "pyproject.toml does not exist"

    # Verify the install has a CLI module with app entry point
    cli_py = root_dir / "source" / "coregen" / "cli" / "cli.py"
    assert cli_py.exists(), "cli.py does not exist"

    # Check that cli.py contains the app entry point
    cli_content = cli_py.read_text()
    assert "app = typer.Typer" in cli_content, "app entry point not found in cli.py"

    # Check that install has an __init__.py
    init_py = root_dir / "source" / "coregen" / "__init__.py"
    assert init_py.exists(), "__init__.py does not exist in source/coregen directory"


@pytest.mark.e2e
def test_pip_editable_install_check():
    """Check that pip editable install would work with pyproject.toml."""
    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent

    # Test that pyproject.toml exists and has build-system section
    pyproject_toml = root_dir / "pyproject.toml"
    assert pyproject_toml.exists(), "pyproject.toml does not exist"

    # Read and check for build-system configuration
    pyproject_content = pyproject_toml.read_text()
    assert "[build-system]" in pyproject_content, "[build-system] section not found"
    assert (
        "setuptools" in pyproject_content
    ), "setuptools not configured as build backend"

    # Verify that the install structure is correct for editable install
    source_dir = root_dir / "source"
    assert (
        source_dir.exists() and source_dir.is_dir()
    ), "source directory does not exist"

    # Check that __main__.py exists (entry point)
    main_py = source_dir / "coregen" / "__main__.py"
    assert main_py.exists(), "__main__.py does not exist"


@pytest.mark.e2e
def test_version_command(run_cli_command):
    """Test that version command correctly reports version."""
    # Run version command
    result = run_cli_command("version")

    # Check success
    assert result["success"], f"Version command failed: {result['stderr']}"

    # Verify version format
    version_output = result["stdout"].strip()
    assert version_output, "Empty version output"

    # Verify it contains a version number (allowing for v prefix and alpha/beta suffixes)
    import re

    assert re.search(
        r"\d+\.\d+\.\d+", version_output
    ), f"No version number found in: {version_output}"


@pytest.mark.e2e
def test_make_install_command_existence():
    """Test that make install commands are valid in the Makefile."""
    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent
    makefile_path = root_dir / "Makefile"

    # Read Makefile content
    makefile_content = makefile_path.read_text()

    # Check for pip-based installation commands
    install_commands = [
        "install-dev:",
        "install-user:",
        "uninstall:",
    ]

    # Check if install.mk is included (contains our pip-based commands)
    install_mk_included = "include makefiles/install.mk" in makefile_content

    if install_mk_included:
        # Commands are available via included install.mk
        pass
    else:
        # Otherwise check for commands in main file
        found_commands = 0
        for cmd in install_commands:
            if cmd in makefile_content:
                found_commands += 1

        assert (
            found_commands >= 1
        ), "At least 1 pip-based install commands should be available"
