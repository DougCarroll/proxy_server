#!/usr/bin/env python3
"""
HTTP proxy server that listens on port 5010 and forwards requests to a target URL.
The target URL is read from target_url.txt in the same directory and can be changed dynamically.
"""

import os
import requests
from flask import Flask, request, Response
from pathlib import Path

app = Flask(__name__)

# Directory where this script lives (for finding target_url.txt)
SCRIPT_DIR = Path(__file__).resolve().parent
TARGET_URL_FILE = SCRIPT_DIR / "target_url.txt"
DEFAULT_TARGET = "http://localhost:8080"


def get_target_url():
    """Read the target URL from the config file. Returns default if file missing or empty."""
    try:
        if TARGET_URL_FILE.exists():
            url = TARGET_URL_FILE.read_text().strip()
            if url:
                return url.rstrip("/")
    except (OSError, IOError):
        pass
    return DEFAULT_TARGET


def proxy_request():
    """Forward the incoming request to the target URL and return the response."""
    target_base = get_target_url()
    # Preserve path and query string from the original request
    path = request.path
    if request.query_string:
        path = f"{path}?{request.query_string.decode()}"
    target_url = f"{target_base}{path}"

    # Build headers for the upstream request (exclude Hop-by-Hop and Host)
    exclude_headers = {
        "host",
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
    headers = {
        k: v
        for k, v in request.headers
        if k.lower() not in exclude_headers
    }

    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(cache=False),
            allow_redirects=False,
            timeout=60,
        )
    except requests.RequestException as e:
        return str(e), 502

    # Build response headers (exclude Hop-by-Hop from upstream)
    response_headers = [
        (k, v)
        for k, v in resp.raw.headers.items()
        if k.lower() not in exclude_headers
    ]

    return Response(
        resp.content,
        status=resp.status_code,
        headers=response_headers,
    )


# Catch-all route: any path is proxied
@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
def proxy(path):
    return proxy_request()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5010))
    print(f"Proxy listening on port {port}")
    print(f"Target URL file: {TARGET_URL_FILE}")
    print(f"Current target: {get_target_url()}")
    print("Connect with HTTP only (not HTTPS), e.g. http://your-server:5010/")
    app.run(host="0.0.0.0", port=port, threaded=True)
