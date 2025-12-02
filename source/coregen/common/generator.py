# static_classes/generator.py

from pathlib import Path
from typing import Any

import jinja2
from jinja2 import UndefinedError
from jinja2.exceptions import TemplateError as JinjaTemplateError
from jinja2.exceptions import TemplateSyntaxError

from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.console import Console
from coregen.common.file_manager import FileManager
from coregen.common.logger import Logger

logger = Logger(__name__)
console = Console


class Generator:
    """
    Handles template generation with Jinja2.
    Core responsibilities:
    - Generate files from templates (.j2 extension)
    - Copy non-template files as-is
    - Respect global file action settings
    - Provide clear user feedback
    """

    @staticmethod
    def generate(
        template_path: str | Path,
        output_path: str | Path,
        template_values: dict[str, Any],
        dry_run: bool | None = None,
        file_action: FileAction | None = None,
        quiet: bool | None = None,
        verbose: bool | None = None,
        no_color: bool | None = None,
        context_name: str | None = None,
    ) -> list[str]:
        """
        Generate a file from a template or copy a non-template file.

        Args:
            template_path: Path to template file (.j2) or source file
            output_path: Where to write the output
            template_values: Values to use in template rendering
            dry_run: If True, simulate operations. None means use settings default.
            file_action: How to handle existing files. None means use settings default.
            quiet: Suppress non-essential output. None means use settings default.
            verbose: Show detailed progress. None means use settings default.
            no_color: Disable colored output. None means use settings default.
            context_name: Optional name of the template context

        Returns:
            List of error messages, empty if successful
        """
        template_path = Path(template_path)
        output_path = Path(output_path)
        errors: list[str] = []

        try:
            # Get settings for default values
            from coregen.config_model.models.settings import get_settings

            settings = get_settings()
            cli_settings = settings.options.global_options

            use_dry_run = dry_run if dry_run is not None else cli_settings.dry_run
            use_file_action = (
                file_action if file_action is not None else cli_settings.file_action
            )
            use_quiet = quiet if quiet is not None else cli_settings.quiet
            use_verbose = verbose if verbose is not None else cli_settings.verbose
            use_no_color = no_color if no_color is not None else cli_settings.no_color

            # Create file manager with settings or provided values
            file_manager = FileManager(
                dry_run=use_dry_run,
                file_action=use_file_action,
                quiet=use_quiet,
                verbose=use_verbose,
                no_color=use_no_color,
            )

            # Handle template vs non-template files
            if template_path.suffix == ".j2":
                # Load and render template
                try:
                    template_dir = template_path.parent

                    # Intelligent autoescape based on output file type
                    # Extract the target extension from output_path
                    output_extension = output_path.suffix.lstrip(".").lower()

                    # Determine autoescape strategy based on output file type
                    if output_extension in ("html", "htm", "xml", "xhtml", "svg"):
                        # For web content, enable strict autoescape
                        autoescape_config = jinja2.select_autoescape(
                            enabled_extensions=("html", "htm", "xml", "xhtml", "svg"),
                            default_for_string=True,
                            default=True,
                        )
                        logger.debug(
                            f"Autoescape enabled for {output_extension} output file"
                        )
                    else:
                        # For config files (yaml, json, makefile, etc), disable autoescape
                        # to prevent interference with intended output
                        autoescape_config = False
                        logger.debug(
                            f"Autoescape disabled for {output_extension or 'no-extension'} output file"
                        )

                    env = jinja2.Environment(
                        loader=jinja2.FileSystemLoader(str(template_dir)),
                        undefined=jinja2.StrictUndefined,  # Make missing variables raise errors
                        autoescape=autoescape_config,
                        trim_blocks=True,  # Remove newlines after block tags
                        lstrip_blocks=True,  # Strip leading whitespace from blocks
                        keep_trailing_newline=True,  # Preserve final newline in templates
                        enable_async=False,  # Explicit async setting for clarity
                        optimized=True,  # Enable optimizations for better performance
                    )
                    template = env.get_template(template_path.name)

                    # Debug context keys
                    logger.debug(
                        f"Template context keys: {list(template_values.keys())}"
                    )
                    for key in template_values:
                        if isinstance(template_values[key], dict):
                            logger.debug(
                                f"Context '{key}' has keys: {list(template_values[key].keys())}"
                            )

                    content = template.render(template_values)

                except TemplateSyntaxError as e:
                    # Syntax error in Jinja2 template: include line number
                    prefix = f"Context: [yellow]{context_name or 'Unknown Context'}[/] "
                    error = (
                        f"{prefix}Template syntax error in {template_path} on line {e.lineno}: "
                        f"[deep_pink1]{e.message}[/]"
                    )
                    console.error(error)
                    errors.append(error)
                    content = None

                except JinjaTemplateError as e:
                    # Other Jinja template errors (e.g., undefined variables)
                    prefix = (
                        f"Context: [yellow]{context_name}[/] " if context_name else ""
                    )

                    error_str = str(e)

                    # Enhanced hyphen detection
                    is_hyphen_related = False
                    var_name = "unknown-variable"
                    likely_hyphenated_component = None

                    if isinstance(e, UndefinedError):
                        import re

                        # Extract the variable name from the error
                        var_match = re.search(r"'([^']+)'", error_str)
                        if var_match:
                            var_name = var_match.group(1)

                        # Check if we can locate the original expression
                        original_expression = None
                        failed_component = None

                        # Try to extract line number from traceback
                        lineno = None
                        tb = e.__traceback__
                        while tb:
                            if tb.tb_frame.f_code.co_filename.endswith(
                                template_path.name
                            ):
                                lineno = tb.tb_lineno
                                break
                            tb = tb.tb_next

                        if lineno and template_path.exists():
                            # Try to read the actual template file to extract the expression
                            try:
                                with open(template_path) as f:
                                    lines = f.readlines()
                                    if 0 < lineno <= len(lines):
                                        line = lines[lineno - 1].strip()
                                        # Extract expression between {{ and }}
                                        expr_match = re.search(r"{{\s*(.+?)\s*}}", line)
                                        if expr_match:
                                            original_expression = expr_match.group(1)

                                            # Try to identify the component with hyphens
                                            parts = original_expression.split(".")
                                            for i, part in enumerate(parts):
                                                if (
                                                    "-" in part and i > 0
                                                ):  # Skip the first part (namespace)
                                                    failed_component = part
                                                    break
                            except (OSError, PermissionError) as file_error:
                                # Log file reading errors for debugging
                                logger.debug(
                                    f"Could not read template file for error analysis: {file_error}"
                                )

                        # Check component keys for potential matches using the var_name
                        component_types = [
                            k for k, v in template_values.items() if isinstance(v, dict)
                        ]

                        for comp_type in component_types:
                            components = template_values.get(comp_type, {})
                            if isinstance(components, dict):
                                # Look for hyphenated component names that might match the error
                                for comp_name in components.keys():
                                    if "-" in comp_name:
                                        parts = comp_name.split("-")
                                        # Check if any part matches our undefined variable
                                        if var_name in parts:
                                            is_hyphen_related = True
                                            likely_hyphenated_component = comp_name
                                            break

                                # If we found a match, no need to check other component types
                                if likely_hyphenated_component:
                                    break

                        if original_expression and failed_component:
                            corrected_expr1 = original_expression.replace(
                                failed_component, f"['{failed_component}']"
                            )
                            corrected_expr2 = original_expression.replace(
                                failed_component, failed_component.replace("-", "_")
                            )

                            error = f"{prefix}Template error in {template_path} on line {lineno}: Invalid syntax using hyphens: {{ {original_expression} }}. Use brackets: {{ {corrected_expr1} }} or update the original yaml value to underscores: {{ {corrected_expr2} }}.\n"
                        elif is_hyphen_related:

                            error = f"{prefix}Template error in {template_path} on line {lineno}: Likely attempting to access a value with hyphens. Use brackets (eg app['app-name'].name) or update the value to use underscores."
                        else:
                            # Extract line number for other undefined variable errors
                            lineno = None
                            tb = e.__traceback__
                            while tb:
                                if tb.tb_frame.f_code.co_filename.endswith(
                                    template_path.name
                                ):
                                    lineno = tb.tb_lineno
                                    break
                                tb = tb.tb_next
                            lineno_info = f" on line {lineno}" if lineno else ""
                            error = f"{prefix}Template error in {template_path}{lineno_info}: [deep_pink1]{str(e)}[/]"
                    console.error(error)
                    errors.append(error)
                    content = None
                except Exception as e:
                    # Unexpected rendering errors
                    error = (
                        f"Unexpected error rendering template {template_path}: {str(e)}"
                    )
                    logger.exception(error)
                    errors.append(error)
                    if not quiet:
                        console.error(f"Error: {error}")
                    content = None

                # Only write if rendering was successful
                if content is not None:
                    file_manager.create_file(
                        output_path, content, source_perms=template_path
                    )

            else:
                # Non-template file, just copy
                logger.debug(f"Non-template file {template_path}, copying as-is")
                try:
                    content = template_path.read_text()
                    file_manager.create_file(
                        output_path, content, source_perms=template_path
                    )
                except Exception as e:
                    error = f"Error copying non-template file {template_path} to {output_path}: {str(e)}"
                    console.error(error)
                    errors.append(error)

        except Exception as e:
            error = f"Error processing file {template_path} -> {output_path}: {str(e)}"
            logger.exception(error)
            errors.append(error)
            if not quiet:
                console.error(f"Error: {error}")

        return errors  # Return collected errors at the end
