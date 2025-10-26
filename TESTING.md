# Testing the Package Workflow

This guide explains how to test the FlexiAI package build and release workflow.

## 📋 Overview

There are **three main ways** to test the package workflow:
1. **Local Build Testing** (Fastest - no GitHub required)
2. **Draft Release Testing** (Recommended - tests full workflow without publishing)
3. **Production Release** (Creates actual release)

---

## 1. 🔨 Local Build Testing

Test the build process locally without creating a GitHub release.

### Step 1: Clean Previous Builds

```bash
rm -rf dist/ build/ *.egg-info
```

### Step 2: Build the Package

```bash
python -m build
```

**Expected Output:**
```
Successfully built flexiai-0.3.0.tar.gz and flexiai-0.3.0-py3-none-any.whl
```

### Step 3: Verify the Build

```bash
# Check the dist directory
ls -lh dist/

# Should show:
# flexiai-0.3.0-py3-none-any.whl
# flexiai-0.3.0.tar.gz
```

### Step 4: Validate with Twine

```bash
twine check dist/*
```

**Expected Output:**
```
Checking dist/flexiai-0.3.0-py3-none-any.whl: PASSED
Checking dist/flexiai-0.3.0.tar.gz: PASSED
```

### Step 5: Test Installation

```bash
# Create a test virtual environment
python -m venv test-env
source test-env/bin/activate  # On Windows: test-env\Scripts\activate

# Install the built package
pip install dist/flexiai-0.3.0-py3-none-any.whl

# Test import
python -c "from flexiai import FlexiAI; print('✅ Package imported successfully')"

# Clean up
deactivate
rm -rf test-env
```

---

## 2. 📦 Draft Release Testing (Recommended)

Test the full GitHub workflow without creating a public release.

### Step 1: Create a Draft Release

```bash
# Via GitHub CLI
gh release create v0.3.1-test \
  --title "Test Release v0.3.1" \
  --notes "Testing the build workflow" \
  --draft

# Or via GitHub Web UI:
# Go to: https://github.com/Touchkin/FlexiAI/releases/new
# - Tag: v0.3.1-test
# - Title: Test Release v0.3.1
# - Check "Set as a draft"
# - Click "Create release"
```

### Step 2: Publish the Draft

In GitHub UI, click **"Publish release"** button. This triggers the workflow.

### Step 3: Monitor the Workflow

```bash
# Watch the workflow run
gh run watch

# Or view in browser:
# https://github.com/Touchkin/FlexiAI/actions
```

### Step 4: Verify the Release

```bash
# Check if artifacts were uploaded
gh release view v0.3.1-test

# Download and test the package
gh release download v0.3.1-test --repo Touchkin/FlexiAI
pip install flexiai-0.3.1-py3-none-any.whl
python -c "from flexiai import FlexiAI; print('✅ Works!')"
```

### Step 5: Clean Up Test Release

```bash
# Delete the test release
gh release delete v0.3.1-test --yes

# Delete the tag
git push --delete origin v0.3.1-test
```

---

## 3. 🚀 Production Release

Create an actual release when ready to publish.

### Step 1: Update Version

Update version in:
- `pyproject.toml`
- `setup.py`
- `flexiai/__init__.py` (if applicable)

```bash
# Example: Update to v0.4.0
git add pyproject.toml setup.py
git commit -m "Bump version to 0.4.0"
git push origin main
```

### Step 2: Create and Push Tag

```bash
git tag -a v0.4.0 -m "Release v0.4.0"
git push origin v0.4.0
```

### Step 3: Create GitHub Release

```bash
gh release create v0.4.0 \
  --title "Release v0.4.0" \
  --notes "## What's New
- Feature 1
- Feature 2
- Bug fixes"

# Or use GitHub Web UI:
# https://github.com/Touchkin/FlexiAI/releases/new
```

### Step 4: Monitor the Workflow

The workflow will automatically:
1. ✅ Build wheel and source distribution
2. ✅ Validate with twine check
3. ✅ Sign with Sigstore
4. ✅ Upload to GitHub Release

```bash
# Watch progress
gh run watch

# Or check Actions tab:
# https://github.com/Touchkin/FlexiAI/actions
```

### Step 5: Verify Installation

Users can install via:

