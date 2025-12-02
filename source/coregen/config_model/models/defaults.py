"""
Core configuration defaults for Coregen.

Provides global defaults and configuration rules that apply across all workspaces.
All program default values should be defined here to ensure consistency.

Model classes:
- SystemSettings: Global system settings that apply across all models
- WorkspaceSettings: Settings specifically for workspace configuration
- ContextSettings: Settings specifically for context configuration
- ComponentSettings: Settings specifically for component configuration
- PathSettings: Path resolution templates for the path resolver
- CliGlobalOptions: Global CLI option settings
- ConfigSettings: Settings specific to the config command
- GetSettings: Settings specific to the get command
- DetectChangesSettings: Settings specific to the detect-changes command
- CheckPatternSettings: Settings specific to the check-pattern command
- CliSettings: Root for all CLI-specific settings

"""

from pathlib import Path
from typing import Annotated, Any, TypeVar, cast

from pydantic import BaseModel, Field, model_validator

from coregen.cli.enums.enum_entity_type import EntityType
from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.enums.enum_format import Format
from coregen.cli.enums.enum_names_format import NamesFormat
from coregen.cli.enums.enum_output_format import (
    CheckPatternOutputFormat,
    DetectChangesOutputFormat,
    GetOutputFormat,
    OutputFormat,
)

# Type var for generic methods
T = TypeVar("T")


class GitSettings(BaseModel):
    """Settings for Git operations."""

    default_base_ref: Annotated[
        str,
        Field("HEAD~1", description="Default git ref for base comparison"),
    ]
    default_head_ref: Annotated[
        str,
        Field("HEAD", description="Default git ref for head comparison"),
    ]


class SystemSettings(BaseModel):
    """Global system settings that apply across all models."""

    config_file_name: Annotated[
        str,
        Field(
            ".cgconfig.yaml",
            description="Default configuration file name (can only be overridden via CLI option `--config-file`)",
            exclude=True,
        ),
    ]
    allowed_extra_field_types: Annotated[
        set[str],
        Field(
            default={"str", "int", "float", "bool", "list", "dict"},
            description="Types allowed for extra fields in models",
        ),
    ]


class WorkspaceSettings(BaseModel):
    """Settings specifically for workspace configuration."""

    workspace_name: Annotated[
        str,
        Field(
            "contexts",
            description="""
            Default workspace name when creating a new configuration, usually matches workspace_dir. Users need to define the path in the config to override
            """,
        ),
    ]
    archive_dir: Annotated[
        str,
        Field(
            "archive",
            description="Default directory name for archives (relative to repo root)",
        ),
    ]
    workspace_dir: Annotated[
        str,
        Field(
            "contexts",
            description="Default directory name for workspaces (relative to repo root)",
        ),
    ]
    output_dir: Annotated[
        str,
        Field(
            "output",
            description="Default directory name for output files (relative to repo root)",
        ),
    ]
    context_config_files: Annotated[
        list[str],
        Field(
            ["**/*-cgvalues.yaml"],
            description="Default patterns for discovering context config files (relative to workspace)",
        ),
    ]
    context_type: Annotated[
        str,
        Field(
            "context",
            description="Default type name for contexts in context configuration",
        ),
    ]


class ContextSettings(BaseModel):
    """Settings specifically for context configuration.

    ContextSettings is a subclass of WorkspaceSettings

    Note: Paths for contexts are set via the location of their config file by the path resolver
    """

    environment: Annotated[
        str,
        Field(
            None,
            description="Default type name for environments in context configuration",
        ),
    ]
    active: Annotated[
        bool, Field(False, description="Default active state for contexts")
    ]
    commit_dir: Annotated[
        str,
        Field(
            "for-commit",
            description="Default directory name where components for commit are copied (relative to context)",
        ),
    ]
    component_type: Annotated[
        str,
        Field(
            "component",
            description="Default type name for components in context configuration",
        ),
    ]


class ComponentSettings(BaseModel):
    """Settings specifically for component configuration."""

    active: Annotated[
        bool, Field(False, description="Default active state for components")
    ]
    for_commit: Annotated[
        bool, Field(False, description="Default for_commit state for components")
    ]
    required: Annotated[
        bool, Field(False, description="Default required state for components")
    ]
    priority: Annotated[
        int | None,
        Field(
            None,
            description="Default priority for component processing order (0 is highest, None for no priority)",
        ),
    ]


