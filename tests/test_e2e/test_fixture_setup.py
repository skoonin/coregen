"""
E2E test fixture setup script.

This script sets up test fixtures for component templates and contexts.
"""

import shutil
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_create_test_templates(env_setup):
    """Test creating test templates for components."""
    # Test templates directory
    templates_dir = env_setup["templates_dir"]
    assert templates_dir.exists()

    # Verify metrics-server directory exists in templates
    metrics_server_dir = templates_dir / "metrics-server"
    assert metrics_server_dir.exists(), "metrics-server template directory not found"

    # Verify prometheus directory exists in templates
    prometheus_dir = templates_dir / "prometheus"
    assert prometheus_dir.exists(), "prometheus template directory not found"

    # Verify e2e-test-component directory exists or create it from existing templates
    e2e_template_dir = templates_dir / "e2e-test-component"
    e2e_template_dir.mkdir(exist_ok=True)

    # Use existing templates or copy from metrics-server if needed
    for template_file in [
        "README.md.j2",
        "deployment.yaml.j2",
        "kustomization.yaml.j2",
    ]:
        target_file = e2e_template_dir / template_file
        if not target_file.exists():
            # Copy template from metrics-server as a reference
            source_file = metrics_server_dir / template_file
            if source_file.exists():
                shutil.copy(source_file, target_file)

    # Verify key template files exist
    readme_template = e2e_template_dir / "README.md.j2"
    assert readme_template.exists()

    # Assert success rather than returning
    assert e2e_template_dir.exists()


@pytest.mark.e2e
def test_create_test_context(env_setup):
    """Test creating a test context for E2E testing."""
    import platform

    # Get contexts directory
    contexts_dir = env_setup["contexts_dir"]
    assert contexts_dir.exists()

    # Verify existing contexts
    context_dev_dir = contexts_dir / "context-dev"
    assert context_dev_dir.exists(), "context-dev context directory not found"

    # Create an E2E test context based on existing context structure
    e2e_context_dir = contexts_dir / "e2e-test"
    e2e_context_dir.mkdir(exist_ok=True)

    # Create values file
    values_file = e2e_context_dir / "e2e-test-cgvalues.yaml"
    if not values_file.exists():
        # Check for reference files but only try to read them on macOS
        reference_files = list(context_dev_dir.glob("*-cgvalues.yaml"))

        # Based on platform, handle file creation differently
        try:
            # Only try to read existing files on macOS and if this fails, fall back to creating a new file
            if platform.system().lower() == "darwin" and reference_files:
                try:
                    reference_content = reference_files[0].read_text()
                    # Update name and environment values
                    modified_content = reference_content.replace(
                        "name: context-dev", "name: e2e-test"
                    ).replace("environment: dev", "environment: e2e")
                    with open(values_file, "w") as f:
                        f.write(modified_content)
                except UnicodeDecodeError:
                    # Fall back to creating a new file
                    create_default_values_file(values_file)
            else:
                # On other platforms or if there are no reference files, just create a new file
                create_default_values_file(values_file)
        except Exception:
            # If any errors occur, fall back to creating a standard file
            create_default_values_file(values_file)

    # Verify file was created
    assert values_file.exists()
    assert e2e_context_dir.exists()


def create_default_values_file(values_file):
    """Create a default values file with standard content."""
    with open(values_file, "w") as f:
        f.write(
            """context:
  name: e2e-test
  environment: e2e
  active: true
  component_type: app

  app:
    - name: metrics-server
      config:
        active: true
        required: false
        generated: true
        dependencies: []
"""
        )


