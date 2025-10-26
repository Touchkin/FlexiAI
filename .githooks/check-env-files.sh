#!/bin/bash
# Prevent .env files from being committed

if git diff --cached --name-only | grep -E "^\.env$|^\.env\.local$|^\.env\.production$|^\.env\.development$" | grep -v "^\.env\.example$"; then
    echo "ERROR: .env file detected!"
    echo ".env files contain secrets and should NEVER be committed."
    echo "These files are already in .gitignore."
    echo "Use .env.example as a template instead."
    exit 1
fi

exit 0
