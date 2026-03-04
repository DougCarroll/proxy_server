# HTTP Proxy Server

Listens on port 5010 and forwards HTTP requests to a target URL. The target URL is read from `target_url.txt` in the same directory and can be changed at any time (no restart needed).

## Setup on Debian Linux

```bash
# Install Python 3 and pip if needed
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy the example config and set your target URL:

```bash
cp target_url.txt.example target_url.txt
```

Edit `target_url.txt` and put the full base URL (e.g. `https://api.example.com`). One URL per file, no trailing slash required. The proxy will append the request path and query string. **Do not commit `target_url.txt`**—it is gitignored so private or credential-bearing URLs are never pushed.

Example contents:
```
https://httpbin.org
```

Change this file anytime; the next request will use the new URL.

## Run

```bash
# From project directory, with venv activated:
python3 proxy_server.py
```

Or with a specific port:
```bash
PORT=5010 python3 proxy_server.py
```

The server binds to `0.0.0.0` so it accepts connections from other hosts.

## Usage

**Use HTTP when connecting to the proxy** (the proxy does not speak HTTPS on this port). The proxy can still forward to HTTPS targets.

- Proxy: `http://your-server:5010`
- Request: `GET http://your-server:5010/anything/foo?bar=1`
- Proxied to: `{target_url}/anything/foo?bar=1`

All common HTTP methods (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS) are forwarded. Headers and body are passed through (except hop-by-hop headers). Redirect responses (3xx) that point to the target host are rewritten to point back to the proxy so the browser stays on the proxy.

**Proxying full web apps (e.g. Orca):** Response bodies for HTML, JavaScript, CSS, and JSON are rewritten so that absolute URLs to the target host (e.g. `https://app.getorca.com`) are replaced with the proxy URL. That way the browser loads assets and API calls through the proxy. **WebSockets** are proxied: when the browser connects to `ws://your-server:5010/...`, the proxy accepts the connection and tunnels it to `wss://target-host/...`, so live features (e.g. Orca live view) work through the proxy.

### Debug

To log each request and response status (and redirect rewrites), run with:

```bash
DEBUG=1 ./run.sh
```

## Run as a service (systemd)

Create `/etc/systemd/system/proxy.service`:

```ini
[Unit]
Description=HTTP Proxy on port 5010
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/proxy
ExecStart=/path/to/proxy/venv/bin/python proxy_server.py
Restart=always
Environment=PORT=5010

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable proxy
sudo systemctl start proxy
sudo systemctl status proxy
```

---

## Cloudflare Orca redirect (macOS)

A separate script keeps the **wm7i.com/orca** Cloudflare Page Rule forwarding URL in sync with a local file. When that file changes, the script updates the Page Rule via the Cloudflare API.

### Setup

1. **Create a Page Rule in Cloudflare** for `wm7i.com/orca` (or a URL pattern that contains `orca`) with “Forwarding URL” to any destination. You will update the destination via the script.

2. **Environment variables** (required):
   - `CLOUDFLARE_API_TOKEN` – API token with Zone/Page Rules edit (e.g. “Edit zone DNS” + “Page Rules”).
   - `CLOUDFLARE_ZONE_ID` – Zone ID for wm7i.com (from the zone’s Overview in the dashboard).

   Optional:
   - `ORCA_URL_FILE` – Path to the URL file (default: `…/FilingCabinet/Burnt Toast/AppData/orca_url.txt` on this Mac).

3. **URL file**  
   Default path on this Mac:
   ```
   ~/Library/Mobile Documents/com~apple~CloudDocs/FilingCabinet/Burnt Toast/AppData/orca_url.txt
   ```
   Put a single destination URL per line (first non-empty, non-`#` line is used), e.g.:
   ```
   https://app.getorca.com/#live/43sin4W6tqm6zABv
   ```

### Run

- **Watch and sync** (runs until you Ctrl+C):
  ```bash
  export CLOUDFLARE_API_TOKEN=your_token
  export CLOUDFLARE_ZONE_ID=your_zone_id
  ./run_cloudflare_sync.sh
  ```
  Whenever `orca_url.txt` is modified, the script updates the Page Rule’s forwarding URL to match.

- **One-off sync** (no watcher):
  ```bash
  ./run_cloudflare_sync.sh --once
  ```

Runs on macOS; only `requests` is required (same venv as the proxy).
