"""Unit tests for template generation functionality."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.generator import Generator


@pytest.fixture
def sample_template() -> Any:
    """Sample Jinja2 template content."""
    return """# {{ title }}
Description: {{ description }}
{% for item in items %}
- {{ item }}
{% endfor %}
{% if show_footer %}
Footer: {{ footer }}
{% endif %}
"""


@pytest.fixture
def template_values() -> Any:
    """Sample template values."""
    return {
        "title": "Test Document",
        "description": "This is a test document",
        "items": ["item1", "item2", "item3"],
        "show_footer": True,
        "footer": "Test Footer",
    }


def test_basic_template_generation(tmp_path, sample_template, template_values):
    """Test basic template generation with valid template and values."""
    template_path = tmp_path / "test.md.j2"
    output_path = tmp_path / "test.md"

    # Create template file
    template_path.write_text(sample_template)

    # Generate from template
    errors = Generator.generate(template_path, output_path, template_values)

    # Verify generation was successful
    assert not errors
    assert output_path.exists()
    content = output_path.read_text()
    assert "# Test Document" in content
    assert "Description: This is a test document" in content
    assert "- item1" in content
    assert "Footer: Test Footer" in content


def test_template_with_missing_variables(tmp_path):
    """Test template generation with missing required variables."""
    template = """{{ required_var }}
{{ optional_var | default('default_value') }}"""

    template_path = tmp_path / "test.j2"
    output_path = tmp_path / "test.txt"
    template_path.write_text(template)

    values = {"optional_var": "custom_value"}
    errors = Generator.generate(template_path, output_path, values)

    assert errors
    assert any("required_var" in error for error in errors)
    assert not output_path.exists()


def test_dry_run_mode(tmp_path, sample_template, template_values):
    """Test template generation in dry run mode."""
    template_path = tmp_path / "test.md.j2"
    output_path = tmp_path / "test.md"

    template_path.write_text(sample_template)

    # Generate with dry run mode
    errors = Generator.generate(
        template_path, output_path, template_values, dry_run=True
    )

    assert not errors
    assert not output_path.exists()  # File should not be created in dry run mode


def test_different_file_actions(tmp_path, sample_template, template_values):
    """Test template generation with different file action modes."""
    template_path = tmp_path / "test.md.j2"
    output_path = tmp_path / "test.md"

    template_path.write_text(sample_template)

    # Create an existing output file
    output_path.write_text("existing content")

    # Test SKIP action
    errors = Generator.generate(
        template_path, output_path, template_values, file_action=FileAction.SKIP
    )
    assert not errors
    assert output_path.read_text() == "existing content"

    # Test OVERWRITE action
    errors = Generator.generate(
        template_path, output_path, template_values, file_action=FileAction.OVERWRITE
    )
    assert not errors
    assert "# Test Document" in output_path.read_text()


def test_non_template_file_copying(tmp_path):
    """Test copying of non-template files."""
    source_path = tmp_path / "source.txt"
    output_path = tmp_path / "output.txt"
    content = "This is a regular file"

    source_path.write_text(content)

    errors = Generator.generate(source_path, output_path, {})

    assert not errors
    assert output_path.exists()
    assert output_path.read_text() == content


def test_template_with_conditional_logic(tmp_path):
    """Test template generation with conditional logic."""
    template = """{% if show_section %}
