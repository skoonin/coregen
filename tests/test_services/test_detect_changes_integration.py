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

# Subprocess-driven integration tests: real git repos, real CLI runs.
pytestmark = pytest.mark.integration
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


def run_detect_changes(
    repo_path,
    base_branch,
    include_required_changes=False,
    filters=None,
    output_dir=None,
    keep_generated=False,
):
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
    for expression in filters or []:
        cmd.extend(["--filter", expression])
    if output_dir is not None:
        cmd.extend(["--output-dir", str(output_dir)])
    if keep_generated:
        cmd.append("--keep-generated")

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


def _commit_all(repo_path, message):
    """Stage every change and commit it with the given message."""
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )


def stage_required_prometheus_change(repo_path):
    """Mark context-dev's prometheus as required and trigger a real change.

    Mirrors the mechanism of the existing cascade tests: marking a component
    required in cgvalues and then adding a file under its template source so the
    generated output differs against the base branch. After two commits the
    triggering state is reachable at HEAD~2.
    """
    cgvalues_file = repo_path / "contexts" / "context-dev" / "context-dev-cgvalues.yaml"
    cgvalues = yaml.safe_load(cgvalues_file.read_text())
    for component in cgvalues["context"]["app"]:
        if component["name"] == "prometheus":
            component["config"]["required"] = True
            break
    cgvalues_file.write_text(yaml.dump(cgvalues, sort_keys=False))
    _commit_all(repo_path, "Mark prometheus as required")

    prometheus_dir = repo_path / "common-templates" / "prometheus"
    (prometheus_dir / "integration-change.txt").write_text("Triggering change\n")
    _commit_all(repo_path, "Change prometheus template source")


@pytest.mark.integration
class TestDetectChangesKeepGenerated:
    """Behavior tests for --keep-generated cleanup semantics (audit N6).

    Contract observed in DetectChangesService.detect_changes: the cleanup branch
    runs only when keep_generated is False AND output_dir is None. A custom
    output_dir therefore always persists; the default timestamped .cgtmp tree is
    removed only on a default run and survives when keep_generated is set.
    """

    def test_keep_generated_with_custom_output_dir_persists_files(
        self, temp_coregen_repo, tmp_path
    ):
        """keep_generated + a custom output_dir leaves the comparison files behind."""
        repo_path = temp_coregen_repo
        modify_component(
            repo_path, "context-dev", "nginx", {"main.tf": "# keep-generated test\n"}
        )
        _commit_all(repo_path, "Update nginx main.tf")

        output_dir = tmp_path / "kept-output"
        result = run_detect_changes(
            repo_path,
            "HEAD~1",
            output_dir=output_dir,
            keep_generated=True,
        )

        assert "changes" in result
        # The service renders the current branch, the extracted base branch, and
        # the base-branch generation into named subdirectories under output_dir.
        assert (output_dir / "current").is_dir()
        assert (output_dir / "base").is_dir()
        assert (output_dir / "base_extracted").is_dir()
        # Rendered comparison output must remain readable after the call returns.
        assert any(output_dir.rglob("*.tf"))

    def test_keep_generated_without_output_dir_persists_temp_tree(
        self, temp_coregen_repo
    ):
        """keep_generated alone leaves the default .cgtmp tree in place."""
        repo_path = temp_coregen_repo
        modify_component(
            repo_path, "context-dev", "nginx", {"main.tf": "# keep tmp test\n"}
        )
        _commit_all(repo_path, "Update nginx main.tf")

        run_detect_changes(repo_path, "HEAD~1", keep_generated=True)

        cgtmp_dir = repo_path / ".cgtmp"
        assert cgtmp_dir.is_dir()
        # A timestamped detect-changes run directory must survive under .cgtmp.
        assert any(cgtmp_dir.glob("detect-changes-*"))

    def test_default_run_cleans_up_temp_tree(self, temp_coregen_repo):
        """Without keep_generated and without output_dir, .cgtmp is removed."""
        repo_path = temp_coregen_repo
        modify_component(
            repo_path, "context-dev", "nginx", {"main.tf": "# default cleanup test\n"}
        )
        _commit_all(repo_path, "Update nginx main.tf")

        run_detect_changes(repo_path, "HEAD~1")

        # The empty .cgtmp parent is also removed once its run directory is gone.
        assert not (repo_path / ".cgtmp").exists()


@pytest.mark.integration
class TestDetectChangesCascadeFilterSurvival:
    """Required-cascade behavior under a != filter, against the real filter (N8).

    CLAUDE.md documents that required-cascade components "cannot be filtered out"
    with !=. The existing filtering unit tests mock FilterService entirely, so
    the invariant was never exercised end-to-end. These tests run the real filter
    with no mocking. _apply_filters_to_results retains any change whose reason is
    required_cascade regardless of the filter, enforcing the invariant.
    """

    def test_cascade_present_before_filtering(self, temp_coregen_repo):
        """Baseline: marking a required component produces a required_cascade entry.

        This proves the cascade fixture is set up correctly and is the precondition
        for the survival check below.
        """
        repo_path = temp_coregen_repo
        stage_required_prometheus_change(repo_path)

        unfiltered = run_detect_changes(
            repo_path, "HEAD~2", include_required_changes=True
        )
        cascade_nginx = next(
            (
                c
                for c in unfiltered["changes"]
                if c["component_name"] == "nginx"
                and c["context_name"] == "context-dev"
                and c["reason"] == "required_cascade"
            ),
            None,
        )
        assert (
            cascade_nginx is not None
        ), "Expected context-dev nginx to appear via required_cascade"

    def test_required_cascade_component_survives_not_equal_filter(
        self, temp_coregen_repo
    ):
        """A cascaded component is retained even when a != filter names it."""
        repo_path = temp_coregen_repo
        stage_required_prometheus_change(repo_path)

        filtered = run_detect_changes(
            repo_path,
            "HEAD~2",
            include_required_changes=True,
            filters=["component.name!=nginx"],
        )
        surviving = next(
            (
                c
                for c in filtered["changes"]
                if c["component_name"] == "nginx"
                and c["context_name"] == "context-dev"
                and c["reason"] == "required_cascade"
            ),
            None,
        )
        assert (
            surviving is not None
        ), "Required-cascade component was filtered out by != (invariant violated)"
