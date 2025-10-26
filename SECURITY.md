# Security Guidelines: Preventing Credential Leaks

## Overview

This repository has multiple layers of protection to prevent accidentally committing sensitive credentials like API keys and service account files.

## 🛡️ Protection Layers

### 1. `.gitignore` Protection

The following patterns are excluded from git tracking:

```gitignore
# API Keys and Secrets
*.key
*.pem
*.p12
*.pfx
.env
.env.*
credentials/
secrets/

# Service Account Files
*.json (except package.json, tsconfig.json)
*-credentials.json
*-key.json
service-account*.json
dev-gemini-*.json
```

### 2. Pre-commit Hooks

Automated checks run before every commit:

#### a. **detect-secrets**
Scans all staged files for potential secrets using entropy analysis and pattern matching.

#### b. **detect-private-key**
Specifically checks for private key patterns (RSA, SSH, etc.)

#### c. **Custom API Key Detection**
Detects common API key patterns:
- OpenAI: `sk-[alphanumeric]{20,}`
- Anthropic: `sk-ant-[alphanumeric_-]{95,}`
- Google Cloud: `AIza[alphanumeric_-]{35}`
- Environment variable assignments: `API_KEY="sk-..."`

#### d. **Service Account File Blocker**
Blocks files matching patterns:
- `*service*account*.json`
- `*-[hexadecimal]{12}.json`
- `dev-gemini*.json`

#### e. **Environment File Protection**
Prevents committing `.env` files:
- `.env`
- `.env.local`
- `.env.production`
- Any `.env.*` variants

### 3. GitHub Secret Scanning

GitHub automatically scans commits for:
- Known secret patterns
- API tokens
- Service account credentials
- Private keys

When a secret is detected, the push is blocked.

## 🚀 Setup Instructions

### Install Pre-commit Hooks

```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Install the git hooks
pre-commit install

# Test the hooks
pre-commit run --all-files
```

### Update detect-secrets Baseline

If you add legitimate secrets (like test fixtures), update the baseline:

```bash
# Generate new baseline
detect-secrets scan --baseline .secrets.baseline

# Or audit and approve specific findings
detect-secrets audit .secrets.baseline
```

## 📝 Best Practices

### ✅ DO

1. **Use Environment Variables**
   ```python
   import os
   api_key = os.getenv("OPENAI_API_KEY")
   ```

2. **Use `.env` files locally** (never commit them!)
   ```bash
   # .env (gitignored)
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   ```

3. **Load environment variables**
   ```python
   from dotenv import load_dotenv
   load_dotenv()  # Loads from .env file
   ```

4. **Use configuration templates**
   ```python
   # config.example.json (committed)
   {
     "openai_api_key": "YOUR_OPENAI_KEY_HERE",
     "anthropic_api_key": "YOUR_ANTHROPIC_KEY_HERE"
   }

   # config.json (gitignored - user creates locally)
   ```

5. **Use secret management in production**
   - AWS Secrets Manager
   - Google Cloud Secret Manager
   - Azure Key Vault
   - HashiCorp Vault

### ❌ DON'T

1. **Hard-code API keys**
   ```python
   # BAD!
   api_key = "sk-proj-abc123..."
   ```

2. **Commit `.env` files**
   ```bash
   # BAD!
   git add .env
   ```

3. **Store credentials in JSON config files in repo**
   ```json
   // BAD!
   {
     "api_key": "sk-real-key-here"
   }
   ```

4. **Use API keys in test files**
   ```python
   # BAD!
   def test_api():
       client = OpenAI(api_key="sk-real-key")
   ```

5. **Disable pre-commit hooks**
   ```bash
   # BAD!
   git commit --no-verify
   ```

## 🧪 Testing the Protection

### Test 1: Try to commit a file with an API key

```bash
# Create a test file with a fake API key
echo 'api_key = "sk-proj-abcdefghijklmnopqrstuvwxyz"' > test_secret.py

# Try to commit
git add test_secret.py
git commit -m "test"

# Should fail with: "ERROR: Potential API key detected!"
```

### Test 2: Try to commit a service account file

```bash
# Create a fake service account file
echo '{"type": "service_account"}' > dev-service-account.json

# Try to commit
git add dev-service-account.json
git commit -m "test"

# Should fail with: "ERROR: Google service account file detected!"
```

### Test 3: Try to commit .env file

```bash
# Create .env file
echo 'API_KEY=test' > .env

# Try to commit
git add .env
git commit -m "test"

# Should fail with: "ERROR: .env file detected!"
```

## 🔧 Bypassing Protection (Emergency Only)

If you absolutely must bypass the hooks (NOT recommended):

```bash
# Skip pre-commit hooks (dangerous!)
git commit --no-verify -m "message"

# Better: Fix the issue properly instead
```

## 🔍 What to Do If You Committed a Secret

### If Not Pushed Yet

```bash
# Remove from last commit
git reset HEAD~1

# Remove the secret from files
# Add to .gitignore
# Commit again
```

### If Already Pushed

1. **Immediately rotate the credential** (most important!)
   - Generate new API key
   - Invalidate old key
   - Update all systems using it

2. **Remove from git history**
   ```bash
   # Using git filter-branch
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch path/to/secret/file" \
     --prune-empty --tag-name-filter cat -- --all

   # Clean up
   rm -rf .git/refs/original/
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive

   # Force push
   git push --force --all
   git push --force --tags
   ```

3. **Contact GitHub support** if the secret was exposed publicly

## 📚 Supported Secret Patterns

The protection detects:

| Type | Pattern Example | Detection Method |
|------|-----------------|------------------|
| OpenAI API Key | `sk-proj-...`, `sk-...` | Regex + Entropy |
| Anthropic API Key | `sk-ant-...` | Regex + Length |
| Google Cloud API Key | `AIza...` | Regex |
| AWS Keys | `AKIA...` | detect-secrets |
| Private Keys | `-----BEGIN PRIVATE KEY-----` | detect-private-key |
| JWT Tokens | `eyJ...` | detect-secrets |
| Service Account JSON | `{"type": "service_account"}` | Filename + Content |
| Environment Files | `.env`, `.env.local` | Filename |

## 🚨 Emergency Contacts

If you discover a leaked credential:

1. **Rotate the credential immediately**
2. **Notify the team**
3. **Check access logs** for unauthorized usage
4. **Remove from git history** (see above)
5. **Update security baseline**

## 📖 Additional Resources

- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [detect-secrets Documentation](https://github.com/Yelp/detect-secrets)
- [Pre-commit Hooks](https://pre-commit.com/)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

## ✅ Security Checklist

Before committing:

- [ ] No hardcoded API keys in code
- [ ] No `.env` files being committed
- [ ] No service account JSON files
- [ ] All secrets loaded from environment variables
- [ ] Configuration files use placeholders
- [ ] Pre-commit hooks installed and passing
- [ ] Sensitive files listed in `.gitignore`

---

**Remember**: Prevention is easier than cleanup. Always use environment variables for secrets!
