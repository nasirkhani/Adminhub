#!/bin/bash

# Navigate to the script's directory (relative path handling)
cd "$(dirname "$0")"
git pull
git pull origin main --rebase

# Stage all changes (you can customize this)
git add .

# Commit with a timestamped message
commit_msg="commit at $(date '+%Y-%m-%d %H:%M:%S')"
git commit -m "$commit_msg instalation guidance"

# Push to current branch
branch=$(git rev-parse --abbrev-ref HEAD)
git push origin "$branch"
