#!/bin/bash
# Start the proxy server (uses venv if present).
# Run from the project directory or from anywhere; script cd's to its own directory.

cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "Run ./install.sh first."
  exit 1
fi

exec venv/bin/python proxy_server.py
