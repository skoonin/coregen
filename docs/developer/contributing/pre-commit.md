# Git Pre-commit Hook Guide

This guide explains the Git pre-commit hook implemented in the Coregen repository to ensure code quality standards.

## Overview

The pre-commit hook automatically runs quality checks on your code before allowing commits to proceed. This helps catch issues early and maintains consistent code standards across the codebase.

## Automatic Setup

The pre-commit hook is automatically installed when you run:

```bash
make setup
```

Or you can install it separately with:

```bash
make install-pre-commit
```

## Quality Checks

The pre-commit framework runs in two phases to maximize auto-fixing and minimize commit failures:

### Phase 1: Auto-fixers (run first, automatically fix issues)

1. **File Formatting**:

   - Trailing whitespace removal
   - End-of-file fixing
   - Mixed line ending standardization (LF)
   - JSON auto-formatting

2. **Python Code Auto-fixing**:
   - **Black**: Auto-formats code to consistent style
   - **Isort**: Sorts and organizes imports
   - **Autoflake**: Removes unused imports and variables
   - **Pyupgrade**: Modernizes Python syntax to Python 3.11+ standards

### Phase 2: Validators (check for issues that can't be auto-fixed)

1. **Syntax Validation**:

   - YAML, TOML, and JSON syntax checking
   - Large file detection
   - Merge conflict detection
   - Case conflict detection

2. **Code Quality Checks**:
   - **Flake8**: PEP8 compliance and code issues (with docstring checks)
   - **Mypy**: Static type checking with strict configuration
   - **Bandit**: Security vulnerability scanning

## How This Prevents Re-commits

The two-phase approach means:

1. **Auto-fixers run first** and modify your files automatically
2. **Only validation errors** that need manual attention cause commit failures
3. **Fewer "fix formatting and re-commit" cycles**

Most common issues (formatting, unused imports, old syntax) are fixed automatically before validation runs.

If syntax errors are found, the commit will be blocked. For Black and Isort, reformatting is done automatically and staged for you. For Flake8, Pylint, and Mypy, warnings are shown but you can choose to proceed with the commit. However, be aware that these issues will cause CI failures if not fixed.

## Manual Installation

The pre-commit hooks are managed by the pre-commit framework. If you need to reinstall:

```bash
# Reinstall pre-commit hooks
pre-commit install

# Or use the make target
make install-pre-commit
```

## Bypassing the Hook

In rare cases where you need to bypass the hook:

```bash
git commit -m "Your message" --no-verify
```

WARNING: **This is not recommended** and should only be used in exceptional circumstances.

## Benefits

Using Git pre-commit hooks provides several advantages:

1. **Consistency**: Ensures all code follows the same formatting standards
2. **Early Detection**: Catches issues before they're committed
3. **CI Efficiency**: Reduces CI failures due to style issues
4. **Better Reviews**: Code reviews can focus on logic, not style
5. **Learning**: Helps developers learn best practices

## Troubleshooting

If you encounter issues with the pre-commit hook:

1. Ensure linting tools are installed: `pip install black flake8 mypy isort pylint`
2. Check that the hook is properly installed in `.git/hooks/pre-commit`
3. Make sure the hook file is executable: `chmod +x .git/hooks/pre-commit`

## Alignment with CI

The pre-commit hook is designed to align with our CI pipeline, which runs the same checks. By using the pre-commit hook, you can catch and fix issues locally before they cause CI failures.

To ensure your code passes CI:

1. Always let Black and Isort format your code automatically
2. Fix Flake8, Pylint, and Mypy warnings locally
3. Run `make lint` and `make format` before pushing to remote

## Configuration Files and Tools

The project uses a standardized set of linting and formatting tools:

| Tool | Purpose | Configuration | Auto-fixes | Notes |
|------|---------|---------------|------------|-------|
| **Black** | Code formatting | Line length 88 (default) | Yes | Formats code according to PEP 8 with some exceptions |
| **isort** | Import sorting | `.isort.cfg` | Yes | Sorts imports into stdlib, third-party, local |
| **flake8** | PEP 8 style checking | `.flake8` | No | Finds style issues and potential bugs |
| **pylint** | Static code analysis | `.pylintrc` | No | Deep code analysis for quality and maintainability |
| **mypy** | Type checking | `mypy.ini` | No | Enforces proper use of type annotations |

We explicitly do not use autopep8 since Black is our primary formatter.

## CI Behavior

In the CI pipeline, any issues detected by these tools will cause the build to fail. The pre-commit hook helps you avoid these failures by catching issues early, but allows you to proceed with a commit if needed (for Flake8, Pylint, and Mypy warnings).
