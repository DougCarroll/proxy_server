#!/usr/bin/env python3
"""
HTTP proxy server that listens on port 5010 and forwards requests to a target URL.
The target URL is read from target_url.txt in the same directory and can be changed dynamically.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from flask import Flask, request, Response

app = Flask(__name__)
DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")

# Directory where this script lives (for finding target_url.txt)
SCRIPT_DIR = Path(__file__).resolve().parent
TARGET_URL_FILE = SCRIPT_DIR / "target_url.txt"
DEFAULT_TARGET = "http://localhost:8080"

# Content types for which we rewrite target URLs to proxy URLs in the body
REWRITE_CONTENT_TYPES = (
    "text/html",
    "text/css",
    "application/javascript",
    "text/javascript",
    "application/json",
    "application/x-javascript",
)


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


def rewrite_response_body(
    body: bytes,
    content_type: str,
    target_netloc: str,
    target_scheme: str,
    proxy_base: str,
    request_host: str,
) -> bytes:
    """Replace target origin URLs with proxy URL in text responses so the browser uses the proxy."""
    if not body or not target_netloc:
        return body
    # Check content type (may be "text/html; charset=utf-8")
    base_type = (content_type or "").split(";")[0].strip().lower()
    if base_type not in REWRITE_CONTENT_TYPES:
        return body
    try:
        text = body.decode("utf-8")
    except (UnicodeDecodeError, LookupError):
        return body
    if target_netloc not in text:
        return body
    # Replace so subsequent requests go through the proxy
    text = text.replace(f"https://{target_netloc}", proxy_base)
    text = text.replace(f"http://{target_netloc}", proxy_base)
    text = text.replace(f"//{target_netloc}", f"//{request_host}")
    # WebSocket URLs (browser will try ws://proxy - we don't proxy WS yet, but rewriting avoids mixed content)
    text = text.replace(f"wss://{target_netloc}", f"ws://{request_host}")
    text = text.replace(f"ws://{target_netloc}", f"ws://{request_host}")
    return text.encode("utf-8")


def proxy_request():
    """Forward the incoming request to the target URL and return the response."""
    target_base = get_target_url()
    # Use only the part before '#' for the base (fragment is never sent to servers)
    if "#" in target_base:
        target_base = target_base.split("#", 1)[0].rstrip("/")
    else:
        target_base = target_base.rstrip("/")
    # Preserve path and query string from the original request
    path = request.path
    if request.query_string:
        path = f"{path}?{request.query_string.decode()}"
    target_url = f"{target_base}{path}"

    # Build headers for the upstream request (exclude Hop-by-Hop)
    exclude_headers = {
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
    # Set Host to the target host so the origin server sees the correct host
    parsed = urlparse(target_url)
    if parsed.netloc:
        headers["Host"] = parsed.netloc

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
        if DEBUG:
            print(f"Upstream error: {e}", file=sys.stderr, flush=True)
        return str(e), 502

    if DEBUG:
        print(f"{request.method} {path} -> {resp.status_code} {target_url}", file=sys.stderr, flush=True)

    # Build response headers (exclude Hop-by-Hop from upstream)
    response_headers = []
    target_netloc = parsed.netloc
    proxy_base = request.host_url.rstrip("/")

    for k, v in resp.raw.headers.items():
        if k.lower() in exclude_headers:
            continue
        # Rewrite redirect Location so the browser stays on the proxy
        if k.lower() == "location" and 300 <= resp.status_code < 400:
            loc = v.strip()
            try:
                loc_parsed = urlparse(loc)
                if loc_parsed.netloc == target_netloc or not loc_parsed.netloc:
                    # Same host as target or relative: point to proxy so browser stays on proxy
                    path_qs = loc_parsed.path or "/"
                    if loc_parsed.query:
                        path_qs += "?" + loc_parsed.query
                    if loc_parsed.fragment:
                        path_qs += "#" + loc_parsed.fragment
                    v = proxy_base + path_qs
                    if DEBUG:
                        print(f"  Location rewritten -> {v}", file=sys.stderr, flush=True)
            except Exception:
                pass
        response_headers.append((k, v))

    # Rewrite target URLs to proxy URLs in response body so the browser sends requests through the proxy
    content_type = resp.headers.get("Content-Type", "")
    body = rewrite_response_body(
        resp.content,
        content_type,
        target_netloc,
        parsed.scheme or "https",
        proxy_base,
        request.host,
    )
    if body is not resp.content:
        # Body was rewritten: drop Content-Length and Content-Encoding (we send plain body now)
        response_headers = [
            (k, v)
            for k, v in response_headers
            if k.lower() not in ("content-length", "content-encoding")
        ]
        if DEBUG:
            print(f"  Body rewritten ({content_type.split(';')[0]})", file=sys.stderr, flush=True)

    return Response(
        body,
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
    if DEBUG:
        print("DEBUG: request logging enabled", file=sys.stderr, flush=True)
    print("Connect with HTTP only (not HTTPS), e.g. http://your-server:5010/")
    app.run(host="0.0.0.0", port=port, threaded=True)
