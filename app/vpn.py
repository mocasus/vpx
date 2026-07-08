import os, time, json, base64, subprocess, urllib.request

API_URL = "https://www.vpngate.net/api/iphone/"
CONFIG_DIR = "/config/vpn"
PID_FILE = "/tmp/openvpn.pid"

class VPNManager:
    def __init__(self):
        self.servers = []
        self.connected = False
        self.current = None

    async def fetch_servers(self):
        try:
            req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                lines = r.read().decode("utf-8", errors="ignore").splitlines()
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
                    })
            # sort by speed descending
            self.servers.sort(key=lambda s: s.get("speed", 0), reverse=True)
        except Exception:
            pass
        return len(self.servers)

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
                    "country": c, "name": s["country_name"],
                    "speed": s.get("speed", 0),
                    "servers": sum(1 for x in self.servers if x["country"] == c)
                })
        return locs

    def _try_connect(self, server):
        """Attempt to connect to a single server. Returns True on success."""
        try:
            cfg = base64.b64decode(server["config_b64"]).decode()
        except Exception:
            return False
        os.makedirs(CONFIG_DIR, exist_ok=True)
        path = os.path.join(CONFIG_DIR, "current.ovpn")
        with open(path, "w") as f:
            f.write(cfg)
        # clean stale pid
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        try:
            subprocess.run(
                ["openvpn", "--config", path, "--daemon",
                 "--writepid", PID_FILE, "--log", "/tmp/openvpn.log"],
                capture_output=True, timeout=5
            )
            for _ in range(30):
                time.sleep(1)
                if os.path.exists(PID_FILE):
                    with open(PID_FILE) as f:
                        pid = f.read().strip()
                    try:
                        os.kill(int(pid), 0)
                        # Check tun0 has IP (OpenVPN writes PID before tunnel ready)
                        tun = subprocess.run(
                            ["ip", "-4", "addr", "show", "tun0"],
                            capture_output=True, text=True
                        )
                        if "inet " in tun.stdout:
                            self.connected = True
                            self.current = server
                            return True
                    except ProcessLookupError:
                        # OpenVPN died — server rejected
                        break
                    except Exception:
                        pass
            # timeout or dead — kill stale openvpn
            self._kill_openvpn()
            return False
        except Exception:
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

    async def connect(self, country=None, idx=None):
        if not self.servers:
            await self.fetch_servers()
        if not self.servers:
            return {"status": "error", "error": "No servers available"}
        if self.connected:
            self.disconnect()
            time.sleep(2)

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

        # Try up to 3 servers
        for server in candidates[:3]:
            if self._try_connect(server):
                return {
                    "status": "connected",
                    "server": server["hostname"],
                    "ip": server["ip"],
                    "country": server["country_name"]
                }
            # Clean up before retry
            self._kill_openvpn()
            time.sleep(1)

        return {"status": "failed", "error": "All servers failed (free VPN servers may be overloaded)"}

    def disconnect(self):
        self._kill_openvpn()
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
        # filter out current server
        candidates = [s for s in candidates if s["hostname"] != old]
        for server in candidates[:3]:
            if self._try_connect(server):
                return {
                    "status": "connected",
                    "server": server["hostname"],
                    "ip": server["ip"],
                    "country": server["country_name"]
                }
            self._kill_openvpn()
            time.sleep(1)
        return {"status": "failed", "error": "All alternative servers failed"}

    def status(self):
        return {
            "connected": self.connected,
            "server": self.current["hostname"] if self.current else None,
            "country": self.current["country_name"] if self.current else None,
            "available": len(self.servers)
        }
