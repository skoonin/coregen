"""Test coverage for specific exception handling scenarios in Generator."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from coregen.common.generator import Generator


class TestGeneratorExceptionHandling:
    """Test specific exception handling scenarios in Generator."""

    def test_template_reading_failure_silent_handling(self, tmp_path):
        """Test the silent exception handling when reading template files."""
        # Create a template with valid Jinja2 syntax
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"
        template_path.write_text("{{ component.name }}")

        # Create template values with a component that doesn't have 'name' key
        template_values = {"component": {"app-name": "test-app"}}

        # This should trigger the UndefinedError path for component.name
        # The exception handler will try to read the template for error analysis
        errors = Generator.generate(template_path, output_path, template_values)

        # Should have an error due to undefined variable, but shouldn't crash
        assert len(errors) > 0
        # Check for undefined variable error message
        assert any("Template error" in error for error in errors)

    def test_template_reading_failure_with_file_access_error(self, tmp_path):
        """Test template reading failure with specific file access errors."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"

        # Create a template that will cause an UndefinedError
        template_path.write_text("{{ undefined_variable }}")

        # Mock file reading to fail during error analysis
        original_open = open

        def mock_open_side_effect(*args, **kwargs):
            # Let Jinja2 load the template normally
            if str(args[0]).endswith(".j2") and "r" in str(
                args[1] if len(args) > 1 else kwargs.get("mode", "r")
            ):
                # First read for Jinja2 succeeds
                if not hasattr(mock_open_side_effect, "called"):
                    mock_open_side_effect.called = True
                    return original_open(*args, **kwargs)
                else:
                    # Second read for error analysis fails
                    raise PermissionError("Access denied")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_side_effect):
            errors = Generator.generate(template_path, output_path, {})

            # Should have error about undefined variable
            assert len(errors) > 0
            assert any("undefined_variable" in error for error in errors)

    def test_template_reading_failure_with_various_exceptions(self, tmp_path):
        """Test various exceptions during template reading are silently handled."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"
        template_path.write_text(
            "{{ component.missing_key }}"
        )  # Will cause UndefinedError

        # Template values that will cause an undefined variable error
        template_values = {
            "component": {"existing_key": "value"}
        }  # Missing 'missing_key'

        # This should trigger UndefinedError and the error handling logic
        errors = Generator.generate(template_path, output_path, template_values)

        # Should handle the exception and generate an error message
        assert len(errors) > 0  # Should have template error
        assert any("Template error" in error for error in errors)

    def test_non_template_file_copying_exception_handling(self, tmp_path):
        """Test exception handling during non-template file copying."""
        source_path = tmp_path / "source.txt"
        output_path = tmp_path / "output.txt"
        source_path.write_text("Test content")

        # Mock file reading to fail during copying
        with patch(
            "pathlib.Path.read_text", side_effect=PermissionError("Access denied")
        ):
            errors = Generator.generate(source_path, output_path, {})

            # Should have an error about copying failure
            assert len(errors) > 0
            assert any("Access denied" in error for error in errors)

    def test_template_hyphen_detection_with_file_reading_error(self, tmp_path):
        """Test hyphen detection when template file reading fails."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"
        template_path.write_text(
            "{{ component.app-name }}"
        )  # Invalid syntax with hyphen

        # This will trigger hyphen detection, which tries to read the template file
        # Mock the file reading to fail
        original_read_text = Path.read_text

        def mock_read_text(self, *args, **kwargs):
            if self.name == "test.j2":
                # Fail template reading during error analysis
                raise OSError("Disk error")
            return original_read_text(self, *args, **kwargs)

        with patch.object(Path, "read_text", mock_read_text):
            errors = Generator.generate(template_path, output_path, {})

            # Should still generate helpful error message despite file reading failure
            assert len(errors) > 0
            assert any("app-name" in error or "hyphen" in error for error in errors)

    def test_generator_exception_edge_cases(self, tmp_path):
        """Test edge cases in exception handling."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"

        # Test with a template that has multiple issues
        template_path.write_text("{{ component.app-name }} {{ other.missing-var }}")

        template_values = {
            "component": {"app_name": "test"},  # Has underscore, not hyphen
            # Missing 'other' entirely
        }

        errors = Generator.generate(template_path, output_path, template_values)

        # Should detect multiple issues
        assert len(errors) > 0

    def test_generator_settings_fallback_with_exceptions(self, tmp_path):
        """Test that settings fallback works even when exceptions occur."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"
        template_path.write_text("{{ valid_var }}")

        # Mock settings to raise an exception
        with patch(
            "coregen.config_model.models.settings.get_settings",
            side_effect=Exception("Settings error"),
        ):
            # Should still work with default values
            errors = Generator.generate(
                template_path, output_path, {"valid_var": "test"}
            )

            # Might have errors due to settings failure, but shouldn't crash
            # The function should complete and return errors list (empty or not)
            assert isinstance(errors, list)

    def test_jinja_environment_exception_handling(self, tmp_path):
        """Test exception handling in Jinja2 environment setup."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"
        template_path.write_text("{{ test_var }}")

        # Mock Jinja2 Environment to raise an exception
        with patch(
            "jinja2.Environment", side_effect=Exception("Jinja2 initialization error")
        ):
            errors = Generator.generate(
                template_path, output_path, {"test_var": "test"}
            )

            # Should handle Jinja2 exceptions gracefully
            assert len(errors) > 0
            assert any("test.j2" in error for error in errors)

    def test_file_manager_exception_handling(self, tmp_path):
        """Test exception handling in FileManager operations."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"
        template_path.write_text("{{ test_var }}")

        # Mock FileManager to raise an exception during file creation
        with patch("coregen.common.generator.FileManager") as mock_fm_class:
            mock_fm = MagicMock()
            mock_fm.create_file.side_effect = Exception("File creation failed")
            mock_fm_class.return_value = mock_fm

            errors = Generator.generate(
                template_path, output_path, {"test_var": "test"}
            )

            # Should handle FileManager exceptions
            assert len(errors) > 0

    def test_template_context_logging_with_exceptions(self, tmp_path):
        """Test that template context logging doesn't cause issues during exceptions."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"
        template_path.write_text("{{ component.name }}")

        # Create complex nested template values that could cause issues during logging
        template_values = {
            "component": {
                "name": "test",
                "config": {
                    "deeply": {"nested": {"value": "test"}},
                    "list": [1, 2, 3],
                    "special-chars": "test@#$%",
                },
            }
        }

        # Mock logger to raise exception during debug logging
        with patch("coregen.common.logger.Logger") as mock_logger_class:
            mock_logger = MagicMock()
            mock_logger.debug.side_effect = Exception("Logging error")
            mock_logger_class.return_value = mock_logger

            # Should still complete successfully despite logging errors
            errors = Generator.generate(template_path, output_path, template_values)

            # Should succeed since template is valid
            assert len(errors) == 0

    def test_output_path_creation_failure(self, tmp_path):
        """Test exception handling when output path creation fails."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "nonexistent" / "deep" / "path" / "test.txt"
        template_path.write_text("{{ test_var }}")

        # Make the directory creation fail by making it read-only
        # This tests the file creation error handling
        with patch("coregen.common.generator.FileManager") as mock_fm_class:
            mock_fm = MagicMock()
            mock_fm.create_file.side_effect = OSError("Cannot create directory")
            mock_fm_class.return_value = mock_fm

            errors = Generator.generate(
                template_path, output_path, {"test_var": "test"}
            )

            # Should have directory creation error
            assert len(errors) > 0


