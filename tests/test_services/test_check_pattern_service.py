"""Unit tests for the CheckPatternService class."""

from unittest.mock import MagicMock, patch

import pytest

from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig
from coregen.config_model.provider import ConfigurationProvider
from coregen.services.check_pattern.check_pattern_service import CheckPatternService


@pytest.fixture
def check_pattern_service_basic_setup():
    """Fixture for CheckPatternService basic setup with mocked dependencies."""
    # Create mock configuration elements
    mock_workspace = MagicMock(spec=WorkspaceConfig)
    mock_workspace.name = "test-workspace"

    mock_context = MagicMock(spec=Context)
    mock_context.name = "test-context"
    mock_context.environment = "dev"

    mock_component = MagicMock(spec=Component)
    mock_component.name = "test-component"

    # Mock provider
    mock_provider = MagicMock(spec=ConfigurationProvider)
    mock_path_service = MagicMock()
    mock_provider.path_service = mock_path_service

    # Create a mock config_access
    mock_config_access = MagicMock()
    mock_config_access._context_lookup = {"test-workspace": ["test-context"]}
    mock_config_access._component_lookup = {
        "test-workspace": {"test-context": ["test-component"]}
    }

    # Setup basic matching results structure
    basic_match_result = {"workspaces": {}, "contexts": {}, "components": {}}

    # Create the service with mocked dependencies
    service = CheckPatternService(config_provider=mock_provider)

    # Inject mock config_access
    service._config_access = mock_config_access

    # Setup console mocking to avoid terminal output in tests
    mock_console = MagicMock()
    service._console = mock_console

    # Service no longer has _present_results method

    yield {
        "service": service,
        "mock_workspace": mock_workspace,
        "mock_context": mock_context,
        "mock_component": mock_component,
        "mock_provider": mock_provider,
        "mock_path_service": mock_path_service,
        "mock_config_access": mock_config_access,
        "basic_match_result": basic_match_result,
        "mock_console": mock_console,
    }


