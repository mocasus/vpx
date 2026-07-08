# VPX

[![Version](https://img.shields.io/badge/v1.0.0-blue)](https://github.com/mocasus/vpx)
[![Docker](https://img.shields.io/badge/docker-ready-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

VPN Proxy Exchange — portable SOCKS5/HTTP proxy backed by free public VPN servers.

---

## 🇬🇧 English

Turn any Docker host into a rotating VPN proxy. Downloads public OpenVPN configs (VPN Gate), routes traffic through SOCKS5 (Dante :1080) and HTTP (TinyProxy :8080), controlled via REST API (FastAPI :8000).

### Features
- Free public VPN configs (VPN Gate) — no account needed
- SOCKS5 proxy (Dante) on :1080 with username/password auth
- HTTP proxy (TinyProxy) on :8080 with BasicAuth
- REST API (FastAPI) on :8000
- One-click VPN rotation
- Single portable Docker container

### Quick Start
```bash
docker run -d --name vpx --cap-add=NET_ADMIN --device=/dev/net/tun \
  -p 1080:1080 -p 8080:8080 -p 8000:8000 -e API_TOKEN=secret mocasus/vpx
```

### Install
```bash
npm install -g vpx && vpx secret         # npm
pip install vpx && vpx secret             # pip
git clone https://github.com/mocasus/vpx && cd vpx && docker compose up -d  # docker
```

### API
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | Auth, get proxy credentials |
| GET | `/status` | VPN + proxy status |
| POST | `/connect?country=JP` | Connect to VPN |
| POST | `/rotate?country=US` | Rotate VPN server |
| GET | `/locations` | List VPN servers |

```bash
curl -X POST http://localhost:8000/login -H "Authorization: Bearer secret"
curl -X POST http://localhost:8000/connect -H "Authorization: Bearer secret"
curl -X POST http://localhost:8000/rotate -H "Authorization: Bearer secret"
```

### Use Proxies
```bash
curl --socks5 user:pass@host:1080 https://ifconfig.me
curl -x http://user:pass@host:8080 https://ifconfig.me
```

## 🇮🇩 Indonesia

Ubah Docker host menjadi proxy VPN yang berputar. Mengunduh konfigurasi OpenVPN publik (VPN Gate), mengarahkan lalu lintas melalui SOCKS5 (Dante :1080) dan HTTP (TinyProxy :8080), dikendalikan via REST API (FastAPI :8000).

### Fitur
- Konfigurasi VPN publik gratis (VPN Gate) — tanpa akun
- Proxy SOCKS5 (Dante) di :1080 dengan autentikasi user/pass
- Proxy HTTP (TinyProxy) di :8080 dengan BasicAuth
- REST API (FastAPI) di :8000
- Rotasi VPN satu klik
- Satu container Docker portabel

### Mulai Cepat
```bash
docker run -d --name vpx --cap-add=NET_ADMIN --device=/dev/net/tun \
  -p 1080:1080 -p 8080:8080 -p 8000:8000 -e API_TOKEN=secret mocasus/vpx
```

### Pasang
```bash
npm install -g vpx && vpx secret         # npm
pip install vpx && vpx secret             # pip
git clone https://github.com/mocasus/vpx && cd vpx && docker compose up -d  # docker
```

### API
| Method | Endpoint | Keterangan |
|--------|----------|------------|
| POST | `/login` | Autentikasi, dapatkan kredensial proxy |
| GET | `/status` | Status VPN + proxy |
| POST | `/connect?country=JP` | Hubungkan ke VPN |
| POST | `/rotate?country=US` | Rotasi server VPN |
| GET | `/locations` | Daftar server VPN |

```bash
curl -X POST http://localhost:8000/login -H "Authorization: Bearer secret"
curl -X POST http://localhost:8000/connect -H "Authorization: Bearer secret"
curl -X POST http://localhost:8000/rotate -H "Authorization: Bearer secret"
```

### Gunakan Proxy
```bash
curl --socks5 user:pass@host:1080 https://ifconfig.me
curl -x http://user:pass@host:8080 https://ifconfig.me
```

---

v1.0.0 · MIT License
