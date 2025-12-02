# Configuration Pattern

## Pattern Name and Purpose

**Configuration Pattern** - Manages application settings, defaults, and configuration loading with proper precedence and validation using Pydantic models.

## When to Use

- **ALWAYS** when accessing application settings
- **ALWAYS** when defining new configuration options
- **ALWAYS** use `get_settings()` singleton
- **NEVER** hardcode configuration values
- **NEVER** create multiple Settings instances

## Implementation Checklist

- [ ] Use `get_settings()` to access settings
- [ ] Define configuration in Pydantic models
- [ ] Follow precedence: CLI args → env vars → config file → defaults
- [ ] Use appropriate settings section (options, system, etc.)
- [ ] Document new settings with Field descriptions
- [ ] Support environment variables with CG\_ prefix
- [ ] Validate configuration with Pydantic

## Code Examples

### ✓CORRECT Settings Access

```python
# Location: Any module needing settings

from config_model.models.settings import get_settings

# Get settings singleton
settings = get_settings()

# Access settings values
default_format = settings.options.global_defaults.output_format
file_action = settings.options.global_options.file_action
config_file = settings.system.config_file_name

# Use in option defaults
def callback(
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--output",
            "-o",
            help="Output format",
        ),
    ] = settings.options.your_command.output_format,  # Default from settings
):
    pass
```

### ✓CORRECT Configuration Model

```python
# Location: source/coregen/config_model/models/options/*.py

from typing import Annotated
from pydantic import BaseModel, Field

class YourCommandOptions(BaseModel):
    """Configuration options for your-command."""

    output_format: Annotated[
        str,
        Field(
            default="text",
            description="Default output format for your-command",
            json_schema_extra={"env": "CG_YOUR_COMMAND_OUTPUT_FORMAT"}
        )
    ] = "text"

    timeout: Annotated[
        int,
        Field(
            default=30,
            gt=0,
            description="Operation timeout in seconds",
            json_schema_extra={"env": "CG_YOUR_COMMAND_TIMEOUT"}
        )
    ] = 30

    enable_cache: Annotated[
        bool,
        Field(
            default=True,
            description="Enable result caching",
            json_schema_extra={"env": "CG_YOUR_COMMAND_ENABLE_CACHE"}
        )
    ] = True
```

### ✓CORRECT Settings Structure

```python
# Location: source/coregen/config_model/models/settings.py

class Settings(BaseModel):
    """Main settings model structure."""

    # System configuration
    system: SystemSettings = Field(
        default_factory=SystemSettings,
        description="System-wide settings"
    )

    # Command options
    options: OptionsSettings = Field(
        default_factory=OptionsSettings,
        description="Command-specific options"
    )

    # Template settings
    templates: TemplateSettings = Field(
        default_factory=TemplateSettings,
        description="Template configuration"
    )

# Singleton pattern
_settings_instance: Settings | None = None

def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
```

### ✗ INCORRECT Implementation (Anti-patterns)

```python
# DON'T DO THIS - Creating new settings instance
settings = Settings()  # WRONG: Use get_settings()

# DON'T DO THIS - Hardcoding values
DEFAULT_TIMEOUT = 30  # WRONG: Put in settings
output_format = "json"  # WRONG: Use settings

# DON'T DO THIS - Direct environment access
import os
verbose = os.getenv("VERBOSE", "false")  # WRONG: Use settings

# DON'T DO THIS - Mutable defaults
class BadOptions(BaseModel):
    items: list = []  # WRONG: Mutable default
    # Correct:
    items: list = Field(default_factory=list)
```

## Configuration Precedence

Settings are loaded with the following precedence (highest to lowest):

1. **CLI Arguments** - Direct command-line flags
2. **Environment Variables** - CG\_ prefixed vars
3. **Config File** - .cgconfig.yaml values
4. **Settings Defaults** - Pydantic model defaults

### Example Precedence

```bash
# Default in settings: output_format = "text"
# Config file has: output_format: yaml
# Environment has: CG_OUTPUT_FORMAT=json
# CLI has: --output table

# Result: output_format = "table" (CLI wins)
```

## Common Mistakes

1. **Creating multiple Settings instances** - Use singleton
2. **Hardcoding configuration values** - Use settings
3. **Not documenting Field descriptions** - Help future developers
4. **Using mutable defaults** - Use default_factory
5. **Wrong environment variable names** - Use CG\_ prefix

