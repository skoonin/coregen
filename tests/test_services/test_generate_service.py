"""Unit tests for the GenerateService class."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from coregen.cli.enums.enum_file_action import FileAction
from coregen.config_model.template_context import TemplateContextAdapter
from coregen.services.config.cfg_generate_service import ConfigGenerateService


class TestGenerateService:
    """Test the GenerateService class."""

    @patch("coregen.config_model.template_context.create_template_context")
    def test_generate_files_for_component(
        self, mock_create_context, generate_service, mock_workspace, mock_component
    ):
        """Test generating files for a component."""

        # Mock template context creation
        mock_template_context = MagicMock(spec=TemplateContextAdapter)
        mock_create_context.return_value = mock_template_context

        # Setup the component in the process_path_patterns result
        generate_service.process_path_patterns.return_value = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {},
            "components": {"test-context/test-component": mock_component},
        }

        # Set up component resolved paths
        mock_component.resolved_paths = {"component_path": "/mock/component/path"}

        # Mock path operations
        with patch("os.path.exists", return_value=True), patch("os.walk") as mock_walk:

            # Mock os.walk to return some files
            mock_walk.return_value = [
                ("/mock/component/path", ["dir1"], ["file1.txt", "template1.txt.j2"])
            ]

            # Call generate_files with a component pattern
            result = generate_service.generate_files(
                ["component/test-workspace/test-context/test-component"]
            )

        # Verify process_path_patterns was called
        generate_service.process_path_patterns.assert_called_once_with(
            ["component/test-workspace/test-context/test-component"]
        )

        # Verify results contain generated_files
        assert "generated_files" in result

    @patch("coregen.config_model.template_context.create_template_context")
    def test_generate_files_for_context(
        self,
        mock_create_context,
        generate_service,
        mock_workspace,
        mock_context,
        mock_component,
    ):
        """Test generating files for a context."""

        # Mock template context creation
        mock_template_context = MagicMock(spec=TemplateContextAdapter)
        mock_create_context.return_value = mock_template_context

        # Setup get_all_components to return our test component
        mock_context.get_all_components.return_value = {
            "test-component": mock_component
        }

        # Setup the context in the process_path_patterns result
        generate_service.process_path_patterns.return_value = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {"test-context": mock_context},
            "components": {"test-context/test-component": mock_component},
        }

        # Mock path operations
        with patch("os.path.exists", return_value=True), patch("os.walk") as mock_walk:

            # Mock os.walk to return some files
            mock_walk.return_value = [
                ("/mock/component/path", ["dir1"], ["file1.txt", "template1.txt.j2"])
            ]

            # Call generate_files with a context pattern
            result = generate_service.generate_files(
                ["context/test-workspace/test-context"]
            )

        # Verify process_path_patterns was called
        generate_service.process_path_patterns.assert_called_once_with(
            ["context/test-workspace/test-context"]
        )

        # Verify results
        assert "generated_files" in result
        assert "skipped_files" in result
        assert "errors" in result

    def test_generate_files_with_filters(self, generate_service, mock_workspace):
        """Test generating files with filters."""
        # Setup empty results to simulate filtering
        generate_service.process_path_patterns.return_value = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {},
            "components": {},
        }

        # Setup empty filter result to simulate filtering everything out
        generate_service.filter_service.apply_filters_complete = MagicMock(
            return_value={
                "workspaces": {"test-workspace": mock_workspace},
                "contexts": {},
                "components": {},
            }
        )

        # Call generate_files with filters
        result = generate_service.generate_files(
            ["context/test-workspace/test-context"], filters=["environment=prod"]
        )

        # Verify process_path_patterns was called
        generate_service.process_path_patterns.assert_called_once()

        # Verify filtering was applied
        generate_service.filter_service.apply_filters_complete.assert_called_once()

        # Since no components match, the result should have appropriate structure
        assert "generated_files" in result
        assert "skipped_files" in result
        assert "errors" in result

    @patch("coregen.config_model.template_context.create_template_context")
    def test_generate_files_include_inactive(
        self,
        mock_create_context,
        generate_service,
        mock_workspace,
        mock_context,
        mock_component,
    ):
        """Test generating files including inactive components."""

        # Mock template context creation
        mock_template_context = MagicMock(spec=TemplateContextAdapter)
        mock_create_context.return_value = mock_template_context

        # Set component to inactive
        mock_component.config.active = False

        # Setup the component in the process_path_patterns result
        generate_service.process_path_patterns.return_value = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {"test-context": mock_context},
            "components": {"test-context/test-component": mock_component},
        }

        # Mock path operations
        with patch("os.path.exists", return_value=True), patch("os.walk") as mock_walk:

            # Mock os.walk to return some files
            mock_walk.return_value = [
                ("/mock/component/path", ["dir1"], ["file1.txt", "template1.txt.j2"])
            ]

            # Call generate_files with include_inactive=True
            result = generate_service.generate_files(
                ["component/test-workspace/test-context/test-component"],
                include_inactive=True,
            )

        # Verify results
        assert "generated_files" in result
        assert "skipped_files" in result
        assert "errors" in result

        # Reset component to active
        mock_component.config.active = True

    @patch("coregen.config_model.template_context.create_template_context")
    def test_generate_files_skip_commit_dir(
        self,
        mock_create_context,
        generate_service,
        mock_workspace,
        mock_context,
        mock_component,
    ):
        """Test generating files with skip_commit_dir option."""

        # Mock template context creation
        mock_template_context = MagicMock(spec=TemplateContextAdapter)
        mock_create_context.return_value = mock_template_context

        # Setup the component in the process_path_patterns result
        generate_service.process_path_patterns.return_value = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {"test-context": mock_context},
            "components": {"test-context/test-component": mock_component},
        }

        # Mock path operations
        with patch("os.path.exists", return_value=True), patch("os.walk") as mock_walk:

            # Mock os.walk to return some files
            mock_walk.return_value = [
                ("/mock/component/path", ["dir1"], ["file1.txt", "template1.txt.j2"])
            ]

            # Call generate_files with skip_commit_dir=True
            result = generate_service.generate_files(
                ["component/test-workspace/test-context/test-component"],
                skip_commit_dir=True,
            )

        # Verify process_path_patterns was called
        generate_service.process_path_patterns.assert_called_once()

        # Verify results
        assert "generated_files" in result
        assert "skipped_files" in result
        assert "errors" in result

    @patch("coregen.config_model.template_context.create_template_context")
    def test_generate_files_custom_output_dir(
        self,
        mock_create_context,
        generate_service,
        mock_workspace,
        mock_context,
        mock_component,
    ):
        """Test generating files with custom output directory."""

        # Mock template context creation
        mock_template_context = MagicMock(spec=TemplateContextAdapter)
        mock_create_context.return_value = mock_template_context

        # Setup the component in the process_path_patterns result
        generate_service.process_path_patterns.return_value = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {"test-context": mock_context},
            "components": {"test-context/test-component": mock_component},
        }

        # Mock path operations
        with patch("os.path.exists", return_value=True), patch("os.walk") as mock_walk:

            # Mock os.walk to return some files
            mock_walk.return_value = [
                ("/mock/component/path", ["dir1"], ["file1.txt", "template1.txt.j2"])
            ]

            # Call generate_files with custom output directory
            custom_output = Path("/custom/output")
            result = generate_service.generate_files(
                ["component/test-workspace/test-context/test-component"],
                output_dir=custom_output,
            )

        # Verify process_path_patterns was called
        generate_service.process_path_patterns.assert_called_once()

        # Verify results
        assert "generated_files" in result
        assert "skipped_files" in result
        assert "errors" in result

    @patch("coregen.config_model.template_context.create_template_context")
    def test_generate_files_output_dir_from_config(
        self,
        mock_create_context,
        generate_service,
        mock_workspace,
        mock_context,
        mock_component,
        mock_config_provider,
    ):
        """Test that output_dir from workspace config is properly resolved when set to '.'."""

        # Mock template context creation
        mock_template_context = MagicMock(spec=TemplateContextAdapter)
        mock_create_context.return_value = mock_template_context

        # Setup workspace with output_dir set to "."
        mock_workspace.output_dir = "."

        # Setup the component in the process_path_patterns result
        generate_service.process_path_patterns.return_value = {
            "workspaces": {"test-workspace": mock_workspace},
            "contexts": {"test-context": mock_context},
            "components": {"test-context/test-component": mock_component},
        }

        # Mock path service resolution via config_provider
        mock_config_provider.path_service.resolve_workspace_paths.return_value = {
            "output_path": Path(
                "/config/root"
            )  # Simulates "." resolving to config root
        }

        # Mock path operations
        with patch("os.path.exists", return_value=True), patch("os.walk") as mock_walk:
            # Mock os.walk to return some files
            mock_walk.return_value = [
                ("/mock/component/path", ["dir1"], ["file1.txt", "template1.txt.j2"])
            ]

            # Call generate_files without explicit output_dir (should use config)
            result = generate_service.generate_files(
                ["component/test-workspace/test-context/test-component"]
            )

        # Verify path_service was called to resolve workspace paths
        mock_config_provider.path_service.resolve_workspace_paths.assert_called_once()

        # Verify results
        assert "generated_files" in result
        assert "skipped_files" in result
        assert "errors" in result

    @patch("coregen.common.console.Console")
    def test_format_results(self, mock_console_class, generate_service, mock_component):
        """Test that results from generate_files are properly structured."""

        # Setup mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Set up component resolved paths
        mock_component.resolved_paths = {"component_path": "/mock/component/path"}

        # Mock path operations
        with patch("os.path.exists", return_value=True), patch("os.walk") as mock_walk:

            # Mock os.walk to return some files
            mock_walk.return_value = [
                ("/mock/component/path", ["dir1"], ["file1.txt", "template1.txt.j2"])
            ]

            # Call generate_files with a component pattern
            result = generate_service.generate_files(
                ["component/test-workspace/test-context/test-component"]
            )

        # Verify results structure
        assert "generated_files" in result
        assert "skipped_files" in result
        assert "errors" in result


class TestConfigGenerateServiceSettings:
    """Test ConfigGenerateService integration with settings."""

    def test_generate_config_with_settings_defaults(self):
        """Test generate_config uses settings defaults when config_file_only is None."""
        # Create mocks
        mock_config = MagicMock()
        mock_config_provider = MagicMock()
        # Return the mock_config from load_config
        mock_config_provider.load_config.return_value = mock_config
        mock_config_provider.create_config.return_value = {}

        mock_file_manager = MagicMock()
        mock_workspace_initializer = MagicMock()
        mock_console = MagicMock()

        # Create test path
        config_file_path = Path("/test/config.yaml")

        # Create mock settings
        mock_settings = MagicMock()
        mock_settings.options.config.config_file_only = (
            False  # Default to initialize workspace
        )

        with patch(
            "coregen.config_model.models.settings.get_settings",
            return_value=mock_settings,
        ):
            # Create service with mocks
            service = ConfigGenerateService(
                file_manager=mock_file_manager,
                workspace_initializer=mock_workspace_initializer,
                console=mock_console,
                config_provider=mock_config_provider,
            )

            # Mock the file_action to be something other than SKIP
            service.file_action = FileAction.OVERWRITE

            # Patch the _create_new_config method to avoid file system operations
            with patch.object(
                ConfigGenerateService, "_create_new_config"
            ) as mock_create_method:
                # Call method with None for config_file_only (should use settings default)
                service.generate_config(config_file_path, config_file_only=None)

                # Check that create_new_config was called
                mock_create_method.assert_called_once()

                # Check that config_provider.load_config was called with correct config file
                mock_config_provider.load_config.assert_called_once_with(
                    config_file_path
                )

                # Verify it initialized workspace with the loaded config (settings default is False)
                mock_workspace_initializer.initialize_workspace.assert_called_once_with(
                    config=mock_config, create_contexts=True
                )

    def test_generate_config_with_explicit_config_file_only(self):
        """Test generate_config respects explicit config_file_only parameter."""
        # Create mocks
        mock_config_provider = MagicMock()
        mock_config_provider.load_config.return_value = MagicMock()
        mock_config_provider.create_config.return_value = {}

        mock_file_manager = MagicMock()
        mock_workspace_initializer = MagicMock()
        mock_console = MagicMock()

        # Create test path
        config_file_path = Path("/test/config.yaml")

        # Create mock settings with opposite default than we'll provide
        mock_settings = MagicMock()
        mock_settings.options.config.config_file_only = (
            False  # Default to initialize workspace
        )

        with patch(
            "coregen.config_model.models.settings.get_settings",
            return_value=mock_settings,
        ):
            # Patch Path.mkdir to avoid permission errors
            with patch("pathlib.Path.mkdir"):
                # Patch Path.exists to return False so it tries to create
                with patch("pathlib.Path.exists", return_value=False):
                    # Create service with mocks
                    service = ConfigGenerateService(
                        file_manager=mock_file_manager,
                        workspace_initializer=mock_workspace_initializer,
                        console=mock_console,
                        config_provider=mock_config_provider,
                    )

                    # Call method with explicit True for config_file_only (should override settings)
                    service.generate_config(config_file_path, config_file_only=True)

                    # Verify it used explicit parameter (True) and skipped workspace initialization
                    mock_workspace_initializer.initialize_workspace.assert_not_called()

    def test_generate_config_settings_default_true(self):
        """Test generate_config when settings default for config_file_only is True."""
        # Create mocks
        mock_config_provider = MagicMock()
        mock_config_provider.load_config.return_value = MagicMock()
        mock_config_provider.create_config.return_value = {}

        mock_file_manager = MagicMock()
        mock_workspace_initializer = MagicMock()
        mock_console = MagicMock()

        # Create test path
        config_file_path = Path("/test/config.yaml")

        # Create mock settings with config_file_only=True
        mock_settings = MagicMock()
        mock_settings.options.config.config_file_only = (
            True  # Default to skip workspace initialization
        )

        # Patch get_settings before creating the service
        with patch(
            "coregen.services.config.cfg_generate_service.get_settings",
            return_value=mock_settings,
        ):
            # Patch Path.mkdir to avoid permission errors
            with patch("pathlib.Path.mkdir"):
                # Patch Path.exists to return False so it tries to create
                with patch("pathlib.Path.exists", return_value=False):
                    # Create service with mocks
                    service = ConfigGenerateService(
                        file_manager=mock_file_manager,
                        workspace_initializer=mock_workspace_initializer,
                        console=mock_console,
                        config_provider=mock_config_provider,
                    )

                    # Call method with None for config_file_only (should use settings default)
                    service.generate_config(config_file_path, config_file_only=None)

                    # Verify it used settings default (True) and skipped workspace initialization
                    mock_workspace_initializer.initialize_workspace.assert_not_called()
