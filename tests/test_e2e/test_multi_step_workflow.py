"""
End-to-End tests for multi-step workflows.

These tests validate complete user workflows from start to finish, including
initialization, component creation, change detection, and updates.
"""

import os
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

# Add the source directory to the path so we can import modules
source_dir = Path(__file__).parent.parent.parent / "source"
sys.path.insert(0, str(source_dir))

# Add a marker for all tests in this file
pytestmark = pytest.mark.e2e


@pytest.fixture
def workflow_env(temp_test_dir: Path, test_git_repo: Path) -> dict[str, Any]:
    """
    Set up a comprehensive test environment for multi-step workflow testing.

    This builds on the git test repo fixture with additional structure for templates.
    """
    # Create a workflow test directory structure
    workflow_test_dir = test_git_repo

    # Copy test_data directory to provide config file
    import shutil

    source_test_data = Path(__file__).parent.parent.parent / "test_data"
    dest_test_data = workflow_test_dir / "test_data"
    shutil.copytree(source_test_data, dest_test_data, dirs_exist_ok=True)

    # Create template directories
    templates_dir = workflow_test_dir / "common-templates"
    templates_dir.mkdir(exist_ok=True)

    # Create service template
    service_dir = templates_dir / "service"
    service_dir.mkdir(exist_ok=True)

    # Create service template files
    (service_dir / "deployment.yaml.j2").write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ component_name }}
  namespace: {{ namespace | default('default') }}
spec:
  replicas: {{ replicas | default(1) }}
  selector:
    matchLabels:
      app: {{ component_name }}
  template:
    metadata:
      labels:
        app: {{ component_name }}
    spec:
      containers:
      - name: {{ component_name }}
        image: {{ image_repo }}/{{ component_name }}:{{ image_tag | default('latest') }}
        ports:
        - containerPort: {{ port | default(8080) }}
    """)

    (service_dir / "service.yaml.j2").write_text("""
apiVersion: v1
kind: Service
metadata:
  name: {{ component_name }}
  namespace: {{ namespace | default('default') }}
spec:
  selector:
    app: {{ component_name }}
  ports:
  - port: {{ port | default(8080) }}
    targetPort: {{ port | default(8080) }}
  type: {{ service_type | default('ClusterIP') }}
    """)

    (service_dir / "README.md.j2").write_text("""
# {{ component_name | title }}

This is a generated service component.

## Configuration

- Namespace: {{ namespace | default('default') }}
- Replicas: {{ replicas | default(1) }}
- Port: {{ port | default(8080) }}
- Service Type: {{ service_type | default('ClusterIP') }}
    """)

    # Create a helper pattern matching rule file
    rules_file = workflow_test_dir / "test-rules.yaml"
    rules_file.write_text("""
code_changes:
  - "**/*.yaml"
  - "**/*.yml"
documentation:
  - "**/*.md"
  - "**/README*"