## Testing the Pattern

### Unit Test Example

```python
# Location: /workspace/tests/config_model/test_settings.py

import pytest
from unittest.mock import patch
from config_model.models.settings import get_settings, Settings

class TestSettings:
    """Test configuration pattern implementation."""

    @pytest.fixture
    def clean_settings(self):
        """Reset settings singleton for testing."""
        # Clear singleton
        import config_model.models.settings
        config_model.models.settings._settings_instance = None
        yield
        # Clean up
        config_model.models.settings._settings_instance = None

    def test_settings_singleton(self, clean_settings):
        """Test get_settings returns same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_environment_override(self, clean_settings):
        """Test environment variables override defaults."""
        with patch.dict("os.environ", {"CG_DRY_RUN": "true"}):
            settings = get_settings()
            assert settings.options.global_options.dry_run is True

    def test_settings_validation(self):
        """Test Pydantic validation works."""
        from config_model.models.options import YourCommandOptions

        # Valid settings
        options = YourCommandOptions(timeout=60)
        assert options.timeout == 60

        # Invalid settings should raise
        with pytest.raises(ValidationError):
            YourCommandOptions(timeout=-1)  # Must be > 0
```

### Testing with Mock Settings

```python
@pytest.fixture
def mock_settings(tmp_path):
    """Provide mock settings for testing."""
    mock = MagicMock(spec=Settings)
    mock.options.global_options.dry_run = False
    mock.options.global_options.verbose = True
    mock.system.config_file_name = ".cgconfig.yaml"

    with patch("config_model.models.settings.get_settings") as mock_get:
        mock_get.return_value = mock
        yield mock
```

## For AI Workers

### Before Making Changes

1. Check if setting already exists
2. Find appropriate section in settings
3. Look for related configuration
4. Check environment variable naming

### When Implementing

1. Always use get_settings() singleton
2. Add new settings to appropriate model
3. Include Field descriptions
4. Follow CG\_ prefix for env vars
5. Use proper validation constraints

### After Implementation

1. Test with different precedence levels
2. Verify environment variable works
3. Update documentation
4. Add to .cgconfig.yaml.example if needed

## Settings Organization

### Directory Structure

```
source/coregen/config_model/
├── models/
│   ├── settings.py          # Main Settings class
│   ├── options/
│   │   ├── __init__.py
│   │   ├── global_options.py    # Global CLI options
│   │   ├── get_options.py       # Get command options
│   │   └── your_options.py      # Your command options
│   ├── system/
│   │   └── system_settings.py   # System configuration
│   └── templates/
│       └── template_settings.py  # Template settings
```

### Adding New Settings

1. **Identify section**: Is it a command option, system setting, or template config?
2. **Create/update model**: Add to appropriate Pydantic model
3. **Document**: Add Field description
4. **Set defaults**: Provide sensible defaults
5. **Add validation**: Use Pydantic validators if needed

## Environment Variables

### Naming Convention

- Always prefix with `CG_`
- Use UPPER_SNAKE_CASE
- Match setting structure

### Examples

```bash
# Global options
CG_DRY_RUN=true
CG_VERBOSE=true
CG_LOG_LEVEL=debug

# Command-specific
CG_GET_OUTPUT_FORMAT=json
CG_GENERATE_TEMPLATE_PATH=/custom/path

# System settings
CG_CONFIG_FILE_NAME=.myconfig.yaml
```

## Related Patterns

- [Global Options Pattern](./global-options-pattern.md) - Uses settings for defaults
- [Service Layer Pattern](./service-layer-pattern.md) - Services access settings
- [CLI Command Pattern](./cli-command-pattern.md) - Commands use settings defaults

## Configuration File Format

### Example .cgconfig.yaml

```yaml
# Coregen configuration file
version: "1.0"

# Global options defaults
options:
  global_options:
    dry_run: false
    verbose: true
    file_action: "ask"

  # Command-specific options
  get:
    output_format: "yaml"
    include_inactive: true

  generate:
    skip_confirmation: false

# System configuration
system:
  template_paths:
    - "./templates"
    - "~/.coregen/templates"
```

## References

- `source/coregen/config_model/models/` - Settings models
- `/workspace/.cgconfig.yaml.example` - Example configuration
- Pydantic documentation: https://docs.pydantic.dev/
