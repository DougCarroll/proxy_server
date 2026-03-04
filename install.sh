#!/bin/bash
# Set up the proxy: create venv, install dependencies, create target_url.txt if missing.
# Run from the project directory (or from anywhere; script cd's to its own directory).

set -e
cd "$(dirname "$0")"

# Check that python3-venv is available (required on Debian/Ubuntu)
tmp_venv=$(mktemp -d)
if ! python3 -m venv "$tmp_venv" 2>/dev/null; then
  rm -rf "$tmp_venv"
  echo "python3-venv is not installed. On Debian/Ubuntu run:"
  echo "  sudo apt update && sudo apt install -y python3-venv"
  echo "Then run ./install.sh again."
  exit 1
fi
rm -rf "$tmp_venv"

echo "Creating virtual environment..."
python3 -m venv venv

echo "Installing dependencies..."
venv/bin/pip install -r requirements.txt

if [ ! -f target_url.txt ]; then
  echo "Creating target_url.txt from example..."
  cp target_url.txt.example target_url.txt
  echo "Edit target_url.txt to set your target URL, then run ./run.sh"
else
  echo "target_url.txt already exists; leaving it unchanged."
fi

echo "Install complete. Run ./run.sh to start the proxy."
