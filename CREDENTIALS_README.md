# Credentials Setup

## ⚠️ SECURITY WARNING

**NEVER commit credential files to git!**

## Service Account Setup for Vertex AI

1. Place your service account JSON file in this directory (it will be ignored by git)
2. Or set the environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-service-account.json
   ```

## Recommended Location

Keep your credentials **outside** the project directory:

```bash
# Good practice
export GOOGLE_APPLICATION_CREDENTIALS=~/credentials/my-service-account.json

# Or in a secure credentials directory
mkdir -p ~/.config/gcloud/
cp your-service-account.json ~/.config/gcloud/
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/your-service-account.json
```

## Example Service Account File Structure

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "service-account@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

## Files That Should NEVER Be Committed

- ❌ `*.json` (service account files)
- ❌ `*.key` (private keys)
- ❌ `*.pem` (certificates)
- ❌ `.env` (environment files with secrets)
- ❌ Any file containing API keys or passwords

## If You Accidentally Commit Credentials

1. **Immediately rotate/delete the credentials** in GCP Console
2. Remove from git history: `git filter-branch` or `git filter-repo`
3. Force push (if remote): `git push --force`
4. Consider the credentials **compromised** and regenerate them

## Safe Practices

✅ Use environment variables
✅ Store credentials outside the repo
✅ Use different credentials for dev/prod
✅ Regularly rotate credentials
✅ Use IAM with minimal permissions
