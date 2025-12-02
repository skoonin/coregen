"""Integration tests for detect-changes command using isolated temp repos.

These tests use fixture-based temporary repositories with subprocess calls
to test the full CLI workflow that users experience.
"""

import json
import shutil
import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def temp_coregen_repo(tmp_path) -> Generator[Path, None, None]:
    """Create a temporary coregen repository by copying test_data.

    Copies the existing test_data directory to get a known-good structure,
    then initializes it as a git repo for testing.

    Returns path to the repo root.
    """
    # Find test_data directory relative to this test file
    test_file_dir = Path(__file__).parent.parent.parent
    test_data_src = test_file_dir / "test_data"

    if not test_data_src.exists():
        pytest.skip("test_data directory not found")

    # Copy test_data to temp location
    repo_path = tmp_path / "test_repo"
    shutil.copytree(test_data_src, repo_path)

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    # Create a second baseline commit to ensure HEAD~1 exists
    (repo_path / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add README"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    return repo_path


def create_component(repo_path, context_name, component_name, **config_overrides):
    """Create a component by adding it to cgvalues and creating component directory.

    Note: Adding to cgvalues alone won't trigger detect-changes. You must also
    create/modify files in the component directory to trigger detection.

    Works with test_data structure where contexts are in contexts/ directory.
    """
    contexts_dir = repo_path / "contexts"
    context_dir = contexts_dir / context_name

    # Read cgvalues file - try both naming patterns
    cgvalues_file = None
    for pattern in [f"{context_name}-cgvalues.yaml", "test-cgvalues.yaml"]:
        candidate = context_dir / pattern
        if candidate.exists():
            cgvalues_file = candidate
            break

    if not cgvalues_file:
        raise FileNotFoundError(f"No cgvalues file found in {context_dir}")

    cgvalues = yaml.safe_load(cgvalues_file.read_text())

    # Default config
    component_config = {
        "name": component_name,
        "config": {
            "active": True,
            "priority": None,
            "required": False,
        },
    }
    # Merge config_overrides into config dict
    if config_overrides:
        component_config["config"].update(config_overrides)

    # Add component to app list
    cgvalues["context"]["app"].append(component_config)

    # Write updated cgvalues - preserve key order
    cgvalues_file.write_text(yaml.dump(cgvalues, sort_keys=False))

    # Create component directory with a YAML file (not markdown - those are ignored)
    component_dir = context_dir / component_name
    component_dir.mkdir(parents=True, exist_ok=True)
    (component_dir / "config.yaml").write_text(
        yaml.dump({"version": "1.0"}, sort_keys=False)
    )


def modify_component(repo_path, context_name, component_name, file_change):
    """Modify a component's files to trigger detect-changes.

    Args:
        repo_path: Path to repo root
        context_name: Name of context (e.g., "context-dev")
        component_name: Name of component (e.g., "nginx", "prometheus")
        file_change: Dict with filename and content, e.g., {"main.tf": "# Updated"}

    Note: detect-changes only triggers on component file changes, NOT cgvalues changes.
    """
    contexts_dir = repo_path / "contexts"
    context_dir = contexts_dir / context_name
    component_dir = context_dir / component_name

    if not component_dir.exists():
        raise FileNotFoundError(f"Component directory not found: {component_dir}")

    # Modify or create the specified file in the component directory
    for filename, content in file_change.items():
        file_path = component_dir / filename
        file_path.write_text(content)


def run_detect_changes(repo_path, base_branch, include_required_changes=False):
    """Run detect-changes command and return parsed output."""
    # Try to use venv coregen, fall back to system PATH (for CI)
    venv_coregen = Path(__file__).parent.parent.parent / ".venv" / "bin" / "coregen"

    if venv_coregen.exists():
        coregen_cmd = str(venv_coregen)
    else:
        # In CI or other environments, use coregen from PATH
        coregen_cmd = "coregen"

    cmd = [
        coregen_cmd,
        "detect-changes",
        "--base-branch",
        base_branch,
        "--output",
        "json",
    ]
    if include_required_changes:
        cmd.append("--include-required-changes")

    # Run in repo_path where .cgconfig.yaml exists
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)

    # Check for errors
    if result.returncode != 0:
        raise RuntimeError(
            f"detect-changes command failed with exit code {result.returncode}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    # Handle empty output
    if not result.stdout or not result.stdout.strip():
        raise RuntimeError(
            f"detect-changes returned empty output\n"
            f"stderr: {result.stderr}\n"
            f"returncode: {result.returncode}"
        )

    return json.loads(result.stdout)


@pytest.mark.integration
class TestDetectChangesIntegration:
    """Integration tests using temporary repos with full CLI workflow."""

    def test_detects_component_file_change(self, temp_coregen_repo):
        """When a component file changes, detect-changes identifies it."""
        repo_path = temp_coregen_repo

        # Modify an actual file in nginx component (which exists in test_data)
        modify_component(
            repo_path, "context-dev", "nginx", {"main.tf": "# Updated main.tf\n"}
        )

        # Commit the change
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Update nginx main.tf"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Run detect-changes
        result = run_detect_changes(repo_path, "HEAD~1")

        # Assert component appears in changes
        assert "changes" in result
        assert len(result["changes"]) >= 1
        # Find nginx in the changes
        nginx_change = next(
            (c for c in result["changes"] if c["component_name"] == "nginx"), None
        )
        assert nginx_change is not None
        assert nginx_change["context_name"] == "context-dev"

    def test_required_component_appears_in_required_changes_when_flag_enabled(
        self, temp_coregen_repo
    ):
        """When a required component changes and flag is ON, it appears in required_changes."""
        repo_path = temp_coregen_repo

        # First, mark prometheus as required in the context config
        contexts_dir = repo_path / "contexts"
        dev_context_dir = contexts_dir / "context-dev"

        cgvalues_file = dev_context_dir / "context-dev-cgvalues.yaml"

        cgvalues = yaml.safe_load(cgvalues_file.read_text())

        # Find prometheus and mark it as required
        for comp in cgvalues["context"]["app"]:
            if comp["name"] == "prometheus":
                comp["config"]["required"] = True
                break

        cgvalues_file.write_text(yaml.dump(cgvalues, sort_keys=False))

        # Commit the metadata change
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Mark prometheus as required"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Now modify prometheus's actual files to trigger detection
        prometheus_dir = dev_context_dir / "../../common-templates/prometheus"
        test_file = prometheus_dir / "test-change.txt"
        test_file.write_text("Updated for testing\n")

        # Commit the file change
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Update prometheus files"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Run detect-changes WITH flag
        result = run_detect_changes(repo_path, "HEAD~2", include_required_changes=True)

        # Assert required_changes key exists
        assert "required_changes" in result

        # Assert component appears in changes array
        assert "changes" in result
        prometheus_change = next(
            (c for c in result["changes"] if c["component_name"] == "prometheus"), None
        )
        assert prometheus_change is not None

        # Prometheus should be in required_changes (this is the key indicator)
        req_prometheus = next(
            (
                c
                for c in result["required_changes"]
                if c["component_name"] == "prometheus"
            ),
            None,
        )
        assert req_prometheus is not None
        # The required_changes array proves the component triggered required cascade
        assert len(result["required_changes"]) >= 1

    def test_required_changes_excluded_by_default(self, temp_coregen_repo):
        """Without --include-required-changes, required_changes not in output."""
        repo_path = temp_coregen_repo

        # First, mark nginx as required in the context config
        contexts_dir = repo_path / "contexts"
        dev_context_dir = contexts_dir / "context-dev"

        cgvalues_file = dev_context_dir / "context-dev-cgvalues.yaml"

        cgvalues = yaml.safe_load(cgvalues_file.read_text())

        # Find nginx and mark it as required
        for comp in cgvalues["context"]["app"]:
            if comp["name"] == "nginx":
                comp["config"]["required"] = True
                break

        cgvalues_file.write_text(yaml.dump(cgvalues, sort_keys=False))

        # Commit the metadata change
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Mark nginx as required"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Now modify nginx's actual files to trigger detection
        modify_component(
            repo_path, "context-dev", "nginx", {"main.tf": "# Modified for test\n"}
        )

        # Commit the file change
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Update nginx files"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Run detect-changes WITHOUT flag
        result = run_detect_changes(repo_path, "HEAD~2", include_required_changes=False)

        # Assert required_changes key NOT in output
        assert "required_changes" not in result

        # Assert component still appears in changes array
        assert "changes" in result
        nginx_change = next(
            (c for c in result["changes"] if c["component_name"] == "nginx"), None
        )
        assert nginx_change is not None

    def test_dependent_of_required_component_gets_required_cascade_reason(
        self, temp_coregen_repo
    ):
        """When required component changes, ALL components in context get required_cascade reason."""
        repo_path = temp_coregen_repo

        # Mark prometheus as required in the context config
        contexts_dir = repo_path / "contexts"
        dev_context_dir = contexts_dir / "context-dev"

        cgvalues_file = dev_context_dir / "context-dev-cgvalues.yaml"

        cgvalues = yaml.safe_load(cgvalues_file.read_text())

        # Find prometheus and mark it as required
        for comp in cgvalues["context"]["app"]:
            if comp["name"] == "prometheus":
                comp["config"]["required"] = True
                break

        cgvalues_file.write_text(yaml.dump(cgvalues, sort_keys=False))

        # Commit the metadata change
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Mark prometheus as required"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Now modify prometheus's actual files to trigger detection
        prometheus_dir = dev_context_dir / "../../common-templates/prometheus"
        test_file = prometheus_dir / "cascade-test.txt"
        test_file.write_text("Cascade test\n")

        # Commit the file change
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Update prometheus files"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Run detect-changes WITH flag - compare against HEAD~2 (before required metadata and file change)
        result = run_detect_changes(repo_path, "HEAD~2", include_required_changes=True)

        # Assert all components in context appear (prometheus triggered cascade)
        assert "changes" in result
        # Should have prometheus (direct) + other components in context (required_cascade)
        assert len(result["changes"]) >= 2

        # Find prometheus in changes
        prometheus = next(
            (c for c in result["changes"] if c["component_name"] == "prometheus"), None
        )
        assert prometheus is not None

        # Prometheus should have direct reason (lowercase)
        assert prometheus["reason"] == "direct"

        # Find at least one other component with required_cascade (lowercase)
        cascade_components = [
            c for c in result["changes"] if c["reason"] == "required_cascade"
        ]
        assert len(cascade_components) >= 1

        # Both prometheus and cascade components should be in required_changes
        assert "required_changes" in result
        assert len(result["required_changes"]) >= 2

        # Verify context grouping in both arrays (changes and required_changes)
        for array_name in ["changes", "required_changes"]:
            if array_name in result and result[array_name]:
                contexts_seen = [
                    (c["workspace_name"], c["context_name"]) for c in result[array_name]
                ]
                unique_contexts_in_order = []
                for ctx in contexts_seen:
                    if (
                        not unique_contexts_in_order
                        or unique_contexts_in_order[-1] != ctx
                    ):
                        unique_contexts_in_order.append(ctx)

                # Each context should appear exactly once (no intermixing)
                assert len(unique_contexts_in_order) == len(
                    set(contexts_seen)
                ), f"Context grouping broken in {array_name}! Contexts: {contexts_seen}"

    def test_detects_changes_across_multiple_contexts(self, temp_coregen_repo):
        """Detects changes in multiple contexts simultaneously."""
        repo_path = temp_coregen_repo

        # Modify nginx in context-dev
        modify_component(
            repo_path, "context-dev", "nginx", {"main.tf": "# Multi-context test dev\n"}
        )

        # Modify nginx in context-prod (different path structure)
        contexts_dir = repo_path / "contexts"
        prod_nginx_dir = contexts_dir / "prod" / "context-prod" / "service" / "nginx"
        prod_nginx_file = prod_nginx_dir / "service.yaml"
        prod_nginx_file.write_text("# Multi-context test prod\n")

        # Commit changes
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Update nginx in both contexts"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Run detect-changes
        result = run_detect_changes(repo_path, "HEAD~1")

        # Assert changes detected in both contexts
        assert "changes" in result
        assert len(result["changes"]) == 2

        context_names = {c["context_name"] for c in result["changes"]}
        assert context_names == {"context-dev", "context-prod"}

        # Both should be nginx components
        component_names = {c["component_name"] for c in result["changes"]}
        assert component_names == {"nginx"}

        # Verify context grouping: components from same context appear together
        contexts_seen = [
            (c["workspace_name"], c["context_name"]) for c in result["changes"]
        ]
        unique_contexts_in_order = []
        for ctx in contexts_seen:
            if not unique_contexts_in_order or unique_contexts_in_order[-1] != ctx:
                unique_contexts_in_order.append(ctx)

        # Each context should appear exactly once (no intermixing)
        assert len(unique_contexts_in_order) == len(
            set(contexts_seen)
        ), f"Context grouping broken! Contexts not grouped together: {contexts_seen}"

    def test_no_changes_returns_message(self, temp_coregen_repo):
        """When no changes exist, returns appropriate message."""
        repo_path = temp_coregen_repo

        # Run detect-changes comparing HEAD to HEAD (no changes)
        result = run_detect_changes(repo_path, "HEAD")

        # Assert message field present
        assert "message" in result
        assert result["message"] == "No changes detected"
