"""Pattern matcher factory.

This module provides a factory class for creating appropriate matcher objects
based on pattern specifications.
"""

from pathlib import Path

from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.config_model.access import ConfigAccess

from .matchers import ComponentMatcher, ContextMatcher, Matcher, WorkspaceMatcher
from .pattern_parser import PatternParser
from .pattern_spec import LogicalPatternSpec, LogicalPrefixType, PatternType


class PatternMatcherFactory:
    """Creates appropriate matchers for pattern specifications."""

    def __init__(
        self,
        config_access: ConfigAccess,
        root_path: Path,
        console: Console | None = None,
        logger: Logger | None = None,
    ):
        """Initialize the factory.

        Args:
            config_access: Access to configuration elements
            root_path: The root path for resolving relative patterns
            console: Optional console for output
            logger: Optional logger for detailed logging
        """
        self.config_access = config_access
        self.root_path = root_path
        self.console = console
        self.logger = logger
        self.parser = PatternParser()

    def create_matcher(self, pattern: str) -> Matcher:
        """Create appropriate matcher for the given pattern.

        Args:
            pattern: The pattern string to match

        Returns:
            A matcher object appropriate for the pattern

        Raises:
            ValueError: If the pattern is invalid or unsupported
        """
        if self.logger:
            self.logger.debug(f"Creating matcher for pattern: {pattern}")

        # Parse the pattern to get a specification
        spec = self.parser.parse(pattern)

        if self.logger:
            self.logger.debug(f"Parsed pattern as: {spec}")

        # Create appropriate matcher based on pattern type
        if spec.pattern_type == PatternType.LOGICAL:
            logical_spec: LogicalPatternSpec = spec

            if logical_spec.prefix_type == LogicalPrefixType.WORKSPACE:
                if self.logger:
                    self.logger.debug(
                        f"Creating WorkspaceMatcher for pattern: {pattern}"
                    )
                return WorkspaceMatcher(logical_spec, self.config_access)

            elif logical_spec.prefix_type == LogicalPrefixType.CONTEXT:
                if self.logger:
                    self.logger.debug(f"Creating ContextMatcher for pattern: {pattern}")
                return ContextMatcher(logical_spec, self.config_access)

            elif logical_spec.prefix_type == LogicalPrefixType.COMPONENT:
                if self.logger:
                    self.logger.debug(
                        f"Creating ComponentMatcher for pattern: {pattern}"
                    )
                return ComponentMatcher(logical_spec, self.config_access)

            else:
                # Defensive guard: statically unreachable for the LogicalPrefixType
                # enum, but exercised at runtime via mocked/out-of-enum specs.
                error_msg = (  # type: ignore[unreachable]
                    f"Unknown logical prefix type: {logical_spec.prefix_type}"
                )
                if self.logger:
                    self.logger.error(error_msg)
                raise ValueError(error_msg)

        else:
            # Defensive guard: statically unreachable for the single-member
            # PatternType enum, but exercised at runtime via mocked specs.
            error_msg = f"Unknown pattern type: {spec.pattern_type}"  # type: ignore[unreachable]
            if self.logger:
                self.logger.error(error_msg)
            raise ValueError(error_msg)
