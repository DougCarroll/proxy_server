#!/bin/bash
# Pull latest changes from GitHub.
# Run from anywhere; uses the directory containing this script as the repo root.

set -e
cd "$(dirname "$0")"

echo "Pulling from origin..."
git pull --rebase origin main

echo "Done."
