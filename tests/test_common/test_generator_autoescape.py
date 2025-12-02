"""Test autoescape functionality in generator.py"""

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from coregen.common.generator import Generator as GeneratorService


@pytest.fixture
def setup_generator_autoescape() -> Generator[dict[str, Any], None, None]:
    """Set up test fixtures."""
    import shutil

    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    yield {
        "temp_dir": temp_dir,
        "temp_path": temp_path,
    }

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestGeneratorAutoescape:
    """Test suite for Jinja2 autoescape configuration based on output file type."""

    def test_autoescape_enabled_for_html_output(self, setup_generator_autoescape):
        """Test that autoescape is enabled when generating HTML files."""

        setup_generator_autoescape["temp_dir"]

        temp_path = setup_generator_autoescape["temp_path"]

        # Create a template with potential XSS content
        template_path = temp_path / "test.html.j2"
        template_path.write_text("{{ user_input }}")

        output_path = temp_path / "output.html"

        # Test with dangerous input that should be escaped
        template_values = {"user_input": "<script>alert('XSS')</script>"}

        with patch("coregen.common.generator.FileManager") as mock_fm:
            mock_instance = MagicMock()
            mock_fm.return_value = mock_instance

            errors = GeneratorService.generate(
                template_path=template_path,
                output_path=output_path,
                template_values=template_values,
                dry_run=False,
            )

            # Verify no errors
            assert errors == []

            # Check that escaped content was written
            mock_instance.create_file.assert_called_once()
            call_args = mock_instance.create_file.call_args
            content = call_args[0][1]  # Second argument is the content

            # The script tag should be escaped
            assert "&lt;script&gt;" in content
            assert "<script>" not in content

    def test_autoescape_enabled_for_xml_output(self, setup_generator_autoescape):
        """Test that autoescape is enabled when generating XML files."""

        setup_generator_autoescape["temp_dir"]

        temp_path = setup_generator_autoescape["temp_path"]

        template_path = temp_path / "test.xml.j2"
        template_path.write_text("<root>{{ data }}</root>")

        output_path = temp_path / "output.xml"

        # Test with content that needs escaping in XML
        template_values = {"data": "<tag>value & special</tag>"}

        with patch("coregen.common.generator.FileManager") as mock_fm:
            mock_instance = MagicMock()
            mock_fm.return_value = mock_instance

            errors = GeneratorService.generate(
                template_path=template_path,
                output_path=output_path,
                template_values=template_values,
                dry_run=False,
            )

            assert errors == []

            # Check that content was escaped
            mock_instance.create_file.assert_called_once()
            call_args = mock_instance.create_file.call_args
            content = call_args[0][1]

            # Special characters should be escaped
            assert "&lt;tag&gt;" in content
            assert "&amp;" in content

    def test_autoescape_disabled_for_yaml_output(self, setup_generator_autoescape):
        """Test that autoescape is disabled when generating YAML files."""

        setup_generator_autoescape["temp_dir"]

        temp_path = setup_generator_autoescape["temp_path"]

        template_path = temp_path / "test.yaml.j2"
        template_path.write_text("key: {{ value }}")

        output_path = temp_path / "output.yaml"

        # YAML content that should NOT be escaped
        template_values = {"value": "string with & and < > characters"}

        with patch("coregen.common.generator.FileManager") as mock_fm:
            mock_instance = MagicMock()
            mock_fm.return_value = mock_instance

            errors = GeneratorService.generate(
                template_path=template_path,
                output_path=output_path,
                template_values=template_values,
                dry_run=False,
            )

            assert errors == []

            # Check that content was NOT escaped
            mock_instance.create_file.assert_called_once()
            call_args = mock_instance.create_file.call_args
            content = call_args[0][1]

            # Special characters should NOT be escaped in YAML
            assert "string with & and < > characters" in content
            assert "&amp;" not in content
            assert "&lt;" not in content

    def test_autoescape_disabled_for_json_output(self, setup_generator_autoescape):
        """Test that autoescape is disabled when generating JSON files."""

        setup_generator_autoescape["temp_dir"]

        temp_path = setup_generator_autoescape["temp_path"]

        template_path = temp_path / "test.json.j2"
        template_path.write_text('{"key": "{{ value }}"}')

        output_path = temp_path / "output.json"

        # JSON content that should NOT be escaped
        template_values = {"value": "value with & and < >"}

        with patch("coregen.common.generator.FileManager") as mock_fm:
            mock_instance = MagicMock()
            mock_fm.return_value = mock_instance

            errors = GeneratorService.generate(
                template_path=template_path,
                output_path=output_path,
                template_values=template_values,
                dry_run=False,
            )

            assert errors == []

            # Check that content was NOT escaped
            mock_instance.create_file.assert_called_once()
            call_args = mock_instance.create_file.call_args
            content = call_args[0][1]

            # Special characters should NOT be escaped in JSON
            assert "value with & and < >" in content
            assert "&amp;" not in content

    def test_autoescape_disabled_for_makefile_output(self, setup_generator_autoescape):
        """Test that autoescape is disabled when generating Makefiles."""

        setup_generator_autoescape["temp_dir"]

        temp_path = setup_generator_autoescape["temp_path"]

        template_path = temp_path / "Makefile.j2"
        template_path.write_text("VAR = {{ value }}")

        output_path = temp_path / "Makefile"

        # Makefile content with special characters
        template_values = {"value": "$(shell echo 'test & < >')"}

        with patch("coregen.common.generator.FileManager") as mock_fm:
            mock_instance = MagicMock()
            mock_fm.return_value = mock_instance

            errors = GeneratorService.generate(
                template_path=template_path,
                output_path=output_path,
                template_values=template_values,
                dry_run=False,
            )

            assert errors == []

            # Check that content was NOT escaped
            mock_instance.create_file.assert_called_once()
            call_args = mock_instance.create_file.call_args
            content = call_args[0][1]

            # Shell syntax should NOT be escaped
            assert "$(shell echo 'test & < >')" in content
            assert "&amp;" not in content

    def test_autoescape_enabled_for_svg_output(self, setup_generator_autoescape):
        """Test that autoescape is enabled for SVG files."""

        setup_generator_autoescape["temp_dir"]

        temp_path = setup_generator_autoescape["temp_path"]

        template_path = temp_path / "test.svg.j2"
        template_path.write_text("<svg><text>{{ label }}</text></svg>")

        output_path = temp_path / "output.svg"

        # SVG content that could be malicious
        template_values = {"label": "<script>alert('XSS')</script>"}

        with patch("coregen.common.generator.FileManager") as mock_fm:
            mock_instance = MagicMock()
            mock_fm.return_value = mock_instance

            errors = GeneratorService.generate(
                template_path=template_path,
                output_path=output_path,
                template_values=template_values,
                dry_run=False,
            )

            assert errors == []

            # Check that content was escaped
            mock_instance.create_file.assert_called_once()
            call_args = mock_instance.create_file.call_args
            content = call_args[0][1]

            # Script tags should be escaped in SVG
            assert "&lt;script&gt;" in content
            assert "<script>" not in content

    def test_autoescape_disabled_for_no_extension(self, setup_generator_autoescape):
        """Test that autoescape is disabled for files without extension."""

        setup_generator_autoescape["temp_dir"]

        temp_path = setup_generator_autoescape["temp_path"]

        template_path = temp_path / "template.j2"
        template_path.write_text("content: {{ value }}")

        output_path = temp_path / "outputfile"  # No extension

        template_values = {"value": "text with < and >"}

        with patch("coregen.common.generator.FileManager") as mock_fm:
            mock_instance = MagicMock()
            mock_fm.return_value = mock_instance

            errors = GeneratorService.generate(
                template_path=template_path,
                output_path=output_path,
                template_values=template_values,
                dry_run=False,
            )

            assert errors == []

            # Check that content was NOT escaped
            mock_instance.create_file.assert_called_once()
            call_args = mock_instance.create_file.call_args
            content = call_args[0][1]

            # Content should NOT be escaped for files without extension
            assert "text with < and >" in content
            assert "&lt;" not in content
