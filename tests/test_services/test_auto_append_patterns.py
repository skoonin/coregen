"""Test auto-append /* functionality for simple patterns."""

from unittest.mock import MagicMock

import pytest

from coregen.services.services_base import ServicesBase


@pytest.fixture
def service_with_mock_logger():
    """Fixture providing a ServicesBase instance with mocked logger."""
    service = ServicesBase()
    service.logger = MagicMock()
    return service


class TestAutoAppendPatterns:
    """Test the auto-append /* functionality."""

    def test_auto_append_simple_patterns(self, service_with_mock_logger):
        """Test that bare logical type patterns get /* appended."""
        test_cases = [
            # (input, expected)
            (["workspace"], ["workspace/*"]),
            (["context"], ["context/*"]),
            (["component"], ["component/*"]),
            (["workspace", "context"], ["workspace/*", "context/*"]),
        ]

        for input_patterns, expected in test_cases:
            result = service_with_mock_logger._auto_append_recursive_pattern(
                input_patterns
            )
            assert result == expected, f"Failed for input {input_patterns}"

    def test_preserve_wildcard_patterns(self, service_with_mock_logger):
        """Test that patterns with wildcards are preserved."""
        test_cases = [
            # Patterns that should NOT be modified
            (["workspace/**"], ["workspace/**"]),
            (["workspace/*"], ["workspace/*"]),
            (["context/*dev"], ["context/*dev"]),
            (["component/*server"], ["component/*server"]),
            (["workspace/*/context"], ["workspace/*/context"]),
        ]

        for input_patterns, expected in test_cases:
            result = service_with_mock_logger._auto_append_recursive_pattern(
                input_patterns
            )
            assert result == expected, f"Failed for input {input_patterns}"

    def test_preserve_directory_patterns(self, service_with_mock_logger):
        """Test that patterns ending with / are preserved."""
        test_cases = [
            (["workspace/"], ["workspace/"]),
            (["contexts/aws/"], ["contexts/aws/"]),
        ]

        for input_patterns, expected in test_cases:
            result = service_with_mock_logger._auto_append_recursive_pattern(
                input_patterns
            )
            assert result == expected, f"Failed for input {input_patterns}"

    def test_preserve_path_component_patterns(self, service_with_mock_logger):
        """Test that patterns with path components are preserved."""
        test_cases = [
            # Patterns with single path component (should NOT be modified)
            (["workspace/aws"], ["workspace/aws"]),
            (["context/dev"], ["context/dev"]),
            (["component/nginx"], ["component/nginx"]),
            (["workspace/prod"], ["workspace/prod"]),
        ]

        for input_patterns, expected in test_cases:
            result = service_with_mock_logger._auto_append_recursive_pattern(
                input_patterns
            )
            assert result == expected, f"Failed for input {input_patterns}"

    def test_mixed_patterns(self, service_with_mock_logger):
        """Test a mix of patterns that should and shouldn't be modified."""
        input_patterns = [
            "workspace",  # Should become workspace/*
            "workspace/aws",  # Should remain unchanged (has path component)
            "workspace/**",  # Should remain unchanged
            "context/*dev",  # Should remain unchanged
            "component/nginx",  # Should remain unchanged (has path component)
            "context/aws-context/nginx",  # Should remain unchanged (complex)
            "contexts/aws/nginx",  # Should remain unchanged (filesystem)
        ]

        expected = [
            "workspace/*",
            "workspace/aws",  # Path component preserved
            "workspace/**",
            "context/*dev",
            "component/nginx",  # Path component preserved
            "context/aws-context/nginx",  # Complex pattern preserved
            "contexts/aws/nginx",  # Filesystem pattern preserved
        ]

        result = service_with_mock_logger._auto_append_recursive_pattern(input_patterns)
        assert result == expected

    def test_logging(self, service_with_mock_logger):
        """Test that appropriate debug messages are logged."""
        patterns = ["workspace", "context/**", "component/*"]
        service_with_mock_logger._auto_append_recursive_pattern(patterns)

        # Check that debug messages were logged
        debug_calls = service_with_mock_logger.logger.debug.call_args_list

        # Should have logged about auto-appending for 'workspace'
        assert any(
            "Auto-appending /*" in str(call) and "workspace" in str(call)
            for call in debug_calls
        )

        # Should have logged about keeping 'context/**' as-is
        assert any(
            "already contains wildcards" in str(call) and "context/**" in str(call)
            for call in debug_calls
        )

        # Should have logged about keeping 'component/*' as-is
        assert any(
            "already contains wildcards" in str(call) and "component/*" in str(call)
            for call in debug_calls
        )

    def test_complex_patterns_preserved(self, service_with_mock_logger):
        """Test that complex patterns are NOT modified."""
        test_cases = [
            # Complex logical patterns (multiple path components)
            (["context/aws-context/nginx"], ["context/aws-context/nginx"]),
            (["workspace/aws/us-west-2/prod"], ["workspace/aws/us-west-2/prod"]),
            (["component/nginx/config/default"], ["component/nginx/config/default"]),
            # Filesystem patterns (don't start with logical prefixes)
            (["contexts/aws/nginx"], ["contexts/aws/nginx"]),
            (["workspaces/prod/service"], ["workspaces/prod/service"]),
            (["some/random/path"], ["some/random/path"]),
        ]

        for input_patterns, expected in test_cases:
            result = service_with_mock_logger._auto_append_recursive_pattern(
                input_patterns
            )
            assert result == expected, f"Failed for input {input_patterns}"

    def test_simple_logical_pattern_detection(self, service_with_mock_logger):
        """Test the _is_simple_logical_pattern helper method."""
        # Simple patterns that should return True (only bare logical types)
        simple_patterns = [
            "workspace",
            "context",
            "component",
        ]

        for pattern in simple_patterns:
            assert service_with_mock_logger._is_simple_logical_pattern(
                pattern
            ), f"Pattern '{pattern}' should be considered simple"

        # Complex patterns that should return False (everything else)
        complex_patterns = [
            "workspace/aws",  # Has path component
            "context/dev",  # Has path component
            "component/nginx",  # Has path component
            "context/aws-context/nginx",  # Multiple path components
            "workspace/aws/us-west-2/prod",  # Multiple path components
            "contexts/aws/nginx",  # Filesystem pattern (plural)
            "workspaces/prod/service",  # Filesystem pattern (plural)
            "some/random/path",  # Not a logical pattern
            "workspace/aws/service/nginx",  # Too many components
        ]

        for pattern in complex_patterns:
            assert not service_with_mock_logger._is_simple_logical_pattern(
                pattern
            ), f"Pattern '{pattern}' should NOT be considered simple"

    def test_input_validation(self, service_with_mock_logger):
        """Test input validation for edge cases."""
        # Test empty list
        result = service_with_mock_logger._auto_append_recursive_pattern([])
        assert result == []

        # Test None input (should be handled gracefully)
        result = service_with_mock_logger._auto_append_recursive_pattern(None)
        assert result == []

        # Test non-list input
        result = service_with_mock_logger._auto_append_recursive_pattern("workspace")
        assert result == ["workspace/*"]

        # Test list with non-string elements
        result = service_with_mock_logger._auto_append_recursive_pattern(
            ["workspace", None, 123, "context"]
        )
        assert result == ["workspace/*", "context/*"]

        # Test list with empty/whitespace strings
        result = service_with_mock_logger._auto_append_recursive_pattern(
            ["workspace", "", "  ", "context"]
        )
        assert result == ["workspace/*", "context/*"]

        # Verify warnings were logged for invalid inputs
        warning_calls = [
            call
            for call in service_with_mock_logger.logger.warning.call_args_list
            if call is not None
        ]
        assert (
            len(warning_calls) >= 3
        )  # Should have warnings for None, 123, and empty strings
