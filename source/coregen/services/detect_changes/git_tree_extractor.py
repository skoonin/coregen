"""Git validation and base-branch extraction for detect-changes.

A single ``GitTreeExtractor`` owns the cached GitPython ``Repo`` object for one
detect_changes() run. It spans two phases:

- ``validate(base_branch)`` confirms the working directory is a git repository,
  resolves the base ref (falling back to ``origin/main`` when ``main`` is
  absent), and returns ``(repo_root, actual_ref)``.
- ``extract(ref, dest_dir)`` streams ``git archive`` into a path-traversal-safe
  tar extraction under ``dest_dir``.

The cached ``Repo`` holds file handles and can spawn subprocesses, so the
extractor is closeable and supports the context-manager protocol. Callers MUST
close it (directly or via ``with``) to release those handles.
"""

import subprocess
import tarfile
from pathlib import Path
from types import TracebackType
from typing import Any

from git import Repo
from git.exc import BadName, GitCommandError, GitError, InvalidGitRepositoryError


class GitTreeExtractor:
    """Owns the cached git repository for one detect-changes run.

    Args:
        logger: Logger used for diagnostic output, shared with the service.
    """

    def __init__(self, logger: Any) -> None:
        """Initialize with a shared logger; the Repo handle is created lazily."""
        self.logger = logger
        self._repo: Repo | None = None

    def __enter__(self) -> "GitTreeExtractor":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Release the cached repository's file handles and subprocesses.

        GitPython ``Repo`` objects hold OS resources that are otherwise only
        reclaimed at garbage-collection time; closing makes that deterministic.
        """
        if self._repo is not None:
            self._repo.close()
            self._repo = None

    def validate(self, base_branch: str) -> tuple[Path, str]:
        """Validate git repository state and resolve the base ref.

        Args:
            base_branch: Base branch to validate

        Returns:
            Tuple of (repository root path, actual base ref to use)

        Raises:
            ValueError: If validation fails
        """
        repo = self._get_repo()
        if not repo:
            raise ValueError(
                "Not in a git repository. The detect-changes command must be "
                "run from within a git repository."
            )

        repo_root = Path(repo.working_dir)

        # Note: git archive has been available since git 1.4.3, so no version
        # check needed. It's much more widely available than worktree (2.5+).

        # Validate base ref exists and is accessible
        actual_base_ref = base_branch
        if not self._ref_exists(base_branch):
            # Try origin/main as fallback if main doesn't exist
            if base_branch == "main" and self._ref_exists("origin/main"):
                actual_base_ref = "origin/main"
                self.logger.info(
                    f"Using '{actual_base_ref}' as base branch since 'main' "
                    "doesn't exist locally"
                )
            else:
                raise ValueError(
                    f"Base ref '{base_branch}' does not exist or is not " "accessible."
                )

        self.logger.debug(
            f"Git repository validation successful: repo_root={repo_root}, "
            f"base_branch={actual_base_ref}"
        )

        return repo_root, actual_base_ref

    def extract(self, ref: str, dest_dir: Path, verbose: bool = False) -> None:
        """Extract base branch files using git archive.

        Args:
            ref: Base ref to extract
            dest_dir: Directory to extract files to
            verbose: Show detailed progress

        Raises:
            RuntimeError: If extraction fails
        """
        if verbose:
            self.logger.debug(f"Extracting files from ref '{ref}' to {dest_dir}")

        # Create output directory
        dest_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Use cached repository instance
            repo = self._get_repo()

            # Stream git archive directly to tar extraction (no temp file)
            proc = subprocess.Popen(
                ["git", "archive", ref],
                cwd=repo.working_dir if repo else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            try:
                # Open tar stream and safely extract
                # Note: mode="r|" for streaming tar without seeking
                with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
                    self._safe_extract(tar, dest_dir)

                # Wait for git archive to complete and check return code
                stderr = proc.stderr.read() if proc.stderr else b""
                rc = proc.wait()

                if rc != 0:
                    error_msg = (
                        stderr.decode("utf-8", errors="replace")
                        if stderr
                        else "Unknown error"
                    )
                    raise RuntimeError(
                        f"git archive failed with exit code {rc}: {error_msg}"
                    )

                if stderr and verbose:
                    self.logger.debug(
                        "Git archive stderr: "
                        f"{stderr.decode('utf-8', errors='replace')}"
                    )

                self.logger.debug(f"Successfully extracted {ref} to {dest_dir}")

            except Exception:
                # Kill the process if it's still running
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                raise

        except subprocess.SubprocessError as e:
            self.logger.error(f"Failed to extract base branch: {e}")
            raise RuntimeError(f"Failed to extract files from ref '{ref}': {e}") from e
        except Exception as e:
            self.logger.error(f"Failed to extract base branch: {e}")
            raise RuntimeError(f"Failed to extract files from ref '{ref}': {e}") from e

    def _safe_extract(self, tar: tarfile.TarFile, path: Path) -> None:
        """Safely extract tar members, preventing path traversal attacks.

        Args:
            tar: TarFile object to extract from
            path: Destination path

        Raises:
            RuntimeError: If unsafe paths are detected
        """
        base = path.resolve()

        for member in tar:
            member_path = (path / member.name).resolve()
            # Structural containment, not string prefix: startswith() treats a
            # sibling like "<base>_evil" as inside "<base>".
            if member_path != base and base not in member_path.parents:
                raise RuntimeError(f"Unsafe path in archive: {member.name}")
            if member.issym() or member.islnk():
                self.logger.warning(
                    f"Skipping symlink/hardlink in archive: {member.name}"
                )
                continue
            if not (member.isfile() or member.isdir()):
                self.logger.warning(
                    f"Skipping non-regular file in archive: {member.name}"
                )
                continue
            tar.extract(member, path)

    def _get_repo(self) -> Repo | None:
        """Get or create the git repository instance.

        This method implements lazy loading and caching of the repository
        object to avoid multiple lookups.

        Returns:
            Repo instance, or None if not in a git repository
        """
        if self._repo is None:
            try:
                self._repo = Repo(search_parent_directories=True)
            except InvalidGitRepositoryError:
                return None
            except GitError:
                return None
        return self._repo

    def _is_safe_git_ref(self, ref: str) -> bool:
        """Validate that a git ref is safe from injection attacks.

        The ref only ever reaches GitPython's repo.commit() and a list-args
        subprocess (never a shell), so the blocklist is stricter than the
        execution path requires. It is kept deliberately: the rejection set is
        the contract pinned by test_detect_changes_security.py, and it also
        excludes range/option-like inputs ('..', leading '-') that are not
        valid single refs for this tool. Loosening it needs product sign-off
        (audit finding DC6).

        Args:
            ref: Git ref to validate

        Returns:
            True if the ref appears safe
        """
        if not ref:
            return False

        # Check for dangerous patterns that could lead to command injection
        dangerous_patterns = [
            "..",  # Path traversal
            ";",  # Command separator
            "|",  # Pipe
            "&",  # Background/command chaining
            "`",  # Command substitution
            "$(",  # Command substitution
            "$((",  # Arithmetic substitution
            ">",  # Redirect output
            "<",  # Redirect input
            "\\",  # Escape character
            "\n",  # Newline
            "\r",  # Carriage return
            "\0",  # Null byte
            "--",  # Could be interpreted as option (except for legitimate use)
        ]

        # Check for dangerous patterns
        for pattern in dangerous_patterns:
            if pattern in ref:
                self.logger.warning(f"Unsafe git ref rejected: contains '{pattern}'")
                return False

        # Check if ref starts with dash (could be interpreted as option)
        if ref.startswith("-"):
            self.logger.warning("Unsafe git ref rejected: starts with '-'")
            return False

        # Additional check: ref should not contain control characters
        if any(ord(c) < 32 for c in ref):
            self.logger.warning("Unsafe git ref rejected: contains control characters")
            return False

        return True

    def _ref_exists(self, ref: str) -> bool:
        """Check if a git ref exists and is accessible.

        This handles local branches, remote branches (origin/main), tags, and
        SHAs.

        Args:
            ref: Git ref to check (branch, tag, SHA, etc.)

        Returns:
            True if ref exists and is accessible
        """
        try:
            # Validate ref name for security
            if not self._is_safe_git_ref(ref):
                return False

            repo = self._get_repo()
            if not repo:
                return False
            # This will raise if ref doesn't resolve
            _ = repo.commit(ref)
            return True
        except (BadName, ValueError):
            # Ref simply doesn't exist - expected
            return False
        except GitCommandError as e:
            self.logger.error(f"Git command failed checking ref '{ref}': {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error checking ref '{ref}': {e}")
            raise
