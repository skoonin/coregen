# Version Management

## Version Format Conventions

The project uses different version formats in different contexts:

| Context | Format | Example | Notes |
|---------|--------|---------|-------|
| **Source code** (`__init__.py`) | `X.Y.Z` or `X.Y.Z-dev` | `1.0.2-dev` | No `v` prefix |
| **Git tags** | `vX.Y.Z` or `vX.Y.Z-dev` | `v1.0.2` | Always has `v` prefix |
| **Branch names** | `release/X.Y.Z` | `release/1.0.2` | No `v` prefix |
| **CLI output** (`coregen version`) | `vX.Y.Z` or `vX.Y.Z-dev` | `v1.0.2-dev` | Adds `v` prefix for display |
| **Commit messages** | `vX.Y.Z` | `chore: prepare release v1.0.2` | Use `v` prefix |
| **PR titles** | `vX.Y.Z` | `Release v1.0.2` | Use `v` prefix |
| **CHANGELOG headers** | `vX.Y.Z` or `vX.Y.Z-dev` | `## v1.0.2 - 2025-01-16` | Use `v` prefix |

## Current Version

```bash
# Check current version
python -c "from source.coregen import __version__; print(__version__)"
# or
coregen version
```

## Version Location

The single source of truth for the version is:

- `source/coregen/__init__.py` - Contains `__version__ = "1.0.0"`

## Manual Version Updates

Versions are updated manually by editing `source/coregen/__init__.py`:

```python
__version__ = "1.0.1"  # Update this line
```

## Release Workflow

### Release Branch Process (Recommended)

1. **Create release branch from `dev`**:

   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b release/1.0.2
   ```

2. **Update version on release branch**:
   - Edit `source/coregen/__init__.py`: `1.0.2-dev` → `1.0.2`
   - Edit `tests/test_e2e/test_config_workflow_direct.py`: Update version assertion
   - Edit `CHANGELOG.md`: Add release date to version header
   - Commit: `git commit -m "chore: prepare release v1.0.2"`

3. **Create PR from release branch to `main`**:

   ```bash
   gh pr create --base main --head release/1.0.2 \
     --title "Release v1.0.2"
   ```

4. **After PR merged, create release**:
   - Go to GitHub Actions → "Coregen Release" workflow
   - Click "Run workflow" from `main` branch
   - This creates tag and GitHub release automatically

5. **Clean up release branch**:

   ```bash
   git branch -d release/1.0.2
   git push origin --delete release/1.0.2
   ```

### Manual Tag Creation

If not using GitHub Actions workflow:

1. **After release branch merged to `main`**:

   ```bash
   git checkout main
   git pull origin main
   git tag v1.0.2
   git push origin v1.0.2
   gh release create v1.0.2 --generate-notes
   ```

## Semantic Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)
- **PRERELEASE**: Development versions (alpha, beta, rc1, etc.)

### Development Versions

The `dev` branch always uses `-dev` suffix:

- **Format**: `X.Y.Z-dev` (e.g., `1.0.2-dev`)
- **Purpose**: Clearly marks code as unreleased and under active development
- **Key principle**: `dev` branch **never** loses the `-dev` suffix
- **Workflow**:
  1. After releasing `1.0.1` to `main`, update `dev` to `1.0.2-dev`
  2. All feature PRs merge to `dev` with this version
  3. When ready to release, create `release/1.0.2` branch from `dev`
  4. On release branch only, remove `-dev` suffix
  5. Merge release branch to `main`, create tag
  6. Optionally increment `dev` to next `-dev` (e.g., `1.0.3-dev`) if starting new features

**Example progression:**

```
dev: 1.0.2-dev (always) → release/1.0.2: 1.0.2 → main: 1.0.2
dev: 1.0.3-dev (always) → release/1.0.3: 1.0.3 → main: 1.0.3
```

## GitHub Workflow Integration

### Automated Releases

The GitHub workflow `.github/workflows/cd-release.yaml` cuts a release from the
version already committed in `source/coregen/__init__.py`. Bump the version
manually before running the workflow.

1. **Bump the version** in `source/coregen/__init__.py` and merge it to `main`
2. **Go to Actions tab** in GitHub
3. **Select "Coregen Release" workflow**
4. **Click "Run workflow"**
5. **Optionally enable `force_release`** to delete and recreate an existing release

The workflow reads `__version__` from `source/coregen/__init__.py` (the only
relevant decision is `force_release`; there is no version input). It then:

- Validates the version is semver and the tag does not already exist
- Runs the full test suite
- Creates the git tag
- Creates the GitHub release with generated notes

### CI/CD Integration

The CI workflow runs on every push and PR:

- **Test suite**: Runs `make test` on all changes
- **Code quality**: Validates formatting and type checking

This ensures every change is tested and release-ready.

## Distribution Methods

### Primary: Git-Based Installation

```bash
# Latest version from main branch
pip install git+https://github.com/skoonin/coregen.git

# Specific version/tag
pip install git+https://github.com/skoonin/coregen.git@v1.0.0

# Development installation
git clone https://github.com/skoonin/coregen.git
cd coregen
pip install -e .
```
