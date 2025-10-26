#!/bin/bash
# Block service account JSON files

if git diff --cached --name-only | grep -E ".*service.*account.*\.json|.*-[a-f0-9]{12}\.json|dev-gemini.*\.json"; then
    echo "ERROR: Google service account file detected!"
    echo "Service account files should NEVER be committed."
    echo "Add them to .gitignore and use GOOGLE_APPLICATION_CREDENTIALS environment variable instead."
    exit 1
fi

exit 0
