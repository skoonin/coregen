# CHANGELOG

## v1.0.6-dev - Unreleased

### Added

- Feature Added: Nested field listings in workspaces and contexts
- 237 unit tests for 8 services (TypeFilter, InactiveFilter, NameFilter, EntityResolution, FormatType, ConfigViewBase, DetectChangesFormatter, DetectChangesSecurity) achieving >90% coverage
- Makefile `test-parallel` target for faster testing with pytest-xdist

### Changed

- Split test_generation.py into 4 focused files (basic, templates, actions, filters)
- Updated 107 test fixtures with modern type hints (Dict → dict[K,V])
- Renamed config model tests: test_access.py → test_config_access.py, test_loader.py → test_config_loader.py
- Updated Makefile for dynamic help generation

### Removed

- 15 legacy/duplicate test files (3,873 lines): consolidated into focused test modules
- 24 duplicate E2E tests now covered by comprehensive unit tests

### Fixed

- Fixed `--changed-only` and `--deleted-only` flags not applying to matrix output format in detect-changes command
- Fixed Logger not falling back to NORMAL level when invalid `LOG_LEVEL` environment variable is provided

## v1.0.5-dev

### Added

- Added pattern/filter validation in `get` command that raises clear errors when pattern entity type doesn't match filter prefix
- Added 6 integration tests for detect-changes using fixture-based temp repos
- Added context grouping assertions to integration tests to verify sorting behavior
- Added 70+ edge case tests for regex filters (None values, numeric fields, invalid patterns)

### Changed

- **BREAKING**: Invalid regex patterns in filters now raise `ValueError` instead of silently returning no matches
  - Affects `--filter` with regex operators (`~=`, `=~`)
  - Invalid patterns like `[`, `(`, `*` will now fail fast with clear error messages
  - Users will immediately see which pattern is invalid instead of wondering why filters don't match
  - Update: Ensure regex patterns are syntactically valid before using in filters
- **BREAKING**: Git ref validation now raises exceptions for unexpected errors instead of silently returning False
  - Distinguishes "ref doesn't exist" (returns False) from "git command failed" or "repo corrupted" (raises exception)
  - Better error messages help diagnose git issues vs missing branches
- Generic None/null filtering now works for any field, not just `priority` and `config.priority`
  - Use `--filter "component.description=none"` to find components with null descriptions
  - Use `--filter "context.custom_field=null"` to find contexts with null custom fields
  - Both `none` and `null` keywords work (case-insensitive: none, None, NONE, null, NULL)
- Shortened validation error messages for pattern/filter mismatches
- Added debug logging when config files outside repo are skipped during detect-changes

### Fixed

- Fixed Pydantic serialization warnings when using `skip_validation` mode (base branch comparison)
  - `model_construct()` bypasses type coercion, leaving YAML string values as strings
  - Now manually coerces field types before constructing Component objects:
    - `priority`: string → int (ensures non-negative, coerces invalid/negative values to None)
    - `active`, `required`, `for_commit`: string → bool (handles "true", "false", "yes", "1")
  - Added debug logging when coercion fails or negative priorities are encountered
  - Added 4 comprehensive tests for type coercion edge cases
- Fixed regex operators (`~=`, `=~`) to work on numeric fields by preventing premature type conversion
- Fixed regex operators (`~=`, `=~`) to work with None/null values by converting to empty string for pattern matching
- Fixed detect-changes validation errors when comparing against base branches with old schema
- Fixed edge case where components with dependencies would fail during base branch comparison
- Fixed Context dependency validation running on base branch (now properly skips when skip_validation=True)

### Removed

- Removed 6 fragile sorting tests that depended on git state (replaced with fixture-based assertions)
- Removed unused `_branch_exists()` compatibility method (dead code with no callers)
- **BREAKING**: Removed `complete_model` deprecated parameter from `FormatTypeService.apply_format()` and `flatten_results()`
  - Parameter was never used (deprecated since filter-first architecture)
- Removed unused `temp_dir` field from defaults (zombie code - never referenced in source or tests)
  - Detect-changes hardcodes `.cgtmp` path instead of using this setting
  - Field was marked deprecated but was actually never used anywhere
- Removed entire shell completion module (zombie code - feature never enabled)
  - Deleted `source/coregen/common/completion.py` (140 lines)
  - Deleted `tests/test_common/test_completion.py` (157 lines)
  - Shell completion was globally disabled with `add_completion=False` in CLI
  - Completion code only provided static wildcards, no real config-based completion
  - Total removal: ~300 lines of untested, unused code
  - No callers were passing this parameter
  - Update: Remove `complete_model` argument from any custom calls (unlikely as it was already deprecated)
- Removed empty `_replace_null_path_with_resolved()` method (zombie code claiming backward compatibility with no callers)
- Removed stub `_get_config_based_completions()` method (unimplemented placeholder that always returned empty list)

### Documentation Updates

- Split docs into usage and developer sections
- Added comprehensive documentation on pattern prefixes and filter compatibility in `docs/usage/filter-operators.md`
- Fixed CLI reference documentation inaccuracies / inconsistencies
- Fixed 40+ broken internal documentation links across all docs directories
- Corrected Quick Start guide workflow (config generate instead of config init)
- Fixed configuration model documentation (field names, defaults, validation rules)
- Enhanced architecture pattern documentation (Global Options, Service Layer, Output Pipeline)

## v1.0.4 - 2025-10-14

### Added

- Added `skip_validation` parameter (internal) to allow detect-changes to analyze historical commits with validation errors

### Changed