class PathSettings(BaseModel):
    """Path resolution templates for the path resolver."""

    workspace_path: Annotated[
        str,
        Field(
            "{root_path}/{workspace_dir}",
            description="Format for workspace paths. Variables: root_path, workspace_dir",
        ),
    ]
    archive_path: Annotated[
        str,
        Field(
            "{root_path}/{archive_dir}",
            description="Format for archive paths. Variables: root_path, archive_dir",
        ),
    ]
    output_path: Annotated[
        str,
        Field(
            "{root_path}/{output_dir}",
            description="Format for output paths. Variables: root_path, output_dir",
        ),
    ]
    context_path: Annotated[
        str,
        Field(
            "{workspace_path}/{name}",
            description="Format for context paths. Variables: workspace_path, name",
        ),
    ]
    commit_path: Annotated[
        str,
        Field(
            "{context_path}/{commit_dir}",
            description="Format for commit directories. Variables: context_path, commit_dir",
        ),
    ]
    component_path: Annotated[
        str,
        Field(
            "{context_path}/{name}",
            description="Format for component paths when component is directly in context path. Variables: context_path, name",
        ),
    ]

    @model_validator(mode="after")
    def validate_path_templates(self) -> "PathSettings":
        """Validate that all path templates contain required variables."""
        # Check workspace_path template
        if (
            "{root_path}" not in self.workspace_path
            or "{workspace_dir}" not in self.workspace_path
        ):
            raise ValueError(
                "workspace_path template must contain {root_path} and {workspace_dir} variables"
            )

        # Check context_path template
        if (
            "{workspace_path}" not in self.context_path
            or "{name}" not in self.context_path
        ):
            raise ValueError(
                "context_path template must contain {workspace_path} and {name} variables"
            )

        # Check component_path template
        if (
            "{context_path}" not in self.component_path
            or "{name}" not in self.component_path
        ):
            raise ValueError(
                "component_path template must contain {context_path} and {name} variables"
            )

        # component_in_dir_path validation has been removed as the template is no longer used

        # Check commit_path template
        if (
            "{context_path}" not in self.commit_path
            or "{commit_dir}" not in self.commit_path
        ):
            raise ValueError(
                "commit_path template must contain {context_path} and {commit_dir} variables"
            )

        return self


# Adding CLI-specific settings classes
class CliGlobalOptions(BaseModel):
    """Global CLI option settings that appear in the Global Options panel."""

    dry_run: Annotated[bool, Field(False, description="Default dry run setting")]

    quiet: Annotated[bool, Field(False, description="Default quiet setting")]

    verbose: Annotated[bool, Field(False, description="Default verbose setting")]

    no_color: Annotated[bool, Field(False, description="Default no color setting")]

    file_action: Annotated[
        FileAction,
        Field(FileAction.OVERWRITE, description="Default file action for CLI options"),
    ]

    config_file: Annotated[
        Path | None,
        Field(
            Path(".cgconfig.yaml"), description="Path to config file (.cgconfig.yaml)"
        ),
    ]


class CliGlobalDefaults(BaseModel):
    """Global default values for command-specific options used across multiple commands."""

    include_inactive: Annotated[
        bool,
        Field(False, description="Default include inactive setting for commands"),
    ]

    type: Annotated[
        EntityType | None,
        Field(None, description="Default entity type filter for commands"),
    ]

    name_only: Annotated[
        bool,
        Field(False, description="Default name-only setting for commands"),
    ]


class ConfigSettings(BaseModel):
    """Settings specific to the config command."""

    config_file_only: Annotated[
        bool, Field(False, description="Default config file only setting")
    ]

    # Config view command default
    view_output_format: Annotated[
        OutputFormat,
        Field(
            OutputFormat.YAML,
            description="Default output format for config view command",
        ),
    ]

    # Config schema command default
    schema_output_format: Annotated[
        OutputFormat,
        Field(
            OutputFormat.JSON,
            description="Default output format for config schema command",
        ),
    ]

    # Config init command default
    init_output_format: Annotated[
        OutputFormat,
        Field(
            OutputFormat.TEXT,
            description="Default output format for config init command",
        ),
    ]

    # Config generate command default
    generate_output_format: Annotated[
        OutputFormat,
        Field(
            OutputFormat.TEXT,
            description="Default output format for config generate command",
        ),
    ]


