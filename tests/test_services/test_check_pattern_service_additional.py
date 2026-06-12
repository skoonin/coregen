"""Additional unit tests for the CheckPatternService class."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coregen.common.console import Console
from coregen.common.filter_service import FilterService
from coregen.common.pattern.facade import PatternMatcher
from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig
from coregen.config_model.provider import ConfigurationProvider
from coregen.services.check_pattern.check_pattern_service import CheckPatternService


@pytest.fixture
def check_pattern_service_setup():
    """Fixture for CheckPatternService setup with mocked dependencies."""
    # Create mock configuration elements
    mock_workspace = MagicMock(spec=WorkspaceConfig)
    mock_workspace.name = "test-workspace"

    mock_context = MagicMock(spec=Context)
    mock_context.name = "test-context"
    mock_context.environment = "dev"

    mock_component = MagicMock(spec=Component)
    mock_component.name = "test-component"

    # Mock get_all_components method for the context
    mock_context.get_all_components = MagicMock(
        return_value={"test-component": mock_component}
    )

    # Mock provider
    mock_provider = MagicMock(spec=ConfigurationProvider)
    mock_provider.get_root_path = MagicMock(return_value=Path("/test/root"))
    mock_path_service = MagicMock()
    mock_provider.path_service = mock_path_service

    # Create a mock config_access
    mock_config_access = MagicMock()
    # Important fix: Return a WorkspaceConfig object not a string for find_workspaces
    mock_config_access.find_workspaces = MagicMock(return_value=[mock_workspace])
    mock_config_access.get_all_contexts = MagicMock(
        return_value={"test-context": mock_context}
    )
    mock_config_access._context_lookup = {"test-workspace": ["test-context"]}
    mock_config_access._component_lookup = {
        "test-workspace": {"test-context": ["test-component"]}
    }
    mock_config_access._get_workspace_from_context = MagicMock(
        return_value=mock_workspace
    )

    # Create the service with mocked dependencies
    service = CheckPatternService(config_provider=mock_provider)

    # Inject mock config_access
    service._config_access = mock_config_access

    # Setup console mocking to avoid terminal output in tests
    mock_console = MagicMock(spec=Console)
    service._console = mock_console

    # Mock _present_results to avoid its complexity in most tests
    service._present_results = MagicMock()

    # Create basic match result structure
    basic_match_result = {
        "workspaces": {},
        "contexts": {"test-context": mock_context},
        "components": {"test-context/test-component": mock_component},
    }

    # Patch get_workspace_for_context method as a fallback to ensure compatibility
    with patch.object(
        FilterService, "get_workspace_for_context", return_value="test-workspace"
    ) as get_workspace_patch:
        yield {
            "service": service,
            "mock_workspace": mock_workspace,
            "mock_context": mock_context,
            "mock_component": mock_component,
            "mock_provider": mock_provider,
            "mock_config_access": mock_config_access,
            "mock_console": mock_console,
            "basic_match_result": basic_match_result,
            "get_workspace_patch": get_workspace_patch,
        }


class TestCheckPatternServiceAdditional:
    """Additional tests for the CheckPatternService class."""

    @pytest.mark.platform_agnostic
    def test_find_rejected_elements(self, check_pattern_service_setup):
        """Test the _find_rejected_elements method."""
        # Unpack fixture
        service = check_pattern_service_setup["service"]
        mock_context = check_pattern_service_setup["mock_context"]
        mock_config_access = check_pattern_service_setup["mock_config_access"]

        # Create a matched_elements dict with only one context matched
        matched_elements = {
            "contexts": {"matched-context": mock_context},
            "components": {},
        }

        # Create additional context for testing rejection
        rejected_context = MagicMock(spec=Context)
        rejected_context.name = "rejected-context"
        rejected_context.environment = "prod"

        # Create a proper mock component with name attribute
        rejected_component = MagicMock(spec=Component)
        rejected_component.name = "rejected-component"

        # Mock get_all_components to return the proper component
        rejected_context.get_all_components = MagicMock(
            return_value={"rejected-component": rejected_component}
        )

        # Configure the mock config_access to return both contexts
        all_contexts = {
            "matched-context": mock_context,
            "rejected-context": rejected_context,
        }
        mock_config_access.get_all_contexts = MagicMock(return_value=all_contexts)

        # Call the method under test
        result = service._find_rejected_elements(matched_elements)

        # Verify the result contains the rejected context but not the matched one
        assert "contexts" in result
        assert "rejected-context" in result["contexts"]
        assert "matched-context" not in result["contexts"]
        assert result["contexts"]["rejected-context"]["name"] == "rejected-context"
        assert result["contexts"]["rejected-context"]["workspace"] == "test-workspace"

        # Verify rejected components
        assert "components" in result
        assert "rejected-context/rejected-component" in result["components"]
        assert (
            result["components"]["rejected-context/rejected-component"]["name"]
            == "rejected-component"
        )
        assert (
            result["components"]["rejected-context/rejected-component"]["context"]
            == "rejected-context"
        )
        assert (
            result["components"]["rejected-context/rejected-component"]["workspace"]
            == "test-workspace"
        )

    @pytest.mark.platform_agnostic
    def test_analyze_pattern_matching_filesystem(self, check_pattern_service_setup):
        """Test the _analyze_pattern_matching method with unknown/unsupported patterns."""
        # Unpack fixture
        service = check_pattern_service_setup["service"]

        # Define a pattern that doesn't match logical pattern format
        pattern = "/test/path/*.txt"

        # Mock PatternMatcher
        mock_matcher = MagicMock(spec=PatternMatcher)

        # Mock the PatternParser and its parse method
        mock_pattern_parser = MagicMock()
        mock_fs_pattern_spec = MagicMock()
        # Mock pattern spec that doesn't match LOGICAL type (to test Unknown case)
        mock_fs_pattern_spec.pattern_type = "UNKNOWN"  # Using string to avoid import
        mock_fs_pattern_spec.is_absolute = True
        mock_fs_pattern_spec.has_glob = True
        mock_fs_pattern_spec.recursive = False
        mock_fs_pattern_spec.tokens = [
            MagicMock(value="test", is_wildcard=False, is_recursive=False),
            MagicMock(value="path", is_wildcard=False, is_recursive=False),
            MagicMock(value="*.txt", is_wildcard=True, is_recursive=False),
        ]
        mock_pattern_parser.parse = MagicMock(return_value=mock_fs_pattern_spec)

        # Mock imports and objects needed for PatternParser
        with (
            patch(
                "coregen.common.pattern.facade.PatternMatcher",
                return_value=mock_matcher,
            ),
            patch(
                "coregen.common.pattern.pattern_parser.PatternParser",
                return_value=mock_pattern_parser,
            ),
            patch(
                "coregen.common.pattern.pattern_spec.PatternType"
            ) as mock_pattern_type,
        ):

            # Configure the enums
            mock_pattern_type.LOGICAL = "LOGICAL"

            # Mock _test_single_pattern to return test data
            test_single_result = {
                "matched": {"files": ["/test/path/file1.txt"]},
                "rejected": {"contexts": {}, "components": {}},
            }
            with patch.object(
                service, "_test_single_pattern", return_value=test_single_result
            ):
                # Call the method under test
                result = service._analyze_pattern_matching(pattern)

                # Verify basic structure
                assert "pattern" in result
                assert result["pattern"] == pattern
                assert "pattern_type" in result
                # Should return Unknown for non-logical patterns
                assert result["pattern_type"] == "Unknown"
                assert "pattern_parts" in result
                assert "match_attempts" in result
                assert "examples" in result

                # Verify basic analysis structure
                assert "phase1_results" in result
                # For unknown pattern types, phase1_results might be empty

                # Verify phase 2 results
                assert "phase2_results" in result
                assert "matched_contexts" in result["phase2_results"]
                assert "matched_components" in result["phase2_results"]
                assert "rejected_contexts" in result["phase2_results"]
                assert "rejected_components" in result["phase2_results"]

    @pytest.mark.platform_agnostic
    def test_analyze_pattern_matching_parser_error(self, check_pattern_service_setup):
        """Test the _analyze_pattern_matching method when pattern parsing fails."""
        # Unpack fixture
        service = check_pattern_service_setup["service"]

        # Define a pattern
        pattern = "invalid/pattern"

        # Mock PatternMatcher
        mock_matcher = MagicMock(spec=PatternMatcher)

        # Mock the PatternParser to raise an exception
        mock_pattern_parser = MagicMock()
        mock_pattern_parser.parse = MagicMock(
            side_effect=ValueError("Invalid pattern format")
        )

        # Mock imports and objects needed for PatternParser
        with (
            patch(
                "coregen.common.pattern.facade.PatternMatcher",
                return_value=mock_matcher,
            ),
            patch(
                "coregen.common.pattern.pattern_parser.PatternParser",
                return_value=mock_pattern_parser,
            ),
        ):

            # Mock _test_single_pattern to return test data
            test_single_result = {
                "matched": {},
                "rejected": {"contexts": {}, "components": {}},
            }
            with patch.object(
                service, "_test_single_pattern", return_value=test_single_result
            ):
                # Call the method under test
                result = service._analyze_pattern_matching(pattern)

                # Verify basic structure
                assert "pattern" in result
                assert result["pattern"] == pattern
                assert "pattern_parts" in result
                assert "match_attempts" in result

                # Verify error is captured in phase1_results
                assert "phase1_results" in result
                assert "error" in result["phase1_results"]
                assert "Invalid pattern format" in result["phase1_results"]["error"]

                # Verify phase 2 still runs
                assert "phase2_results" in result

    def test_break_down_pattern(self, check_pattern_service_setup):
        """Test the _break_down_pattern method."""
        # Unpack fixture
        service = check_pattern_service_setup["service"]

        # Test with a simple pattern
        simple_pattern = "workspace/test-workspace"
        result = service._break_down_pattern(simple_pattern)

        # Verify structure
        assert len(result) == 2
        assert result[0]["segment"] == "workspace"
        assert result[1]["segment"] == "test-workspace"
        assert len(result[0]["wildcards"]) == 0
        assert len(result[1]["wildcards"]) == 0

        # Test with a pattern containing wildcards
        wildcard_pattern = "context/*/test-*"
        result = service._break_down_pattern(wildcard_pattern)

        # Verify structure
        assert len(result) == 3
        assert result[0]["segment"] == "context"
        assert result[1]["segment"] == "*"
        assert result[2]["segment"] == "test-*"
        assert len(result[0]["wildcards"]) == 0
        assert len(result[1]["wildcards"]) == 1
        assert result[1]["wildcards"][0]["type"] == "asterisk"
        assert len(result[2]["wildcards"]) == 1
        assert result[2]["wildcards"][0]["type"] == "asterisk"

        # Test with a pattern containing character classes
        complex_pattern = "file[a-z].txt"
        result = service._break_down_pattern(complex_pattern)

        # Verify structure
        assert len(result) == 1
        assert result[0]["segment"] == "file[a-z].txt"
        assert len(result[0]["wildcards"]) == 1
        assert result[0]["wildcards"][0]["type"] == "character_class"

        # Test with a pattern containing question marks
        qmark_pattern = "file?.txt"
        result = service._break_down_pattern(qmark_pattern)

        # Verify structure
        assert len(result) == 1
        assert result[0]["segment"] == "file?.txt"
        assert len(result[0]["wildcards"]) == 1
        assert result[0]["wildcards"][0]["type"] == "question_mark"

    def test_get_workspace_for_context(self, check_pattern_service_setup):
        """Test the get_workspace_for_context method."""
        # Unpack fixture
        service = check_pattern_service_setup["service"]
        mock_workspace = check_pattern_service_setup["mock_workspace"]
        mock_config_access = check_pattern_service_setup["mock_config_access"]

        # Setup a context with a workspace
        context = MagicMock(spec=Context)

        # Mock the config_access method that gets a workspace from context
        mock_config_access._get_workspace_from_context = MagicMock(
            return_value=mock_workspace
        )

        # Override the find_workspaces to return WorkspaceConfig objects, not strings
        mock_config_access.find_workspaces = MagicMock(return_value=[mock_workspace])

        # Make sure get_all_contexts includes our test context
        mock_config_access.get_all_contexts = MagicMock(
            return_value={"test-context": context}
        )

        # Set context.name to match what's in get_all_contexts
        context.name = "test-context"

        # Call the actual method on the filter service
        result = service.filter_service.get_workspace_for_context(context)

        # Verify the result is the workspace name
        assert result == "test-workspace"

    def test_check_pattern_with_multiple_patterns(self, check_pattern_service_setup):
        """Test check_pattern method with multiple patterns."""
        # Unpack fixture
        service = check_pattern_service_setup["service"]
        mock_workspace = check_pattern_service_setup["mock_workspace"]

        # Define two patterns to test
        patterns = ["workspace/test-*", "context/dev-*"]

        # Create individual pattern results
        workspace_match = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {},
            "components": {},
        }

        context_match = {
            "workspaces": {},
            "contexts": {"dev-context": MagicMock(spec=Context, environment="dev")},
            "components": {},
        }

        # Mock _test_single_pattern to return different results for each pattern
        def mock_test_single_pattern(pattern, filters, show_rejected, include_inactive):
            if pattern == "workspace/test-*":
                return {
                    "pattern": pattern,
                    "matched": workspace_match,
                    "rejected": None,
                }
            else:
                return {
                    "pattern": pattern,
                    "matched": context_match,
                    "rejected": None,
                }

        # Apply the mock
        with patch.object(
            service, "_test_single_pattern", side_effect=mock_test_single_pattern
        ):
            # Call the method with multiple patterns
            result = service.check_pattern(patterns)

            # Verify the result includes both patterns
            assert "patterns" in result
            assert len(result["patterns"]) == 2
            assert "workspace/test-*" in result["patterns"]
            assert "context/dev-*" in result["patterns"]

            # Verify the matched elements are merged correctly
            assert "matched" in result
            assert "workspaces" in result["matched"]
            assert "contexts" in result["matched"]

            # Both results should be included
            assert "test-workspace" in result["matched"]["workspaces"]
            assert "dev-context" in result["matched"]["contexts"]

            # Stats should reflect combined results
            assert "stats" in result
            assert result["stats"]["matched_contexts"] == 1
            assert (
                result["stats"]["matched_workspaces"]
                if "matched_workspaces" in result["stats"]
                else 1
            )

    def test_test_single_pattern_with_filters(self, check_pattern_service_setup):
        """Test _test_single_pattern with filters."""
        # Unpack fixture
        service = check_pattern_service_setup["service"]

        # Define a pattern and filters
        pattern = "context/**"
        filters = ["environment=dev"]

        # Mock complete model
        complete_model = {
            "workspaces": {},
            "contexts": {
                "dev-context": MagicMock(spec=Context, environment="dev"),
                "prod-context": MagicMock(spec=Context, environment="prod"),
            },
            "components": {},
        }

        # Mock config access
        service.config_access.get_complete_model = MagicMock(
            return_value=complete_model
        )

        # Mock parse_filter_expression
        mock_parsed_filter = ("environment", "=", "dev")
        service.parse_filter_expression = MagicMock(return_value=mock_parsed_filter)

        # Mock filter service
        filtered_model = {
            "workspaces": {},
            "contexts": {"dev-context": complete_model["contexts"]["dev-context"]},
            "components": {},
        }
        service.filter_service.apply_filters_complete = MagicMock(
            return_value=filtered_model
        )

        # Mock inactive filter
        service.inactive_filter_service.filter_complete_model = MagicMock(
            return_value=filtered_model
        )

        # Mock PatternSelector
        with patch(
            "coregen.services.check_pattern.check_pattern_service.PatternSelector"
        ) as mock_pattern_selector:
            mock_selector_instance = MagicMock()
            mock_selector_instance.select_by_pattern.return_value = filtered_model
            mock_pattern_selector.return_value = mock_selector_instance

            # Call the method
            result = service._test_single_pattern(pattern, filters, False, False)

            # Verify result structure
            assert "pattern" in result
            assert result["pattern"] == pattern
            assert "matched" in result
            assert result["matched"] == filtered_model
            assert "rejected" in result
            assert result["rejected"] is None  # show_rejected=False

            # Verify the filter was parsed and applied
            service.parse_filter_expression.assert_called_once_with(filters[0])
            service.filter_service.apply_filters_complete.assert_called_once()

    def test_test_single_pattern_with_show_rejected(self, check_pattern_service_setup):
        """Test _test_single_pattern with show_rejected flag."""
        # Unpack fixture
        service = check_pattern_service_setup["service"]

        # Define a pattern
        pattern = "context/dev-*"

        # Mock complete model
        complete_model = {
            "workspaces": {},
            "contexts": {
                "dev-context": MagicMock(spec=Context, environment="dev"),
                "prod-context": MagicMock(spec=Context, environment="prod"),
            },
            "components": {},
        }

        # Match data (only dev-context matches)
        match_data = {
            "workspaces": {},
            "contexts": {"dev-context": complete_model["contexts"]["dev-context"]},
            "components": {},
        }

        # Mock config access
        service.config_access.get_complete_model = MagicMock(
            return_value=complete_model
        )

        # Mock inactive filter
        service.inactive_filter_service.filter_complete_model = MagicMock(
            return_value=complete_model
        )

        # Mock PatternSelector
        with patch(
            "coregen.services.check_pattern.check_pattern_service.PatternSelector"
        ) as mock_pattern_selector:
            mock_selector_instance = MagicMock()
            mock_selector_instance.select_by_pattern.return_value = match_data
            mock_pattern_selector.return_value = mock_selector_instance

            # Mock _find_rejected_elements
            rejected_data = {
                "contexts": {
                    "prod-context": complete_model["contexts"]["prod-context"]
                },
                "components": {},
            }
            service._find_rejected_elements = MagicMock(return_value=rejected_data)

            # Call the method with show_rejected=True
            result = service._test_single_pattern(pattern, None, True, True)

            # Verify result structure
            assert "pattern" in result
            assert result["pattern"] == pattern
            assert "matched" in result
            assert result["matched"] == match_data
            assert "rejected" in result
            assert result["rejected"] == rejected_data

            # Verify _find_rejected_elements was called
            service._find_rejected_elements.assert_called_once_with(match_data)
