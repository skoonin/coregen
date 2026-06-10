"""Pattern parser module.

This module provides functionality for parsing raw pattern strings into structured
pattern specifications that can be efficiently processed for matching.
"""

from .pattern_spec import (
    LogicalPatternSpec,
    LogicalPrefixType,
    PatternToken,
    PatternType,
)


class PatternParseError(ValueError):
    """Exception raised when pattern parsing fails with helpful context."""

    def __init__(
        self, message: str, pattern: str, suggestions: list[str] | None = None
    ):
        """Initialize pattern parse error.

        Args:
            message: Error message
            pattern: The pattern that failed to parse
            suggestions: Optional list of suggested alternatives
        """
        super().__init__(message)
        self.pattern = pattern
        self.suggestions = suggestions or []


# Define the recognized prefixes - logical patterns only
PATTERN_PREFIXES = {
    # Workspace patterns
    "w/": LogicalPrefixType.WORKSPACE,
    "workspace/": LogicalPrefixType.WORKSPACE,
    # Context patterns
    "c/": LogicalPrefixType.CONTEXT,
    "context/": LogicalPrefixType.CONTEXT,
    # Component patterns
    "cm/": LogicalPrefixType.COMPONENT,
    "component/": LogicalPrefixType.COMPONENT,
}


class PatternParser:
    """Parses raw pattern strings into PatternSpec objects."""

    def parse(self, pattern: str) -> LogicalPatternSpec:
        """Parse a raw pattern string into a PatternSpec.

        Args:
            pattern: The raw pattern string to parse

        Returns:
            A PatternSpec representing the parsed pattern

        Raises:
            ValueError: If the pattern is invalid or cannot be parsed
        """
        if not pattern:
            raise ValueError("Pattern cannot be empty")

        # Check for recognized prefixes
        for prefix, prefix_type in PATTERN_PREFIXES.items():
            if pattern.startswith(prefix):
                # Handle logical patterns - prefix_type is LogicalPrefixType here
                return self._parse_logical(pattern, prefix, prefix_type)

        # No recognized prefix - this is now an error since all patterns must have prefixes
        raise PatternParseError(
            f"Pattern must start with a recognized prefix. Got: '{pattern}'",
            pattern,
            suggestions=[
                "For workspace patterns: w/ or workspace/",
                "For context patterns: c/ or context/",
                "For component patterns: cm/ or component/",
            ],
        )

    def _parse_logical(
        self, pattern: str, prefix: str, prefix_type: LogicalPrefixType
    ) -> LogicalPatternSpec:
        """Parse a logical pattern (e.g., 'workspace/aws/**').

        Args:
            pattern: The full pattern string
            prefix: The logical prefix found in the pattern
            prefix_type: The type of logical prefix

        Returns:
            A LogicalPatternSpec representing the parsed pattern
        """
        # Remove prefix to get the rest of the pattern
        remaining = pattern[len(prefix) :]

        # Handle special case of combined patterns like "aws**" and split into proper segments
        # This helps with patterns like "context/aws**" which should match like "context/aws/**"
        modified_remaining = remaining
        if remaining and "**" in remaining and not remaining.endswith("/**"):
            # Handle case where ** is in middle or attached to name (e.g., "aws**")
            # But NOT when ** is at the start (e.g., "**" in "workspace/**")
            for i in range(len(remaining)):
                if (
                    remaining[i : i + 2] == "**"
                    and remaining[i - 1 : i] != "/"
                    and i > 0
                ):
                    # Insert a slash before ** to properly split segments
                    modified_remaining = remaining[:i] + "/" + remaining[i:]
                    break

        # Split the remaining pattern into segments
        segments = modified_remaining.split("/") if modified_remaining else []

        # Tokenize the full pattern (including the prefix)
        tokens = []
        # Add prefix token
        tokens.append(
            PatternToken(
                value=prefix.rstrip("/"), is_wildcard=False, is_recursive=False
            )
        )

        # Add segment tokens - using the original pattern to maintain raw pattern matching
        remaining_parts = modified_remaining.split("/") if modified_remaining else []
        for segment in remaining_parts:
            is_recursive = segment == "**"
            is_wildcard = "*" in segment or "?" in segment or "[" in segment
            tokens.append(
                PatternToken(
                    value=segment, is_wildcard=is_wildcard, is_recursive=is_recursive
                )
            )

        # Create logical pattern specification with processed segments
        pattern_spec = LogicalPatternSpec(
            raw_pattern=pattern,
            pattern_type=PatternType.LOGICAL,
            tokens=tokens,
            prefix_type=prefix_type,
            segments=segments,
        )

        # If we had to modify the pattern, update the raw pattern for consistency
        if modified_remaining != remaining:
            # Set the normalized pattern with inserted slash
            normalized_pattern = f"{prefix}{modified_remaining}"
            pattern_spec.raw_pattern = normalized_pattern

        return pattern_spec