class GetSettings(BaseModel):
    """Settings specific to the get command."""

    format: Annotated[
        Format,
        Field(Format.NESTED, description="Default format for get command output"),
    ]

    output_format: Annotated[
        GetOutputFormat,
        Field(
            GetOutputFormat.YAML, description="Default output format for get command"
        ),
    ]


class DetectChangesSettings(BaseModel):
    """Settings specific to the detect-changes command."""

    format: Annotated[
        Format,
        Field(Format.NESTED, description="Default format for detect-changes output"),
    ]

    names_format: Annotated[
        NamesFormat,
        Field(NamesFormat.ALL, description="Default names format for detect-changes"),
    ]

    output_format: Annotated[
        DetectChangesOutputFormat,
        Field(
            DetectChangesOutputFormat.TABLE,
            description="Default output format for detect-changes command",
        ),
    ]

    name_only: Annotated[
        bool,
        Field(
            False,
            description="Default to name-only output for detect-changes",
        ),
    ]

    base_branch: Annotated[
        str,
        Field(
            "main",
            description="Default base branch for comparison",
        ),
    ]

    changed_only: Annotated[
        bool,
        Field(
            False,
            description="Show only changed components (exclude unchanged/deleted)",
        ),
    ]

    deleted_only: Annotated[
        bool,
        Field(
            False,
            description="Show only deleted components",
        ),
    ]

    keep_generated: Annotated[
        bool,
        Field(
            False,
            description="Don't delete generated files after comparison",
        ),
    ]

    include_required_changes: Annotated[
        bool,
        Field(
            False,
            description="Include required_changes array in JSON/YAML output",
        ),
    ]


class CheckPatternSettings(BaseModel):
    """Settings specific to the check-pattern command."""

    output_format: Annotated[
        CheckPatternOutputFormat,
        Field(
            CheckPatternOutputFormat.TABLE,
            description="Default output format for check-pattern command",
        ),
    ]


class CliSettings(BaseModel):
    """Root for all CLI-specific settings."""

    global_options: Annotated[
        CliGlobalOptions,
        Field(
            default_factory=CliGlobalOptions,
            description="Global CLI options that appear in the Global Options panel",
        ),
    ]

    global_defaults: Annotated[
        CliGlobalDefaults,
        Field(
            default_factory=CliGlobalDefaults,
            description="Global default values for command-specific options",
        ),
    ]

    config: Annotated[
        ConfigSettings,
        Field(
            default_factory=ConfigSettings,
            description="Settings specific to the config command",
        ),
    ]

    get: Annotated[
        GetSettings,
        Field(
            default_factory=GetSettings,
            description="Settings specific to get command",
        ),
    ]

    detect_changes: Annotated[
        DetectChangesSettings,
        Field(
            default_factory=DetectChangesSettings,
            description="Settings specific to detect-changes command",
        ),
    ]

    check_pattern: Annotated[
        CheckPatternSettings,
        Field(
            default_factory=CheckPatternSettings,
            description="Settings specific to check-pattern command",
        ),
    ]

    def get_enum_defaults(self) -> dict[type, Any]:
        """Get all enum defaults."""
        return {
            FileAction: self.global_options.file_action,
            Format: self.get.format,
            NamesFormat: self.detect_changes.names_format,
            EntityType: self.global_defaults.type,
        }

    def get_enum_default(self, enum_type: type[T]) -> T:
        """Get the default value for an enum type."""
        enum_defaults = self.get_enum_defaults()
        if enum_type not in enum_defaults:
            raise ValueError(f"No default configured for enum type: {enum_type}")
        return cast(T, enum_defaults[enum_type])

    def get_bool_defaults(self) -> dict[str, bool]:
        """Get all boolean defaults as a dictionary."""
        return {
            "dry_run": self.global_options.dry_run,
            "quiet": self.global_options.quiet,
            "verbose": self.global_options.verbose,
            "no_color": self.global_options.no_color,
            "include_inactive": self.global_defaults.include_inactive,
            "name_only": self.global_defaults.name_only,
        }