@pytest.mark.e2e
def test_create_test_component_dir(env_setup):
    """Test creating a directory for components in the test context."""
    # Get test context directory
    contexts_dir = env_setup["contexts_dir"]
    e2e_context_dir = contexts_dir / "e2e-test"

    # Create the context directory first if it doesn't exist
    e2e_context_dir.mkdir(exist_ok=True)

    # Verify existing component directories to use as references
    reference_component_dirs = []
    for ctx_dir in contexts_dir.iterdir():
        if ctx_dir.is_dir():
            for comp_dir in ctx_dir.iterdir():
                if comp_dir.is_dir() and comp_dir.name != "generated":
                    reference_component_dirs.append(comp_dir)

    # Create component directory
    component_dir = e2e_context_dir / "e2e-test-component"
    component_dir.mkdir(exist_ok=True)

    # Optionally copy some reference files if available
    if reference_component_dirs:
        for ref_file in reference_component_dirs[0].glob("*.yaml"):
            if not (component_dir / ref_file.name).exists():
                shutil.copy(ref_file, component_dir)

    # Verify directory was created
    assert component_dir.exists()


@pytest.fixture(scope="session")
def e2e_test_setup(request):
    """Set up all test fixtures for E2E testing."""
    # Create a temporary directory for tests
    test_dir = Path(request.config.cache.makedir("e2e_test_setup"))

    # Copy test data
    source_test_data = Path(__file__).parent.parent.parent / "test_data"
    dest_test_data = test_dir / "test_data"

    if dest_test_data.exists():
        shutil.rmtree(dest_test_data)

    shutil.copytree(source_test_data, dest_test_data)

    # Set up test context and templates
    contexts_dir = dest_test_data / "contexts"
    templates_dir = dest_test_data / "common-templates"

    # Verify our templates directory has the required components
    assert templates_dir.exists(), "Templates directory not found in test_data"

    # Get config file path
    config_path = dest_test_data / ".cgconfig.yaml"
    assert config_path.exists(), "Config file not found in test_data"

    # Create test context for e2e tests specifically
    e2e_context_dir = contexts_dir / "e2e-test"
    e2e_context_dir.mkdir(exist_ok=True)

    # Create values file based on existing contexts structure
    values_file = e2e_context_dir / "e2e-test-cgvalues.yaml"

    # Create a values file with standard content
    # This avoids encoding issues when reading existing files
    if not values_file.exists():
        # Try to read existing reference values files on macOS, but only if it's safe
        import platform

        reference_values_files = list(
            contexts_dir.glob("**/context-dev/*-cgvalues.yaml")
        )
        if platform.system().lower() == "darwin" and reference_values_files:
            try:
                # Try to use existing reference files on macOS
                reference_content = reference_values_files[0].read_text()
                # Update context properties for our e2e test
                modified_content = reference_content.replace(
                    "name: context-dev", "name: e2e-test"
                ).replace("environment: dev", "environment: e2e")
                with open(values_file, "w") as f:
                    f.write(modified_content)
            except UnicodeDecodeError:
                # Fall back to creating a new file
                create_default_values_file(values_file)
        else:
            # On other platforms or if no reference files found, create a default file
            create_default_values_file(values_file)

    # Create component directory
    component_dir = e2e_context_dir / "metrics-server"
    component_dir.mkdir(exist_ok=True)

    # Create e2e-test-component using metrics-server as template
    e2e_component_dir = e2e_context_dir / "e2e-test-component"
    e2e_component_dir.mkdir(exist_ok=True)

    # For our templates, let's use the existing ones from metrics-server
    e2e_template_dir = templates_dir / "e2e-test-component"
    if not e2e_template_dir.exists():
        # Create directory
        e2e_template_dir.mkdir(exist_ok=True)

        # Copy templates from metrics-server
        metrics_server_dir = templates_dir / "metrics-server"
        if metrics_server_dir.exists():
            for template_file in metrics_server_dir.glob("*.j2"):
                shutil.copy(template_file, e2e_template_dir)

    # Return all test paths
    return {
        "test_dir": test_dir,
        "test_data_dir": dest_test_data,
        "contexts_dir": contexts_dir,
        "templates_dir": templates_dir,
        "e2e_context_dir": e2e_context_dir,
        "e2e_template_dir": e2e_template_dir,
        "component_dir": component_dir,
        "values_file": values_file,
        "config_path": config_path,
    }
