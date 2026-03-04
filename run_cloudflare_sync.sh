#!/bin/bash
# Run the Cloudflare Orca URL sync (watch orca_url.txt and update Page Rule).
# Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID (e.g. in .env or export).

cd "$(dirname "$0")"

if [ -z "$CLOUDFLARE_API_TOKEN" ] || [ -z "$CLOUDFLARE_ZONE_ID" ]; then
  echo "Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID."
  echo "Optional: ORCA_URL_FILE=/path/to/orca_url.txt"
  exit 1
fi

# Use venv if present
if [ -d venv ]; then
  exec venv/bin/python cloudflare_orca_sync.py "$@"
fi
exec python3 cloudflare_orca_sync.py "$@"