class TestCheckPatternService:
    """Test the CheckPatternService class."""

    def test_check_pattern_workspace(self, check_pattern_service_basic_setup):
        """Test pattern checking for workspace patterns."""
        # Unpack fixture
        service = check_pattern_service_basic_setup["service"]
        mock_workspace = check_pattern_service_basic_setup["mock_workspace"]
        check_pattern_service_basic_setup["mock_context"]
        check_pattern_service_basic_setup["mock_component"]
        # Define pattern to test
        pattern = "workspace/test-workspace"

        # Setup match data
        workspace_match = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {},
            "components": {},
        }

        # Mock the complete model
        mock_complete_model = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {},
            "components": {},
        }

        # Mock config access to return complete model
        service.config_access.get_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock inactive filter to return the same model (not filter anything)
        service.inactive_filter_service.filter_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock PatternSelector
        with patch(
            "coregen.services.check_pattern.check_pattern_service.PatternSelector"
        ) as mock_pattern_selector:
            mock_selector_instance = MagicMock()
            mock_selector_instance.select_by_pattern.return_value = workspace_match
            mock_pattern_selector.return_value = mock_selector_instance

            # Test pattern checking
            result = service.check_pattern([pattern])

            # Verify PatternSelector was used
            mock_pattern_selector.assert_called()
            mock_selector_instance.select_by_pattern.assert_called_with(
                mock_complete_model, pattern
            )

            # Verify results structure
            assert "patterns" in result
            assert pattern in result["patterns"]
            assert "matched" in result
            assert "workspaces" in result["matched"]
            assert "test-workspace" in result["matched"]["workspaces"]

            # Verify stats
            assert "stats" in result

    def test_check_pattern_context(self, check_pattern_service_basic_setup):
        """Test pattern checking for context patterns."""
        # Unpack fixture
        service = check_pattern_service_basic_setup["service"]
        check_pattern_service_basic_setup["mock_workspace"]
        mock_context = check_pattern_service_basic_setup["mock_context"]
        check_pattern_service_basic_setup["mock_component"]
        # Unpack fixture
        service = check_pattern_service_basic_setup["service"]
        # Setup pattern matching result - includes context
        context_match = {
            "workspaces": {},
            "contexts": {"test-context": mock_context},
            "components": {},
        }

        # Define pattern to test
        pattern = "context/test-workspace/test-context"

        # Mock the complete model
        mock_complete_model = {
            "workspaces": {},
            "contexts": {"test-context": mock_context},
            "components": {},
        }

        # Mock config access to return complete model
        service.config_access.get_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock inactive filter to return the same model (not filter anything)
        service.inactive_filter_service.filter_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock PatternSelector
        with patch(
            "coregen.services.check_pattern.check_pattern_service.PatternSelector"
        ) as mock_pattern_selector:
            mock_selector_instance = MagicMock()
            mock_selector_instance.select_by_pattern.return_value = context_match
            mock_pattern_selector.return_value = mock_selector_instance

            # Check context pattern
            result = service.check_pattern([pattern])

            # Verify PatternSelector was used
            mock_pattern_selector.assert_called()
            mock_selector_instance.select_by_pattern.assert_called_with(
                mock_complete_model, pattern
            )

            # Verify results structure based on the actual implementation
            assert "patterns" in result
            assert pattern in result["patterns"]
            assert "matched" in result
            assert "contexts" in result["matched"]
            assert "test-context" in result["matched"]["contexts"]

    def test_check_pattern_component(self, check_pattern_service_basic_setup):
        """Test pattern checking for component patterns."""
        # Unpack fixture
        service = check_pattern_service_basic_setup["service"]
        check_pattern_service_basic_setup["mock_workspace"]
        check_pattern_service_basic_setup["mock_context"]
        mock_component = check_pattern_service_basic_setup["mock_component"]
        # Setup pattern matching result - includes component
        component_match = {
            "workspaces": {},
            "contexts": {},
            "components": {"test-context/test-component": mock_component},
        }

        # Define pattern to test
        pattern = "component/test-workspace/test-context/test-component"

        # Mock the complete model
        mock_complete_model = {
            "workspaces": {},
            "contexts": {},
            "components": {"test-context/test-component": mock_component},
        }

        # Mock config access to return complete model
        service.config_access.get_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock inactive filter to return the same model (not filter anything)
        service.inactive_filter_service.filter_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock PatternSelector
        with patch(
            "coregen.services.check_pattern.check_pattern_service.PatternSelector"
        ) as mock_pattern_selector:
            mock_selector_instance = MagicMock()
            mock_selector_instance.select_by_pattern.return_value = component_match
            mock_pattern_selector.return_value = mock_selector_instance

            # Check component pattern
            result = service.check_pattern([pattern])

            # Verify PatternSelector was used
            mock_pattern_selector.assert_called()
            mock_selector_instance.select_by_pattern.assert_called_with(
                mock_complete_model, pattern
            )

            # Verify results structure
            assert "patterns" in result
            assert pattern in result["patterns"]
            assert "matched" in result
            assert "components" in result["matched"]
            assert "test-context/test-component" in result["matched"]["components"]

    def test_check_pattern_filesystem(self, check_pattern_service_basic_setup):
        """Test pattern checking for filesystem patterns."""
        # Unpack fixture
        service = check_pattern_service_basic_setup["service"]
        check_pattern_service_basic_setup["mock_workspace"]
        check_pattern_service_basic_setup["mock_context"]
        check_pattern_service_basic_setup["mock_component"]
        # Unpack fixture
        service = check_pattern_service_basic_setup["service"]
        # Setup mock for filesystem pattern matching - simulating files
        filesystem_match = {
            "workspaces": {},
            "contexts": {},
            "components": {},
            "files": ["/test/root/file1.txt", "/test/root/file2.txt"],
        }

        # Define pattern to test - filesystem path
        pattern = "/test/root/*.txt"

        # Mock the complete model (empty for filesystem patterns)
        mock_complete_model = {
            "workspaces": {},
            "contexts": {},
            "components": {},
        }

        # Mock config access to return complete model
        service.config_access.get_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock inactive filter to return the same model (not filter anything)
        service.inactive_filter_service.filter_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock PatternSelector - filesystem patterns return files
        with patch(
            "coregen.services.check_pattern.check_pattern_service.PatternSelector"
        ) as mock_pattern_selector:
            mock_selector_instance = MagicMock()
            mock_selector_instance.select_by_pattern.return_value = filesystem_match
            mock_pattern_selector.return_value = mock_selector_instance

            # Check filesystem pattern
            result = service.check_pattern([pattern])

            # Verify PatternSelector was used
            mock_pattern_selector.assert_called()
            mock_selector_instance.select_by_pattern.assert_called_with(
                mock_complete_model, pattern
            )

            # Verify results structure for filesystem results
            assert "patterns" in result
            assert pattern in result["patterns"]
            assert "matched" in result
            assert "files" in result["matched"]
            assert len(result["matched"]["files"]) == 2

    def test_check_pattern_with_filters(self, check_pattern_service_basic_setup):
        """Test pattern checking with filters."""
        # Unpack fixture
        service = check_pattern_service_basic_setup["service"]
        check_pattern_service_basic_setup["mock_workspace"]
        check_pattern_service_basic_setup["mock_context"]
        check_pattern_service_basic_setup["mock_component"]
        # Setup pattern matching with mock data for filtering
        match_data = {
            "workspaces": {},
            "contexts": {
                "dev-context": MagicMock(spec=Context, environment="dev"),
                "prod-context": MagicMock(spec=Context, environment="prod"),
            },
            "components": {},
        }

        # Define pattern and filters to test
        pattern = "context/**"
        filters = ["environment=dev"]

        # Mock the complete model
        mock_complete_model = match_data

        # Mock config access to return complete model
        service.config_access.get_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock filter service
        filtered_model = {
            "workspaces": {},
            "contexts": {"dev-context": match_data["contexts"]["dev-context"]},
            "components": {},
        }
        service.filter_service.apply_filters_complete = MagicMock(
            return_value=filtered_model
        )

        # Mock parse_filter_expression
        service.parse_filter_expression = MagicMock(
            return_value=("environment", "=", "dev")
        )

        # Mock PatternSelector
        with patch(
            "coregen.services.check_pattern.check_pattern_service.PatternSelector"
        ) as mock_pattern_selector:
            mock_selector_instance = MagicMock()
            mock_selector_instance.select_by_pattern.return_value = filtered_model
            mock_pattern_selector.return_value = mock_selector_instance

            # Check pattern with filters
            result = service.check_pattern([pattern], filters=filters)

            # Verify parse_filter_expression was called
            service.parse_filter_expression.assert_called_once_with(filters[0])

            # Verify filter service was called
            service.filter_service.apply_filters_complete.assert_called_once()

            # Verify filtered results
            assert "matched" in result
            assert "contexts" in result["matched"]
            assert "dev-context" in result["matched"]["contexts"]
            assert "prod-context" not in result["matched"]["contexts"]

    def test_check_pattern_show_rejected(self, check_pattern_service_basic_setup):
        """Test pattern checking with show_rejected flag."""
        # Unpack fixture
        service = check_pattern_service_basic_setup["service"]
        check_pattern_service_basic_setup["mock_workspace"]
        check_pattern_service_basic_setup["mock_context"]
        check_pattern_service_basic_setup["mock_component"]
        # Unpack fixture
        service = check_pattern_service_basic_setup["service"]
        # Setup pattern matching with some data
        match_data = {
            "workspaces": {},
            "contexts": {"matched-context": MagicMock(spec=Context)},
            "components": {},
        }

        # Define pattern to test
        pattern = "context/test-*"

        # Mock the complete model with both matched and unmatched contexts
        mock_complete_model = {
            "workspaces": {},
            "contexts": {
                "matched-context": MagicMock(spec=Context),
                "rejected-context": MagicMock(spec=Context),
            },
            "components": {},
        }

        # Mock config access to return complete model
        service.config_access.get_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock inactive filter to return the same model (not filter anything)
        service.inactive_filter_service.filter_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock PatternSelector to only match "matched-context"
        with patch(
            "coregen.services.check_pattern.check_pattern_service.PatternSelector"
        ) as mock_pattern_selector:
            mock_selector_instance = MagicMock()
            mock_selector_instance.select_by_pattern.return_value = match_data
            mock_pattern_selector.return_value = mock_selector_instance

            # Mock _find_rejected_elements
            rejected_data = {
                "contexts": {
                    "rejected-context": mock_complete_model["contexts"][
                        "rejected-context"
                    ]
                }
            }
            service._find_rejected_elements = MagicMock(return_value=rejected_data)

            # Check pattern with show_rejected flag
            result = service.check_pattern([pattern], show_rejected=True)

            # Verify _find_rejected_elements was called
            service._find_rejected_elements.assert_called_once()

            # Verify rejected data is included
            assert "rejected" in result
            assert result["rejected"] is not None
            assert "contexts" in result["rejected"]
            assert "rejected-context" in result["rejected"]["contexts"]

    def test_find_rejected_elements_real_logic(self, check_pattern_service_basic_setup):
        """Exercise the REAL _find_rejected_elements (not a stub).

        Builds matched/all-element structures and asserts the method actually
        identifies the unmatched (rejected) context and component.
        """
        service = check_pattern_service_basic_setup["service"]

        matched_context = MagicMock(spec=Context)
        matched_context.name = "matched-context"
        matched_context.environment = "dev"
        matched_context.get_all_components = MagicMock(
            return_value={"keep": MagicMock(spec=Component, name="keep")}
        )

        rejected_context = MagicMock(spec=Context)
        rejected_context.name = "rejected-context"
        rejected_context.environment = "prod"
        rejected_component = MagicMock(spec=Component)
        rejected_component.name = "drop"
        rejected_context.get_all_components = MagicMock(
            return_value={"drop": rejected_component}
        )

        all_contexts = {
            "matched-context": matched_context,
            "rejected-context": rejected_context,
        }

        # config_access drives discovery of all workspaces/contexts.
        service.config_access.find_workspaces = MagicMock(return_value=["ws"])
        service.config_access.get_all_contexts = MagicMock(return_value=all_contexts)

        # filter_service resolves the owning workspace name for each context.
        service.filter_service._get_workspace_for_context = MagicMock(return_value="ws")

        matched_elements = {
            "contexts": {"matched-context": matched_context},
            # Component keys are "<context>/<component>".
            "components": {"matched-context/keep": MagicMock()},
        }

        rejected = service._find_rejected_elements(matched_elements)

        # Rejected context identified; matched one excluded.
        assert "rejected-context" in rejected["contexts"]
        assert "matched-context" not in rejected["contexts"]
        assert rejected["contexts"]["rejected-context"]["environment"] == "prod"
        assert rejected["contexts"]["rejected-context"]["workspace"] == "ws"

        # Rejected component in the rejected context identified by composite key.
        assert "rejected-context/drop" in rejected["components"]
        # The matched component is not rejected.
        assert "matched-context/keep" not in rejected["components"]

    def test_check_pattern_analyze(self, check_pattern_service_basic_setup):
        """Test pattern checking with analyze flag."""
        # Unpack fixture
        service = check_pattern_service_basic_setup["service"]
        check_pattern_service_basic_setup["mock_workspace"]
        check_pattern_service_basic_setup["mock_context"]
        check_pattern_service_basic_setup["mock_component"]
        # Setup pattern matching data
        match_data = {
            "workspaces": {},
            "contexts": {"test-context": MagicMock(spec=Context)},
            "components": {},
        }

        # Define pattern to test
        pattern = "context/test-*"

        # Mock the complete model
        mock_complete_model = match_data

        # Mock config access to return complete model
        service.config_access.get_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock inactive filter to return the same model (not filter anything)
        service.inactive_filter_service.filter_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock PatternSelector
        with patch(
            "coregen.services.check_pattern.check_pattern_service.PatternSelector"
        ) as mock_pattern_selector:
            mock_selector_instance = MagicMock()
            mock_selector_instance.select_by_pattern.return_value = match_data
            mock_pattern_selector.return_value = mock_selector_instance

            # Mock private analysis method
            analysis_data = {
                "pattern": pattern,
                "tokens": ["context", "test-*"],
                "reason": "Pattern matched by name prefix",
                "pattern_type": "Context",
                "pattern_parts": [
                    {"segment": "context", "wildcards": []},
                    {
                        "segment": "test-*",
                        "wildcards": [
                            {
                                "type": "wildcard",
                                "description": "Matches any characters",
                            }
                        ],
                    },
                ],
                "match_attempts": ["Matched context by name prefix"],
                "examples": {
                    "matched": [
                        {
                            "path": "test-context",
                            "type": "Context",
                            "reason": "Prefix matched",
                        }
                    ],
                    "rejected": [],
                },
            }

            # Mock _analyze_pattern_matching
            service._analyze_pattern_matching = MagicMock(return_value=analysis_data)

            # Check pattern with analyze flag
            result = service.check_pattern([pattern], analyze=True)

            # Verify _analyze_pattern_matching was called
            service._analyze_pattern_matching.assert_called_once_with(pattern)

            # Verify analysis data is included
            assert "analysis" in result
            assert result["analysis"] is not None
            assert pattern in result["analysis"]
            assert result["analysis"][pattern] == analysis_data

    def test_format_results_text(self, check_pattern_service_basic_setup):
        """Test formatting results as text."""
        # Unpack fixture
        service = check_pattern_service_basic_setup["service"]
        check_pattern_service_basic_setup["mock_workspace"]
        mock_context = check_pattern_service_basic_setup["mock_context"]
        check_pattern_service_basic_setup["mock_component"]
        # Unpack fixture
        service = check_pattern_service_basic_setup["service"]
        # Setup pattern matching data
        match_data = {
            "workspaces": {},
            "contexts": {"test-ctx": mock_context},
            "components": {},
        }

        # Define pattern
        pattern = "context/test-*"

        # Mock the complete model
        mock_complete_model = match_data

        # Mock config access to return complete model
        service.config_access.get_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock inactive filter to return the same model (not filter anything)
        service.inactive_filter_service.filter_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock PatternSelector
        with patch(
            "coregen.services.check_pattern.check_pattern_service.PatternSelector"
        ) as mock_pattern_selector:
            mock_selector_instance = MagicMock()
            mock_selector_instance.select_by_pattern.return_value = match_data
            mock_pattern_selector.return_value = mock_selector_instance

            # Just verify this runs without errors
            service.check_pattern([pattern])

            # Verify PatternSelector was called
            mock_pattern_selector.assert_called()
            mock_selector_instance.select_by_pattern.assert_called_once()

    def test_format_results_json(self, check_pattern_service_basic_setup):
        """Test formatting results as JSON."""
        # Unpack fixture
        service = check_pattern_service_basic_setup["service"]
        check_pattern_service_basic_setup["mock_workspace"]
        mock_context = check_pattern_service_basic_setup["mock_context"]
        check_pattern_service_basic_setup["mock_component"]
        # Setup pattern matching data
        match_data = {
            "workspaces": {},
            "contexts": {"test-ctx": mock_context},
            "components": {},
        }

        # Define pattern
        pattern = "context/test-*"

        # Mock the complete model
        mock_complete_model = match_data

        # Mock config access to return complete model
        service.config_access.get_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock inactive filter to return the same model (not filter anything)
        service.inactive_filter_service.filter_complete_model = MagicMock(
            return_value=mock_complete_model
        )

        # Mock PatternSelector
        with patch(
            "coregen.services.check_pattern.check_pattern_service.PatternSelector"
        ) as mock_pattern_selector:
            mock_selector_instance = MagicMock()
            mock_selector_instance.select_by_pattern.return_value = match_data
            mock_pattern_selector.return_value = mock_selector_instance

            # Just verify this runs without errors
            service.check_pattern([pattern])

            # Verify PatternSelector was called
            mock_pattern_selector.assert_called()
            mock_selector_instance.select_by_pattern.assert_called_once()
