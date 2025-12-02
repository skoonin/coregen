# Release Guide

Complete guide for creating and managing Coregen releases.

## Quick Release Checklist

- [ ] All changes merged to `dev`
- [ ] All tests pass on `dev`: `make test`
- [ ] Create `release/X.Y.Z` branch from `dev`
- [ ] Version updated in `source/coregen/__init__.py` on release branch
- [ ] Version updated in test: `tests/test_e2e/test_config_workflow_direct.py` on release branch
- [ ] `CHANGELOG.md` updated with release date on release branch
- [ ] PR from `release/X.Y.Z` to `main` created and approved
- [ ] Resolve merge conflicts (expected - accept release branch changes with `--ours`)
- [ ] Merged to `main`
- [ ] GitHub Actions release workflow (run manually) from `main`
- [ ] Installation tested: `pip install git+...@v1.0.X`
- [ ] Version verified: `coregen --version`
- [ ] After release, increment `dev` version to next `-dev` if starting new features

## Branch Strategy

- **`main`** - Default branch, production-ready code with stable releases
- **`dev`** - Protected development branch where all feature PRs are merged first, always has `-dev` version suffix
- **`release/X.Y.Z`** - Temporary release branches created from `dev` for preparing releases
- **Workflow**: Feature branches → `dev` → `release/X.Y.Z` → `main` (via release PR)

## Version Management

### Version Format Conventions

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

### Version Location

Version is defined in **one authoritative location**:

- `source/coregen/__init__.py`: `__version__ = "1.0.1"`

**Additional files requiring version updates:**

- `tests/test_e2e/test_config_workflow_direct.py` (line ~105): Test expectation must match

The `pyproject.toml` dynamically reads this version via:

```toml
[tool.setuptools.dynamic]
version = {attr = "coregen.__version__"}
```

### Semantic Versioning

- **Major** (1.0.0): Breaking changes
- **Minor** (0.1.0): New features, backwards compatible
- **Patch** (0.0.1): Bug fixes, documentation updates

### Development Versioning

The `dev` branch always uses `-dev` suffix:

- **Format**: `X.Y.Z-dev` (e.g., `1.0.2-dev`)
- **Purpose**: Indicates unreleased changes being tested in development
- **Key principle**: `dev` branch **never** loses the `-dev` suffix
- **Workflow**:
  1. After a release (e.g., `1.0.1`), increment version on `dev` to next patch/minor with `-dev` suffix (e.g., `1.0.2-dev`)
  2. Feature PRs merge to `dev` and update `CHANGELOG.md` under the `-dev` version section
  3. When ready to release, create `release/X.Y.Z` branch from `dev`
  4. On the release branch only, remove `-dev` suffix and add release date to CHANGELOG
  5. Merge release branch to `main`, create tag
  6. After release, optionally increment `dev` version to next `-dev` (e.g., `1.0.3-dev`) if starting new features

**Example CHANGELOG.md structure:**

```markdown
## 1.0.2-dev

### Fixed
- Fix for feature X (#123)

## 1.0.1 - 2025-01-16

### Added
- Released feature Y
```

## Release Process

### Step 1: Verify Dev Branch

```bash
# Ensure you're on dev branch with latest changes
git checkout dev
git pull origin dev

# Run full test suite to ensure everything passes
make test
make lint
make type-check
```

### Step 2: Create Release Branch

```bash
# Create release branch from dev (dev stays at X.Y.Z-dev)
git checkout -b release/1.0.2

# Release branch is now ready for version updates
```

### Step 3: Update Version on Release Branch

On the `release/1.0.2` branch only:

- [ ] Update version in `source/coregen/__init__.py` (remove `-dev` suffix: `1.0.2-dev` → `1.0.2`)
- [ ] Update version in test file: `tests/test_e2e/test_config_workflow_direct.py` (line ~105)
- [ ] Update `CHANGELOG.md`: change version header from `## 1.0.2-dev` to `## 1.0.2 - YYYY-MM-DD`
- [ ] Review all changes in `CHANGELOG.md` are accurate and complete
- [ ] Commit changes: `git commit -m "chore: prepare release v1.0.2"`

### Step 4: Create Release PR

```bash
# Create PR from release branch to main
gh pr create --base main --head release/1.0.2 \
  --title "Release v1.0.2" \
  --body "Release notes here"

# Or via GitHub UI:
# 1. Go to Pull requests
# 2. New pull request
# 3. Base: main ← Compare: release/1.0.2
```

### Step 5: Resolve Merge Conflicts (Expected)

