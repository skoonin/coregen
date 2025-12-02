"""Tests for matrix formatter with environment field support."""

import json

import pytest

from coregen.common.formatters.matrix import MatrixFormatter


class TestMatrixFormatterEnvironment:
    """Test matrix formatter handles environment fields correctly."""

    @pytest.fixture
    def formatter(self) -> MatrixFormatter:
        """Create a matrix formatter instance."""
        return MatrixFormatter()

    def test_component_with_environment_field(self, formatter: MatrixFormatter) -> None:
        """Test component data includes environment in matrix output."""
        data = {
            "components": [
                {
                    "name": "nginx",
                    "environment": "production",
                    "context": "aws-cluster-prod",
                    "workspace": "aws-workspace",
                    "config": {
                        "active": True,
                        "required": False,
                        "for_commit": True,
                    },
                }
            ],
            "contexts": [],
            "workspaces": [],
        }

        result = formatter.format(data)
        parsed = json.loads(result)

        assert "include" in parsed
        assert len(parsed["include"]) == 1

        matrix_item = parsed["include"][0]

        # Check environment field is present
        assert "environment" in matrix_item
        assert matrix_item["environment"] == "production"

        # Check other expected fields
        assert matrix_item["component"] == "nginx"
        assert matrix_item["context"] == "aws-cluster-prod"
        assert matrix_item["workspace"] == "aws-workspace"

    def test_multiple_components_different_environments(
        self, formatter: MatrixFormatter
    ) -> None:
        """Test multiple components with different environment values."""
        data = {
            "components": [
                {
                    "name": "frontend",
                    "environment": "dev",
                    "context": "dev-context",
                    "workspace": "dev-workspace",
                },
                {
                    "name": "backend",
                    "environment": "prod",
                    "context": "prod-context",
                    "workspace": "prod-workspace",
                },
                {
                    "name": "database",
                    "environment": None,
                    "context": "test-context",
                    "workspace": "test-workspace",
                },
            ],
            "contexts": [],
            "workspaces": [],
        }

        result = formatter.format(data)
        parsed = json.loads(result)

        assert len(parsed["include"]) == 3

        # Check each component has correct environment
        items = {item["component"]: item for item in parsed["include"]}

        assert items["frontend"]["environment"] == "dev"
        assert items["backend"]["environment"] == "prod"
        assert items["database"]["environment"] is None

    def test_component_inherits_context_environment(
        self, formatter: MatrixFormatter
    ) -> None:
        """Test component gets environment from context data when available."""
        data = {
            "components": [
                {
                    "name": "service1",
                    "environment": "staging",
                    "context": "staging-ctx",
                    "workspace": "main-workspace",
                }
            ],
            "contexts": [
                {
                    "name": "staging-ctx",
                    "environment": "staging",
                    "workspace": "main-workspace",
                }
            ],
            "workspaces": [
                {
                    "name": "main-workspace",
                }
            ],
        }

        result = formatter.format(data)
        parsed = json.loads(result)

        matrix_item = parsed["include"][0]

        # Component should have environment field
        assert matrix_item["environment"] == "staging"

        # Context fields should also be present
        assert "context_name" in matrix_item
        assert matrix_item["context_name"] == "staging-ctx"
        assert "context_environment" in matrix_item
        assert matrix_item["context_environment"] == "staging"

    def test_flat_format_with_environment(self, formatter: MatrixFormatter) -> None:
        """Test flat format (from detect-changes) includes environment."""
        # Simulate detect-changes output format
        data = {
            "components": [
                {
                    "name": "app-component",
                    "environment": "qa",
                    "context": "qa-context",
                    "workspace": "qa-workspace",
                    "status": "changed",
                    "reason": "direct",
                }
            ]
        }

        result = formatter.format(data)
        parsed = json.loads(result)

        matrix_item = parsed["include"][0]

        assert "environment" in matrix_item
        assert matrix_item["environment"] == "qa"
        assert matrix_item["component"] == "app-component"

    def test_command_generation_with_environment(
        self, formatter: MatrixFormatter
    ) -> None:
        """Test command generation is not affected by environment field."""
        data = {
            "components": [
                {
                    "name": "test-comp",
                    "environment": "prod",
                    "context": "prod-ctx",
                    "workspace": "prod-ws",
                }
            ]
        }

        result = formatter.format(data)
        parsed = json.loads(result)

        matrix_item = parsed["include"][0]

        # Command should still be generated correctly
        assert "command" in matrix_item
        expected_command = (
            "cm/test-comp --filter workspace.name=prod-ws "
            "--filter context.name=prod-ctx"
        )
        assert matrix_item["command"] == expected_command

    def test_empty_environment_handling(self, formatter: MatrixFormatter) -> None:
        """Test handling of empty string environment values."""
        data = {
            "components": [
                {
                    "name": "comp1",
                    "environment": "",
                    "context": "ctx1",
                    "workspace": "ws1",
                },
                {
                    "name": "comp2",
                    "environment": "   ",  # Whitespace
                    "context": "ctx2",
                    "workspace": "ws2",
                },
            ]
        }

        result = formatter.format(data)
        parsed = json.loads(result)

        # Empty string should be preserved
        assert parsed["include"][0]["environment"] == ""
        # Whitespace should be preserved as-is
        assert parsed["include"][1]["environment"] == "   "

    def test_context_only_matrix(self, formatter: MatrixFormatter) -> None:
        """Test matrix with only contexts (no components)."""
        data = {
            "contexts": [
                {
                    "name": "context1",
                    "environment": "dev",
                    "workspace": "workspace1",
                },
                {
                    "name": "context2",
                    "environment": "prod",
                    "workspace": "workspace2",
                },
            ],
            "components": [],
            "workspaces": [],
        }

        result = formatter.format(data)
        parsed = json.loads(result)

        # Should have 2 context items
        assert len(parsed["include"]) == 2

        for item in parsed["include"]:
            assert "context" in item
            assert "workspace" in item
            # Contexts don't have top-level environment field
            assert "context_environment" in item

    def test_nested_component_config(self, formatter: MatrixFormatter) -> None:
        """Test component with nested config still gets environment field."""
        data = {
            "components": [
                {
                    "name": "complex-component",
                    "environment": "test",
                    "context": "test-context",
                    "workspace": "test-workspace",
                    "config": {
                        "active": True,
                        "required": True,
                        "for_commit": False,
                        "priority": 0,
                        "dependencies": [
                            {"name": "dep1"},
                            {"name": "dep2", "path": "/custom/path"},
                        ],
                    },
                }
            ]
        }

        result = formatter.format(data)
        parsed = json.loads(result)

        matrix_item = parsed["include"][0]

        # Environment should be at top level
        assert matrix_item["environment"] == "test"

        # Config fields should be flattened with prefix
        assert matrix_item["component_active"] is True
        assert matrix_item["component_required"] is True
        assert matrix_item["component_for_commit"] is False
        assert matrix_item["component_priority"] == 0

        # Dependencies should be handled
        assert "component_dependencies" in matrix_item
        assert len(matrix_item["component_dependencies"]) == 2