```bash
# From specific release
pip install git+https://github.com/Touchkin/FlexiAI.git@v0.4.0

# Or download wheel
gh release download v0.4.0 --repo Touchkin/FlexiAI
pip install flexiai-0.4.0-py3-none-any.whl
```

---

## 🧪 Testing Checklist

Before creating a production release, ensure:

- [ ] **Local build succeeds**: `python -m build`
- [ ] **Twine check passes**: `twine check dist/*`
- [ ] **Package installs**: `pip install dist/*.whl`
- [ ] **Import works**: `python -c "from flexiai import FlexiAI"`
- [ ] **Tests pass**: `pytest tests/`
- [ ] **Linters pass**: `black --check . && isort --check-only . && flake8`
- [ ] **Security checks pass**: `bandit -r flexiai/ && detect-secrets scan`
- [ ] **Version updated** in `pyproject.toml` and `setup.py`
- [ ] **CHANGELOG.md updated** with new version notes
- [ ] **Draft release tested** (optional but recommended)

---

## 🔍 Troubleshooting

### Build Fails

**Issue:** `python -m build` fails

**Solution:**
```bash
# Update build tools
pip install --upgrade build setuptools wheel

# Check for syntax errors
python -m py_compile flexiai/*.py

# Verify pyproject.toml is valid
python -c "import tomli; tomli.load(open('pyproject.toml', 'rb'))"
```

### Twine Check Fails

**Issue:** `twine check dist/*` reports errors

**Solution:**
```bash
# Check README.md is valid
python -m readme_renderer README.md

# Ensure long_description_content_type is set in pyproject.toml
grep "long_description_content_type" pyproject.toml
```

### Import Fails After Installation

**Issue:** `ModuleNotFoundError: No module named 'flexiai'`

**Solution:**
```bash
# Check if package was installed
pip list | grep flexiai

# Verify package structure
python -c "import sys; print(sys.path)"

# Reinstall
pip uninstall flexiai -y
pip install dist/*.whl
```

### GitHub Workflow Fails

**Issue:** Workflow fails in Actions tab

**Solutions:**

**Build step fails:**
```bash
# Test locally first
python -m build
twine check dist/*
```

**Self-hosted runner not available:**
- Verify runner is online: Check Settings → Actions → Runners
- Ensure runner has labels: `[self-hosted, Linux, X64, python36]`
- Check runner logs for errors
- Restart runner if needed

**Upload to Release fails:**
- Ensure `GITHUB_TOKEN` has `contents: write` permission
- Check release tag matches: `${{ github.ref_name }}`
- Verify release exists before upload

**Action not allowed error:**
- Organization policy restricts third-party actions
- Only GitHub-created and Touchkin-owned actions are allowed
- Workflow has been updated to comply with these restrictions

---

## 📊 Workflow Files

### `.github/workflows/publish.yml`
Triggers on release publication:
- Runs on self-hosted runner: `[self-hosted, Linux, X64, python36]`
- Builds package (wheel + sdist)
- Validates with twine
- Uploads to GitHub Release

### `.github/workflows/tests.yml`
Triggers on push/PR to main:
- Runs on self-hosted runner: `[self-hosted, Linux, X64, python36]`
- Runs tests on Python 3.9-3.12
- Linters (black, isort, flake8)
- Security checks (bandit, detect-secrets)
- Build verification

---

## 🎯 Quick Commands Reference

```bash
# Clean build artifacts
rm -rf dist/ build/ *.egg-info

# Build package
python -m build

# Validate package
twine check dist/*

# Install locally
pip install dist/*.whl

# Create draft release
gh release create v0.x.x-test --draft

# Watch workflow
gh run watch

# Download release
gh release download v0.x.x

# Delete test release
gh release delete v0.x.x-test --yes
```

---

## 📝 Notes

- **Always test locally first** before creating a release
- **Use draft releases** to test the full workflow
- **Semantic versioning**: Use `vX.Y.Z` format (e.g., `v0.3.0`)
- **Tags must match release version** for workflow to trigger
- **GitHub-only distribution**: No PyPI publishing configured
- **Self-hosted runners**: Workflows run on `[self-hosted, Linux, X64, python36]`
- **Organization policy**: Only GitHub and Touchkin-owned actions are allowed

For more details, see [RELEASE_PROCESS.md](RELEASE_PROCESS.md).
