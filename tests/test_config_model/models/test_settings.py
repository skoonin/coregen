"""Tests for config.models.settings module."""

from coregen.config_model.models.settings import CoregenSettings, get_settings


class TestCoregenSettings:
    """Tests for CoregenSettings."""

    def test_get_settings_returns_instance(self):
        """Should return a CoregenSettings instance."""
        settings = get_settings()
        assert isinstance(settings, CoregenSettings)

    def test_settings_has_expected_sections(self):
        """Should have all expected sections."""
        settings = CoregenSettings()
        assert hasattr(settings, "system")
        assert hasattr(settings, "workspace")
        assert hasattr(settings, "context")
        assert hasattr(settings, "component")
        assert hasattr(settings, "paths")
        assert hasattr(settings, "options")

    def test_get_defaults_returns_flattened_dict(self):
        """Should return a flattened dictionary of defaults."""
        settings = CoregenSettings()
        defaults = settings.get_defaults()
        assert isinstance(defaults, dict)
        # Check for some expected defaults
        assert "workspace_name" in defaults
        assert "context_type" in defaults
        assert "component_type" in defaults

    def test_get_model_schema(self):
        """Should return a JSON schema for the model."""
        settings = CoregenSettings()
        schema = settings.get_model_schema()
        assert isinstance(schema, dict)
        assert "title" in schema
        assert schema["title"] == "CoregenSettings"

    def test_get_yaml_schema(self):
        """Should return a YAML schema for the model."""
        settings = CoregenSettings()
        yaml_schema = settings.get_yaml_schema()
        assert isinstance(yaml_schema, str)
        # Basic check that it looks like YAML
        assert ":" in yaml_schema
        assert "title: CoregenSettings" in yaml_schema
