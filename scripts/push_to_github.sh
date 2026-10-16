#!/usr/bin/env bash
# Manual alternative to the connected GitHub uploader.
set -euo pipefail
repo="${1:-stanmasked/vice-project-doom-switch-hd}"
git init -b main 2>/dev/null || true
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/${repo}.git"
git add .github .gitattributes .gitignore README.md docs native_core tools tests switch_viewer scripts
git commit -m 'chore: import native HD remake research toolkit' || true
git push -u origin main
