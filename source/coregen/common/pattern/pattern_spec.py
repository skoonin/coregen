"""Pattern specification models.

This module provides data models for pattern specifications in Coregen.
These specifications represent logical (workspace/context/component) patterns,
with proper structure for efficient pattern matching.
"""

from dataclasses import dataclass
from enum import Enum, auto


class PatternType(Enum):
    """Type of pattern being matched."""

    LOGICAL = auto()


class LogicalPrefixType(Enum):
    """Type of logical prefix for patterns."""

    WORKSPACE = auto()
    CONTEXT = auto()
    COMPONENT = auto()


@dataclass
class PatternToken:
    """Represents a token in a pattern string."""

    value: str
    is_wildcard: bool
    is_recursive: bool  # True for '**', False otherwise

    def __str__(self) -> str:
        """String representation of the token."""
        if self.is_recursive:
            return f"RecursiveToken({self.value})"
        elif self.is_wildcard:
            return f"WildcardToken({self.value})"
        return f"Token({self.value})"


@dataclass
class PatternSpec:
    """Base class for pattern specifications.

    This is a data model that holds parsed pattern information.
    The actual pattern matching logic is implemented in the Matcher classes
    (WorkspaceMatcher, ContextMatcher, ComponentMatcher) in the matchers module.
    """

    raw_pattern: str
    pattern_type: PatternType
    tokens: list[PatternToken]

    def __str__(self) -> str:
        """String representation of the pattern spec."""
        tokens_str = ", ".join(str(t) for t in self.tokens)
        return f"{self.__class__.__name__}('{self.raw_pattern}', tokens=[{tokens_str}])"


@dataclass
class LogicalPatternSpec(PatternSpec):
    """Specification for logical patterns (workspace/*, context/*, etc.).

    This is a data model that holds parsed logical pattern information.
    The actual matching is performed by the appropriate Matcher class.
    """

    prefix_type: LogicalPrefixType
    segments: list[str]  # ['aws', '*', 'component-name']

    def __str__(self) -> str:
        """String representation of the logical pattern spec."""
        base = super().__str__()
        return f"{base}, prefix={self.prefix_type}, segments={self.segments}"
