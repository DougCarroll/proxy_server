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

All common HTTP methods (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS) are forwarded. Headers and body are passed through (except hop-by-hop headers).

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
