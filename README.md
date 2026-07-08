<div align="center">

# VPNX

**VPN Proxy Exchange** — self-hosted rotating VPN proxy in one Docker container.

Free public VPN servers → SOCKS5 + HTTP proxy → REST API control.

[![Version](https://img.shields.io/badge/v2.0.0-blue?style=flat-square)](https://github.com/mocasus/vpnx)
[![npm](https://img.shields.io/badge/npm-@mocasus/vpnx-CB3837?style=flat-square&logo=npm&logoColor=white)](https://www.npmjs.com/package/@mocasus/vpnx)
[![PyPI](https://img.shields.io/badge/pypi-vpnx--cli-3775A9?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/vpnx-cli/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)]()
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

</div>

---

## What is this?

VPNX turns any Docker host into a **rotating VPN proxy** — no VPN subscription, no account needed.

It grabs free OpenVPN configs from public VPN servers, creates a VPN tunnel, and exposes it as a standard SOCKS5 + HTTP proxy you can use from any tool. Want to switch country or rotate to a new server? One API call.

**Multi-source fallback** — VPNX tries multiple sources to find working VPN servers:

1. **VPN Gate API** (`/api/iphone/`) — CSV endpoint, fastest when available
2. **VPN Gate HTML scrape** (`/en/`) — parses the website table and downloads `.ovpn` configs directly
3. **GitHub mirror** — cached configs as last resort

If one source is down, VPNX automatically falls back to the next. No manual intervention.

**What you get:**
- 🔒 SOCKS5 proxy with auth (use from curl, browsers, scrapers, anything)
- 🌐 HTTP proxy with auth
- 🔄 REST API to connect, rotate, disconnect, and check status
- 🌍 7+ countries, 80+ servers available at any time
- 🏠 Works on any Linux Docker host — no VPN client needed on your machine

**Use cases:** web scraping with IP rotation, geo-testing, bypassing rate limits, hiding your origin IP.

---

## Quick Start

```bash
docker run -d --name vpnx \
  --cap-add=NET_ADMIN --device=/dev/net/tun \
  -p 1080:1080 -p 8080:8080 -p 8000:8000 \
  -e API_TOKEN=your-secret \
  mocasus/vpnx:latest
```

Or use the CLI wrapper:

```bash
npm install -g @mocasus/vpnx && vpnx your-secret    # npm
pip install vpnx-cli && vpnx your-secret             # pip
```

**Ports:** SOCKS5 `:1080` · HTTP `:8080` · API `:8000`

### Example session

```bash
# Check status
curl http://localhost:8000/status -H "Authorization: Bearer your-secret"
# → {"vpn": {"connected": false, ...}, "proxy": {"socks5": ":1080", ...}}

# Connect to a VPN server (auto-picks fastest)
curl -X POST http://localhost:8000/connect -H "Authorization: Bearer your-secret"
# → {"status": "connected", "server": "vpn599400160.opengw.net", "country": "Japan"}

# Use the proxy — traffic goes through VPN
curl --socks5 user:pass@localhost:1080 https://ifconfig.me
# → 36.14.213.219  (your VPN IP, not your real IP)

# Rotate to a new server
curl -X POST http://localhost:8000/rotate -H "Authorization: Bearer your-secret"
# → {"status": "connected", "server": "vpn851315872.opengw.net", ...}

# List available locations
curl http://localhost:8000/locations -H "Authorization: Bearer your-secret"
# → [{"country": "JP", "name": "Japan", "servers": 50, "speed": 948}, ...]

# Disconnect
curl -X POST http://localhost:8000/disconnect -H "Authorization: Bearer your-secret"
```

---

## API

All endpoints require `Authorization: Bearer <API_TOKEN>` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/login` | Get proxy credentials |
| `GET` | `/status` | VPN + proxy status |
| `POST` | `/connect?country=JP` | Connect to VPN (auto-picks fastest if no country) |
| `POST` | `/disconnect` | Disconnect VPN |
| `POST` | `/rotate?country=US` | Rotate to a new VPN server |
| `GET` | `/locations` | List available VPN servers by country |

### Country filter

Pass `?country=XX` (ISO 3166-1 alpha-2) to `/connect` or `/rotate`:

```bash
curl -X POST "http://localhost:8000/connect?country=JP" -H "Authorization: Bearer your-secret"
curl -X POST "http://localhost:8000/rotate?country=KR" -H "Authorization: Bearer your-secret"
```

---

## Using the Proxy

```bash
# SOCKS5
curl --socks5 user:pass@host:1080 https://ifconfig.me

# HTTP
curl -x http://user:pass@host:8080 https://ifconfig.me
```

Get proxy credentials from `/login` or `/status` endpoint.

---

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `API_TOKEN` | *(required)* | API authentication token |
| `SOCKS_USER` | `vpnx<random>` | Proxy username (auto-generated if not set) |
| `SOCKS_PASS` | `<random>` | Proxy password (auto-generated if not set) |

**Requires:** Docker with `--cap-add=NET_ADMIN` + `--device=/dev/net/tun` (Linux host only)

---

## How it works

```
┌─────────────────────────────────────────────────┐
│                  VPNX Container                  │
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │ FastAPI  │───▶│ VPN Mgr  │───▶│ OpenVPN   │  │
│  │ :8000    │    │          │    │ (tun0)    │  │
│  └──────────┘    └──────────┘    └─────┬─────┘  │
│       │                               │         │
│  ┌────▼────┐                   ┌─────▼─────┐  │
│  │ Dante    │                   │ VPN Gate  │  │
│  │ SOCKS5   │                   │ Servers   │  │
│  │ :1080    │                   │ (free)    │  │
│  └─────────┘                   └───────────┘  │
│  ┌─────────┐                                    │
│  │Tinyproxy│                                    │
│  │ HTTP    │                                    │
│  │ :8080   │                                    │
│  └─────────┘                                    │
└─────────────────────────────────────────────────┘
```

1. **Fetch** — VPNX queries VPN Gate for available servers (API → HTML scrape → GitHub mirror)
2. **Connect** — Downloads `.ovpn` config, starts OpenVPN daemon, waits for tunnel
3. **Proxy** — Dante (SOCKS5) and Tinyproxy (HTTP) route traffic through the VPN tunnel
4. **Rotate** — Kills old OpenVPN, picks next server, reconnects

---

## 🇮🇩 Bahasa Indonesia

Proxy VPN berputar dalam satu container Docker. Gratis, tanpa akun — pakai server VPN publik dari VPN Gate.

**Multi-source fallback** — VPNX otomatis beralih sumber server jika satu mati:
1. VPN Gate API (CSV endpoint)
2. VPN Gate HTML scrape (parse website + download config)
3. GitHub mirror (cached configs)

### Mulai Cepat

```bash
docker run -d --name vpnx \
  --cap-add=NET_ADMIN --device=/dev/net/tun \
  -p 1080:1080 -p 8080:8080 -p 8000:8000 \
  -e API_TOKEN=rahasia-anda \
  mocasus/vpnx:latest
```

Atau via CLI:

```bash
npm install -g @mocasus/vpnx && vpnx rahasia-anda    # npm
pip install vpnx-cli && vpnx rahasia-anda             # pip
```

### API

Semua endpoint butuh header `Authorization: Bearer <API_TOKEN>`.

| Method | Endpoint | Keterangan |
|--------|----------|------------|
| `POST` | `/login` | Dapat kredensial proxy |
| `GET` | `/status` | Status VPN + proxy |
| `POST` | `/connect?country=JP` | Hubungkan ke VPN |
| `POST` | `/disconnect` | Putuskan VPN |
| `POST` | `/rotate?country=US` | Rotasi server VPN |
| `GET` | `/locations` | Daftar server VPN per negara |

### Menggunakan Proxy

```bash
curl --socks5 user:pass@host:1080 https://ifconfig.me   # SOCKS5
curl -x http://user:pass@host:8080 https://ifconfig.me    # HTTP
```

---

v2.0.0 · MIT License
