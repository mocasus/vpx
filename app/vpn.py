"""
VPNX VPN Manager — multi-source OpenVPN config fetcher.

Sources (tried in order):
  1. VPN Gate API (/api/iphone/) — CSV endpoint, fastest when working
  2. VPN Gate HTML scrape (/en/) — parse server table + download .ovpn
  3. GitHub mirror (VPNGate/configs) — cached .ovpn files

Each source populates self.servers with unified schema so downstream
connect/rotate/status work identically regardless of source.
"""

import os
import re
import asyncio
import time
import base64
import subprocess
import urllib.request
import http.cookiejar
import json
import logging

log = logging.getLogger("vpnx.vpn")

API_URL = "https://www.vpngate.net/api/iphone/"
HTML_URL = "https://www.vpngate.net/en/"
DOWNLOAD_URL = "https://www.vpngate.net/common/openvpn_download.aspx"
CONFIG_DIR = "/config/vpn"
PID_FILE = "/tmp/openvpn.pid"
GITHUB_MIRROR_URL = "https://raw.githubusercontent.com/VPNGate/configs/main/servers.json"


class VPNManager:
    def __init__(self):
        self.servers = []
        self.connected = False
        self.current = None
        self.source = None
        self._cookie_jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cookie_jar)
        )
        self._opener.addheaders = [
            ("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
        ]
        self._html_sid = None

    # ── Source 1: VPN Gate CSV API ──────────────────────────────────

    async def _fetch_api(self):
        """Try the original CSV API endpoint."""
        try:
            req = urllib.request.Request(API_URL, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read().decode("utf-8", errors="ignore")
            if raw.startswith("<!DOCTYPE") or "<html" in raw[:200].lower():
                log.warning("VPN Gate API returned HTML, not CSV — endpoint broken")
                return 0
            lines = raw.splitlines()
            for line in lines[2:]:  # skip header rows
                parts = line.split(",")
                if len(parts) >= 15 and parts[14]:
                    self.servers.append({
                        "hostname": parts[0],
                        "ip": parts[1],
                        "score": int(parts[2]) if parts[2] else 0,
                        "ping": int(parts[3]) if parts[3] else 9999,
                        "speed": int(parts[4]) if parts[4] else 0,
                        "country": parts[6],
                        "country_name": parts[5],
                        "config_b64": parts[14],
                        "tcp": 443,
                        "udp": 1194,
                        "hid": None,
                    })
            if self.servers:
                self.servers.sort(key=lambda s: s.get("speed", 0), reverse=True)
                self.source = "api"
                log.info(f"API source: {len(self.servers)} servers")
            return len(self.servers)
        except Exception as e:
            log.warning(f"VPN Gate API failed: {e}")
            return 0

    # ── Source 2: VPN Gate HTML scrape ───────────────────────────────

    async def _fetch_html(self):
        """Scrape the VPN Gate website HTML for server list + download links."""
        try:
            resp = self._opener.open(HTML_URL, timeout=20)
            html = resp.read().decode("utf-8", errors="ignore")

            # Extract session ID from HTML (used in download URLs)
            sid_match = re.search(r"sid=(\d+)", html)
            self._html_sid = sid_match.group(1) if sid_match else None
            if not self._html_sid:
                log.warning("Could not extract sid from HTML")
                return 0

            # Parse each table row
            rows = re.split(r"<tr>", html)
            for row in rows:
                link = re.search(
                    r"do_openvpn\.aspx\?fqdn=([^&]+)&ip=([^&]+)"
                    r"&tcp=(\d+)&udp=(\d+)&sid=\d+&hid=(\d+)",
                    row,
                )
                if not link:
                    continue
                fqdn, ip, tcp, udp, hid = link.groups()
                tcp_i, udp_i = int(tcp), int(udp)
                # Only include servers with OpenVPN TCP support
                if tcp_i == 0:
                    continue

                flag = re.search(r"flags/([A-Z]{2})\.png.*?<br>([^<]+)", row)
                cc = flag.group(1) if flag else "??"
                cname = flag.group(2).strip() if flag else "Unknown"

                speed_m = re.search(r"([\d.]+)\s*Mbps", row)
                speed = float(speed_m.group(1)) if speed_m else 0.0

                ping_m = re.search(r"Ping:\s*<b>(\d+)\s*ms</b>", row)
                ping = int(ping_m.group(1)) if ping_m else 9999

                self.servers.append({
                    "hostname": fqdn,
                    "ip": ip,
                    "score": 0,
                    "ping": ping,
                    "speed": int(speed),
                    "country": cc,
                    "country_name": cname,
                    "config_b64": None,  # will download on demand
                    "tcp": tcp_i,
                    "udp": udp_i,
                    "hid": hid,
                })

            if self.servers:
                self.servers.sort(key=lambda s: s.get("speed", 0), reverse=True)
                self.source = "html"
                log.info(f"HTML scrape source: {len(self.servers)} servers")
            return len(self.servers)
        except Exception as e:
            log.warning(f"HTML scrape failed: {e}")
            return 0

    # ── Unified fetch with fallback ─────────────────────────────────

    async def fetch_servers(self):
        """Try each source in order until we get servers."""
        self.servers = []

        # Source 1: API
        if await self._fetch_api():
            return len(self.servers)

        # Source 2: HTML scrape
        if await self._fetch_html():
            return len(self.servers)

        # Source 3: GitHub mirror (best-effort, may be stale)
        try:
            req = urllib.request.Request(GITHUB_MIRROR_URL, headers={
                "User-Agent": "Mozilla/5.0"
            })
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
            for entry in data if isinstance(data, list) else []:
                self.servers.append({
                    "hostname": entry.get("hostname", ""),
                    "ip": entry.get("ip", ""),
                    "score": 0,
                    "ping": entry.get("ping", 9999),
                    "speed": entry.get("speed", 0),
                    "country": entry.get("country", "??"),
                    "country_name": entry.get("country_name", "Unknown"),
                    "config_b64": entry.get("config_b64"),
                    "tcp": entry.get("tcp", 443),
                    "udp": entry.get("udp", 0),
                    "hid": None,
                })
            if self.servers:
                self.servers.sort(key=lambda s: s.get("speed", 0), reverse=True)
                self.source = "github"
                log.info(f"GitHub mirror source: {len(self.servers)} servers")
        except Exception as e:
            log.warning(f"GitHub mirror failed: {e}")

        return len(self.servers)

    # ── Config download ─────────────────────────────────────────────

    def _get_config(self, server):
        """Download or decode the OpenVPN config for a server."""
        # If we have a base64 config (from API), decode it
        b64 = server.get("config_b64")
        if b64:
            try:
                return base64.b64decode(b64).decode()
            except Exception:
                pass

        # If HTML source, download the .ovpn file
        if self.source == "html" and self._html_sid and server.get("hid"):
            try:
                dl_url = (
                    f"{DOWNLOAD_URL}?sid={self._html_sid}&tcp=1"
                    f"&host={server['hostname']}&port={server['tcp']}"
                    f"&hid={server['hid']}"
                )
                referer = (
                    f"https://www.vpngate.net/en/do_openvpn.aspx?"
                    f"fqdn={server['hostname']}&ip={server['ip']}"
                    f"&tcp={server['tcp']}&udp={server['udp']}"
                    f"&sid={self._html_sid}&hid={server['hid']}"
                )
                req = urllib.request.Request(dl_url)
                req.add_header("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
                req.add_header("Referer", referer)
                resp = self._opener.open(req, timeout=15)
                config = resp.read().decode("utf-8", errors="ignore")
                if "remote" in config and "dev tun" in config:
                    return config
                log.warning(f"Downloaded config for {server['hostname']} is invalid")
            except Exception as e:
                log.warning(f"Config download failed for {server['hostname']}: {e}")

        return None

    # ── Locations ────────────────────────────────────────────────────

    def get_locations(self, country=None):
        if country:
            return [s for s in self.servers
                    if s["country"].upper() == country.upper()]
        seen = set()
        locs = []
        for s in self.servers:
            c = s["country"]
            if c not in seen:
                seen.add(c)
                locs.append({
                    "country": c,
                    "name": s["country_name"],
                    "speed": s.get("speed", 0),
                    "servers": sum(1 for x in self.servers if x["country"] == c),
                })
        return locs

    # ── Connect / Disconnect / Rotate ────────────────────────────────

    async def _try_connect(self, server):
        """Attempt to connect to a single server. Returns True on success."""
        config = self._get_config(server)
        if not config:
            return False

        os.makedirs(CONFIG_DIR, exist_ok=True)
        path = os.path.join(CONFIG_DIR, "current.ovpn")
        with open(path, "w") as f:
            f.write(config)

        self._kill_all_openvpn()

        try:
            subprocess.run(
                ["openvpn", "--config", path, "--daemon",
                 "--writepid", PID_FILE, "--log", "/tmp/openvpn.log"],
                capture_output=True, timeout=5
            )
            for _ in range(30):
                await asyncio.sleep(1)
                if os.path.exists(PID_FILE):
                    with open(PID_FILE) as f:
                        pid = f.read().strip()
                    try:
                        os.kill(int(pid), 0)
                        tun = subprocess.run(
                            ["ip", "-4", "addr", "show", "tun0"],
                            capture_output=True, text=True
                        )
                        if "inet " in tun.stdout:
                            self.connected = True
                            self.current = server
                            log.info(f"Connected to {server['hostname']} ({server['country_name']})")
                            return True
                    except ProcessLookupError:
                        log.warning(f"Server {server['hostname']} rejected connection")
                        break
                    except Exception:
                        pass
            self._kill_openvpn()
            log.warning(f"Timeout connecting to {server['hostname']}")
            return False
        except Exception as e:
            log.warning(f"Failed to start openvpn for {server['hostname']}: {e}")
            return False

    def _kill_openvpn(self):
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE) as f:
                    pid = f.read().strip()
                subprocess.run(["kill", pid], capture_output=True)
            except Exception:
                pass
            os.remove(PID_FILE)

    def _kill_all_openvpn(self):
        """Kill ALL openvpn processes — PID file + pkill safety net."""
        self._kill_openvpn()
        subprocess.run(["pkill", "-9", "openvpn"], capture_output=True)
        time.sleep(1)

    async def connect(self, country=None, idx=None):
        if not self.servers:
            await self.fetch_servers()
        if not self.servers:
            return {"status": "error", "error": "No servers available from any source"}

        if self.connected:
            self._kill_all_openvpn()
            self.connected = False
            self.current = None

        # Build candidate list
        if idx is not None and idx < len(self.servers):
            candidates = [self.servers[idx]]
        elif country:
            candidates = [s for s in self.servers
                          if s["country"].upper() == country.upper()]
            if not candidates:
                candidates = self.servers[:5]
        else:
            candidates = self.servers[:5]

        # Try up to 5 servers
        for server in candidates[:5]:
            if await self._try_connect(server):
                return {
                    "status": "connected",
                    "server": server["hostname"],
                    "ip": server["ip"],
                    "country": server["country_name"],
                    "source": self.source,
                }
            self._kill_openvpn()
            await asyncio.sleep(1)

        return {"status": "failed", "error": "All servers failed (free VPN servers may be overloaded)"}

    def disconnect(self):
        self._kill_all_openvpn()
        self.connected = False
        self.current = None
        return {"status": "disconnected"}

    async def rotate(self, country=None):
        if not self.servers:
            await self.fetch_servers()
        old = self.current["hostname"] if self.current else None
        candidates = ([s for s in self.servers
                       if s["country"].upper() == country.upper()]
                      if country else self.servers)
        candidates = [s for s in candidates if s["hostname"] != old]
        for server in candidates[:10]:
            if await self._try_connect(server):
                return {
                    "status": "connected",
                    "server": server["hostname"],
                    "ip": server["ip"],
                    "country": server["country_name"],
                    "source": self.source,
                }
            self._kill_openvpn()
            await asyncio.sleep(1)
        return {"status": "failed", "error": "All alternative servers failed"}

    def status(self):
        return {
            "connected": self.connected,
            "server": self.current["hostname"] if self.current else None,
            "country": self.current["country_name"] if self.current else None,
            "available": len(self.servers),
            "source": self.source,
        }

    def is_tunnel_alive(self):
        """Check if tun0 interface has an IP (VPN tunnel is up)."""
        if not self.connected:
            return False
        try:
            out = subprocess.run(
                ["ip", "-4", "addr", "show", "tun0"],
                capture_output=True, text=True, timeout=5
            )
            return "inet " in out.stdout
        except Exception:
            return False

    async def watchdog(self, interval=30):
        """Background task: reconnect if VPN tunnel drops."""
        while True:
            await asyncio.sleep(interval)
            if self.connected and not self.is_tunnel_alive():
                log.warning("VPN tunnel dropped — attempting reconnect")
                self.connected = False
                self._kill_all_openvpn()
                result = await self.connect()
                if result.get("status") == "connected":
                    log.info(f"Watchdog reconnected to {result['server']}")
                else:
                    log.error("Watchdog reconnect failed")
