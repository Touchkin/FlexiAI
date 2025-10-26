# Release Process Guide

This document describes how to create a new release of FlexiAI.

## Prerequisites

Before creating a release, ensure:

- [ ] All tests are passing on `main` branch
- [ ] Documentation is up to date
- [ ] CHANGELOG.md is updated with new version
- [ ] Version number is bumped in `pyproject.toml`
- [ ] All security checks pass
- [ ] Pre-commit hooks are satisfied

## Version Numbering

FlexiAI follows [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 0.3.0)
  - **MAJOR**: Breaking changes
  - **MINOR**: New features (backward compatible)
  - **PATCH**: Bug fixes (backward compatible)

## Release Steps

### 1. Update Version Number

Edit `pyproject.toml`:

```toml
[project]
name = "flexiai"
version = "0.4.0"  # Update this
```

### 2. Update CHANGELOG.md

Add a new section for the release:

```markdown
## [0.4.0] - 2025-10-26

### Added
- New feature X
- New feature Y

### Changed
- Updated behavior of Z

### Fixed
- Bug in component A
- Issue with B

### Security
- Fixed credential leak protection
```

### 3. Commit Version Changes

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore: Bump version to 0.4.0"
git push origin main
```

### 4. Create a Git Tag

```bash
# Create annotated tag
git tag -a v0.4.0 -m "Release version 0.4.0"

# Push tag to GitHub
git push origin v0.4.0
```

### 5. Create GitHub Release

#### Option A: Using GitHub CLI

```bash
# Create release from tag
gh release create v0.4.0 \
  --title "FlexiAI v0.4.0" \
  --notes-file RELEASE_NOTES.md

# Or with auto-generated notes
gh release create v0.4.0 \
  --title "FlexiAI v0.4.0" \
  --generate-notes
```

#### Option B: Using GitHub Web Interface

1. Go to https://github.com/Touchkin/FlexiAI/releases
2. Click "Draft a new release"
3. Choose tag: `v0.4.0`
4. Release title: `FlexiAI v0.4.0`
5. Description: Copy from CHANGELOG.md
6. Click "Publish release"

### 6. Automatic Package Build

Once the release is published, GitHub Actions will automatically:

1. ✅ Build the package (wheel and source distribution)
2. ✅ Run quality checks with `twine check`
3. ✅ Sign packages with Sigstore
4. ✅ Upload distributions to GitHub Release

Monitor the workflow:
```bash
gh run list --workflow=publish.yml
```

Or visit: https://github.com/Touchkin/FlexiAI/actions

### 7. Verify Publication

After the workflow completes:

```bash
# Download the release artifacts from GitHub
gh release download v0.4.0

# Install from the wheel file
pip install flexiai-0.4.0-py3-none-any.whl

# Verify installation
python -c "import flexiai; print(flexiai.__version__)"
# Should print: 0.4.0
```

Visit: https://github.com/Touchkin/FlexiAI/releases

## Installation from GitHub Release

Users can install FlexiAI directly from GitHub releases:

### Option 1: Install from Release Artifacts

```bash
# Download the latest release
gh release download v0.4.0 --repo Touchkin/FlexiAI

# Install the wheel file
pip install flexiai-0.4.0-py3-none-any.whl
```

### Option 2: Install Directly from GitHub

```bash
# Install from a specific release tag
pip install git+https://github.com/Touchkin/FlexiAI.git@v0.4.0

# Or install from main branch
pip install git+https://github.com/Touchkin/FlexiAI.git
```

## Workflow Files

### `.github/workflows/publish.yml`

Triggers on: Release published

Jobs:
1. **build-and-publish**:
   - Build wheel and sdist
   - Sign packages with Sigstore
   - Upload artifacts to GitHub Release

### `.github/workflows/tests.yml`

Triggers on: Push to main, Pull requests

Jobs:
1. **test**: Run tests on Python 3.9-3.12
2. **build-check**: Verify package builds correctly

## Rollback

If you need to rollback a release:

```bash
# Delete the release on GitHub
gh release delete v0.4.0 --yes

# Delete the tag
git tag -d v0.4.0
git push origin :refs/tags/v0.4.0
```

**Note**: Once artifacts are downloaded by users, they cannot be recalled. Consider yanking the release instead by editing the release and marking it as a pre-release or draft.

## Pre-release / Beta Versions

For beta/alpha releases:

```bash
# Version: 0.4.0-beta.1
git tag -a v0.4.0-beta.1 -m "Beta release"
git push origin v0.4.0-beta.1

# Create pre-release on GitHub
gh release create v0.4.0-beta.1 \
  --title "FlexiAI v0.4.0-beta.1" \
  --notes "Beta release for testing" \
  --prerelease
```

## Release Checklist

Before publishing:

- [ ] All CI checks passing
- [ ] Version bumped in `pyproject.toml`
- [ ] CHANGELOG.md updated
- [ ] Documentation reviewed
- [ ] Security scan clean
- [ ] Breaking changes documented
- [ ] Migration guide (if needed)
- [ ] Tag created and pushed
- [ ] Release notes prepared

After publishing:

- [ ] PyPI package available
- [ ] GitHub release created
- [ ] Distributions attached to release
- [ ] Installation tested from GitHub release
- [ ] Announcement posted (if major release)
- [ ] Documentation site updated (if applicable)

## Troubleshooting

### Workflow fails with "Upload to GitHub Release failed"

- Check that the release was published (not draft)
- Verify GitHub Actions has write permissions
- Check the release tag matches the workflow trigger

### Package build fails

- Run locally: `python -m build`
- Check `pyproject.toml` syntax
- Verify all files are included in package

### Tests fail in CI

- Run tests locally: `pytest tests/`
- Check Python version compatibility
- Review test logs in GitHub Actions

### Sigstore signing fails

- This is optional - the workflow will continue
- Check Sigstore status: https://status.sigstore.dev/

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [Python Packaging Guide](https://packaging.python.org/)
- [Semantic Versioning](https://semver.org/)
- [Sigstore](https://www.sigstore.dev/)

---

**Need help?** Open an issue or contact the maintainers.
