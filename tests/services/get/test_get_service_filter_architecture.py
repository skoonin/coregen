"""
Test suite for the filter-first architecture.

This test validates the filter-first approach for all
pattern and filter combinations.
"""

from pathlib import Path
from typing import Any

import pytest

from coregen.cli.global_options import GlobalOptions
from coregen.services.get.get_service import GetService


class TestFilterArchitecture:
    """Test the filter-first architecture."""

    @pytest.fixture
    def test_config_path(self) -> Path:
        """Path to test configuration."""
        return Path("test_data/.cgconfig.yaml")

    @pytest.fixture
    def get_service(self, test_config_path: Path) -> GetService:
        """Create GetService instance with test config loaded."""
        # Create service with test config
        global_options = GlobalOptions(config_file=test_config_path)
        service = GetService(global_options=global_options)
        return service

    def run_filter_test(
        self, service: GetService, patterns: list[str], filters: list[str] | None = None
    ) -> dict[str, Any]:
        """Run get_elements and return results."""
        return service.get_elements(patterns=patterns, filters=filters)

    def test_basic_patterns_no_filters(self, get_service: GetService) -> None:
        """Test basic patterns without filters work correctly."""
        test_cases = [
            ["w/*"],  # All workspaces
            ["c/*"],  # All contexts
            ["cm/*"],  # All components
            ["w/aws"],  # Specific workspace
            ["c/*-prod"],  # Contexts matching pattern
            ["cm/prometheus"],  # Components matching pattern
        ]

        for patterns in test_cases:
            result = self.run_filter_test(get_service, patterns)
            # Just verify we get results
            assert isinstance(result, dict)

    def test_filters_on_direct_properties(self, get_service: GetService) -> None:
        """Test filters on direct entity properties."""
        test_cases = [
            # Workspace filters
            (["w/*"], ["workspace.name=aws"]),
            # Context filters
            (["c/*"], ["context.active=true"]),
            (["c/*"], ["context.environment=prod"]),
            # Component filters
            (["cm/*"], ["component.name=prometheus"]),
            (["cm/*"], ["config.active=true"]),
        ]

        for patterns, filters in test_cases:
            result = self.run_filter_test(get_service, patterns, filters)
            # Verify we get results
            assert isinstance(result, dict)

    def test_cross_entity_filters_capability(self, get_service: GetService) -> None:
        """Test that cross-entity filters now raise validation errors."""
        # Cross-entity filtering (cm/* with context.*) is no longer supported
        # This should now raise a ValueError
        patterns = ["cm/*"]
        filters = ["context.environment=prod"]

        with pytest.raises(ValueError, match="Pattern/filter mismatch.*context fields"):
            self.run_filter_test(get_service, patterns, filters)

    def test_multiple_filters(self, get_service: GetService) -> None:
        """Test multiple filters applied together."""
        test_cases = [
            (["c/*"], ["context.active=true", "context.environment=dev"]),
            (["cm/*"], ["config.active=true", "component.name~=metrics"]),
        ]

        for patterns, filters in test_cases:
            result = self.run_filter_test(get_service, patterns, filters)
            # Verify we get results
            assert isinstance(result, dict)

    def test_inactive_filtering(self, get_service: GetService) -> None:
        """Test inactive filtering works correctly."""
        # Test with include_inactive=False (default)
        result_filtered = get_service.get_elements(patterns=["cm/*"])

        # Test with include_inactive=True
        result_all = get_service.get_elements(patterns=["cm/*"], include_inactive=True)

        # Should filter out inactive by default
        assert len(result_filtered.get("components", {})) < len(
            result_all.get("components", {})
        )

    def test_format_type_consistency(self, get_service: GetService) -> None:
        """Test format_type produces correct results."""
        test_cases = [
            (["w/*"], None, "nested"),
            (["w/*"], None, "flat"),
            (["cm/*"], ["config.active=true"], "flat"),
        ]

        for patterns, filters, format_type in test_cases:
            result_formatted = get_service.get_elements(
                patterns=patterns, filters=filters, format_type=format_type
            )

            # For flat format, verify it's a list structure
            if format_type == "flat":
                # Check we have list structures for entities
                for entity_type in ["workspaces", "contexts", "components"]:
                    if entity_type in result_formatted:
                        assert isinstance(result_formatted[entity_type], list)
            else:
                # For nested format, verify it's a dict structure
                assert isinstance(result_formatted, dict)
