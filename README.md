<div align="center">

# VPX

**VPN Proxy Exchange**

Self-hosted rotating VPN proxy in a single Docker container.
Free public VPN servers → SOCKS5 + HTTP proxy → REST API control.

[![Version](https://img.shields.io/badge/v1.0.0-blue?style=flat-square)](https://github.com/mocasus/vpx)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)]()
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

</div>

---

## How It Works

```
┌─────────────────────────────────────────────────┐
│                   Docker Container               │
│                                                   │
│   ┌─────────┐    ┌───────────┐    ┌───────────┐  │
│   │ OpenVPN │───▶│  tun0     │───▶│   Dante   │  │
│   │ (VPN    │    │  (tunnel  │    │  SOCKS5   │  │
│   │  Gate)  │    │   iface)  │    │   :1080   │  │
│   └─────────┘    └───────────┘    └─────┬─────┘  │
│                                         │        │
│                                   ┌─────▼─────┐  │
│                                   │ TinyProxy │  │
│                                   │  HTTP     │  │
│                                   │  :8080    │  │
│                                   └─────┬─────┘  │
│                                         │        │
│   ┌─────────────────────────────────────▼──────┐ │
│   │            FastAPI :8000                    │ │
│   │  /connect  /rotate  /status  /locations    │ │
│   └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
         ▲                              ▲
         │ curl / SDK                   │ curl --socks5 / -x
    Your API client              Your proxy client
```

VPX downloads free OpenVPN configs from [VPN Gate](https://www.vpngate.net), creates a VPN tunnel, and routes all proxy traffic through it. Rotate servers or switch countries via REST API — no VPN client needed on your machine.

## Quick Start

```bash
docker run -d --name vpx \
  --cap-add=NET_ADMIN --device=/dev/net/tun \
  -p 1080:1080 -p 8080:8080 -p 8000:8000 \
  -e API_TOKEN=your-secret \
  mocasus/vpx:latest
```

That's it. VPX is now running:
- **SOCKS5 proxy** → `localhost:1080`
- **HTTP proxy** → `localhost:8080`
- **REST API** → `localhost:8000`

## Install (CLI wrapper)

| Method | Command |
|--------|---------|
| npm | `npm install -g vpx && vpx your-secret` |
| pip | `pip install vpx && vpx your-secret` |
| Docker Compose | `git clone https://github.com/mocasus/vpx && cd vpx && docker compose up -d` |

The CLI wrapper generates a token, pulls the image, and starts the container with the right flags.

## API Reference

All endpoints require `Authorization: Bearer <API_TOKEN>` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/login` | Get proxy credentials (username/password) |
| `GET` | `/status` | VPN connection + proxy status |
| `POST` | `/connect?country=JP` | Connect to VPN (optional country code) |
| `POST` | `/rotate?country=US` | Rotate to a different VPN server |
| `GET` | `/locations` | List available VPN servers by country |

### Examples

```bash
# Get proxy credentials
curl -X POST http://localhost:8000/login \
  -H "Authorization: Bearer your-secret"

# Connect to Japan VPN
curl -X POST "http://localhost:8000/connect?country=JP" \
  -H "Authorization: Bearer your-secret"

# Rotate to a US server
curl -X POST "http://localhost:8000/rotate?country=US" \
  -H "Authorization: Bearer your-secret"

# Check status
curl http://localhost:8000/status \
  -H "Authorization: Bearer your-secret"
```

## Using the Proxy

```bash
# SOCKS5
curl --socks5 user:pass@localhost:1080 https://ifconfig.me

# HTTP proxy
curl -x http://user:pass@localhost:8080 https://ifconfig.me
```

Works with any tool that supports SOCKS5 or HTTP proxies — browsers, scrapers, HTTP clients, etc.

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `API_TOKEN` | *(required)* | Bearer token for API authentication |
| `SOCKS_USER` | `vpx<random>` | SOCKS5/HTTP proxy username |
| `SOCKS_PASS` | `<random>` | SOCKS5/HTTP proxy password |

## Requirements

- Docker (or Podman with `--cap-add=NET_ADMIN`)
- Linux host with `/dev/net/tun` available
- `NET_ADMIN` capability (for creating TUN interfaces)

## Tech Stack

- **OpenVPN** — VPN tunnel via VPN Gate public servers
- **Dante** — SOCKS5 proxy with username/password auth
- **TinyProxy** — HTTP proxy with BasicAuth
- **FastAPI** — REST API for control plane
- **Supervisor** — Process management inside container

---

<div align="center">

## 🇮🇩 Bahasa Indonesia

**VPN Proxy Exchange** — proxy VPN berputar dalam satu container Docker.

Unduh konfigurasi OpenVPN publik gratis (VPN Gate), arahkan lalu lintas melalui SOCKS5 dan HTTP proxy, kontrol via REST API.

### Mulai Cepat

```bash
docker run -d --name vpx \
  --cap-add=NET_ADMIN --device=/dev/net/tun \
  -p 1080:1080 -p 8080:8080 -p 8000:8000 \
  -e API_TOKEN=rahasia-anda \
  mocasus/vpx:latest
```

### Pemasangan

| Metode | Perintah |
|--------|----------|
| npm | `npm install -g vpx && vpx rahasia-anda` |
| pip | `pip install vpx && vpx rahasia-anda` |
| Docker Compose | `git clone https://github.com/mocasus/vpx && cd vpx && docker compose up -d` |

### API

Semua endpoint butuh header `Authorization: Bearer <API_TOKEN>`.

| Method | Endpoint | Keterangan |
|--------|----------|------------|
| `POST` | `/login` | Dapatkan kredensial proxy (user/pass) |
| `GET` | `/status` | Status VPN + proxy |
| `POST` | `/connect?country=JP` | Hubungkan ke VPN (kode negara opsional) |
| `POST` | `/rotate?country=US` | Rotasi ke server VPN lain |
| `GET` | `/locations` | Daftar server VPN per negara |

### Contoh

```bash
# Dapatkan kredensial proxy
curl -X POST http://localhost:8000/login \
  -H "Authorization: Bearer rahasia-anda"

# Hubungkan ke VPN Jepang
curl -X POST "http://localhost:8000/connect?country=JP" \
  -H "Authorization: Bearer rahasia-anda"

# Rotasi ke server US
curl -X POST "http://localhost:8000/rotate?country=US" \
  -H "Authorization: Bearer rahasia-anda"
```

### Menggunakan Proxy

```bash
# SOCKS5
curl --socks5 user:pass@localhost:1080 https://ifconfig.me

# HTTP proxy
curl -x http://user:pass@localhost:8080 https://ifconfig.me
```

### Konfigurasi

| Env Var | Default | Keterangan |
|---------|---------|------------|
| `API_TOKEN` | *(wajib)* | Token Bearer untuk autentikasi API |
| `SOCKS_USER` | `vpx<random>` | Username proxy SOCKS5/HTTP |
| `SOCKS_PASS` | `<random>` | Password proxy SOCKS5/HTTP |

### Kebutuhan Sistem

- Docker (atau Podman dengan `--cap-add=NET_ADMIN`)
- Host Linux dengan `/dev/net/tun`
- Capability `NET_ADMIN` (untuk membuat interface TUN)

</div>

---

v1.0.0 · MIT License
