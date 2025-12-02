"""Tests for config.dictionary_validator module."""

from coregen.config_model.dictionary_validator import ConfigDictValidator
from coregen.config_model.models.settings import CoregenSettings


class TestConfigDictValidator:
    """Tests for ConfigDictValidator class."""

    def test_init_with_settings(self):
        """Should initialize with custom settings."""
        settings = CoregenSettings()
        validator = ConfigDictValidator(settings)
        assert validator.settings is settings

    def test_init_without_settings(self):
        """Should initialize with default settings."""
        validator = ConfigDictValidator()
        assert isinstance(validator.settings, CoregenSettings)

    def test_validate_config_valid_structure(self):
        """Should validate a valid config structure."""
        validator = ConfigDictValidator()
        config_dict = {"workspaces": [{"name": "test-workspace"}]}
        errors = validator.validate_config(config_dict)
        assert len(errors) == 0

    def test_validate_config_not_dict(self):
        """Should return error when config is not a dict."""
        validator = ConfigDictValidator()
        config_dict = "not a dict"
        errors = validator.validate_config(config_dict)
        assert len(errors) == 1
        assert "Configuration must be a dictionary" in errors[0]

    def test_validate_version(self):
        """Should validate the version if present."""
        validator = ConfigDictValidator()
        config_dict = {"version": "1.0.0", "workspaces": [{"name": "test-workspace"}]}
        errors = validator.validate_config(config_dict)
        assert len(errors) == 0

    def test_validate_version_not_string(self):
        """Should return error when version is not a string."""
        validator = ConfigDictValidator()
        config_dict = {
            "version": 1.0,  # Not a string
            "workspaces": [{"name": "test-workspace"}],
        }
        errors = validator.validate_config(config_dict)
        assert len(errors) == 1
        assert "Version must be a string" in errors[0]

    def test_validate_missing_workspaces(self):
        """Should return error when workspaces key is missing."""
        validator = ConfigDictValidator()
        config_dict = {
            "version": "1.0.0"
            # Missing workspaces key
        }
        errors = validator.validate_config(config_dict)
        assert len(errors) == 1
        assert "missing 'workspaces' key" in errors[0]

    def test_validate_workspaces_not_list(self):
        """Should return error when workspaces is not a list."""
        validator = ConfigDictValidator()
        config_dict = {"workspaces": "not a list"}
        errors = validator.validate_config(config_dict)
        assert len(errors) == 1
        assert "'workspaces' must be a list" in errors[0]

    def test_validate_workspace_not_dict(self):
        """Should return error when a workspace is not a dict."""
        validator = ConfigDictValidator()
        config_dict = {"workspaces": ["not a dict"]}
        errors = validator.validate_config(config_dict)
        assert len(errors) == 1
        assert "workspace must be a dictionary" in errors[0]

    def test_validate_workspace_missing_name(self):
        """Should return error when workspace is missing name."""
        validator = ConfigDictValidator()
        config_dict = {
            "workspaces": [
                {
                    # Missing name key
                }
            ]
        }
        errors = validator.validate_config(config_dict)
        assert len(errors) == 1
        assert "workspace missing 'name' key" in errors[0]

    def test_validate_contexts(self):
        """Should validate contexts if present."""
        validator = ConfigDictValidator()
        config_dict = {
            "workspaces": [
                {"name": "test-workspace", "context": [{"name": "test-context"}]}
            ]
        }
        errors = validator.validate_config(config_dict)
        assert len(errors) == 0

    def test_validate_contexts_not_list(self):
        """Should return error when contexts is not a list."""
        validator = ConfigDictValidator()
        config_dict = {
            "workspaces": [
                {"name": "test-workspace", "context": "not a list"}  # Invalid
            ]
        }
        errors = validator.validate_config(config_dict)
        assert len(errors) == 1
        assert "'context' must be a list" in errors[0]

    def test_validate_context_not_dict(self):
        """Should return error when a context is not a dict."""
        validator = ConfigDictValidator()
        config_dict = {
            "workspaces": [
                {"name": "test-workspace", "context": ["not a dict"]}  # Invalid
            ]
        }
        errors = validator.validate_config(config_dict)
        assert len(errors) == 1
        assert "context entry must be a dictionary" in errors[0]

    def test_validate_context_missing_name(self):
        """Should return error when context is missing name."""
        validator = ConfigDictValidator()
        config_dict = {
            "workspaces": [
                {
                    "name": "test-workspace",
                    "context": [
                        {
                            # Missing name key
                        }
                    ],
                }
            ]
        }
        errors = validator.validate_config(config_dict)
        assert len(errors) == 1
        assert "context missing 'name' key" in errors[0]

    def test_validate_components(self):
        """Should validate components if present."""
        validator = ConfigDictValidator()
        config_dict = {
            "workspaces": [
                {
                    "name": "test-workspace",
                    "context": [
                        {
                            "name": "test-context",
                            "component": [{"name": "test-component"}],
                        }
                    ],
                }
            ]
        }
        errors = validator.validate_config(config_dict)
        assert len(errors) == 0

    def test_validate_components_not_list(self):
        """Should return error when components is not a list."""
        validator = ConfigDictValidator()
        config_dict = {
            "workspaces": [
                {
                    "name": "test-workspace",
                    "context": [
                        {"name": "test-context", "component": "not a list"}  # Invalid
                    ],
                }
            ]
        }
        errors = validator.validate_config(config_dict)
        assert len(errors) == 1
        assert "'component' must be a list" in errors[0]

    def test_validate_component_not_dict(self):
        """Should return error when a component is not a dict."""
        validator = ConfigDictValidator()
        config_dict = {
            "workspaces": [
                {
                    "name": "test-workspace",
                    "context": [
                        {"name": "test-context", "component": ["not a dict"]}  # Invalid
                    ],
                }
            ]
        }
        errors = validator.validate_config(config_dict)
        assert len(errors) == 1
        assert "component entry must be a dictionary" in errors[0]

    def test_validate_component_missing_name(self):
        """Should return error when component is missing name."""
        validator = ConfigDictValidator()
        config_dict = {
            "workspaces": [
                {
                    "name": "test-workspace",
                    "context": [
                        {
                            "name": "test-context",
                            "component": [
                                {
                                    # Missing name key
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        errors = validator.validate_config(config_dict)
        assert len(errors) == 1
        assert "component missing 'name' key" in errors[0]

    def test_validate_component_config_not_dict(self):
        """Should return error when component config is not a dict."""
        validator = ConfigDictValidator()
        config_dict = {
            "workspaces": [
                {
                    "name": "test-workspace",
                    "context": [
                        {
                            "name": "test-context",
                            "component": [
                                {
                                    "name": "test-component",
                                    "config": "not a dict",  # Invalid
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        errors = validator.validate_config(config_dict)
        assert len(errors) == 1
        assert "component 'test-component' has invalid 'config'" in errors[0]
