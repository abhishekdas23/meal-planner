#!/bin/bash
set -e

MSG="${1:-deploy update}"

git add -A
git commit -m "$MSG"
git push origin main
echo "Pushed to GitHub. Render will auto-deploy."
