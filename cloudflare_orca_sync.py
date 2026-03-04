#!/usr/bin/env python3
"""
Watch orca_url.txt and update the Cloudflare Page Rule for wm7i.com/orca
so the forwarding destination URL matches the file contents.

Runs on macOS. Requires CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID.
"""

import os
import sys
import time
from pathlib import Path

import requests

# Default path to the URL file (macOS iCloud path)
ORCA_URL_FILE = Path(
    os.environ.get(
        "ORCA_URL_FILE",
        "/Users/doug/Library/Mobile Documents/com~apple~CloudDocs/FilingCabinet/Burnt Toast/AppData/orca_url.txt",
    )
)

# Cloudflare API
API_BASE = "https://api.cloudflare.com/client/v4"
# How we identify the Orca page rule (target URL pattern contains this)
ORCA_TARGET_MATCH = "orca"


def get_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"Error: set {name} (e.g. in .env or export)", file=sys.stderr)
        sys.exit(1)
    return val


def read_destination_url() -> str | None:
    """Read the first non-empty line from the URL file. Returns None if missing or empty."""
    try:
        if not ORCA_URL_FILE.exists():
            return None
        text = ORCA_URL_FILE.read_text().strip()
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
        return None
    except OSError as e:
        print(f"Read error: {e}", file=sys.stderr)
        return None


def list_page_rules(zone_id: str, token: str) -> list:
    """List all Page Rules for the zone."""
    r = requests.get(
        f"{API_BASE}/zones/{zone_id}/pagerules",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(data.get("errors", [{"message": "Unknown API error"}]))
    return data.get("result", [])


def find_orca_rule(rules: list) -> dict | None:
    """Return the Page Rule whose target matches ORCA_TARGET_MATCH (e.g. orca)."""
    for rule in rules:
        for t in rule.get("targets", []):
            if t.get("target") == "url":
                val = (t.get("constraint", {}).get("value") or "").lower()
                if ORCA_TARGET_MATCH in val:
                    return rule
    return None


def update_page_rule_forwarding_url(
    zone_id: str,
    rule_id: str,
    token: str,
    destination_url: str,
    existing_rule: dict,
    status_code: int = 302,
) -> None:
    """Update the Page Rule so the forwarding URL action points to destination_url."""
    # PATCH with targets + new actions so we don't wipe existing config
    body = {
        "targets": existing_rule.get("targets", []),
        "actions": [
            {
                "id": "forwarding_url",
                "value": {
                    "url": destination_url,
                    "status_code": status_code,
                },
            }
        ],
    }
    r = requests.patch(
        f"{API_BASE}/zones/{zone_id}/pagerules/{rule_id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(data.get("errors", [{"message": "Unknown API error"}]))


def sync_once(zone_id: str, token: str, verbose: bool = True) -> bool:
    """Read orca_url.txt and update Cloudflare if we have a URL and found the rule. Returns True if updated."""
    url = read_destination_url()
    if not url:
        if verbose:
            print("No URL in file or file missing; skip.", file=sys.stderr)
        return False
    rules = list_page_rules(zone_id, token)
    rule = find_orca_rule(rules)
    if not rule:
        print("No Page Rule found matching orca; create one in Cloudflare for wm7i.com/orca.", file=sys.stderr)
        return False
    rule_id = rule["id"]
    # See what the current forwarding URL is
    current_url = None
    for a in rule.get("actions", []):
        if a.get("id") == "forwarding_url":
            current_url = (a.get("value") or {}).get("url")
            break
    if current_url == url:
        if verbose:
            print(f"Already set to {url}; no change.", file=sys.stderr)
        return False
    update_page_rule_forwarding_url(zone_id, rule_id, token, url, existing_rule=rule)
    if verbose:
        print(f"Updated Page Rule forwarding URL to: {url}", file=sys.stderr)
    return True


def watch_and_sync(zone_id: str, token: str, poll_interval: float = 2.0) -> None:
    """Watch the URL file and sync whenever it changes (polling on macOS)."""
    last_mtime: float = 0
    last_content: str = ""
    print(f"Watching {ORCA_URL_FILE}", file=sys.stderr)
    print("Press Ctrl+C to stop.", file=sys.stderr)
    while True:
        try:
            mtime = ORCA_URL_FILE.stat().st_mtime if ORCA_URL_FILE.exists() else 0
            content = read_destination_url() or ""
            if mtime != last_mtime or content != last_content:
                last_mtime = mtime
                last_content = content
                if content:
                    sync_once(zone_id, token, verbose=True)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
        time.sleep(poll_interval)


def main() -> None:
    token = get_env("CLOUDFLARE_API_TOKEN")
    zone_id = get_env("CLOUDFLARE_ZONE_ID")

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        sync_once(zone_id, token)
        return

    watch_and_sync(zone_id, token)


if __name__ == "__main__":
    main()
