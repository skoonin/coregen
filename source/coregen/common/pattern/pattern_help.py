"""Pattern help and error message utilities.

This module provides helpful error messages and guidance when patterns fail,
including shell expansion detection and pattern usage tips.
"""

from coregen.common.console import Console


class PatternHelpProvider:
    """Provides helpful guidance for pattern-related errors."""

    def __init__(self, console: Console | None = None):
        """Initialize the help provider.

        Args:
            console: Console instance for output, defaults to Console class
        """
        self.console = console or Console

    def provide_pattern_help(
        self, patterns: list[str], additional_context: str | None = None
    ) -> None:
        """Provide comprehensive help when patterns fail to match.

        Args:
            patterns: The patterns that failed to match
            additional_context: Optional additional context about the failure
        """
        if not patterns:
            return

        # Show basic error message
        if len(patterns) == 1:
            self.console.error(f"No matches found for pattern: {patterns[0]}")
        else:
            self.console.error(f"No matches found for patterns: {', '.join(patterns)}")

        # Show general pattern tips
        self._show_general_pattern_tips()

    def _show_general_pattern_tips(self) -> None:
        """Show general tips for pattern usage."""
        self.console.error("")
        self.console.info("Pattern Tips:")
        self.console.info("   • All patterns require prefixes:")
        self.console.info('     - Workspace: "w/aws" or "workspace/aws"')
        self.console.info('     - Context: "c/dev" or "context/dev"')
        self.console.info('     - Component: "cm/nginx" or "component/nginx"')
        self.console.info('   • Quote patterns with wildcards: "w/aws/*"')
        self.console.info("   • Use * for wildcard matching within names and paths")
        self.console.info(
            '   • Use check-pattern to test: coregen check-pattern "your-pattern"'
        )
        self.console.info(
            '   • Try broader patterns first: "w/*" to see all workspaces'
        )

    def show_pattern_examples(self) -> None:
        """Show comprehensive pattern examples."""
        self.console.info("")
        self.console.info("📋 Pattern Examples:")
        self.console.info("")
        self.console.info("Workspace Patterns:")
        self.console.info(
            '   "w/aws"                    # All contexts in aws workspace'
        )
        self.console.info(
            '   "w/aws/*"                  # All contexts in aws workspace (explicit)'
        )
        self.console.info('   "workspace/aws/*"          # All contexts (long form)')
        self.console.info("")
        self.console.info("Context Patterns:")
        self.console.info('   "c/dev-cluster"            # Specific context')
        self.console.info('   "c/*-dev"                  # All dev contexts')
        self.console.info(
            '   "context/staging-*"        # All staging contexts (long form)'
        )
        self.console.info("")
        self.console.info("Component Patterns:")
        self.console.info('   "cm/metrics-server"        # Specific component')
        self.console.info(
            '   "cm/prom*"                 # Components starting with "prom"'
        )
        self.console.info(
            '   "component/nginx*"         # Nginx components (long form)'
        )
        self.console.info("")
        self.console.info("Advanced Patterns:")
        self.console.info('   "w/*"                      # All workspaces')
        self.console.info(
            '   "w/*/dev-*"                # All dev contexts across workspaces'
        )


def provide_pattern_help(
    patterns: list[str],
    console: Console | None = None,
    additional_context: str | None = None,
) -> None:
    """Convenience function to provide pattern help.

    Args:
        patterns: The patterns that failed to match
        console: Optional console instance for output
        additional_context: Optional additional context about the failure
    """
    helper = PatternHelpProvider(console)
    helper.provide_pattern_help(patterns, additional_context)
