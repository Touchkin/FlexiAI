#!/bin/bash
# Detect API keys in staged files (excluding documentation)

# Exclude documentation and example files
if git diff --cached --diff-filter=ACM -- . ':(exclude)SECURITY.md' ':(exclude).env.example' ':(exclude)*.md' | \
   grep -iE "(sk-[a-zA-Z0-9]{20,}|sk-ant-[a-zA-Z0-9_-]{95,}|AIza[0-9A-Za-z_-]{35})"; then
    echo "ERROR: Potential API key detected in staged files!"
    echo "Please remove the API key and use environment variables instead."
    exit 1
fi

exit 0
