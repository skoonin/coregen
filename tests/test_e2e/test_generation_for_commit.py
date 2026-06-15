"""End-to-End tests for the for_commit x --skip-commit-dir matrix (audit N7).

The only commit-copy site is GenerateService (``if not skip_commit_dir and
...for_commit``). Existing tests only assert result-dict keys and flag
forwarding; these assert the observable effect: whether rendered files actually
land under the context's commit directory (default ``for-commit``).
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

pytestmark = pytest.mark.e2e


def _set_prometheus_for_commit(gen_test_env: dict[str, Any], value: bool) -> None:
    """Set context-dev prometheus's for_commit flag in its cgvalues file."""
    cgvalues_file = (
        gen_test_env["contexts_dir"] / "context-dev" / "context-dev-cgvalues.yaml"
    )
    cgvalues = yaml.safe_load(cgvalues_file.read_text())
    for component in cgvalues["context"]["app"]:
        if component["name"] == "prometheus":
            component["config"]["for_commit"] = value
            break
    cgvalues_file.write_text(yaml.dump(cgvalues, sort_keys=False))


def _commit_files(root_dir: Path) -> list[Path]:
    """Return rendered prometheus files found under any for-commit directory."""
    matches: list[Path] = []
    for path in Path(root_dir).rglob("for-commit/prometheus/*"):
        if path.is_file():
            matches.append(path)
    return matches


@pytest.mark.e2e
def test_for_commit_true_writes_commit_dir(
    gen_test_env: dict[str, Any], run_cli_command
):
    """for_commit: true and skip_commit_dir unset writes files to for-commit/."""
    _set_prometheus_for_commit(gen_test_env, True)
    os.chdir(gen_test_env["root_dir"])

    result = run_cli_command(
        f"generate context/context-dev component/prometheus "
        f"--config-file {gen_test_env['config_path']}",
        expected_code=0,
    )
    assert result["success"]

    assert _commit_files(
        gen_test_env["root_dir"]
    ), "for_commit: true should render files under for-commit/prometheus/"


@pytest.mark.e2e
def test_for_commit_true_with_skip_commit_dir_omits_commit_dir(
    gen_test_env: dict[str, Any], run_cli_command
):
    """--skip-commit-dir suppresses the commit-dir copy even when for_commit: true."""
    _set_prometheus_for_commit(gen_test_env, True)
    os.chdir(gen_test_env["root_dir"])

    result = run_cli_command(
        f"generate context/context-dev component/prometheus --skip-commit-dir "
        f"--config-file {gen_test_env['config_path']}",
        expected_code=0,
    )
    assert result["success"]

    assert not _commit_files(
        gen_test_env["root_dir"]
    ), "--skip-commit-dir must suppress the for-commit/ copy"


@pytest.mark.e2e
def test_for_commit_false_never_writes_commit_dir(
    gen_test_env: dict[str, Any], run_cli_command
):
    """for_commit: false produces no commit-dir copy regardless of the flag."""
    _set_prometheus_for_commit(gen_test_env, False)
    os.chdir(gen_test_env["root_dir"])

    result = run_cli_command(
        f"generate context/context-dev component/prometheus "
        f"--config-file {gen_test_env['config_path']}",
        expected_code=0,
    )
    assert result["success"]

    assert not _commit_files(
        gen_test_env["root_dir"]
    ), "for_commit: false must never write to for-commit/"
