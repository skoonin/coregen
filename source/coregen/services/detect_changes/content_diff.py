"""Content comparison helpers for detect-changes.

Pure functions for deciding whether two generated files differ. Comparison
ignores formatting noise: JSON/YAML files are canonicalized by parse-and-
re-serialize, other text is normalized by stripping comments and collapsing
whitespace, and binary files are compared byte-for-byte.

These functions hold no service state. The module logger is used only for
diagnostic output; behavior never depends on it.
"""

import fnmatch
import json
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Files that don't affect functionality and shouldn't trigger deployments.
IGNORE_PATTERNS = [
    ".DS_Store",
    ".gitkeep",
    "*.swp",
    "*.swo",
    "*~",
    ".#*",
    "#*#",
    "Thumbs.db",
    "desktop.ini",
    "*.md",
    "*.log",
]


def is_binary(path: Path) -> bool:
    """Check if a file appears to be binary.

    Args:
        path: Path to file to check

    Returns:
        True if file appears to be binary
    """
    try:
        with open(path, "rb") as f:
            chunk = f.read(4096)
            return b"\0" in chunk
    except Exception:
        return False


def files_differ(file1: Path, file2: Path) -> bool:
    """Compare two files ignoring whitespace and comments.

    Comment syntaxes handled:
    - Python/Hash (#)
    - C/C++ (// and /* */)
    - Shell (## and #)
    - HTML/XML (<!-- -->)

    Args:
        file1: First file path
        file2: Second file path

    Returns:
        True if files are different (content has changed)
    """
    try:
        # Check if files are binary
        if is_binary(file1) or is_binary(file2):
            # For binary files, compare bytes directly
            return file1.read_bytes() != file2.read_bytes()

        # For text files, normalize and compare (pass file path for type detection)
        content1 = normalize_content(file1.read_text(), file1)
        content2 = normalize_content(file2.read_text(), file2)
        return content1 != content2
    except Exception as e:
        logger.warning(f"Error comparing files {file1} and {file2}: {e}")
        # If we can't compare, assume they're different
        return True


def normalize_content(content: str, file_path: Path | None = None) -> str:
    """Normalize content for comparison.

    For JSON/YAML files, parses and re-serializes to eliminate formatting
    differences. For other files, removes comments and normalizes whitespace.

    Args:
        content: File content to normalize
        file_path: Optional file path to determine file type

    Returns:
        Normalized content
    """
    structured = _normalize_structured(content, file_path)
    if structured is not None:
        return structured
    return _normalize_text(content, file_path)


def _normalize_structured(content: str, file_path: Path | None) -> str | None:
    """Canonicalize JSON/YAML content by parse-and-re-serialize.

    Returns the canonical form, or None when the file is not JSON/YAML or
    parsing fails (caller falls back to text normalization).

    Args:
        content: File content to normalize
        file_path: File path used to detect JSON/YAML by suffix

    Returns:
        Canonical content string, or None to fall through to text handling
    """
    if not file_path:
        return None

    suffix = file_path.suffix.lower()

    # Handle JSON files - parse and re-serialize with sorted keys
    if suffix == ".json":
        try:
            data = json.loads(content)
            # Re-serialize with sorted keys and consistent formatting
            return json.dumps(data, sort_keys=True, indent=2)
        except (json.JSONDecodeError, ValueError):
            # If parsing fails, fall through to normal processing
            logger.debug(
                f"Failed to parse {file_path} as JSON, using text normalization"
            )

    # Handle YAML files - parse and re-serialize canonically
    elif suffix in [".yaml", ".yml"]:
        try:
            data = yaml.safe_load(content)
            # Re-serialize with consistent formatting
            return yaml.dump(data, default_flow_style=False, sort_keys=True)
        except yaml.YAMLError:
            # If parsing fails, fall through to normal processing
            logger.debug(
                f"Failed to parse {file_path} as YAML, using text normalization"
            )

    return None


def _normalize_text(content: str, file_path: Path | None = None) -> str:
    """Normalize free-form text by stripping comments and whitespace.

    Handles Python/Hash, C/C++, shell, and HTML/XML comment syntaxes, plus
    YAML inline comments when file_path identifies a YAML file.

    Args:
        content: File content to normalize
        file_path: Optional file path; enables YAML inline-comment stripping

    Returns:
        Normalized content
    """
    lines = []
    in_multiline_comment = False

    for line in content.splitlines():
        # Strip trailing whitespace but preserve indentation for now
        line = line.rstrip()

        # Skip empty lines
        if not line or line.isspace():
            continue

        # Handle C-style multi-line comments more carefully
        if in_multiline_comment:
            # Check if comment ends on this line
            if "*/" in line:
                in_multiline_comment = False
                # Keep the part after the comment ends
                _, _, after = line.partition("*/")
                line = after.strip()
                if not line:
                    continue
            else:
                # Still in multiline comment, skip entire line
                continue

        # Check for multiline comment start
        if "/*" in line:
            # Handle single-line /* ... */ comments
            if "*/" in line:
                # Remove just the comment part, keep rest of line
                before, _, rest = line.partition("/*")
                _, _, after = rest.partition("*/")
                line = before + after
                line = line.strip()
                if not line:
                    continue
            else:
                # Comment continues to next line
                in_multiline_comment = True
                # Keep the part before the comment
                before, _, _ = line.partition("/*")
                line = before.strip()
                if not line:
                    continue

        # Strip inline comments for YAML files (but not inside quoted strings)
        # This handles comments like "key: value # comment"
        if file_path and file_path.suffix.lower() in [".yaml", ".yml"]:
            # Simple approach: if line contains # not inside quotes, remove from
            # # onward
            if "#" in line:
                # Check if # is inside quotes (simple check)
                in_single_quote = False
                in_double_quote = False
                for i, char in enumerate(line):
                    if char == "'" and (i == 0 or line[i - 1] != "\\"):
                        in_single_quote = not in_single_quote
                    elif char == '"' and (i == 0 or line[i - 1] != "\\"):
                        in_double_quote = not in_double_quote
                    elif char == "#" and not in_single_quote and not in_double_quote:
                        # Found a comment outside quotes
                        line = line[:i].rstrip()
                        break

        # Handle line-starting comments
        line_stripped = line.lstrip()
        if line_stripped.startswith("#") or line_stripped.startswith("//"):
            continue

        # HTML/XML comments (simple handling)
        if line_stripped.startswith("<!--") and line_stripped.endswith("-->"):
            continue

        # Normalize remaining whitespace
        line = " ".join(line.split())

        # Add normalized line
        if line:
            lines.append(line)

    return "\n".join(lines)


def filter_ignored_files(file_paths: set[str]) -> set[str]:
    """Filter out files that match ignore patterns.

    Args:
        file_paths: Set of file paths to filter

    Returns:
        Filtered set of file paths with ignored files removed
    """
    filtered = set()
    for file_path in file_paths:
        file_name = Path(file_path).name

        # Check if file matches any ignore pattern
        should_ignore = False
        for pattern in IGNORE_PATTERNS:
            if fnmatch.fnmatch(file_name, pattern):
                should_ignore = True
                logger.debug(f"Ignoring file {file_path} (matches pattern {pattern})")
                break

        if not should_ignore:
            filtered.add(file_path)

    return filtered