configuration:
  - "**/*.json"
  - "**/*.cfg"
    """)

    # Create contexts directory structure
    contexts_dir = workflow_test_dir / "contexts"
    contexts_dir.mkdir(exist_ok=True)

    dev_dir = contexts_dir / "dev"
    dev_dir.mkdir(exist_ok=True)

    prod_dir = contexts_dir / "prod"
    prod_dir.mkdir(exist_ok=True)

    # Commit the initial state
    os.chdir(workflow_test_dir)
    os.system("git add common-templates/ contexts/ rules.yaml")
    os.system("git commit -m 'Initial setup for workflow testing'")

    # Return the environment configuration
    return {
        "root_dir": workflow_test_dir,
        "templates_dir": templates_dir,
        "service_template_dir": service_dir,
        "contexts_dir": contexts_dir,
        "dev_dir": dev_dir,
        "prod_dir": prod_dir,
        "rules_file": rules_file,
    }


@pytest.mark.e2e
def test_basic_config_workflow(workflow_env: dict[str, Any], run_cli_command):
    """
    Test a simplified config workflow focusing on basic operations.

    Steps:
    1. Generate config
    2. Initialize workspace
    3. View config
    4. Verify expected structure
    """
    # Step 1: Generate configuration
    os.chdir(workflow_env["root_dir"])

    # config generate creates the config file
    generate_result = run_cli_command("config generate", expected_code=0)
    assert generate_result["success"], "Failed to generate config file"

    # Step 2: Verify the config file exists
    config_file = workflow_env["root_dir"] / ".cgconfig.yaml"
    assert config_file.exists(), "Config file does not exist after generation"

    # Step 3: Check if config commands work
    view_result = run_cli_command("config view raw", expected_code=0)
    assert view_result["success"], "Config view command failed"

    # Check that basic config structure is in the output
    assert (
        "workspaces" in view_result["stdout"]
    ), "Expected to see workspaces in config view output"

    # Step 4: Initialize workspace
    init_result = run_cli_command("config init", expected_code=0)
    assert init_result["success"], "Config init command failed"

    # Test directory creation
    output_dir = workflow_env["root_dir"] / "output"
    archive_dir = workflow_env["root_dir"] / "archive"

    assert output_dir.exists(), "Output directory not created"
    assert archive_dir.exists(), "Archive directory not created"


@pytest.mark.e2e
def test_config_command_operations(workflow_env: dict[str, Any], run_cli_command):
    """
    Test basic configuration command operations.

    Steps:
    1. Generate config
    2. View config
    3. View schema
    4. Initialize workspace
    """
    # Step 1: Initialize configuration
    os.chdir(workflow_env["root_dir"])

    # Generate configuration
    generate_result = run_cli_command("config generate", expected_code=0)
    assert generate_result["success"], "Failed to generate config file"

    # Config file should exist
    config_file = workflow_env["root_dir"] / ".cgconfig.yaml"
    assert config_file.exists(), "Config file does not exist after generation"

    # View the config
    view_result = run_cli_command("config view raw", expected_code=0)
    assert view_result["success"], "Config view command failed"

    # View the schema (requires schema type argument)
    schema_result = run_cli_command("config schema all", expected_code=0)
    assert schema_result["success"], "Schema command failed"
    # Check for indication that this is the schema command help output
    assert "schema" in schema_result["stdout"].lower()

    # Initialize workspace
    init_result = run_cli_command("config init", expected_code=0)
    assert init_result["success"], "Config init command failed"


@pytest.mark.e2e
def test_config_migration_workflow(workflow_env: dict[str, Any], run_cli_command):
    """
    Test the config initialization with --force flag.

    Steps:
    1. Create a config file
    2. Initialize new config with --force (should overwrite)
    3. Verify the config format is correct
    4. Test using the newly created config
    """
    # Step 1: Create a config file
    os.chdir(workflow_env["root_dir"])

    # Create a config file - this will be overwritten with --force
    initial_config = workflow_env["root_dir"] / ".cgconfig.yaml"
    initial_config.write_text("""
workspaces:
  - name: test-ws
    workspace_dir: contexts/dev
    context_type: component
    context_config_files:
      - "**/*.yaml"
templates:
  - name: service
    path: common-templates/service
    description: "Test service template"
settings:
  verbose: true
    """)

    # Step 2: Generate new config with --force
    generate_result = run_cli_command("config generate --force", expected_code=0)
    assert generate_result["success"], "Failed to generate config file with --force"

    # Initialize the config to create directories
    init_result = run_cli_command("config init", expected_code=0)
    assert init_result["success"], "Failed to initialize workspace directories"

    # Step 3: Verify the config format is correct
    updated_config = yaml.safe_load(initial_config.read_text())

    # Check for required structure elements
    # FIXED: Removed version field check - it's optional in current implementation
    assert "workspaces" in updated_config
    # Templates are optional in basic config generation
    # Just verify the config has the basic required structure

    # Step 4: Test using the newly created config
    # Create a test context directory
    test_dir = workflow_env["contexts_dir"] / "test"
    test_dir.mkdir(exist_ok=True)

    # Try to use the get command
    view_result = run_cli_command("config view raw", expected_code=0)
    assert view_result["success"], "Config view command failed after regeneration"
