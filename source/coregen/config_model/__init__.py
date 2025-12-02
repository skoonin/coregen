"""
Configuration system for Coregen.

This module provides a comprehensive configuration management system
for Coregen, including loading, processing, and accessing configuration data.

The configuration system follows a three-level validation architecture:
1. Schema Validation: Fast checks for correct structure and types
2. Model Validation: Deeper checks for relationships and business rules
3. Path Validation: Environment-specific checks for filesystem state

Key components:
- ConfigLoader: Loads configuration files and discovers context config files
- ConfigProcessor: Processes raw dictionaries into model instances
- ConfigAccess: Provides path-based access to configuration data
- ConfigCreator: Creates new configuration dictionaries
- ConfigurationProvider: Main facade for the configuration system
- TemplateContextAdapter: Adapts configuration models for template rendering
"""

from coregen.common.logger import Logger
from coregen.config_model.access import ConfigAccess
from coregen.config_model.creator import ConfigCreator
from coregen.config_model.dictionary_validator import ConfigDictValidator
from coregen.config_model.loader import ConfigLoader
from coregen.config_model.processor import ConfigProcessor
from coregen.config_model.provider import ConfigurationProvider

# Import and initialize console output
from coregen.config_model.template_context import (
    TemplateContextAdapter,
    create_template_context,
    render_with_context,
)

# Create module-level logger
logger = Logger(__name__)

# Import module components

__all__ = [
    "ConfigurationProvider",
    "ConfigLoader",
    "ConfigProcessor",
    "ConfigAccess",
    "ConfigCreator",
    "ConfigDictValidator",
    "TemplateContextAdapter",
    "create_template_context",
    "render_with_context",
]
