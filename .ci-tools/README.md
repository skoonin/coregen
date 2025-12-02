# Coregen CI Tools

Development and CI/CD utility scripts for the Coregen project.

## Notes

- These are mostly used in our Makefile and CI/CD pipelines, rarely run directly
- All scripts are designed to work from the repository root

## Scripts

### detect-python.sh

Find suitable Python 3.11+ installation and return path to executable.

```bash
./detect-python.sh
```

Searches for Python 3.11+ in priority order:

1. `.venv/bin/python` (virtual environment)
2. `python3.11`, `python3.12`, `python3.13` (system)
3. `python3` (system default)
4. Homebrew paths on macOS (`/opt/homebrew/bin/python3`, `/usr/local/bin/python3`)

Validates version is 3.11+ and returns absolute path to executable. Exits with error if no suitable Python found.

### setup-venv.sh

Create virtual environment and install project dependencies from pyproject.toml.

```bash
./setup-venv.sh
```

**What it does:**

- Uses `detect-python.sh` to find Python 3.11+
- Creates `.venv/` if it doesn't exist
- Upgrades pip, setuptools, and wheel
- Installs project with dev dependencies: `pip install -e ".[dev]"`

**Prerequisites:**

- Python 3.11+ must be available
- `pyproject.toml` must exist in current directory

### check-setup.sh

Validate development environment including Python version, venv health, and dependencies.

```bash
./check-setup.sh
```

**Checks performed:**

- ✓ Python 3.11+ available
- ✓ Virtual environment exists (`.venv` on host, `/opt/venv` in container)
- ✓ Virtual environment activated
- ✓ `pyproject.toml` present
- ✓ `patchelf` installed (Linux only, for standalone builds)

Exits with error code equal to number of failed checks. Use in CI/CD pipelines or before running tests.

### cli-tree.py

Typer CLI command structure visualizer. Analyzes Python files to find and display Typer applications as a tree.

```bash
python .ci-tools/cli-tree.py <file> [options]
python .ci-tools/cli-tree.py --example
```

**Options:**

- `--verbose, -v` - Show detailed import detection information
- `--example, -e` - Show example app structure
- `--show-help` - Include help text for commands and options

**Example:**

```bash
# Visualize the main CLI
python .ci-tools/cli-tree.py source/coregen/main.py

# Show example with help text
python .ci-tools/cli-tree.py --example --show-help

# Debug import issues
python .ci-tools/cli-tree.py source/coregen/cli/cli.py --verbose
```

### clean-commit.sh

Find and clean resolved commit directories from coregen contexts.

```bash
./clean-commit.sh [--dry-run|--clean] [--config|-c CONFIG_FILE]
```

**Options:**

- `--dry-run, -d` - Show what would be cleaned (default)
- `--clean, -c` - Actually remove the directories
- `--config, -cf CONFIG_FILE` - Path to .cgconfig.yaml (auto-detected if not provided)

**What it does:**

- Queries `coregen config view enhanced` for resolved commit_dir paths
- Identifies existing generated directories
- Removes directories when run with `--clean` flag
- Auto-detects config file (`.cgconfig.yaml` or `test_data/.cgconfig.yaml`)

**Safety:**

- Defaults to dry-run mode
- Shows all directories before removal
- Only removes directories that actually exist

### platform_utils.py

Platform detection and normalization utilities for OS, architecture, and Python version checking.

**Features:**

- Normalizes architecture names (`x86_64` → `amd64`, `aarch64` → `arm64`)
- Provides boolean helpers for OS detection
- Returns Python version as tuple
- Validates minimum Python version requirements