**Conflicts are normal** because `dev` and `main` have divergent histories. After each release, `dev` continues accumulating commits while `main` stays at the previous release. When merging the release PR, Git must reconcile these divergent states.

**Why conflicts happen:**

- `dev` accumulated 20-30+ commits since last release
- These commits modified files that exist in `main` from the previous release
- File reorganizations, test updates, and code changes create conflicts
- Even though `main` itself didn't change, the histories diverged

**Resolution process:**

```bash
# Ensure you're on the release branch
git checkout release/1.0.2

# Merge main into release branch to identify conflicts
git fetch origin main
git merge origin/main

# Resolve all conflicts by accepting release branch changes
# For content conflicts (most common):
git checkout --ours CHANGELOG.md source/coregen/__init__.py Makefile tests/...

# For modify/delete conflicts (files deleted in dev):
git rm <file-that-was-deleted-on-dev>

# For add/add conflicts (new files):
git checkout --ours <new-file-from-dev>

# Stage all resolved changes
git add -A

# Commit the merge
git commit -m "Merge branch 'main' into release/1.0.2

Resolved conflicts by accepting release branch changes"

# Push the resolution
git push origin release/1.0.2
```

**Strategy**: Always accept release branch changes (`--ours`) since it contains the latest complete state from `dev`. The release branch represents what `main` should become.

### Step 6: Merge to Main

After PR approval and merge:

```bash
git checkout main
git pull origin main

# Delete release branch (no longer needed)
git branch -d release/1.0.2
git push origin --delete release/1.0.2
```

### Step 7: Create Release

Use GitHub Actions workflow:

1. Go to **Actions** tab in GitHub
2. Select **"Coregen Release"** workflow
3. Click **"Run workflow"**
4. Select **`main` branch** as target
5. Optionally check "Force release" if replacing an existing release

The workflow automatically:

- Detects version from `source/coregen/__init__.py`
- Runs tests to verify functionality
- Creates git tag and GitHub release from `main`
- Generates release notes

### Step 8: Post-Release Verification

```bash
# Test installation from release tag
pip install git+https://github.com/skoonin/coregen.git@v1.0.2

# Verify version
coregen --version  # Should show: v1.0.2

# Test basic functionality
coregen --help
```

### Step 9: Prepare Dev Branch for Next Release

After releasing to `main`, update `dev` branch for the next development cycle:

```bash
# Checkout dev branch
git checkout dev
git pull origin main  # Pull the release changes

# Increment version with -dev suffix in source/coregen/__init__.py
# Example: __version__ = "1.0.2" → __version__ = "1.0.3-dev"

# Add new version section to CHANGELOG.md
# Example:
## 1.0.3-dev

## 1.0.2 - 2025-01-16
...

# Commit and push
git add source/coregen/__init__.py CHANGELOG.md
git commit -m "chore: bump version to 1.0.3-dev"
git push origin dev
```

## Manual Release Process (If Needed)

### Creating Tags Manually

```bash
# Ensure you're on main with merged release
git checkout main
git pull origin main

# Create and push tag
git tag -a v1.0.2 -m "Release version 1.0.2"
git push origin v1.0.2

# Create GitHub release
gh release create v1.0.2 \
  --title "Coregen v1.0.2" \
  --notes "Release notes here"
```

## Installation Methods

### From Latest Release (Recommended)

```bash
# Latest stable from main
pip install git+https://github.com/skoonin/coregen.git

# Specific version
pip install git+https://github.com/skoonin/coregen.git@v1.0.2
```

### Development Installation

```bash
# Clone and install in editable mode
git clone https://github.com/skoonin/coregen.git
cd coregen
pip install -e .
```

## Rollback Strategy

### Hotfix Approach (Recommended)

If a release has issues, create a patch:

```bash
# Fix issue on dev branch
git checkout dev
# ... make fixes ...
git commit -m "Fix: critical bug in v1.0.2"

# Fast-track to main
gh pr create --base main --head dev \
  --title "Hotfix v1.0.3" \
  --body "Fixes critical issue in v1.0.2"

# After merge, create new release v1.0.3
```

### Tag Removal (Emergency Only)

```bash
# Remove local tag
git tag -d v1.0.2

# Remove remote tag
git push origin --delete v1.0.2

# Delete GitHub release
gh release delete v1.0.2
```

## Best Practices

1. **Always release from `main`** after merging from `dev`
2. **Test the release** immediately after creating
3. **Use semantic versioning** consistently
4. **Document breaking changes** clearly in CHANGELOG
5. **Keep releases small** and frequent
6. **Tag every release** for easy rollback