- **BREAKING**: Removed `preserve_dependencies` parameter from ComponentSorterService (unused)
- Simplified ComponentSorterService to use priority-only sorting (0→1→2→...→null)
- Enhanced validation to always enforce 5 rules: (1) no duplicate priorities, (2) priority cannot depend on null, (3) dependencies must have equal/better priority, (4) null cannot depend on null, (5) no circular dependencies
- Deprecated `strict_validation` in ComponentSorterService (accepted but ignored; PathService still uses it)
- Renamed ComponentSortError to ComponentValidationError; removed unused exception classes
- Improved validation error messages with component/context names and suggested fixes

### Fixed

- Fixed test_include_required_changes_flag_enables_output to use HEAD^1 on main branch
- Fixed validation errors being silently swallowed during configuration loading
- Improved validation to report all errors at once instead of failing on first error
- Fixed table output not displaying components in priority order

## v1.0.3 - 2025-10-09

> **Note**: Version 1.0.3 was tagged but never officially released. All changes from 1.0.3 are included in version 1.0.4.

### Added

- Comprehensive integration tests for detect-changes filtering in `tests/test_services/test_detect_changes_filtering.py`
- Strict validation for component priorities and dependencies in ComponentSorterService
  - Detects duplicate priority values within same context
  - Validates priority consistency (dependencies must have ≤ priority number)
  - Enabled by default via `STRICT_VALIDATION = True` in `component_sorter_config.py`
- Refactored detect-changes filtering to use FilterService
- Added `--include-required-changes` flag to detect-changes command for optional required_changes array in JSON/YAML output
  - OFF by default to reduce output duplication (it was an unexpected output for users)
  - required_changes includes components that are both required and have changes. They trigger updates in dependent components called required_cascade.
  - Useful for debugging required component cascade logic

### Changed

- **BREAKING**: Filter operators `~=` and `=~` now use regular expression matching instead of glob patterns
  - Substring matching is now default: `name~=aws` matches any name containing "aws"
  - Both `~=` and `=~` operators are accepted and work identically

### Fixed

- Fixed detect-changes filtering and standardized usage across commands
- Fixed component dependency sorting for non-priority components (priority=None)
  - Non-priority components are now topologically sorted to respect dependencies
  - Previously sorted alphabetically only, ignoring dependency relationships
  - Affects both `get` and `detect-changes` commands
  - Added new helper method `_topo_sort_alphabetical()` for alphabetical tie-breaking
- Fixed detect-changes component sorting order to properly group components by context
  - Sorting now happens AFTER `_apply_required_cascade()` and filter operations
  - All three output arrays are now sorted: `changes`, `deleted`, and `required_changes`
  - Ensures consistent context grouping in all output formats (text, JSON, YAML, table, matrix)

### Migration Guide

The filter operators now use regular expressions instead of glob patterns. Update your scripts and commands:

```bash
# Old glob patterns
coregen get "cm/*" --filter "component.name~=*prometheus*"  # Contains
coregen get "cm/*" --filter "component.name~=prometheus*"   # Starts with

# New regex patterns
coregen get "cm/*" --filter "component.name~=prometheus"    # Contains (substring match)
coregen get "cm/*" --filter "component.name~=^prometheus"   # Starts with (anchored)
```

## v1.0.2 - 2025-10-01

### Added

- Migration script `scripts/migration/migrate_config.py` with automatic backup functionality

### Changed

- **BREAKING**: Component config field `generated` renamed to `for_commit`
- **BREAKING**: Context field `generated_dir` renamed to `commit_dir`
- **BREAKING**: CLI parameter `--skip-generated-dir` renamed to `--skip-commit-dir`
- **BREAKING**: Makefile target `clean-generated` renamed to `clean-commit`
- CI script renamed from `clean-generated.sh` to `clean-commit.sh`
- All documentation updated to use new terminology

### Fixed

- Fixed DELETE file action to remove component directories instead of entire context directory
- Fixed output_dir configuration not being respected in generate command
- Fixed detect-changes filter bug where filtered components were incorrectly showing as deleted
- Fixed detect-changes output sorting to match other coregen commands with priority and dependency-based ordering
  - Fixed ComponentSorterService to handle ComponentChange objects by checking both `component_dependencies` and `dependencies` fields
- Removed unnecessary Console.debug() noise from verbose output (29 lines removed across 6 service files)

### Migration Guide

The field renaming changes clarify that these fields are for components that need files committed to the repository (e.g., ArgoCD configs), not just temporarily generated.

**Migration Required**: Use the provided migration script to update existing configurations:

```bash
# Preview changes
python scripts/migration/migrate_config.py --dry-run ./contexts/

# Apply migration (creates backups)
python scripts/migration/migrate_config.py ./contexts/

# Remove backups after verification
find . -name '*.backup*' -delete
```

## v1.0.1 - 2025-09-16

### Added

- Environment fields (`environment` and `context_environment`) to matrix output for components in both `get` and `detect-changes` commands
- Runtime context fields (`environment`, `workspace`, `context`) to Component model for better type safety
- Added `environment` to all outputs

### Changed

- Components now use explicit field definitions instead of dynamic attributes for runtime context
- Release process shifted to using a git flow strategy: feature branches → `dev` → `main` (via release PR)
- Cleaned up cli-tree script with various mypy issues

### Removed

- Legacy static formatter methods for backward compatibility
- Environment aliasing functionality between `env` and `environment` fields

## v1.0.0 - 2025-08-14 [Initial Release]

- Initial release of the project with full functionality.
- Initial program commit by @skoonin
- bug fix: fix install paths by @skoonin
- refactor: consolidate and improve test suite organization by @skoonin
- Make System Refactor - Simplify, Fix Build and Release Targets by @skoonin
- help output cleanup by @skoonin
- fix: eliminate duplicate context entries in matrix output by @skoonin
- SRE-538 - Major refactor - Implement pip - Remove Builds by @skoonin
- v1 doc updates by @skoonin