Section content
{% endif %}
{% if not hidden %}
Visible content
{% endif %}"""

    template_path = tmp_path / "test.j2"
    output_path = tmp_path / "test.txt"
    template_path.write_text(template)

    # Test with different conditions
    values = {"show_section": True, "hidden": False}
    errors = Generator.generate(template_path, output_path, values)

    assert not errors
    content = output_path.read_text()
    assert "Section content" in content
    assert "Visible content" in content


def test_template_with_nested_values(tmp_path):
    """Test template generation with nested dictionary values."""
    template = """{{ user.name }}
{{ user.address.city }}, {{ user.address.country }}
{% for skill in user.skills %}
- {{ skill }}
{% endfor %}"""

    template_path = tmp_path / "test.j2"
    output_path = tmp_path / "test.txt"
    template_path.write_text(template)

    values = {
        "user": {
            "name": "Test User",
            "address": {"city": "Test City", "country": "Test Country"},
            "skills": ["skill1", "skill2"],
        }
    }

    errors = Generator.generate(template_path, output_path, values)

    assert not errors
    content = output_path.read_text()
    assert "Test User" in content
    assert "Test City, Test Country" in content
    assert "- skill1" in content
    assert "- skill2" in content


def test_error_handling(tmp_path):
    """Test error handling for various failure scenarios."""
    template_path = tmp_path / "test.j2"
    output_path = tmp_path / "test.txt"

    # Test with non-existent template
    errors = Generator.generate(template_path / "nonexistent.j2", output_path, {})
    assert errors

    # Test with invalid template syntax
    template_path.write_text("{{ invalid syntax }")
    errors = Generator.generate(template_path, output_path, {})
    assert errors

    # Test with non-writable output path
    with patch("pathlib.Path.open", side_effect=PermissionError):
        errors = Generator.generate(template_path, output_path, {})
        assert errors


def test_output_formatting(tmp_path, sample_template, template_values):
    """Test generation without output format parameter."""
    template_path = tmp_path / "test.md.j2"
    output_path = tmp_path / "test.md"
    template_path.write_text(sample_template)

    # Generator no longer accepts output_format parameter
    errors = Generator.generate(template_path, output_path, template_values)
    assert not errors


def test_generator_uses_settings_defaults(tmp_path, mock_settings):
    """Test that Generator uses settings for default values."""
    source_path = tmp_path / "test.txt"
    output_path = tmp_path / "output.txt"
    content = "This is a test file"
    source_path.write_text(content)

    # Patch both settings and FileManager
    with (
        patch(
            "coregen.config_model.models.settings.get_settings",
            return_value=mock_settings,
        ),
        patch("coregen.common.generator.FileManager") as mock_file_manager_class,
    ):

        # Set up the mock file manager
        mock_file_manager = MagicMock()
        mock_file_manager_class.return_value = mock_file_manager

        # Call Generator with None for parameters that should use settings
        Generator.generate(
            source_path,
            output_path,
            {},
            dry_run=None,
            file_action=None,
            quiet=None,
            verbose=None,
            no_color=None,
        )

        # Verify FileManager was created with settings values
        mock_file_manager.create_file.assert_called_once()

        # Verify that FileManager was initialized with settings defaults
        _, kwargs = mock_file_manager_class.call_args
        assert kwargs["dry_run"] == mock_settings.options.global_options.dry_run
        assert kwargs["file_action"] == mock_settings.options.global_options.file_action
        assert kwargs["quiet"] == mock_settings.options.global_options.quiet
        assert kwargs["verbose"] == mock_settings.options.global_options.verbose
        # output_format removed from FileManager
        assert kwargs["no_color"] == mock_settings.options.global_options.no_color


def test_generator_parameter_overrides(tmp_path, mock_settings):
    """Test that explicit parameters override settings defaults."""
    source_path = tmp_path / "test.txt"
    output_path = tmp_path / "output.txt"
    content = "This is a test file"
    source_path.write_text(content)

    # Override values (opposite of settings defaults)
    override_dry_run = True  # Different from mock_settings
    override_file_action = FileAction.SKIP  # Different from mock_settings
    override_quiet = True  # Different from mock_settings

    # Patch both settings and FileManager
    with (
        patch(
            "coregen.config_model.models.settings.get_settings",
            return_value=mock_settings,
        ),
        patch("coregen.common.generator.FileManager") as mock_file_manager_class,
    ):

        # Set up the mock file manager
        mock_file_manager = MagicMock()
        mock_file_manager_class.return_value = mock_file_manager

        # Call Generator with explicit parameters (should override settings)
        Generator.generate(
            source_path,
            output_path,
            {},
            dry_run=override_dry_run,
            file_action=override_file_action,
            quiet=override_quiet,
            verbose=None,  # Use settings for these
            no_color=None,
        )

        # Verify FileManager was created with override values
        mock_file_manager.create_file.assert_called_once()

        # Verify that FileManager was initialized with overridden values
        _, kwargs = mock_file_manager_class.call_args
        assert kwargs["dry_run"] == override_dry_run
        assert kwargs["file_action"] == override_file_action
        assert kwargs["quiet"] == override_quiet
        # Settings values for those not overridden
        assert kwargs["verbose"] == mock_settings.options.global_options.verbose
        # output_format removed from FileManager
        assert kwargs["no_color"] == mock_settings.options.global_options.no_color
