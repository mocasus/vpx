import os, json, subprocess, time, re

CRED_FILE = "/config/credentials.json"
DANTE_CONF = "/config/danted.conf"

class ProxyManager:
    def __init__(self):
        self.creds = {"username": "", "password": ""}
        self.loaded = False

    def load(self):
        if os.path.exists(CRED_FILE):
            with open(CRED_FILE) as f:
                self.creds = json.load(f)
            self.loaded = True

    def info(self):
        return {
            "socks5": ":1080",
            "http": ":8080",
            "username": self.creds.get("username"),
            "password": self.creds.get("password"),
        }

    def set_external(self, iface):
        """Switch dante external to the IP of the given interface.
        Retries up to 5s. If unresolved, keeps existing config."""
        if not os.path.exists(DANTE_CONF):
            return
        ext = None
        for _ in range(5):
            try:
                out = subprocess.check_output(
                    ["ip", "-4", "addr", "show", iface],
                    stderr=subprocess.DEVNULL,
                ).decode()
                m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", out)
                if m:
                    ext = m.group(1)
                    break
            except Exception:
                pass
            time.sleep(1)
        if not ext:
            return  # keep existing config — don't break danted
        with open(DANTE_CONF) as f:
            lines = f.readlines()
        with open(DANTE_CONF, "w") as f:
            for line in lines:
                if line.strip().startswith("external:"):
                    f.write(f"external: {ext}\n")
                else:
                    f.write(line)
        subprocess.run(["pkill", "danted"], capture_output=True)
        time.sleep(2)
