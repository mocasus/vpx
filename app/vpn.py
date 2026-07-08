import os, base64, subprocess, time, httpx

VPNGATE_API = "http://www.vpngate.net/api/iphone/"
CONFIG_DIR = os.environ.get("VPN_CONFIG_DIR", "/config/vpn")
PID_FILE = "/tmp/openvpn.pid"

class VPNManager:
    def __init__(self):
        self.servers = []
        self.current = None
        self.connected = False

    async def fetch_servers(self):
        async with httpx.AsyncClient() as c:
            r = await c.get(VPNGATE_API, timeout=30)
            r.raise_for_status()
        lines = r.text.strip().split("\n")
        headers = None
        servers = []
        for line in lines:
            line = line.strip()
            if not line or line[0] in "*$":
                continue
            if line.startswith("#"):
                headers = line[1:].split(",")
                continue
            parts = line.split(",")
            if len(parts) < 15 or not headers:
                continue
            try:
                s = {}
                for i, h in enumerate(headers):
                    h = h.strip()
                    v = parts[i] if i < len(parts) else ""
                    if h in ("Score", "Ping", "Speed", "NumVpnSessions",
                             "Uptime", "TotalUsers", "TotalTraffic"):
                        v = int(v) if v else 0
                    s[h] = v
                s["hostname"] = s.get("HostName", "")
                s["ip"] = s.get("IP", "")
                s["country"] = s.get("CountryShort", "")
                s["country_name"] = s.get("CountryLong", "")
                s["config_b64"] = s.get("OpenVPN_ConfigData_Base64", "")
                if s["config_b64"] and s["country"]:
                    servers.append(s)
            except:
                continue
        servers.sort(key=lambda x: (-x.get("Speed", 0), x.get("Ping", 999)))
        self.servers = servers
        return servers

    def get_locations(self, country=None):
        if not self.servers:
            return []
        if country:
            return [
                {"hostname": s["hostname"], "ip": s["ip"],
                 "speed": s.get("Speed", 0), "ping": s.get("Ping", 0),
                 "country": s["country_name"]}
                for s in self.servers
                if s["country"].upper() == country.upper()
            ][:20]
        seen = set()
        locs = []
        for s in self.servers:
            c = s["country"]
            if c not in seen:
                seen.add(c)
                locs.append({
                    "country": c, "name": s["country_name"],
                    "speed": s.get("Speed", 0),
                    "servers": sum(1 for x in self.servers if x["country"] == c)
                })
        return locs

    async def connect(self, country=None, idx=None):
        if not self.servers:
            await self.fetch_servers()
        if not self.servers:
            return {"status": "error", "error": "No servers available"}
        if self.connected:
            self.disconnect()
        if idx is not None and idx < len(self.servers):
            server = self.servers[idx]
        elif country:
            cands = [s for s in self.servers
                     if s["country"].upper() == country.upper()]
            server = cands[0] if cands else self.servers[0]
        else:
            server = self.servers[0]
        try:
            cfg = base64.b64decode(server["config_b64"]).decode()
        except:
            return {"status": "error", "error": "Failed to decode config"}
        os.makedirs(CONFIG_DIR, exist_ok=True)
        path = os.path.join(CONFIG_DIR, "current.ovpn")
        with open(path, "w") as f:
            f.write(cfg)
        try:
            subprocess.run(
                ["openvpn", "--config", path, "--daemon",
                 "--writepid", PID_FILE, "--log", "/tmp/openvpn.log"],
                capture_output=True, timeout=5
            )
            for _ in range(10):
                time.sleep(1)
                if os.path.exists(PID_FILE):
                    with open(PID_FILE) as f:
                        pid = f.read().strip()
                    try:
                        os.kill(int(pid), 0)
                        self.connected = True
                        self.current = server
                        return {
                            "status": "connected",
                            "server": server["hostname"],
                            "ip": server["ip"],
                            "country": server["country_name"]
                        }
                    except:
                        pass
            return {"status": "failed", "error": "OpenVPN timeout"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def disconnect(self):
        if os.path.exists(PID_FILE):
            with open(PID_FILE) as f:
                pid = f.read().strip()
            subprocess.run(["kill", pid], capture_output=True)
            os.remove(PID_FILE)
        self.connected = False
        self.current = None
        return {"status": "disconnected"}

    async def rotate(self, country=None):
        if not self.servers:
            await self.fetch_servers()
        old = self.current["hostname"] if self.current else None
        cands = ([s for s in self.servers
                  if s["country"].upper() == country.upper()]
                 if country else self.servers)
        for s in cands:
            if s["hostname"] != old:
                i = self.servers.index(s)
                return await self.connect(idx=i)
        return {"status": "error", "error": "No alternative servers"}

    def status(self):
        return {
            "connected": self.connected,
            "server": self.current["hostname"] if self.current else None,
            "country": self.current["country_name"] if self.current else None,
            "available": len(self.servers)
        }
