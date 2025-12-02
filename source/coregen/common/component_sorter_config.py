"""
Configuration for ComponentSorterService.

Centralizes all configuration knobs and defaults for component sorting behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

# Top-level knobs (easy to tweak without touching callers)
DEFAULT_PRIORITY_HIGH_VALUE = 1_000_000
ELEVATE_NON_PRIORITY_DEPENDENCIES = True
CYCLE_BREAK_STRATEGY = "stable"  # options: "stable"
STRICT_VALIDATION = True  # Enable strict validation for priorities and dependencies


@dataclass
class ComponentSorterConfig:
    """Configuration for component sorting behavior."""

    elevate_non_priority_deps: bool
    none_priority_value: int
    cycle_break_strategy: str
    strict_validation: bool  # DEPRECATED for ComponentSorterService: Accepted but ignored. Component validation rules now always run.

    @classmethod
    def create(
        cls,
        *,
        elevate_non_priority_deps: bool | None = None,
        none_priority_value: int | None = None,
        cycle_break_strategy: str | None = None,
        strict_validation: bool | None = None,
    ) -> ComponentSorterConfig:
        """Create configuration with defaults."""
        return cls(
            elevate_non_priority_deps=(
                ELEVATE_NON_PRIORITY_DEPENDENCIES
                if elevate_non_priority_deps is None
                else bool(elevate_non_priority_deps)
            ),
            none_priority_value=(
                DEFAULT_PRIORITY_HIGH_VALUE
                if none_priority_value is None
                else int(none_priority_value)
            ),
            cycle_break_strategy=cycle_break_strategy or CYCLE_BREAK_STRATEGY,
            strict_validation=(
                STRICT_VALIDATION
                if strict_validation is None
                else bool(strict_validation)
            ),
        )


@dataclass(frozen=True)
class GroupKey:
    """Key for grouping components by workspace and context."""

    workspace: str
    context: str


__all__ = [
    "DEFAULT_PRIORITY_HIGH_VALUE",
    "ELEVATE_NON_PRIORITY_DEPENDENCIES",
    "CYCLE_BREAK_STRATEGY",
    "STRICT_VALIDATION",
    "ComponentSorterConfig",
    "GroupKey",
]