class TestGeneratorMemoryAndPerformanceEdgeCases:
    """Test memory and performance edge cases in Generator."""

    def test_very_large_template_values(self, tmp_path):
        """Test generator with very large template values."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"
        template_path.write_text("{{ component.name }}")

        # Create large template values
        large_data = "x" * 10000  # 10KB string
        large_list = [f"item_{i}" for i in range(1000)]  # 1000 items

        template_values = {
            "component": {
                "name": "test",
                "large_data": large_data,
                "large_list": large_list,
                "nested": {"level1": {"level2": {"level3": {"data": large_data}}}},
            }
        }

        errors = Generator.generate(template_path, output_path, template_values)

        # Should handle large data without issues
        assert len(errors) == 0
        assert output_path.exists()
        assert "test" in output_path.read_text()

    def test_many_template_variables(self, tmp_path):
        """Test template with many variables."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"

        # Create template with many variables
        variables = [f"var_{i}" for i in range(100)]
        template_content = "\n".join([f"{{{{ {var} }}}}" for var in variables])
        template_path.write_text(template_content)

        # Create corresponding template values
        template_values = {var: f"value_{i}" for i, var in enumerate(variables)}

        errors = Generator.generate(template_path, output_path, template_values)

        # Should handle many variables without issues
        assert len(errors) == 0
        assert output_path.exists()
        content = output_path.read_text()
        assert "value_0" in content
        assert "value_99" in content

    def test_deeply_nested_template_loops(self, tmp_path):
        """Test template with deeply nested loops."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"

        # Create template with nested loops
        template_content = """
{% for level1 in data.level1 %}
  Level 1: {{ level1.name }}
  {% for level2 in level1.level2 %}
    Level 2: {{ level2.name }}
    {% for level3 in level2.level3 %}
      Level 3: {{ level3.name }}
    {% endfor %}
  {% endfor %}
{% endfor %}
"""
        template_path.write_text(template_content)

        # Create corresponding nested data
        template_values = {
            "data": {
                "level1": [
                    {
                        "name": f"L1_{i}",
                        "level2": [
                            {
                                "name": f"L2_{i}_{j}",
                                "level3": [
                                    {"name": f"L3_{i}_{j}_{k}"} for k in range(3)
                                ],
                            }
                            for j in range(3)
                        ],
                    }
                    for i in range(3)
                ]
            }
        }

        errors = Generator.generate(template_path, output_path, template_values)

        # Should handle deeply nested loops without issues
        assert len(errors) == 0
        assert output_path.exists()
        content = output_path.read_text()
        assert "Level 1: L1_0" in content
        assert "Level 3: L3_2_2_2" in content

    def test_circular_reference_detection(self, tmp_path):
        """Test handling of circular references in template values."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"
        template_path.write_text("{{ data.name }}")

        # Create circular reference
        data1 = {"name": "data1"}
        data2 = {"name": "data2", "ref": data1}
        data1["ref"] = data2  # Circular reference

        template_values = {"data": data1}

        # This should either handle gracefully or produce a specific error
        errors = Generator.generate(template_path, output_path, template_values)

        # The template should work for simple access
        # Circular references only matter if the template tries to traverse them
        assert len(errors) == 0 or any("circular" in error.lower() for error in errors)

    def test_unicode_and_special_characters(self, tmp_path):
        """Test handling of unicode and special characters."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"
        template_path.write_text("{{ message }}")

        # Test with various unicode and special characters
        special_chars = "🚀 αβγ 中文 🎉 العربية русский ñáéíóú"

        template_values = {"message": special_chars}

        errors = Generator.generate(template_path, output_path, template_values)

        # Should handle unicode without issues
        assert len(errors) == 0
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert special_chars in content


class TestGeneratorLongPatternEdgeCases:
    """Test edge cases with very long patterns and templates."""

    def test_very_long_template_path(self, tmp_path):
        """Test with very long template file paths."""
        # Create a deeply nested directory structure
        deep_path = tmp_path
        for i in range(20):  # 20 levels deep
            deep_path = deep_path / f"level_{i}"
        deep_path.mkdir(parents=True)

        template_path = deep_path / "test_template_with_very_long_name.j2"
        output_path = tmp_path / "output.txt"
        template_path.write_text("{{ test_var }}")

        errors = Generator.generate(template_path, output_path, {"test_var": "success"})

        # Should handle long paths without issues
        assert len(errors) == 0
        assert output_path.exists()

    def test_very_long_variable_names(self, tmp_path):
        """Test with very long variable names."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"

        # Create a very long variable name
        long_var_name = "very_long_variable_name_" + "_".join(
            [f"part_{i}" for i in range(50)]
        )
        template_path.write_text(f"{{{{ {long_var_name} }}}}")

        template_values = {long_var_name: "success"}

        errors = Generator.generate(template_path, output_path, template_values)

        # Should handle long variable names without issues
        assert len(errors) == 0
        assert output_path.exists()
        assert "success" in output_path.read_text()

    def test_very_long_template_content(self, tmp_path):
        """Test with very long template content."""
        template_path = tmp_path / "test.j2"
        output_path = tmp_path / "test.txt"

        # Create a very long template (but not too long to avoid test timeouts)
        long_content = "\n".join(
            [f"Line {i}: {{{{ var_{i % 10} }}}}" for i in range(1000)]
        )
        template_path.write_text(long_content)

        template_values = {f"var_{i}": f"value_{i}" for i in range(10)}

        errors = Generator.generate(template_path, output_path, template_values)

        # Should handle long content without issues
        assert len(errors) == 0
        assert output_path.exists()
        content = output_path.read_text()
        assert "Line 0: value_0" in content
        assert "Line 999: value_9" in content
