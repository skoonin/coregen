"""Characterization (behavior-pinning) unit tests for DetectChangesService.

These tests pin CURRENT behavior of detect_changes_service.py internals so that
upcoming refactors have a safety net. They intentionally assert what the code
does today, including behavior that looks odd (noted inline) -- the source is
NOT modified here.

Tests that need real filesystem/path behavior carry @pytest.mark.integration so
they opt out of the autouse path-mocking fixture in conftest.py.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from coregen.services.detect_changes.detect_changes_service import (
    DetectChangesService,
)
from coregen.services.detect_changes.models import (
    ChangeReason,
    ChangeStatus,
    ComponentChange,
    DetectChangesResult,
)


@pytest.fixture
def service():
    """Construct a DetectChangesService cheaply with PathService patched out.

    Mirrors the fixture pattern in test_detect_changes_security.py.
    """
    with patch("coregen.services.detect_changes.detect_changes_service.PathService"):
        return DetectChangesService()


# ---------------------------------------------------------------------------
# A. _normalize_content characterization
# ---------------------------------------------------------------------------


class TestNormalizeContentJson:
    """Pin _normalize_content behavior for .json files."""

    def test_json_key_order_canonicalized(self, service):
        path = Path("config.json")
        a = service._normalize_content('{"b": 1, "a": 2}', path)
        b = service._normalize_content('{"a": 2, "b": 1}', path)
        assert a == b
        # Canonical form is json.dumps(sort_keys=True, indent=2)
        assert a == json.dumps({"a": 2, "b": 1}, sort_keys=True, indent=2)

    def test_json_nested_key_order_canonicalized(self, service):
        path = Path("config.json")
        a = service._normalize_content('{"x": {"q": 1, "p": 2}}', path)
        b = service._normalize_content('{"x": {"p": 2, "q": 1}}', path)
        assert a == b

    def test_invalid_json_falls_through_to_text(self, service):
        path = Path("config.json")
        # Not valid JSON -> text normalization. A full-line '#' comment is
        # stripped by the text path, proving it fell through.
        content = "# comment line\nnot json at all"
        result = service._normalize_content(content, path)
        assert "# comment line" not in result
        assert "not json at all" in result


class TestNormalizeContentYaml:
    """Pin _normalize_content behavior for .yaml/.yml files."""

    def test_yaml_reserialized_canonical(self, service):
        path = Path("config.yaml")
        a = service._normalize_content("b: 1\na: 2\n", path)
        b = service._normalize_content("a: 2\nb: 1\n", path)
        assert a == b
        assert a == yaml.dump(
            {"a": 2, "b": 1}, default_flow_style=False, sort_keys=True
        )

    def test_yml_suffix_also_handled(self, service):
        path = Path("config.yml")
        result = service._normalize_content("a: 1\nb: 2\n", path)
        assert result == yaml.dump(
            {"a": 1, "b": 2}, default_flow_style=False, sort_keys=True
        )

    def test_invalid_yaml_falls_to_text_path(self, service):
        path = Path("config.yaml")
        # A YAML mapping with a value that also opens a flow-sequence is invalid;
        # this raises yaml.YAMLError and falls to text normalization.
        content = "key: [unclosed\n# a comment"
        result = service._normalize_content(content, path)
        # Text path strips full-line '#' comments.
        assert "# a comment" not in result

    def test_yaml_quote_aware_hash_scanner_on_text_fallback(self, service):
        """When YAML parse fails, the text path runs the quote-aware '#' scanner.

        A '#' inside quotes is preserved; a '#' outside quotes is stripped from
        that point onward.
        """
        path = Path("config.yaml")
        # Force the YAML parser to fail (unclosed flow sequence on first line),
        # so subsequent lines go through the text-path quote-aware scanner.
        content = (
            "bad: [unclosed\n"
            'kept: "value # not a comment"\n'
            "stripped: value # trailing comment\n"
        )
        result = service._normalize_content(content, path)
        assert 'kept: "value # not a comment"' in result
        assert "stripped: value" in result
        assert "trailing comment" not in result


class TestNormalizeContentText:
    """Pin _normalize_content text-path behavior (non JSON/YAML files)."""

    def test_full_line_hash_comment_stripped(self, service):
        path = Path("script.txt")
        result = service._normalize_content("# comment\nreal line\n", path)
        assert result == "real line"

    def test_double_slash_comment_stripped(self, service):
        path = Path("code.txt")
        result = service._normalize_content("// comment\nkeep me\n", path)
        assert result == "keep me"

    def test_c_style_single_line_block_removed(self, service):
        path = Path("code.txt")
        result = service._normalize_content("before /* mid */ after\n", path)
        # Comment span removed; the resulting double space collapses to one via
        # the final " ".join(line.split()) whitespace normalization.
        assert result == "before after"

    def test_c_style_multiline_block_removed(self, service):
        path = Path("code.txt")
        content = "keep1\n/* start\nstill comment\nend */ tail\nkeep2\n"
        result = service._normalize_content(content, path)
        lines = result.split("\n")
        assert "keep1" in lines
        assert "tail" in lines
        assert "keep2" in lines
        assert "start" not in result
        assert "still comment" not in result

    def test_html_comment_full_line_stripped(self, service):
        path = Path("page.txt")
        result = service._normalize_content("<!-- comment -->\nkeep\n", path)
        assert result == "keep"

    def test_whitespace_normalized_and_blank_lines_dropped(self, service):
        path = Path("data.txt")
        # Internal runs of whitespace collapse to a single space; blank lines drop;
        # trailing whitespace stripped.
        content = "a    b\tc   \n\n   \n  d  \n"
        result = service._normalize_content(content, path)
        assert result == "a b c\nd"

    def test_no_file_path_uses_text_normalization(self, service):
        # With file_path=None the JSON/YAML branches are skipped entirely.
        result = service._normalize_content("# c\nkeep\n", None)
        assert result == "keep"

    def test_inline_hash_not_stripped_for_non_yaml(self, service):
        """For non-YAML text, inline (non-leading) '#' is NOT stripped.

        Only full-line leading '#'/'//' comments are removed; this pins the
        asymmetry between YAML and generic text handling.
        """
        path = Path("data.txt")
        result = service._normalize_content("value # inline\n", path)
        assert result == "value # inline"


# ---------------------------------------------------------------------------
# B. _is_binary
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIsBinary:
    def test_nul_byte_is_binary(self, service, tmp_path):
        p = tmp_path / "bin.dat"
        p.write_bytes(b"abc\x00def")
        assert service._is_binary(p) is True

    def test_utf8_text_not_binary(self, service, tmp_path):
        p = tmp_path / "text.txt"
        p.write_text("hello world\nsecond line\n")
        assert service._is_binary(p) is False

    def test_unreadable_path_returns_false(self, service, tmp_path):
        # Missing file -> open() raises -> documented fail behavior is False.
        assert service._is_binary(tmp_path / "does-not-exist") is False


# ---------------------------------------------------------------------------
# C. _compare_file_content (files-differ semantics; True == changed)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCompareFileContent:
    def test_identical_files_no_change(self, service, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("same\n")
        f2.write_text("same\n")
        # Returns True only when files differ; identical -> False.
        assert service._compare_file_content(f1, f2) is False

    def test_identical_after_normalization_no_change(self, service, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("# comment\nvalue\n")
        f2.write_text("value\n")
        assert service._compare_file_content(f1, f2) is False

    def test_differing_files_changed(self, service, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("one\n")
        f2.write_text("two\n")
        assert service._compare_file_content(f1, f2) is True

    def test_unreadable_file_failsafe_changed(self, service, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("data\n")
        f2.write_text("data\n")
        # Documented fail-safe: any error during comparison -> treated as changed.
        with patch.object(Path, "read_text", side_effect=OSError("boom")):
            assert service._compare_file_content(f1, f2) is True

    def test_binary_files_compared_by_bytes(self, service, tmp_path):
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"\x00\x01\x02")
        f2.write_bytes(b"\x00\x01\x03")
        assert service._compare_file_content(f1, f2) is True

    def test_identical_binary_files_no_change(self, service, tmp_path):
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"\x00\x01\x02")
        f2.write_bytes(b"\x00\x01\x02")
        assert service._compare_file_content(f1, f2) is False


# ---------------------------------------------------------------------------
# D. _filter_ignored_files
# ---------------------------------------------------------------------------


class TestFilterIgnoredFiles:
    def test_filters_each_pattern_class(self, service):
        survivors = service._filter_ignored_files(
            {"foo.md", "bar.log", "x.swp", "real.yaml"}
        )
        assert survivors == {"real.yaml"}

    def test_covers_full_ignore_pattern_list(self, service):
        # One representative per pattern in self._ignore_patterns.
        ignored = {
            ".DS_Store",
            ".gitkeep",
            "vim.swp",
            "vim.swo",
            "backup~",
            ".#lockfile",
            "#autosave#",
            "Thumbs.db",
            "desktop.ini",
            "README.md",
            "run.log",
        }
        assert service._filter_ignored_files(ignored) == set()

    def test_matches_basename_only(self, service):
        # Pattern match is on Path(...).name, so directory prefixes don't matter.
        result = service._filter_ignored_files({"dir/sub/notes.md", "dir/keep.yaml"})
        assert result == {"dir/keep.yaml"}


# ---------------------------------------------------------------------------
# E. Config discovery branches (real tmp dirs)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestConfigDiscovery:
    CONFIG_NAME = ".cgconfig.yaml"

    def test_find_for_current_branch_in_start_dir(self, service, tmp_path):
        (tmp_path / self.CONFIG_NAME).write_text("workspaces: {}\n")
        found = service._find_config_file_for_current_branch(tmp_path, tmp_path)
        assert found == tmp_path / self.CONFIG_NAME

    def test_find_for_current_branch_in_parent(self, service, tmp_path):
        repo_root = tmp_path
        (repo_root / self.CONFIG_NAME).write_text("workspaces: {}\n")
        start = repo_root / "a" / "b"
        start.mkdir(parents=True)
        found = service._find_config_file_for_current_branch(start, repo_root)
        assert found == repo_root / self.CONFIG_NAME

    def test_find_for_current_branch_none_when_absent(self, service, tmp_path):
        start = tmp_path / "a"
        start.mkdir()
        found = service._find_config_file_for_current_branch(start, tmp_path)
        assert found is None

    def test_find_default_config_uses_extracted_copy(self, service, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / self.CONFIG_NAME).write_text("workspaces: {}\n")
        start = repo_root / "x"
        start.mkdir()
        extracted = tmp_path / "extracted"
        extracted.mkdir()
        (extracted / self.CONFIG_NAME).write_text("workspaces: {}\n")

        found = service._find_default_config_file(start, repo_root, extracted)
        assert found == extracted / self.CONFIG_NAME

    def test_find_default_config_none_when_extracted_missing(self, service, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / self.CONFIG_NAME).write_text("workspaces: {}\n")
        extracted = tmp_path / "extracted"
        extracted.mkdir()
        # Config exists in repo_root but NOT in the extracted tree -> None.
        found = service._find_default_config_file(repo_root, repo_root, extracted)
        assert found is None

    def test_find_default_config_none_when_no_config(self, service, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        extracted = tmp_path / "extracted"
        extracted.mkdir()
        found = service._find_default_config_file(repo_root, repo_root, extracted)
        assert found is None


# ---------------------------------------------------------------------------
# H. Other cheap-to-test internals
# ---------------------------------------------------------------------------


class TestHasContentChangedMetadata:
    def test_active_flag_flip_is_change(self, service):
        current = {"metadata": {"active": False}, "files": []}
        base = {"metadata": {"active": True}, "files": []}
        assert (
            service._has_content_changed(
                "ws/ctx/comp",
                current,
                base,
                Path("/cur"),
                Path("/base"),
            )
            is True
        )

    def test_differing_file_lists_is_change(self, service):
        current = {"metadata": {"active": True}, "files": ["a.tf"]}
        base = {"metadata": {"active": True}, "files": ["b.tf"]}
        assert (
            service._has_content_changed(
                "ws/ctx/comp", current, base, Path("/cur"), Path("/base")
            )
            is True
        )

    def test_only_ignored_files_differ_is_not_change(self, service):
        # File lists differ only by ignored files (*.md, *.log) -> filtered to
        # equal empty sets -> no change, no filesystem access needed.
        current = {"metadata": {"active": True}, "files": ["notes.md"]}
        base = {"metadata": {"active": True}, "files": ["run.log"]}
        assert (
            service._has_content_changed(
                "ws/ctx/comp", current, base, Path("/cur"), Path("/base")
            )
            is False
        )


class TestCalculateStatistics:
    def test_counts_changed_deleted_contexts_workspaces(self, service):
        result = DetectChangesResult()
        result.changes = [
            ComponentChange(
                component_name="c1",
                context_name="ctx1",
                workspace_name="ws1",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
            ),
            ComponentChange(
                component_name="c2",
                context_name="ctx2",
                workspace_name="ws1",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
            ),
        ]
        result.deleted = [
            ComponentChange(
                component_name="d1",
                context_name="ctx3",
                workspace_name="ws2",
                status=ChangeStatus.DELETED,
                reason=ChangeReason.DELETED,
            )
        ]
        result.total_analyzed = 5

        out = service._calculate_statistics(result)
        assert out.total_changed == 2
        assert out.total_deleted == 1
        # Two distinct (ws,ctx) tuples among changes.
        assert out.total_contexts_affected == 2
        assert out.total_workspaces_affected == 1
        # total_unchanged = analyzed - (changed + deleted) = 5 - 3 = 2
        assert out.total_unchanged == 2

    def test_zero_analyzed_yields_zero_unchanged(self, service):
        result = DetectChangesResult()
        result.total_analyzed = 0
        out = service._calculate_statistics(result)
        assert out.total_unchanged == 0


class TestCreateComponentChange:
    def test_changed_component_builds_command_and_metadata(self, service):
        change = service._create_component_change(
            workspace="ws",
            context="ctx",
            component="comp",
            status=ChangeStatus.CHANGED,
            reason=ChangeReason.DIRECT,
            metadata={
                "active": True,
                "required": True,
                "priority": 3,
                "dependencies": ["dep1"],
                "path": "/some/path",
                "environment": "prod",
            },
        )
        assert change.command == (
            "cm/comp --filter workspace.name=ws --filter context.name=ctx"
        )
        assert change.component_active is True
        assert change.component_required is True
        assert change.component_priority == 3
        assert change.component_dependencies == ["dep1"]
        assert change.component_path == Path("/some/path")
        assert change.environment == "prod"

    def test_deleted_component_has_no_command_and_inactive(self, service):
        change = service._create_component_change(
            workspace="ws",
            context="ctx",
            component="comp",
            status=ChangeStatus.DELETED,
            reason=ChangeReason.DELETED,
            metadata={"active": True},
        )
        # Deleted components never get a command and are forced inactive.
        assert change.command is None
        assert change.component_active is False


class TestApplyRequiredCascade:
    def test_required_change_cascades_to_context_siblings(self, service):
        result = DetectChangesResult()
        # A required component that changed.
        result.changes = [
            ComponentChange(
                component_name="reqcomp",
                context_name="ctx",
                workspace_name="ws",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                component_required=True,
            )
        ]
        # Sibling component in the same context that did NOT change directly.
        current_components = {
            "ws/ctx/reqcomp": {"metadata": {"required": True}},
            "ws/ctx/sibling": {"metadata": {"active": True}},
            "ws/other/unrelated": {"metadata": {"active": True}},
        }

        # _create_component_change calls _get_context_config_file_path; stub it.
        service._get_context_config_file_path = MagicMock(return_value=None)

        out = service._apply_required_cascade(result, current_components, MagicMock())

        names = {
            (c.workspace_name, c.context_name, c.component_name) for c in out.changes
        }
        # Sibling in same context added via cascade.
        assert ("ws", "ctx", "sibling") in names
        # Unrelated context component NOT added.
        assert ("ws", "other", "unrelated") not in names
        # Cascade change carries the REQUIRED_CASCADE reason.
        cascade = next(c for c in out.changes if c.component_name == "sibling")
        assert cascade.reason == ChangeReason.REQUIRED_CASCADE
        # The required change is tracked in required_changes.
        assert any(c.component_name == "reqcomp" for c in out.required_changes)

    def test_no_required_changes_is_noop(self, service):
        result = DetectChangesResult()
        result.changes = [
            ComponentChange(
                component_name="comp",
                context_name="ctx",
                workspace_name="ws",
                status=ChangeStatus.CHANGED,
                reason=ChangeReason.DIRECT,
                component_required=False,
            )
        ]
        current_components = {"ws/ctx/sibling": {"metadata": {}}}
        out = service._apply_required_cascade(result, current_components, MagicMock())
        # No required change -> no cascade, original single change unchanged.
        assert len(out.changes) == 1
        assert out.required_changes == []


class TestCompareOutputs:
    """Pin _compare_outputs branch behavior with mocked context-path lookup."""

    def _generate_service(self):
        return MagicMock()

    def test_new_component_marked_changed(self, service):
        service._get_context_config_file_path = MagicMock(return_value=None)
        current = {"ws/ctx/comp": {"metadata": {"active": True}, "files": []}}
        base = {}
        result = service._compare_outputs(
            current, base, Path("/cur"), Path("/base"), self._generate_service()
        )
        assert len(result.changes) == 1
        assert result.changes[0].status == ChangeStatus.CHANGED
        assert result.changes[0].reason == ChangeReason.DIRECT
        assert result.deleted == []
        assert result.total_analyzed == 1

    def test_deleted_component_recorded_in_both_lists(self, service):
        service._get_context_config_file_path = MagicMock(return_value=None)
        current = {}
        base = {"ws/ctx/comp": {"metadata": {"active": True}, "files": []}}
        result = service._compare_outputs(
            current, base, Path("/cur"), Path("/base"), self._generate_service()
        )
        assert len(result.changes) == 1
        assert result.changes[0].status == ChangeStatus.DELETED
        # Deleted components appear in BOTH changes and deleted.
        assert len(result.deleted) == 1
        assert result.deleted[0].component_active is False

    def test_present_in_both_unchanged_yields_no_change(self, service):
        service._get_context_config_file_path = MagicMock(return_value=None)
        comp = {"metadata": {"active": True}, "files": []}
        current = {"ws/ctx/comp": comp}
        base = {"ws/ctx/comp": dict(comp)}
        result = service._compare_outputs(
            current, base, Path("/cur"), Path("/base"), self._generate_service()
        )
        # Identical metadata + empty file lists -> no change detected.
        assert result.changes == []
        assert result.total_analyzed == 1

    def test_present_in_both_changed_via_active_flip(self, service):
        service._get_context_config_file_path = MagicMock(return_value=None)
        current = {"ws/ctx/comp": {"metadata": {"active": False}, "files": []}}
        base = {"ws/ctx/comp": {"metadata": {"active": True}, "files": []}}
        result = service._compare_outputs(
            current, base, Path("/cur"), Path("/base"), self._generate_service()
        )
        assert len(result.changes) == 1
        assert result.changes[0].status == ChangeStatus.CHANGED

    def test_invalid_component_key_skipped_and_not_analyzed(self, service):
        service._get_context_config_file_path = MagicMock(return_value=None)
        # Key without the required 3 parts is skipped (not counted as analyzed).
        current = {"badkey": {"metadata": {}, "files": []}}
        base = {}
        result = service._compare_outputs(
            current, base, Path("/cur"), Path("/base"), self._generate_service()
        )
        assert result.changes == []
        assert result.total_analyzed == 0


class TestGetContextConfigFilePath:
    def test_returns_path_when_present(self, service):
        gen = MagicMock()
        ctx = MagicMock()
        ctx.config_file_path = "/cfg/.cgconfig.yaml"
        gen.config_access.get_context.return_value = ctx
        result = service._get_context_config_file_path("ws", "ctx", gen)
        assert result == Path("/cfg/.cgconfig.yaml")

    def test_returns_none_when_attribute_missing(self, service):
        gen = MagicMock()
        ctx = MagicMock(spec=[])  # no config_file_path attribute
        gen.config_access.get_context.return_value = ctx
        assert service._get_context_config_file_path("ws", "ctx", gen) is None

    def test_returns_none_on_lookup_error(self, service):
        gen = MagicMock()
        gen.config_access.get_context.side_effect = ValueError("nope")
        assert service._get_context_config_file_path("ws", "ctx", gen) is None


class TestGetWorkspaceForContext:
    def test_returns_context_workspace_field(self, service):
        gen = MagicMock()
        ws = MagicMock()
        ws.name = "ws-found-in"
        gen.config_access.workspaces = [ws]
        ctx = MagicMock()
        ctx.workspace = "ws-on-context"
        gen.config_access.get_context.return_value = ctx
        assert service._get_workspace_for_context("ctx", gen) == "ws-on-context"

    def test_falls_back_to_workspace_name_when_context_field_empty(self, service):
        gen = MagicMock()
        ws = MagicMock()
        ws.name = "ws-found-in"
        gen.config_access.workspaces = [ws]
        ctx = MagicMock()
        ctx.workspace = None
        gen.config_access.get_context.return_value = ctx
        assert service._get_workspace_for_context("ctx", gen) == "ws-found-in"

    def test_raises_when_context_not_in_any_workspace(self, service):
        gen = MagicMock()
        ws = MagicMock()
        ws.name = "ws"
        gen.config_access.workspaces = [ws]
        gen.config_access.get_context.side_effect = ValueError("missing")
        with pytest.raises(ValueError, match="not found in any workspace"):
            service._get_workspace_for_context("ctx", gen)


class TestRefExistsAndRepoHealth:
    def test_ref_exists_rejects_unsafe_ref_without_repo_call(self, service):
        # Unsafe refs are rejected before any git access.
        service._get_repo = MagicMock()
        assert service._ref_exists("main;rm -rf /") is False
        service._get_repo.assert_not_called()

    def test_ref_exists_true_when_commit_resolves(self, service):
        repo = MagicMock()
        repo.commit.return_value = MagicMock()
        service._get_repo = MagicMock(return_value=repo)
        assert service._ref_exists("main") is True
        repo.commit.assert_called_once_with("main")

    def test_ref_exists_false_when_no_repo(self, service):
        service._get_repo = MagicMock(return_value=None)
        assert service._ref_exists("main") is False

    def test_ref_exists_false_on_value_error(self, service):
        repo = MagicMock()
        repo.commit.side_effect = ValueError("bad name")
        service._get_repo = MagicMock(return_value=repo)
        assert service._ref_exists("nope") is False

    def test_check_repo_health_true_when_accessible(self, service):
        repo = MagicMock()
        repo.git_dir = "/repo/.git"
        repo.head.commit = MagicMock()
        service._get_repo = MagicMock(return_value=repo)
        assert service._check_repo_health() is True

    def test_check_repo_health_false_when_no_repo(self, service):
        service._get_repo = MagicMock(return_value=None)
        assert service._check_repo_health() is False

    def test_check_repo_health_false_on_attribute_error(self, service):
        class FakeRepo:
            git_dir = "/repo/.git"

            @property
            def head(self):
                # Reading repo.head.commit raises -> caught by the handler.
                raise AttributeError("no head")

        service._get_repo = MagicMock(return_value=FakeRepo())
        assert service._check_repo_health() is False
